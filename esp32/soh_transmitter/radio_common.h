// Ortak protokol tanımlarını aynı dosyada iki kez tanımlamayı önle.
#pragma once
// Arduino temel türleri, GPIO ve seri port fonksiyonları.
#include <Arduino.h>
// ESP32 ile NRF modülü arasındaki SPI veri yolu sürücüsü.
#include <SPI.h>
// nRF24L01+ için RF24 kütüphanesi; Arduino Library Manager üzerinden kurulmalıdır.
#include <RF24.h>
// Gelen özelliklerin sonlu olup olmadığını kontrol etmek için isfinite.
#include <math.h>

// İki kartta da aynı pin düzeni: CE/CSN kontrol; SCK/MISO/MOSI SPI hatlarıdır.
constexpr int NRF_CE=27, NRF_CSN=26, NRF_SCK=18, NRF_MISO=19, NRF_MOSI=23;
// Gönderici ve alıcı aynı RF kanalını kullanmalıdır; mevcut seçim 76.
constexpr uint8_t RADIO_CHANNEL=76;
// Beş bayt radyo adresi ve C string sonlandırıcısı; bu adres şifreleme anahtarı değildir.
static const uint8_t RADIO_ADDRESS[6]="SOH01";
// Tek mesaj nRF24 payload sınırına uygun 32 bayttır; parçalı birleştirme gerekmez.
constexpr size_t PACKET_SIZE=32;
// Gerilim 0.1 mV, akım 0.1 mA, sıcaklıklar 0.01 °C basamaklarla kodlanır.
static const float FEATURE_SCALE[10]={10000,10000,10000,10000,10000,10000,10000,10,100,100};
// İlk yedi gerilime çözümlemede 3.5 V geri eklenir; diğer özelliklerin ofseti sıfırdır.
static const float FEATURE_OFFSET[10]={3.5f,3.5f,3.5f,3.5f,3.5f,3.5f,3.5f,0,0,0};

// İlk n bayt üzerinde CRC16-CCITT-FALSE; rastgele bozulma denetimidir, kimlik doğrulama değildir.
inline uint16_t crc16(const uint8_t* data,size_t n) {
  // CRC yazmacının başlangıç değeri; Python üreticiyle birebir aynı olmalıdır.
  uint16_t crc=0xFFFF;
  // Paketin kontrol edilecek alanlarını sırayla işle.
  for(size_t i=0;i<n;++i) {
    // Gelen baytı üst sekiz bite XOR ile ekle.
    crc^=uint16_t(data[i])<<8;
    // Her biti kaydır; üst bit birse 0x1021 polinomunu uygula, uint16_t 16 bite sınırlar.
    for(int b=0;b<8;++b) crc=(crc&0x8000)?uint16_t((crc<<1)^0x1021):uint16_t(crc<<1);
  }
  return crc;
}
// 16 bit sayıyı little-endian yaz: düşük bayt önce; yapı hizalamasına bağımlılık yok.
inline void put16(uint8_t* p,uint16_t v){p[0]=v&255;p[1]=v>>8;}
// Ardışık iki bayttan unsigned 16 bit sayıyı geri oluştur.
inline uint16_t get16(const uint8_t* p){return uint16_t(p[0])|(uint16_t(p[1])<<8);}
// Oturum kimliğini dört bayta little-endian düzeninde ayır.
inline void put32(uint8_t* p,uint32_t v){for(int i=0;i<4;++i)p[i]=(v>>(8*i))&255;}
// Dört baytı kaydırıp OR ile birleştirerek oturum kimliğini geri al.
inline uint32_t get32(const uint8_t* p){uint32_t v=0;for(int i=0;i<4;++i)v|=uint32_t(p[i])<<(8*i);return v;}

// Modelden önce fiziksel birimlerde protokol aralıklarını denetle.
inline bool validFeatures(const float* f) {
  // Herhangi bir NaN veya sonsuz girdi geçersiz mesaj demektir.
  for(int i=0;i<10;++i) if(!isfinite(f[i]))return false;
  // İlk yedi alan gerilimdir; aynı kabul aralığını her birine uygula.
  for(int i=0;i<7;++i) if(f[i]<2.4f || f[i]>4.25f)return false;
  // Başlangıç tam şarja yakın, akım C/5 civarında, sıcaklık ve artış kabul aralığında olmalı.
  return f[0]>=4.10f && f[7]>=-800 && f[7]<=-400 && f[8]>=10 && f[8]<=75
         && f[9]>=-30 && f[9]<=50;
}

