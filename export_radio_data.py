"""Yalnız ayrılmış test örneklerini, NRF24 paketine uygun sabit dizilere aktar.

Gerçek etiketler sadece alıcı değerlendirmesinde kullanılır. Model yeniden
eğitilmez; var olan NPZ ağırlıklarıyla paket yuvarlamasının etkisi ölçülür.
Üretilen başlıkları elle düzenlemek yerine bu dosyayı yeniden çalıştırın.
"""
# Model başlığından kısa sürüm kimliği hesaplamak için SHA-256.
import hashlib
import json
from pathlib import Path
import shutil
# Python ile C++ arasında açık boyutlu ve little-endian bayt düzeni kurar.
import struct

import numpy as np
import pandas as pd

from tinyml import FEATURES, forward, metrics

# Kaynak dosyanın klasörü; verileri terminalin konumundan bağımsız bul.
ROOT=Path(__file__).resolve().parent
# Yedi gerilim 0.1 mV, akım 0.1 mA, sıcaklıklar 0.01 °C çözünürlükle taşınır.
SCALES=np.array([10000]*7+[10,100,100],dtype=np.float32)
# Gerilimden 3.5 V çıkarılması int16 aralığını daha verimli kullanır.
OFFSETS=np.array([3.5]*7+[0,0,0],dtype=np.float32)


# CRC16-CCITT-FALSE: başlangıç 0xFFFF, polinom 0x1021; şifreleme değildir.
def crc16(data):
    # 16 bit CRC yazmacını standart başlangıç değeriyle doldur.
    crc=0xFFFF
    for byte in data:
        # Yeni baytı CRC yazmacının üst sekiz bitine XOR ile kat.
        crc ^= byte<<8
        # Her baytın sekiz biti için polinom bölme adımını uygula.
        for _ in range(8):
            # Üst bit set ise 0x1021 ile XOR yap; maske Python tamsayısını 16 bit içinde tutar.
            crc=((crc<<1)^0x1021 if crc&0x8000 else crc<<1)&0xFFFF
    return crc


# 30 bayt başlık+özellik alanına iki bayt CRC ekleyerek 32 bayt paket döndür.
def encode(model_id,session,seq,q):
    # < little-endian; B byte, H uint16, I uint32, 10h on signed int16 alanıdır.
    body=struct.pack('<BBHIH10h',0xA7,1,model_id,session,seq,*q)
    return body+struct.pack('<H',crc16(body))


