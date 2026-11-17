# ESP32 ile Batarya Sağlık Tahmini

Bu proje, bataryanın sağlık durumunu (SOH) tahmin eden küçük bir yapay sinir ağı ve iki ESP32 arasında kablosuz veri aktarımı içerir.

Model bilgisayarda eğitilir. Birinci ESP32 test örneklerini saniyede bir gönderir. İkinci ESP32 gelen mesajı kontrol eder ve geçerli verilerle SOH tahmini yapar.

## Kullanılan teknolojiler

- Python, NumPy, Pandas ve Matplotlib
- ESP32-WROOM-32D
- nRF24L01+ ve RF24 kütüphanesi
- FreeRTOS
- VS Code ve PlatformIO

## Model

Model, kontrollü deşarjın ilk 30 dakikasındaki gerilim, akım ve sıcaklıktan çıkarılan 10 özelliği kullanır.

- Ağ yapısı: **10 → 16 → 8 → 1**
- Parametre sayısı: **321**
- Test kümesindeki ortalama mutlak hata: **1,55 SOH yüzde puanı**

Eğitim ve test grupları hücre bazında ayrılır. Kablosuz uygulama, hazırlanmış test vektörlerini gönderir; canlı sensör ölçümü yapmaz.

## Python ile çalıştırma

Gerekli paketleri kurup ana programı çalıştırın:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Tam eğitim akışı için batarya CSV verilerinin yerel olarak sağlanması gerekir. Yalnız ESP32 demosunu kullanmak için modeli yeniden eğitmek gerekmez.

## ESP32 kurulumu

1. VS Code'a **PlatformIO IDE** eklentisini kurun.
2. `esp32/soh_transmitter` ve `esp32/soh_receiver` klasörlerini ayrı pencerelerde açın.
3. Her projenin `platformio.ini` dosyasında kendi COM portunu ayarlayın.
4. **Build** ile derleyip **Upload** ile ilgili karta yükleyin.
5. Seri monitörleri **115200 baud** hızında açın.
6. Önce alıcıyı başlatın; `READY` mesajından sonra vericiyi resetleyin.

PlatformIO gerekli ESP32 araçlarını ve RF24 kütüphanesini indirir. FreeRTOS, Arduino-ESP32 altyapısına dahildir.

Verici 81 örneği gönderince durur. Tekrar göndermek için resetleyin. Model güncellendiğinde iki kartın firmware'ini birlikte güncelleyin.

## NRF bağlantıları

Her iki kartta aynı bağlantıları kullanın:

| nRF24L01+ | ESP32 |
|---|---|
| VCC | 3,3 V |
| GND | GND |
| CE | GPIO27 |
| CSN | GPIO26 |
| SCK | GPIO18 |
| MOSI | GPIO23 |
| MISO | GPIO19 |

IRQ bağlantısı kullanılmaz. NRF modülünü kararlı bir **3,3 V** kaynağından besleyin.

## FreeRTOS görevleri

- **transmitTask:** Test örneklerini saniyede bir gönderir.
- **receiveTask:** Mesajın CRC, sürüm, sıra numarası ve değer aralıklarını kontrol eder; geçerli veriyi kuyruğa aktarır.
- **inferenceTask:** Kuyruktaki veriyle SOH tahmini yapar ve sonucu seri porta yazar.

## Ana dosyalar

| Dosya | Görevi |
|---|---|
| `main.py` | İşlem adımlarını sırayla çalıştırır |
| `load_dataset.py` | CSV verilerini okur ve aykırı değerleri işaretler |
| `preprocessing.py` | Veri kalitesini inceler |
| `tinyml.py` | Özellikleri hazırlar, modeli eğitir ve C++ olarak dışa aktarır |
| `export_radio_data.py` | ESP32 için test dizilerini oluşturur |
| `esp32/soh_transmitter/` | Verici firmware'i |
| `esp32/soh_receiver/` | Alıcı firmware'i |
