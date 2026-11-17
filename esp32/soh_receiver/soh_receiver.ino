// Ortak radyo ayarları ve mesaj geçerlilik kontrolleri.
#include "radio_common.h"
// Eğitilmiş float32 ağırlıklar, ölçekleme ve ileri yayılım fonksiyonu.
#include "soh_model.h"
// İndeksle erişilen gerçek SOH ve paketlenmiş bilgisayar tahminleri; eğitim girdisi değildir.
#include "test_reference.h"
// FreeRTOS temel türleri ve başarılı/başarısız API sonuçları.
#include <freertos/FreeRTOS.h>
// İki çekirdeğe bağlı görev oluşturma ve bekleme fonksiyonları.
#include <freertos/task.h>
// Alım ve model görevleri arasında güvenli veri kopyalama kuyruğu.
#include <freertos/queue.h>

// Radyo nesnesine çalışma sırasında yalnız receiveTask erişir; çıkarım SPI kullanmaz.
RF24 radio(NRF_CE,NRF_CSN);
// Kuyruğa kopyalanan mesaj: model girdisi 10 float, izleme için oturum ve indeks.
struct ValidatedSample {uint32_t session;uint16_t seq;float features[10];};
// setup içinde oluşturulacak sekiz mesajlık kuyruğun işletim sistemi tanıtıcısı.
QueueHandle_t inferenceQueue=nullptr;

