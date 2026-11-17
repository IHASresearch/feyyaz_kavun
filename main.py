"""SOH tahmini projesinin işlem adımları."""

# CSV yükleme fonksiyonunu al; import işlemi verileri henüz okumaz.
from load_dataset import load_datasets
# Çalışma klasöründen bağımsız dosya yolları oluşturmak için Path kullanılır.
from pathlib import Path

# Ham verilerin eksik, aykırı ve kesintili kısımlarını raporlayan modül.
from preprocessing import create_preprocessing_reports
# SOH etiketlerini/özelliklerini hazırlayan ve ağı eğiten fonksiyonlar.
from tinyml import build_training_table, train_and_export
# Eğitimde görülmeyen test örneklerini ESP32 dizilerine dönüştürür.
from export_radio_data import export_radio_data


# Projenin bütün adımlarını tek giriş noktasında sıralar.
def main():
    # 1. Kalite kontrolü için ham satırları koru, aykırı değerleri işaretle.
    # True seçimi hatalı satırları silmez; zaman boşlukları incelenebilir kalır.
    datasets = load_datasets(keep_invalid=True)
    print(f"\nToplam {len(datasets)} veri seti yüklendi.")

    # 2. Kalite, Ns ve kesintisiz bölüm adaylarını raporla.
    # reports yolu main.py dosyasının bulunduğu klasöre göre hesaplanır.
    output_dir = Path(__file__).resolve().parent / "reports"
    create_preprocessing_reports(datasets, output_dir)
    print(f"\nRaporlar kaydedildi: {output_dir}")

    # 3. Tam kapasite testlerinden etiket ve ilk 30 dakikadan özellik üret.
    # Özellik tablosu, ağırlıklar, tahminler ve grafikler artifacts altında saklanır.
    model_dir = Path(__file__).resolve().parent / "artifacts"
    table = build_training_table(datasets, model_dir)
    # Ham ölçümler eğitim sırasında bellekte tutulmak zorunda değil.
    # Büyük ham DataFrame listesinin referansını bırak; eğitimde küçük tablo yeterlidir.
    del datasets
    # 4. Hücre bazında ayır, eğit, değerlendir ve ESP32 başlığını dışa aktar.
    train_and_export(table, model_dir)
    # 5. Yalnız test hücrelerini iki ESP32'li NRF demosu için dışa aktar.
    export_radio_data()


# Dosya doğrudan çalıştırılırsa başlat; başka dosyadan import edilirse başlatma.
if __name__ == "__main__":
    main()
