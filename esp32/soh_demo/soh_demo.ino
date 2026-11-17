// Eğitilmiş ağ ve kayıtlı EXAMPLE test vektörü; canlı sensör okuması yapılmaz.
#include "soh_model.h"

// Tek kart self-check deneyini Arduino açılışında bir defa çalıştır.
void setup() {
  // Seri monitörün 115200 baud ayarında olması gerekir.
  Serial.begin(115200);
  // Seri bağlantının açılması için kısa başlangıç beklemesi.
  delay(1000);
  // Çıkarımdan hemen önce mikro-saniye sayacını al.
  const uint32_t start = micros();
  // Kayıtlı test örneğinin on özelliğinden SOH tahmini üret.
  const float result = predict_soh(EXAMPLE);
  // Yalnız model çağrısının geçen süresini ölç; seri yazdırmayı dahil etme.
  const uint32_t elapsed = micros() - start;
  // Hesaplanan ve bilgisayarda beklenen SOH değerini yan yana göster.
  Serial.printf("SOH: %.5f %%\nReference: %.5f %%\n", result, EXPECTED_SOH);
  // 0.01 yüzde puanı toleransıyla eşleşmeyi, çıkarım süresini ve boş heap’i raporla.
  Serial.printf("Self-check: %s\nInference: %lu us\nFree heap: %lu bytes\n",
                fabsf(result - EXPECTED_SOH) < 0.01f ? "PASS" : "FAIL",
                (unsigned long)elapsed, (unsigned long)ESP.getFreeHeap());
}

// Tek seferlik demo tamamlanmıştır; burada sensör veya ağ işlemi yoktur.
void loop() {
  // Bu demo yalnız ayrılmış bir test vektörünü doğrular; fiziksel sensör okumaz.
}
