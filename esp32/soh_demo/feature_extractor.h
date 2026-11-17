// Başlığın tek derleme biriminde tekrar tanımlanmasını önle.
#pragma once
// Sonluluk, mutlak değer ve pencere sonu sınırlandırması için sayısal fonksiyonlar.
#include <math.h>

// Ölçümleri C/5 deşarjın başladığı andan itibaren ver; önceki şarj/dinlenmeyi dahil etme.
// Deşarj akımı negatiftir. Birimler sırasıyla saniye, V, mA ve °C.
// Ham ölçüm geçmişi tutulmaz; her yeni teşhis testinden önce reset() çağır.
// Canlı ölçümlerden ilk 1800 saniyenin on özelliğini geçmişi saklamadan çıkarır.
struct SohWindow {
  // Sıra: 0..6 gerilim; 7 ortalama akım; 8 ortalama sıcaklık; 9 sıcaklık artışı.
  float features[10] = {};
  // started ilk örnek alındı, ready 30 dakika doldu, failed pencere geçersiz demektir.
  bool started=false, ready=false, failed=false;
  // Bir önceki örnek, doğrusal interpolasyon ve trapez integral için yeterlidir.
  float previousTime=0, previousV=0, previousI=0, previousT=0;
  // Başlangıç sıcaklığı ve zaman ağırlıklı ortalamalar için integral birikimleri.
  float initialT=0, integralI=0, integralT=0;
  // 0. saniye ilk örnekte alınır; sıradaki gerilim noktası 300. saniyedir.
  int nextVoltage=1;

  // Yeni bir teşhis testinde bütün durum ve birikimleri başlangıca döndür.
  void reset() { *this=SohWindow(); }
  // Her örnekte çağır: göreli saniye, volt, mA, °C. True döndüğünde model çalıştırılabilir.
  bool add(float seconds, float volts, float currentMA, float tempC) {
    // Biten/iptal edilen pencereyi yeni ölçümle değiştirme; yeni test için reset gerekir.
    if(failed || ready) return ready;
    // NaN/sonsuz veya protokol dışı ölçümde pencereyi iptal et.
    if(!isfinite(seconds) || !isfinite(volts) || !isfinite(currentMA) || !isfinite(tempC)
       || volts<2.4f || volts>4.25f || currentMA<-800 || currentMA>-400
       || tempC<10 || tempC>75) { failed=true; return false; }
    // İlk örnek C/5 deşarj başlangıcında ve zaman=0 olmalıdır; şarj kayıtlarını verme.
    if(!started) {
      // Yaklaşık sıfır başlangıç zamanı ve en az 4.10 V başlangıç gerilimini zorunlu tut.
      if(fabsf(seconds)>0.001f || volts<4.10f) {failed=true; return false;}
      // İlk ölçümü hem başlangıç hem önceki örnek olarak kaydet.
      started=true; previousTime=0; previousV=volts; previousI=currentMA;
      // Başlangıç sıcaklığını koru; ilk gerilim özelliğini doğrudan doldur.
      previousT=initialT=tempC; features[0]=volts; return false;
    }
    // Ölçümler arası gerçek süre; sabit örnekleme hızı varsayılmaz.
    float dt=seconds-previousTime;
    // Tekrarlı/geriye giden zaman veya 60 saniyeyi aşan boşluk varsa integral güvenilir değildir.
    if(dt<=0 || dt>60) {failed=true; return false;}
    // 1800 saniyeyi aşan son aralığın yalnız pencere içine düşen kısmını kullan.
    float stop=fminf(seconds,1800.0f), fraction=(stop-previousTime)/dt;
    // Son kısmi aralığın bitiş akımını doğrusal interpolasyonla bul.
    float endI=previousI+fraction*(currentMA-previousI);
    // Aynı pencere sınırında sıcaklığı da interpolasyonla hesapla.
    float endT=previousT+fraction*(tempC-previousT);
    // Trapez alanı: iki uç akım ortalaması × geçen saniye; henüz ortalamaya bölünmez.
    integralI+=0.5f*(previousI+endI)*(stop-previousTime);
    // Sıcaklığın zaman integralini aynı şekilde biriktir.
    integralT+=0.5f*(previousT+endT)*(stop-previousTime);
    // Bir aralık birden fazla 300 saniyelik noktayı kapsarsa hepsini sırayla doldur.
    while(nextVoltage<=6 && nextVoltage*300.0f<=stop) {
      // Hedef gerilim zamanının iki komşu ölçüm arasında hangi orana düştüğünü bul.
      float f=(nextVoltage*300.0f-previousTime)/dt;
      // Doğrusal gerilim örneğini yaz ve bir sonraki 300 saniyelik hedefe geç.
      features[nextVoltage]=previousV+f*(volts-previousV); ++nextVoltage;
    }
    // Otuz dakika dolunca integral ve sıcaklık artışından son üç özelliği tamamla.
    if(seconds>=1800) {
      // Zaman integrallerini 1800’e bölerek zaman ağırlıklı ortalamaları elde et.
      features[7]=integralI/1800; features[8]=integralT/1800;
      // Başlangıca göre sıcaklık artışını hesapla ve pencereyi hazır olarak işaretle.
      features[9]=endT-initialT; ready=true;
    }
    // Sonraki add çağrısının interpolasyonu için mevcut ölçümü önceki örnek yap.
    previousTime=seconds; previousV=volts; previousI=currentMA; previousT=tempC;
    // False veri toplamaya devam, True on özellik model için hazır anlamına gelir.
    return ready;
  }
};