# Sadece ayrılmış test hücrelerini verici dizisine ve alıcı değerlendirme tablolarına aktar.
def export_radio_data():
    # Önceki eğitim çalıştırmasının tahmin tablosunu oku; burada eğitim yapılmaz.
    table=pd.read_csv(ROOT/'artifacts/predictions.csv')
    # Eğitim ve doğrulama örneklerini çıkar; yeni indeks paket sıra numarası olacaktır.
    test=table.loc[table.split=='test'].reset_index(drop=True)
    # Boş veya 16 bit örnek indeksine sığmayan veri kümesini reddet.
    if test.empty or len(test)>65535:
        raise ValueError('Test sample count must be 1..65535')
    # Test dışı hücreleri çıkararak gruplar arası ortak kimlik olmadığını denetle.
    others=set(table.loc[table.split!='test','source_file'])
    # Hücre bazında sızıntı varsa dışa aktarımı durdur.
    assert not set(test.source_file)&others
    # Test hücrelerini eğitim raporundaki kayıtla da karşılaştır.
    config=json.loads((ROOT/'artifacts/metrics.json').read_text())
    assert set(test.source_file)==set(config['split_cells']['test'])
    # Sütunları modelin beklediği sırayla al; gerçek SOH hiçbir paketin giriş alanına girmez.
    raw=test[FEATURES].to_numpy(np.float32)
    # Ofset/ölçek sonrası en yakın tamsayıya yuvarla; bu işlem küçük nicemleme hatası oluşturur.
    q=np.rint((raw-OFFSETS)*SCALES)
    # int16 türüne çevirmeden taşma ve sonlu olmama durumlarını yakala.
    assert np.isfinite(q).all() and (q>=-32768).all() and (q<=32767).all()
    # Kodlanan tamsayıları geri fiziksel birime çevir; model paket sonrası değerlere göre de sınanır.
    q=q.astype(np.int16); restored=q.astype(np.float32)/SCALES+OFFSETS
    # Alıcının aralık kontrollerinin bütün üretilen örnekleri kabul edeceğini doğrula.
    assert ((restored[:,:7]>=2.4)&(restored[:,:7]<=4.25)).all()
    # İlk gerilim tam şarj başlangıcına yakın olmalıdır.
    assert (restored[:,0]>=4.1).all()
    # Alıcının aralık kontrollerinin bütün üretilen örnekleri kabul edeceğini doğrula.
    assert ((restored[:,7]>=-800)&(restored[:,7]<=-400)).all()
    # Alıcının aralık kontrollerinin bütün üretilen örnekleri kabul edeceğini doğrula.
    assert ((restored[:,8]>=10)&(restored[:,8]<=75)).all()
    # Alıcının aralık kontrollerinin bütün üretilen örnekleri kabul edeceğini doğrula.
    assert ((restored[:,9]>=-30)&(restored[:,9]<=50)).all()
    # Eğitilmiş float32 ağırlıkları yükle; model yeniden öğrenilmez.
    model=np.load(ROOT/'artifacts/model.npz'); weights=[model[f'p{i}'] for i in range(6)]
    # Yuvarlanmış girdilerle bilgisayardaki referans SOH tahminlerini hesapla.
    preds=forward((restored-model['mean'])/model['std'],weights)[0]*100
    # NPZ ile model başlığının tek bir referans vektöründeki tahminini karşılaştır.
    import re
    # Kartta kullanılacak model başlığını oku; NPZ ile referans eşleşmesi kontrol edilir.
    header=(ROOT/'esp32/soh_demo/soh_model.h').read_text()
    # Başlıktaki EXAMPLE dizisini sayısal test vektörü olarak çöz.
    example=np.array([float(s.rstrip('f')) for s in re.search(r'EXAMPLE\[10\] = \{([^}]+)',header)[1].split(',')],np.float32)
    # Başlığa gömülü beklenen demo SOH değerini al.
    expected=float(re.search(r'EXPECTED_SOH = ([^;]+)',header)[1].rstrip('f'))
    # Yanlış/stale model dosyasının taşınmasını tek referans vektörüyle kontrol et.
    assert abs(forward(((example-model['mean'])/model['std'])[None,:],weights)[0][0]*100-expected)<.001
    # Başlık özetinin ilk iki baytını kısa kimlik yap; yorum değişikliği de kimliği değiştirebilir.
    model_id=int.from_bytes(hashlib.sha256(header.encode()).digest()[:2],'little')
    tx=ROOT/'esp32/soh_transmitter';rx=ROOT/'esp32/soh_receiver'
    # Ortak protokolün iki sketch klasöründeki kopyalarını aynı kaynaktan güncelle.
    for folder in [tx,rx]:
        folder.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'esp32/radio_common.h',folder/'radio_common.h')
    # Açıklamalar da şablonda bulunur; yeniden üretimde başlıklardan kaybolmaz.
    common=(
        '// Otomatik üretilir: export_radio_data.py. Dizileri elle değiştirmeyin.\n'
        '#pragma once\n'
        '// Açık boyutlu tamsayılar iki ESP32 arasında aynı bayt düzenini sağlar.\n'
        '#include <stdint.h>\n'
        '// Model başlığının kısa sürüm kimliği; iki kartta aynı olmalıdır.\n'
        f'static const uint16_t MODEL_ID={model_id};\n'
        '// Sıra numarası 0 ile bu sayının bir eksiği arasındadır.\n'
        f'static const uint16_t TEST_SAMPLE_COUNT={len(test)};\n'
    )
    # Her satırı sabit on int16 özellik içeren C++ dizi satırı olarak biçimlendir.
    rows=',\n'.join(
        f'  // Örnek {seq}: kaynak hücre {test.source_file.iloc[seq]}; ayrıntı radio_test_manifest.csv içinde.\n'
        '  {'+','.join(str(int(v)) for v in row)+'}' for seq,row in enumerate(q)
    )
    # Gerçek SOH gönderilmez. İlk yedi sütun gerilim, son üçü akım/sıcaklık özellikleridir.
    sample_notes=(
        '// Her satır tek ham ölçüm değil, ilk 1800 saniyeden çıkarılmış on özelliktir.\n'
        '// Sütun 0..6: (V-3.5)*10000; sütun 7: ortalama mA*10.\n'
        '// Sütun 8: ortalama sıcaklık*100; sütun 9: sıcaklık artışı*100.\n'
        '// Bu dizi yalnız eğitimde/doğrulamada görülmeyen hücrelerden oluşur.\n'
    )
    (tx/'test_samples.h').write_text(common+sample_notes+f'static const int16_t TEST_SAMPLES[{len(test)}][10]={{\n{rows}\n}};\n',encoding='utf-8')
    ref=common
    # Gerçek etiket ve bilgisayar tahmini alıcıda değerlendirme içindir, model girdisi değildir.
    for name,values in [('TRUE_SOH',test.soh_percent),('EXPECTED_QUANTIZED_SOH',preds)]:
        # İki referansın rolleri farklıdır: biri ölçülmüş hedef, diğeri bilgisayar çıkarımıdır.
        ref+=('// Tam kapasite testinden hesaplanan gerçek SOH; yalnız hata ölçümünde kullanılır.\n'
              if name=='TRUE_SOH' else
              '// Paket yuvarlaması sonrası bilgisayarda beklenen tahmin; kartla sayısal eşleşme içindir.\n')
        ref+=f'static const float {name}[{len(test)}]={{'+','.join(f'{float(v):.9e}f' for v in values)+'};\n'
    (rx/'test_reference.h').write_text(ref,encoding='utf-8')
    shutil.copyfile(ROOT/'esp32/soh_demo/soh_model.h',rx/'soh_model.h')
    # Paket sıra numarasını özgün hücre ve test zamanı ile eşleştiren CSV hazırla.
    manifest=test[['source_file','start_s','soh_percent','predicted_soh_percent']].copy()
    manifest.insert(0,'sequence',range(len(test)))
    manifest['radio_predicted_soh_percent']=preds
    manifest.to_csv(ROOT/'artifacts/radio_test_manifest.csv',index=False)
    # Bütün test paketlerinde boyut, CRC ve tamsayıların kayıpsız geri çözümünü kontrol et.
    for seq,row in enumerate(q):
        packet=encode(model_id,123456,seq,row)
        assert len(packet)==32 and crc16(packet[:30])==struct.unpack('<H',packet[30:])[0]
        # Paketin alanlarını aynı açık bayt düzeniyle tekrar oku.
        unpacked=struct.unpack('<BBHIH10hH',packet)
        assert unpacked[4]==seq and np.array_equal(unpacked[5:15],row)
    # Temsili paketteki her tek-bit bozulmasının CRC ile yakalandığını doğrula.
    packet=encode(model_id,123456,0,q[0])
    # Temsili paketin her bitini ayrı bozarak 256 tek-bit CRC testi yap.
    for bit in range(256):
        # Orijinal paketi değiştirmeden yalnız seçilen biti ters çevir.
        bad=bytearray(packet);bad[bit//8]^=1<<(bit%8)
        assert crc16(bad[:30])!=struct.unpack('<H',bad[30:])[0]
    # Sıkıştırmanın tahmine etkisini ve yapılan/yapılmayan doğrulamaları raporla.
    result=dict(samples=len(test),cells=sorted(test.source_file.unique()),model_id=model_id,
                payload_bytes=32,interval_ms=1000,
                max_feature_quantization_error=np.max(abs(restored-raw),axis=0).tolist(),
                max_prediction_change_pp=float(np.max(abs(preds-test.predicted_soh_percent))),
                quantized_test_metrics=metrics(test.soh_percent.to_numpy(),preds),
                protocol_roundtrips_passed=len(test),single_bit_corruptions_rejected=256,
                firmware_compiled=False,hardware_tested=False)
    (ROOT/'artifacts/radio_export_report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    return result


# Dosya komut satırından çalıştırıldığında dışa aktar; import edilirken çalıştırma.
if __name__=='__main__':
    export_radio_data()