// Baytlar açık little-endian yazılır; C++ struct padding bilgisi radyo paketine taşınmaz.
// Paket: 0=sabit, 1=sürüm, 2..3=model, 4..7=oturum, 8..9=sıra, 10..29=özellik, 30..31=CRC.
inline void encodePacket(uint8_t* p,uint16_t modelId,uint32_t session,uint16_t seq,const int16_t* q) {
  // On bayt başlığı yaz; model kimliği yanlış başlıkla üretilmiş verileri ayırt eder.
  p[0]=0xA7;p[1]=1;put16(p+2,modelId);put32(p+4,session);put16(p+8,seq);
  // Signed int16 özelliğin iki tümleyen bit düzenini iki bayt olarak yaz.
  for(int i=0;i<10;++i)put16(p+10+2*i,static_cast<uint16_t>(q[i]));
  // CRC yalnız ilk 30 bayt üzerinden hesaplanır; CRC alanı kendi hesabına katılmaz.
  put16(p+30,crc16(p,30));
}

// Başlık ve CRC doğruysa alanları çöz; sıra ve fiziksel aralık kontrolüyle geçerlilik döndür.
inline bool decodePacket(const uint8_t* p,uint16_t modelId,uint16_t sampleCount,
                         uint32_t& session,uint16_t& seq,float* f) {
  // Sabit, sürüm, model veya CRC uyuşmazlığında modeli çalıştırmadan paketi reddet.
  if(p[0]!=0xA7 || p[1]!=1 || get16(p+2)!=modelId || get16(p+30)!=crc16(p,30))return false;
  // Oturum ve örnek indeksi model girişinden ayrı metadata alanlarıdır.
  session=get32(p+4);seq=get16(p+8);
  // Geçersiz indeksin referans dizisine erişerek bellek sınırını aşmasını önle.
  if(seq>=sampleCount)return false;
  for(int i=0;i<10;++i) {
    // Özelliğin ham 16 bit desenini önce unsigned olarak oku.
    uint16_t u=get16(p+10+2*i);
    // Üst bit set ise 65536 çıkararak negatif iki tümleyen değerini açıkça çöz.
    int32_t signedValue=(u&0x8000)?int32_t(u)-65536:int32_t(u);
    // Kodlama ölçeğini geri al ve ofseti ekle; model orijinal V/mA/°C birimlerini bekler.
    f[i]=signedValue/FEATURE_SCALE[i]+FEATURE_OFFSET[i];
  }
  // CRC doğru olsa bile uygunsuz sayısal değer taşıyan mesajı reddet.
  return validFeatures(f);
}

// Radyo kurulumunu iki kart için ortak tut; receiver rolüne göre dinleme/yazma açılır.
inline bool setupRadio(RF24& radio,bool receiver) {
  // Kablolamaya karşılık gelen SPI pinlerini açıkça seç.
  SPI.begin(NRF_SCK,NRF_MISO,NRF_MOSI,NRF_CSN);
  // SPI üzerinden NRF çipi başlatılamazsa üst katmana başarısızlık bildir.
  if(!radio.begin())return false;
  // İki kartın aynı RF kanalında buluşmasını sağla.
  radio.setChannel(RADIO_CHANNEL);
  // Hava hızı 1 Mbit/s; bu değer uygulamanın saniyede bir gönderim hızından farklıdır.
  if(!radio.setDataRate(RF24_1MBPS))return false;
  // Yakın masaüstü deneyi için düşük çıkış gücü seç; menzil sonucu ölçülmüş değildir.
  radio.setPALevel(RF24_PA_LOW);
  // Beş bayt adres ve otomatik donanım ACK kullan.
  radio.setAddressWidth(5); radio.setAutoAck(true);
  // Sınırlı otomatik yeniden deneme ve iki bayt donanım CRC etkinleştirilir.
  radio.setRetries(5,5); radio.setCRCLength(RF24_CRC_16);
  // Dinamik uzunluğu kapat; iki uç da tam 32 bayt okuyup yazar.
  radio.disableDynamicPayloads(); radio.setPayloadSize(PACKET_SIZE);
  // Alıcı rolünde pipe 1 açıp dinlemeyi başlat.
  if(receiver){radio.openReadingPipe(1,RADIO_ADDRESS);radio.startListening();}
  // Verici rolünde aynı hedef adresini ayarla ve dinleme modundan çık.
  else {radio.openWritingPipe(RADIO_ADDRESS);radio.stopListening();}
  return true;
}
