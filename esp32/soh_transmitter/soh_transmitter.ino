// Ortak pinler, radyo kurulumu ve paket kodlama fonksiyonları.
#include "radio_common.h"
// Yalnız ayrılmış test hücrelerinden gelen, otomatik üretilmiş int16 özellik dizisi.
#include "test_samples.h"
// Her yeniden başlatmada oturum kimliği üretmek için esp_random.
#include <esp_system.h>
// Arduino-ESP32 ile birlikte gelen gerçek zamanlı işletim sistemi türleri.
#include <freertos/FreeRTOS.h>
// Görev oluşturma, periyodik bekleme ve görevi sonlandırma API fonksiyonları.
#include <freertos/task.h>

// NRF sürücüsünü CE ve CSN pinleriyle oluştur; SPI setup sırasında başlatılır.
RF24 radio(NRF_CE,NRF_CSN);

// Bu uygulama görevi bir oturumdaki bütün test örneklerini sırayla gönderir.
void transmitTask(void*) {
  // Alıcının reset sonrası yeniden başlayan sıra numaralarını ayırması için oturum kimliği.
  const uint32_t session=esp_random();
  // Periyodu sabit bir başlangıç anına bağla; döngü süresinin birikimli kaymasını azalt.
  TickType_t wake=xTaskGetTickCount();
  // Her örneği yalnız bir kez dene; dizi sonunda otomatik başa sarma yapılmaz.
  for(uint16_t seq=0;seq<TEST_SAMPLE_COUNT;++seq) {
    // Yığında tek NRF payload tamponu; her iterasyonda bütün alanları doldurulur.
    uint8_t packet[PACKET_SIZE];
    // Özellikleri, model kimliğini, oturumu ve indeksi CRC içeren pakete yaz.
    encodePacket(packet,MODEL_ID,session,seq,TEST_SAMPLES[seq]);
    // Donanım onayı alınıp alınmadığını öğren; bu, alıcı model görevinin işi bitirdiğini göstermez.
    bool ack=radio.write(packet,sizeof(packet));
    // Gönderilen oturum/indeks ve ACK durumunu seri portta izlenebilir tut.
    Serial.printf("TX session=%lu seq=%u ack=%s\n",(unsigned long)session,seq,ack?"YES":"NO");
    // Saniyede bir yeni örnek; otomatik radyo tekrarları aynı periyot içinde gerçekleşir.
    // İlk gönderim hemen yapılır; sonraki uygulama örnekleri 1000 ms hedef aralıkla gönderilir.
    vTaskDelayUntil(&wake,pdMS_TO_TICKS(1000));
  }
  // Son örnekten sonra tamamlanma bildir; yeniden oynatma için kartı resetle.
  Serial.println("DONE: all held-out samples sent once. Reset to replay.");
  // Görev bitince kendi kaynaklarını işletim sistemine bırak.
  vTaskDelete(nullptr);
}

// Arduino bu fonksiyonu açılışta bir kez çalıştırır.
void setup() {
  // 115200 baud seri portu aç ve başlangıç için kısa bekleme yap.
  Serial.begin(115200);delay(500);
  // Radyo başlatılamazsa task oluşturma; logla ve setup fonksiyonundan çık.
  if(!setupRadio(radio,false)){Serial.println("FATAL: NRF initialization failed");return;}
  // 4096 bayt yığın, öncelik 2, çekirdek 1 ile gönderim görevini oluştur; dönüşünü denetle.
  if(xTaskCreatePinnedToCore(transmitTask,"transmit",4096,nullptr,2,nullptr,1)!=pdPASS)
    Serial.println("FATAL: transmit task creation failed");
}
// İş transmitTask içindedir; Arduino döngüsü CPU tüketmeden bekler.
void loop(){delay(1000);}
