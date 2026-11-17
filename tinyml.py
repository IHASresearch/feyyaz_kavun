"""C/5 teşhis testinin ilk 1800 saniyesinden SOH regresyonu.

NumPy ile eğitilen küçük MLP, kütüphanesiz float32 C++ olarak dışa aktarılır.
Tam kapasite yalnızca hedef üretiminde kullanılır; girdilere dahil edilmez.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

# Özellik sırası bir sözleşmedir: Python, radyo ve ESP32 aynı sırayı kullanmalıdır.
FEATURES = [f"voltage_{s}s_V" for s in range(0, 1801, 300)] + [
    "mean_current_mA", "mean_temperature_C", "temperature_rise_C"
]


# Tam testten hedef, yalnız ilk 1800 saniyeden giriş üret; her satır bir teşhis testidir.
def build_training_table(datasets, output_dir):
    # Kabul edilen özellikler ve bütün adayların denetim kayıtları ayrı listelerde tutulur.
    records, audit = [], []
    for df in datasets:
        source = df.attrs["source_file"]
        ns = df.Ns.to_numpy()
        # Ns=3 olan her satırı değil, bu koda geçiş yapılan ilk satırları bul.
        starts = np.flatnonzero((ns == 3) & np.r_[True, ns[:-1] != 3])
        # Testin sonu olabilecek dinlenme/yeniden şarj kodlarının satır konumları.
        stops = np.flatnonzero((ns == 8) | (ns == 0))
        for start in starts:
            # Ns=3 görevde dinlenme, referans kapasite testinde düşük akımlı deşarj olabilir.
            # Başlangıç akımı C/5 civarında değilse kapasite testi adayı olarak işleme.
            if not -800 < df.I_mA.iloc[start] < -400:
                continue
            # Yalnız bu başlangıçtan sonra gelen bitişleri dikkate al.
            next_stops = stops[stops > start]
            # İlk bitişe kadar olan aralığı al; bitiş yoksa dosya sonunu incele.
            end = int(next_stops[0]) if len(next_stops) else len(df)
            # iloc bitiş indeksini dahil etmez; Ns=8/0 satırı test bloğunun dışında kalır.
            block = df.iloc[start:end]
            # Büyük deney zamanını test başlangıcına göre sıfırlanmış saniyelere dönüştür.
            t = block.time_s.to_numpy() - block.time_s.iloc[0]
            # Gerilim dizisi, tam deşarj aralığı kontrolü ve erken pencere özellikleri için kullanılır.
            v = block.Ecell_V.to_numpy()
            # Akım işareti deşarjda negatiftir; kapasite integralinde işareti ters çevrilir.
            i = block.I_mA.to_numpy()
            # Cihazın pozitif birikimli deşarj yükü sayacı, mAh.
            q = block.QDischarge_mA_h.to_numpy()
            # Bir adayda birden fazla sorun varsa hepsini kaydet; ilk hatada bilgiyi kaybetme.
            reasons = []
            # Çok kısa veya herhangi bir sayısal alanı sonlu olmayan testleri reddet.
            if len(block) < 10 or not np.isfinite(block.select_dtypes('number')).all().all():
                reasons.append("nonfinite_or_short")
            # Genel altı aralık kontrolünden geçmeyen ölçüm varsa tüm test adayını reddet.
            if not block.is_valid.all():
                reasons.append("outlier")
            # Tekrarlı/geriye giden zamanı ve 60 saniyeden büyük kesintileri yakala.
            if len(t) < 2 or np.any(np.diff(t) <= 0) or np.max(np.diff(t), initial=0) > 60:
                reasons.append("time_discontinuity")
            # Tam şarja yakın başlayıp alt gerilim sınırında bitmeyen aday tam kapasiteyi temsil etmez.
            if v[0] < 4.10 or not 2.40 <= v[-1] <= 2.60:
                reasons.append("incomplete_voltage_span")
            # En az iki saatlik, düşük akımlı ve şarj içermeyen bir test olmasını denetle.
            if t[-1] < 7200 or np.min(i) < -1000 or np.max(i) > 1:
                reasons.append("not_complete_c5_test")
            # Sayaç sıfırlanması veya önceki testten taşan yüksek başlangıç etiket üretimini bozar.
            if np.any(np.diff(q) < -1) or q[0] > 5:
                reasons.append("capacity_counter_discontinuity")
            # İlk sayaç ofsetini çıkararak bu testte çekilen toplam yükü hesapla.
            capacity = float(q[-1] - q[0])
            # Trapez akım integrali: mA·s değerini 3600 ile bölerek mAh elde et.
            integral = float(np.trapezoid(-i, t) / 3600)
            # Sayaç ile integral en fazla %2 veya 20 mAh toleransında uyuşmalıdır.
            if not 500 < capacity < 3300 or abs(integral - capacity) > max(20, .02 * capacity):
                reasons.append("capacity_integral_mismatch")
            # Kabul/ret kararını kaynak satırlarla sakla; test seçimi sonradan incelenebilir olur.
            audit.append(dict(source_file=source, start_row=int(start), end_row=end-1,
                              capacity_mAh=capacity, integrated_mAh=integral,
                              accepted=not reasons, rejection=";".join(reasons)))
            # Bir kontrol bile başarısızsa bu adayı eğitim tablosuna dahil etme.
            if reasons:
                continue
            # Girdiler yalnız ilk 1800 saniyeden gelir; uç noktayı interpolasyonla tamamla.
            # Pencereyi tam 1800 saniyede kapat; son ölçüm çakışmıyorsa interpolasyon kullan.
            times = np.r_[t[t < 1800], 1800.0]
            temp = block.Temperature__C.to_numpy()
            # 0,300,...,1800 saniyelerindeki yedi gerilimi yerel doğrusal interpolasyonla örnekle.
            features = list(np.interp(np.arange(0, 1801, 300), t, v))
            # Akım/sıcaklık ortalamaları zaman ağırlıklıdır; son özellik başlangıca göre sıcaklık artışıdır.
            features += [np.trapezoid(np.interp(times, t, i), times)/1800,
                         np.trapezoid(np.interp(times, t, temp), times)/1800,
                         np.interp(1800, t, temp)-temp[0]]
            # Tam kapasiteyi metadata/hedef için sakla; model girdisi yalnız FEATURES sütunlarıdır.
            records.append(dict(source_file=source, start_s=float(block.time_s.iloc[0]),
                                capacity_mAh=capacity, **dict(zip(FEATURES, features))))
    # Kabul edilen her kapasite testini bir eğitim örneğine dönüştür.
    table = pd.DataFrame(records)
    if table.empty:
        raise ValueError("Geçerli kapasite testi bulunamadı")
    # Referans, nominal kapasite değil aynı hücrenin ilk kabul edilen tam testidir.
    # Her hücrenin ilk kabul edilen test kapasitesini aynı hücrenin bütün satırlarına yay.
    table["reference_capacity_mAh"] = table.groupby("source_file")["capacity_mAh"].transform("first")
    # Kapasiteye dayalı SOH: mevcut kapasite / başlangıç referansı × 100.
    table["soh_percent"] = 100 * table.capacity_mAh / table.reference_capacity_mAh
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_dir / "training_table.csv", index=False)
    pd.DataFrame(audit).to_csv(output_dir / "capacity_test_audit.csv", index=False)
    return table


# Bir veya çok örneğin ileri yayılımı; ara aktivasyonlar geri yayılımda da kullanılır.
def forward(x, weights):
    # Parametre listesi her katmanda ağırlık matrisi ve bias vektörü sırasıyla tutulur.
    w1,b1,w2,b2,w3,b3 = weights
    # @ matris çarpımıdır; bias her örneğe yayılır, ReLU negatif aktivasyonları sıfırlar.
    h1 = np.maximum(x @ w1+b1, 0)
    # İlk gizli katmandan sekiz nöronlu ikinci gizli katmana geç.
    h2 = np.maximum(h1 @ w2+b2, 0)
    # Doğrusal çıkışı tek boyutlu vektör yap; SOH yüzdesine çarpma çağıran tarafta yapılır.
    return (h2 @ w3+b3).ravel(), h1, h2


# Hataları SOH yüzde puanı olarak döndür; yüzde göreli hata hesaplanmaz.
def metrics(y, pred):
    # MAE mutlak hatayı, RMSE büyük hataları, max_error en kötü örneği özetler.
    return dict(mae_pp=float(np.mean(abs(y-pred))),
                rmse_pp=float(np.sqrt(np.mean((y-pred)**2))),
                max_error_pp=float(np.max(abs(y-pred))))


# Hücre ayrımı, ölçekleme, MLP eğitimi, değerlendirme ve C++ üretimi ana fonksiyonu.
def train_and_export(table, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Sabit tohumla hücre karıştırma ve ağırlık başlangıcını yeniden üretilebilir tut.
    rng = np.random.default_rng(42)
    # Hücre adlarını tekilleştir ve sırala; satır sayısından bağımsız hücre ayrımı yap.
    cells = np.array(sorted(table.source_file.unique()))
    # Az hücre varsa ayrılmış test/doğrulama değerlendirmesini erken durdur.
    if len(cells) < 10:
        raise ValueError("Güvenilir hücre ayrımı için en az 10 hücre gerekli")
    # Hücre kimliklerini karıştır; aynı hücrenin örnekleri bölünmez.
    shuffled = rng.permutation(cells)
    # İlk beş hücre test, sonraki dört doğrulama, kalanlar eğitim grubudur.
    groups = dict(test=list(shuffled[:5]), validation=list(shuffled[5:9]), train=list(shuffled[9:]))
    # Her tablo satırını ait olduğu hücre grubuyla eşleştiren boolean diziler.
    masks = {k: table.source_file.isin(v).to_numpy() for k,v in groups.items()}
    # Sadece on özellik sütununu float64 matrise al; kimlik/kapasite gibi metadata girdi olmaz.
    x = table[FEATURES].to_numpy(dtype=np.float64)
    # Gerçek SOH yüzdesini hedef vektör olarak al.
    y = table.soh_percent.to_numpy(dtype=np.float64)
    # Veri sızıntısını önlemek için ölçekleme istatistiklerini yalnız eğitimden öğren.
    mean, std = x[masks['train']].mean(0), x[masks['train']].std(0)
    # Sabit veya çok az değişen özelliklerde sıfıra bölmeyi önle.
    std = np.maximum(std, 1e-6)
    # Eğitimden öğrenilen aynı dönüşümü bütün gruplara uygula.
    x = (x-mean)/std
    # Hedefi yaklaşık 0..1 ölçeğine al; değerlendirmede tahminleri aralığa kırpma.
    # Eğitim hedefini yaklaşık 0..1 ölçeğine getir; değerlendirmede tekrar yüzdeye çevir.
    target = y/100
    weights = []
    # 10→16→8→1 ağı için her katmanın ağırlık/bias çiftini oluştur.
    for ins,outs in [(10,16),(16,8),(8,1)]:
        # ReLU ile uyumlu giriş boyutuna bağlı rastgele ağırlıklar; bias başlangıçta sıfırdır.
        weights.extend([rng.normal(0, np.sqrt(2/ins), (ins,outs)), np.zeros(outs)])
    # Adam için her parametrenin birinci moment (ortalama gradyan) belleği.
    moments = [np.zeros_like(w) for w in weights]
    # Adam için ikinci moment (gradyan kareleri) belleği.
    variances = [np.zeros_like(w) for w in weights]
    # En iyi doğrulama hatası, kopya ağırlıklar, sabır sayacı ve Adam adımı.
    best_loss, best, stale, step = np.inf, None, 0, 0
    history = []
    # Hücre sayısına ters ağırlık ver; mini-batch içinde normalize ederek uzun kayıtların etkisini azalt.
    # Daha çok test içeren hücrelerin eğitimde baskınlığını azaltmak için hücre başına say.
    counts = table.loc[masks['train']].groupby('source_file').size()
    # Örnek ağırlığı hücrenin örnek sayısının tersidir; yalnız eğitim indekslerinde kullanılır.
    sample_weights = table.source_file.map(1/counts).to_numpy()
    # Üst sınır 3000; erken durdurma daha önce sonlandırabilir.
    for epoch in range(1, 3001):
        # Her epoch eğitim örneklerinin sırasını karıştır; doğrulama/test ağırlık güncellemez.
        indices = rng.permutation(np.flatnonzero(masks['train']))
        # Eğitim indekslerini yaklaşık en fazla 32 örnekli mini-batch parçalarına böl.
        for batch in np.array_split(indices, max(1, int(np.ceil(len(indices)/32)))):
            # Bu mini-batch için standartlaştırılmış girdiler ve 0..1 hedefler.
            xb, yb = x[batch], target[batch]
            # Çıkış ve iki gizli aktivasyonu birlikte hesapla; türevlerde tekrar kullanılacak.
            pred,h1,h2 = forward(xb, weights)
            # Bu mini-batch içindeki hücre dengeleme ağırlıklarını toplamları bir olacak şekilde normalize et.
            sw = sample_weights[batch]; sw = sw/sw.sum()
            # Ağırlıklı karesel kaybın çıkışa türevi; [:,None] sütun vektörü oluşturur.
            d = (2*(pred-yb)*sw)[:,None]
            # Parametre listesi her katmanda ağırlık matrisi ve bias vektörü sırasıyla tutulur.
            w1,b1,w2,b2,w3,b3 = weights
            # Zincir kuralıyla ikinci gizli katmana hatayı taşı; ReLU türevi pozitiflerde birdir.
            d2 = (d @ w3.T)*(h2>0)
            # Hata gradyanını ilk gizli katmana taşı.
            d1 = (d2 @ w2.T)*(h1>0)
            # Her katmanda ağırlık türevi girişᵀ×hata, bias türevi örnekler boyunca hata toplamıdır.
            grads = [xb.T@d1,d1.sum(0),h1.T@d2,d2.sum(0),h2.T@d,d.sum(0)]
            # Adam bias düzeltmesi için epoch değil mini-batch güncelleme sayısını tut.
            step += 1
            # Her ağırlık ve bias dizisini aynı Adam formülüyle güncelle.
            for j,g in enumerate(grads):
                # Çift indeksler ağırlık matrisidir; bias vektörlerine L2 uygulanmaz.
                if j % 2 == 0:
                    # Ağırlık büyümesini sınırlayan 10⁻⁴ katsayılı L2 gradyan katkısı.
                    g = g + 1e-4*weights[j]
                # Gradyanın üstel hareketli ortalaması, beta1=0.9.
                moments[j] = .9*moments[j]+.1*g
                # Gradyan karesinin üstel ortalaması, beta2=0.999.
                variances[j] = .999*variances[j]+.001*g*g
                # Bias-düzeltilmiş Adam güncellemesi; öğrenme oranı 0.001, epsilon 1e-8.
                weights[j] -= .001*(moments[j]/(1-.9**step))/(np.sqrt(variances[j]/(1-.999**step))+1e-8)
        # Güncellenmiş ağı doğrulamada değerlendir ve SOH yüzde ölçeğine dön.
        val_pred = forward(x[masks['validation']],weights)[0]*100
        # Epoch seçimi için doğrulama ortalama karesel hatası; test kümesine bakılmaz.
        val_loss = float(np.mean((val_pred-y[masks['validation']])**2))
        # Grafik ve sonradan inceleme için eğitim/doğrulama RMSE geçmişini sakla.
        history.append(dict(epoch=epoch, validation_rmse_pp=np.sqrt(val_loss),
                            train_rmse_pp=metrics(y[masks['train']],forward(x[masks['train']],weights)[0]*100)['rmse_pp']))
        # Yeterli iyileşme varsa en iyi ağırlıkları bağımsız kopya olarak sakla.
        if val_loss < best_loss-1e-5:
            # En iyi doğrulama hatası, kopya ağırlıklar, sabır sayacı ve Adam adımı.
            best_loss, best, stale = val_loss, [w.copy() for w in weights], 0
            best_epoch = epoch
        else:
            # İyileşmeyen ardışık epoch sayısını artır.
            stale += 1
        # 250 epoch boyunca iyileşme yoksa aşırı eğitimi ve gereksiz hesabı sınırla.
        if stale >= 250:
            break
    # Son epoch yerine doğrulamada en iyi ağırlıkları seç; ESP32 gösterimi float32 olur.
    weights = [w.astype(np.float32) for w in best]
    # Ölçekleme sabitlerini de kartta kullanılan float32 türüne çevir.
    mean,std = mean.astype(np.float32),std.astype(np.float32)
    # Değerlendirmeyi gömülü giriş hassasiyetiyle yapabilmek için float32 girdiler.
    raw = table[FEATURES].to_numpy(dtype=np.float32)
    # Bütün kümelerin tahminlerini aynı son modelle hesapla.
    preds = forward((raw-mean)/std,weights)[0]*100
    # Mimari, bellek, epoch ve ayrım bilgilerini ölçümlerle birlikte belgeleyen sözlük.
    report = dict(architecture=[10,16,8,1], parameters=sum(w.size for w in weights),
                  weight_bytes=sum(w.nbytes for w in weights), preprocessing_bytes=mean.nbytes+std.nbytes,
                  best_epoch=best_epoch, epochs_run=epoch, split_cells=groups,
                  features=FEATURES, window_seconds=1800,
                  test_used_for_selection=False, board_tested=False)
    # Karşılaştırma için eğitim hedeflerinin ortalamasını sabit tahmin olarak kullan.
    baseline = float(y[masks['train']].mean())
    # Her küme için hata ve sabit tahmin referansı; eğitim/doğrulama/test ayrı tutulur.
    report['metrics'] = {k: dict(rows=int(m.sum()), **metrics(y[m],preds[m]),
                                 baseline_mae_pp=float(np.mean(abs(y[m]-baseline)))) for k,m in masks.items()}
    # Gerçek hedeflerin yanına tahminleri ekle; kaynak eğitim tablosunu değiştirme.
    out = table.copy(); out['predicted_soh_percent']=preds
    out['split']=''
    # CSV içinde her örneğin hangi gruba ait olduğunu belirt.
    for k,m in masks.items(): out.loc[m,'split']=k
    out.to_csv(output_dir/'predictions.csv',index=False)
    per_cell = []
    # Toplam hatanın gizleyebileceği hücre farklılıklarını ayrı raporla.
    for cell,g in out.groupby('source_file'):
        per_cell.append(dict(source_file=cell, split=g.split.iloc[0], rows=len(g),
                             **metrics(g.soh_percent.to_numpy(),g.predicted_soh_percent.to_numpy())))
    pd.DataFrame(per_cell).to_csv(output_dir/'per_cell_metrics.csv',index=False)
    pd.DataFrame(history).to_csv(output_dir/'history.csv',index=False)
    # Parametre ve ölçekleme dizilerini kayıpsız sayısal arşive yaz.
    np.savez(output_dir/'model.npz',mean=mean,std=std,**{f'p{j}':w for j,w in enumerate(weights)})
    # İlk test örneğiyle kart self-check referansı ve model başlığını üret.
    export_header(output_dir, weights, mean, std, raw[masks['test']][0], float(preds[masks['test']][0]))
    report['test_soh_range'] = [float(y[masks['test']].min()),float(y[masks['test']].max())]
    (output_dir/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    plot_results(out,history,output_dir)
    print(json.dumps(report,indent=2))
    return report


# Ağırlıkları düz dizilere, ileri yayılımı kütüphanesiz C++ fonksiyonuna dönüştür.
def export_header(output_dir, weights, mean, std, example, expected):
    firmware = Path(__file__).resolve().parent/'esp32'/'soh_demo'
    firmware.mkdir(parents=True,exist_ok=True)
    lines = ['// Otomatik üretilir: tinyml.export_header. Parametreleri elle değiştirmeyin.', '#pragma once', '#include <math.h>', '// Özellik sırası: '+', '.join(FEATURES)]
    # Katman sırasını C++ içindeki W1/SOH_B1/W2/B2/W3/B3 adlarıyla eşleştir.
    arrays = dict(zip(['W1','SOH_B1','W2','B2','W3','B3'],weights))
    # Eğitim ortalaması/std ve demo test vektörünü aynı başlığa koy.
    arrays.update(MEAN=mean,STD=std,EXAMPLE=example)
    # Her parametre dizisini satır öncelikli düzleştirerek C dizisi olarak yaz.
    # Üretilmiş parametre dizilerinin fiziksel/matematiksel rollerini de başlığa yaz.
    array_notes = {'W1': '10 giriş × 16 nöron; W1[i*16+j] bağlantısı, satır öncelikli düz dizi.', 'SOH_B1': 'İlk gizli katmanın 16 bias değeri.', 'W2': '16 aktivasyon × 8 nöron; W2[i*8+j] bağlantısı.', 'B2': 'İkinci gizli katmanın sekiz bias değeri.', 'W3': 'Sekiz aktivasyondan tek doğrusal çıkışa bağlantılar.', 'B3': 'Tek çıkış nöronunun bias değeri.', 'MEAN': 'Yalnız eğitim hücrelerinden hesaplanan on özellik ortalaması.', 'STD': 'Yalnız eğitim hücrelerinden hesaplanan standart sapmalar.', 'EXAMPLE': 'Kart self-check için ayrılmış test vektörü; özellik sırası yukarıdadır.'}
    for name,a in arrays.items():
        # Dokuz ondalıklı bilimsel gösterim ve f soneki float32 değerleri korumayı hedefler.
        values = ','.join(f'{float(v):.9e}f' for v in a.ravel())
        lines.append('// '+array_notes[name])
        lines.append(f'static const float {name}[{a.size}] = {{{values}}};')
    lines.append('// EXAMPLE için bilgisayarda hesaplanan referans SOH yüzdesi; model girdisi değildir.')
    lines.append(f'static const float EXPECTED_SOH = {expected:.9e}f;')
    lines.append('''
// Geçersiz girdide NAN döndürür; aralık dışı tahminleri gizlemek için çıktı kırpılmaz.
// On fiziksel özellikten SOH yüzdesi hesaplar; eğitim veya ağırlık güncelleme yapmaz.
inline float predict_soh(const float* features) {
  // Standartlaştırılmış giriş, 16 ve 8 nöronlu ara aktivasyonlar yığında tutulur.
  float x[10], a[16], b[8];
  // Özellik sırası: yedi gerilim, ortalama akım, ortalama sıcaklık, sıcaklık artışı.
  for(int i=0;i<10;++i) {
    // NaN/sonsuz girdi varsa güvenilir tahmin üretilemez; NAN ile hatayı bildir.
    if(!isfinite(features[i])) return NAN;
    // Eğitim hücrelerinden öğrenilen ortalama ve standart sapmayla aynı ölçeklemeyi uygula.
    x[i]=(features[i]-MEAN[i])/STD[i];
  }
  // İlk gizli katmanın 16 nöronunu hesapla; her nöron on girdiyi kullanır.
  for(int j=0;j<16;++j) {
    // Bias ile başla, giriş×ağırlık katkılarını ekle; W1 satır öncelikli düz dizidir.
    float s=SOH_B1[j]; for(int i=0;i<10;++i) s+=x[i]*W1[i*16+j];
    // ReLU: negatif toplamı sıfıra eşle, pozitif toplamı koru.
    a[j]=fmaxf(0,s);
  }
  // İkinci gizli katmanın sekiz nöronunu ilk katmanın 16 aktivasyonundan hesapla.
  for(int j=0;j<8;++j) {
    // W2[i*8+j] i. girişten j. nörona bağlantıyı temsil eder.
    float s=B2[j]; for(int i=0;i<16;++i) s+=a[i]*W2[i*8+j];
    // İkinci katmanda da ReLU uygula; bu ağa doğrusal olmayan temsil kazandırır.
    b[j]=fmaxf(0,s);
  }
  // Son katman doğrusal: sekiz aktivasyonu tek çıkışta bias ile topla.
  float s=B3[0]; for(int i=0;i<8;++i) s+=b[i]*W3[i];
  // Eğitimde 100’e bölünen hedefi SOH yüzdesine geri çevir; çıktıyı zorla 0..100 yapma.
  return s*100.0f;
}
''')
    (firmware/'soh_model.h').write_text('\n'.join(lines),encoding='utf-8')
    # C döngüsünün toplama sırasını taklit eden bağımsız float32 karşılaştırması.
    # C++ döngüsündeki çarp/topla sırasını taklit eden bağımsız float32 karşılaştırması.
    def sequential(f):
        # Karttaki giriş standardizasyonuyla aynı dönüşüm.
        a=(f-mean)/std
        # Listenin çift indekslerindeki ağırlıklarla tek indekslerindeki biasları eşleştir.
        for w,b in zip(weights[::2],weights[1::2]):
            # Her nöronun toplamına bias ile başla.
            z=b.copy()
            # Her giriş katkısını float32 olarak sırayla ekle; matris kütüphanesiyle toplama sırası değişebilir.
            for i in range(w.shape[0]): z=np.float32(z+np.float32(a[i]*w[i]))
            # Son katman hariç ReLU uygula; tek çıkışlı son katman doğrusaldır.
            a=np.maximum(z,0) if w.shape[1]!=1 else z
        return float(a[0]*np.float32(100))
    # Karttaki self-check için tek bir referans vektör ve beklenen sonuç gömülür.
    # Tek referans örneğinin iki hesap yöntemi arasındaki mutlak SOH farkı.
    diff=abs(sequential(example)-expected)
    # 0.01 yüzde puanından büyük dışa aktarım farkında sessizce devam etme.
    if diff > .01:
        raise AssertionError(f'Export mismatch: {diff}')
    (output_dir/'export_check.json').write_text(json.dumps(dict(
        example_expected_soh=expected, sequential_float32_soh=sequential(example),
        absolute_difference_pp=diff, compiled_cpp_verified=False)),encoding='utf-8')


# Ayrılmış test hücreleri, hata histogramı ve öğrenme eğrisini PNG olarak kaydet.
def plot_results(out,history,output_dir):
    import matplotlib
    # Grafik arayüzü açmadan dosya üret; otomatik çalıştırmaya uygundur.
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # Gerçek–tahmin grafiğine yalnız eğitimde görülmeyen hücreleri al.
    test=out[out.split=='test']
    # Üç panel: gerçek/tahmin, hata dağılımı, epoch boyunca RMSE.
    fig,axes=plt.subplots(1,3,figsize=(16,4.5))
    # Toplam hatanın gizleyebileceği hücre farklılıklarını ayrı raporla.
    for cell,g in test.groupby('source_file'):
        axes[0].scatter(g.soh_percent,g.predicted_soh_percent,s=16,label=cell)
    lo=min(test.soh_percent.min(),test.predicted_soh_percent.min())-2
    hi=max(test.soh_percent.max(),test.predicted_soh_percent.max())+2
    # Kesikli diyagonal ideal tahmini temsil eder.
    axes[0].plot([lo,hi],[lo,hi],'k--'); axes[0].set(xlabel='Measured SOH (%)',ylabel='Predicted SOH (%)',title='Held-out cells')
    axes[0].legend(fontsize=7)
    # İşaretli hata = tahmin − gerçek; negatif değer düşük tahmindir.
    axes[1].hist(test.predicted_soh_percent-test.soh_percent,bins=20)
    axes[1].set(xlabel='Error (percentage points)',ylabel='Tests',title='Test errors')
    h=pd.DataFrame(history)
    # Eğitim ve doğrulama eğrileri genelleme farkını görünür kılar.
    axes[2].plot(h.epoch,h.train_rmse_pp,label='Train')
    axes[2].plot(h.epoch,h.validation_rmse_pp,label='Validation')
    axes[2].set(xlabel='Epoch',ylabel='RMSE (percentage points)',title='Learning curve'); axes[2].legend()
    # Etiket çakışmalarını azalt, dosyayı kaydet ve grafik belleğini serbest bırak.
    fig.tight_layout(); fig.savefig(output_dir/'results.png',dpi=160); plt.close(fig)