// Daha yüksek öncelikli alım görevi; radyo FIFO’sunu tüketir ve geçersiz mesajları ayıklar.
void receiveTask(void*) {
  // İlk geçerli mesajdan önce lastSession/lastSeq değerlerini kıyaslama.
  bool haveSequence=false;
  // Aynı oturumdaki sıra denetimi için son kabul edilen oturum.
  uint32_t lastSession=0;
  // Başarıyla kuyruğa konan son örneğin indeksi.
  uint16_t lastSeq=0;
  for(;;) {
    // FIFO içinde paket kaldığı sürece tamamını oku; sonra kısa süre CPU bırak.
    while(radio.available()) {
      // Radyo verisini sabit uzunluklu ham tampon içine al.
      uint8_t packet[PACKET_SIZE];radio.read(packet,sizeof(packet));
      // Kuyruğa verilecek yerel nesneyi sıfırla; doğrulama alanları bunun içine doldurur.
      ValidatedSample sample{};
      // CRC, sürüm, model, indeks veya özellik aralığı hatalıysa kuyruğa verme.
      if(!decodePacket(packet,MODEL_ID,TEST_SAMPLE_COUNT,sample.session,sample.seq,sample.features)) {
        Serial.println("RX REJECT: header/model/CRC/index/range");continue;
      }
      // Aynı oturumda tekrarları ve geriden gelen örnekleri modelden önce reddet.
      if(haveSequence && sample.session==lastSession && sample.seq<=lastSeq) {
        Serial.println("RX REJECT: duplicate/out-of-order");continue;
      }
      // Arada kayıp sıra varsa sayısını logla; mevcut bağımsız örnek yine işlenebilir.
      if(haveSequence && sample.session==lastSession && sample.seq>lastSeq+1)
        Serial.printf("RX GAP: %u missing samples\n",sample.seq-lastSeq-1);
      // Kuyruk mesajı kopyalar; model görevi NRF veya SPI durumuna erişmez.
      // Sıfır bekleme: kuyruk doluysa radyo görevini bekletmek yerine paketi düşür ve logla.
      if(xQueueSend(inferenceQueue,&sample,0)!=pdTRUE) {
        Serial.println("RX DROP: inference queue full");continue;
      }
      // Yalnız kuyruğa başarıyla yazıldıktan sonra son kabul edilen sıra bilgisini güncelle.
      lastSession=sample.session;lastSeq=sample.seq;haveSequence=true;
    }
    // Boş FIFO sorgusunda 5 ms bekleyerek çekirdeği sürekli meşgul etme.
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

// Düşük öncelikli ikinci uygulama görevi; radyo sürücüsüne dokunmadan SOH hesaplar.
void inferenceTask(void*) {
  // Kuyruktan kopyalanan geçerli örneğin yerel çalışma alanı.
  ValidatedSample sample;
  // Oturuma özgü değerlendirme sayacı ve birikimli mutlak/kare hata toplamları.
  uint32_t activeSession=0,count=0;float sumAbs=0,sumSquared=0;
  for(;;) {
    // Mesaj yokken portMAX_DELAY ile bloklan; boşta sürekli CPU döngüsü kullanma.
    if(xQueueReceive(inferenceQueue,&sample,portMAX_DELAY)!=pdTRUE)continue;
    // İlk mesajda veya yeni verici oturumunda değerlendirme toplamlarını yeniden başlat.
    if(!count || sample.session!=activeSession) {
      // Kümülatif metrikler yalnız bu oturumda alınan/işlenen örnekleri kapsasın.
      activeSession=sample.session;count=0;sumAbs=0;sumSquared=0;
    }
    // Yalnız model çıkarımının süresini ölç; kablosuz uçtan uca gecikme değildir.
    uint32_t start=micros();float predicted=predict_soh(sample.features);
    // micros farkı unsigned aritmetikle alınır; seri çıktı süresi bu ölçüme dahil değildir.
    uint32_t elapsed=micros()-start;
    // Model NaN/sonsuz üretirse hatalı sonucu metrik toplamlarına katma.
    if(!isfinite(predicted)){Serial.println("MODEL ERROR: nonfinite output");continue;}
    // Gerçek SOH yalnız yerel değerlendirme verisidir; modele ASLA giriş olarak verilmez.
    // Yerel gerçek etiketle hata hesapla; truth değeri predict_soh fonksiyonuna verilmez.
    float truth=TRUE_SOH[sample.seq], error=predicted-truth;
    // MAE için mutlak hata, RMSE için kare hata biriktir.
    ++count;sumAbs+=fabsf(error);sumSquared+=error*error;
    // Tahmin/gerçek/hata ve bilgisayar referans farkını; süre ve kümülatif MAE/RMSE ile yaz.
    Serial.printf("SOH session=%lu seq=%u pred=%.4f true=%.4f error_pp=%.4f ref_delta=%.6f us=%lu MAE=%.4f RMSE=%.4f n=%lu\n",
      (unsigned long)sample.session,sample.seq,predicted,truth,error,
      predicted-EXPECTED_QUANTIZED_SOH[sample.seq],(unsigned long)elapsed,
      sumAbs/count,sqrtf(sumSquared/count),(unsigned long)count);
  }
}

// Radyo ve kuyruk görevlerden önce bir kez oluşturulur.
void setup() {
  // İki kartın seri monitörünü de 115200 baud kullan.
  Serial.begin(115200);delay(500);
  // Alıcı radyo başlatılamazsa hiçbir uygulama görevi başlatma.
  if(!setupRadio(radio,true)){Serial.println("FATAL: NRF initialization failed");return;}
  // Sekiz adet ValidatedSample için kopyalama kuyruğu oluştur; pointer kuyruğu değildir.
  inferenceQueue=xQueueCreate(8,sizeof(ValidatedSample));
  // Bellek ayrılamadıysa task başlatmadan erken çık.
  if(!inferenceQueue){Serial.println("FATAL: queue allocation failed");return;}
  // İkinci task oluşturulamazsa ilkini temizlemek için tanıtıcıyı sakla.
  TaskHandle_t inferenceHandle=nullptr;
  // Model görevi: 6144 bayt yığın, öncelik 1, çekirdek 1.
  if(xTaskCreatePinnedToCore(inferenceTask,"inference",6144,nullptr,1,&inferenceHandle,1)!=pdPASS) {
    Serial.println("FATAL: inference task creation failed");return;
  }
  // Alım görevi: 4096 bayt yığın, öncelik 2, çekirdek 0.
  if(xTaskCreatePinnedToCore(receiveTask,"receive",4096,nullptr,2,nullptr,0)!=pdPASS) {
    // Alım görevi yoksa boşta kalacak çıkarım görevini sonlandır.
    vTaskDelete(inferenceHandle);Serial.println("FATAL: receive task creation failed");return;
  }
  // Bu mesaj iki uygulama görevinin de oluşturulduğunu bildirir.
  Serial.println("READY: validated radio messages -> queue -> SOH inference");
}
// İşler FreeRTOS görevlerindedir; Arduino ana döngüsü bekleyerek CPU bırakır.
void loop(){delay(1000);}
