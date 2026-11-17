"""Empedans haricindeki CSV'leri oku ve aralık dışındaki satırları çıkar.

Gereksinim: pip install pandas
Çalıştırma: python load_dataset.py
Ham CSV dosyaları değiştirilmez. Sonuçlar bellekte DataFrame listesi olarak tutulur.
"""

from pathlib import Path

# Pandas CSV verisini sütun adlarıyla erişilebilen DataFrame tablolarına yükler.
import pandas as pd


# Veri klasörünü bu kaynak dosyasına göre bul; terminal konumu önemli değildir.
DATASET_DIR = Path(__file__).resolve().parent / "dataset"

# Dahil sınırlar: bunların dışındaki değerleri içeren satırlar çıkarılır.
# Bunlar ön tarama eşikleridir; kesin fiziksel çalışma sınırları değildir.
# Alt/üst sınırlar dahildir. Bunlar öğrenilmiş istatistiksel eşikler değil ön tarama kurallarıdır.
VALID_RANGES = {
    "Ecell_V": (2.40, 4.25),
    "I_mA": (-25_000, 5_000),
    "Temperature__C": (10, 75),
    "QDischarge_mA_h": (0, 3_300),
    "EnergyDischarge_W_h": (-13, 0),
    "EnergyCharge_W_h": (0, 14),
}


def mark_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Ham sıra bilgisini koru; geçersiz ölçümleri silmeden işaretle."""
    # Altı kontrol sütunundan eksik olanları küme farkıyla belirle.
    missing_columns = set(VALID_RANGES) - set(df.columns)
    # Eksik şemayla sessizce devam etmek yerine anlaşılır bir hata üret.
    if missing_columns:
        raise ValueError(f"Eksik sütunlar: {sorted(missing_columns)}")
    # Çağıranın tablosunu değiştirmemek için ayrı bir çalışma kopyası oluştur.
    df = df.copy()
    # Silme veya indeks sıfırlama sonrası ölçümü ham kayda bağlayabilmek için orijinal sıra.
    df["source_row"] = range(len(df))  # Başlık hariç, sıfırdan başlayan sıra.
    # Başlangıçta tüm satırlar geçerli; her sütun kontrolü bu maskeyi daraltır.
    valid_rows = pd.Series(True, index=df.index)
    # Her özellik için ilgili fiziksel birimdeki alt ve üst sınırı kullan.
    for column, (lower, upper) in VALID_RANGES.items():
        # Sayıya çevrilemeyen değerleri NaN yap; between bunları geçerli saymaz.
        numeric = pd.to_numeric(df[column], errors="coerce")
        # Mantıksal VE: tek bir sütun bile sınır dışındaysa satır geçersiz kalır.
        valid_rows &= numeric.between(lower, upper, inclusive="both")
    # Satırları çıkarmadan önce geçerlilik bilgisini ayrı sütunda sakla.
    df["is_valid"] = valid_rows
    return df


def remove_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Altı sütundan herhangi biri geçersizse satırı çıkar.

    Bu sütunlardaki eksik, sayısal olmayan ve sonsuz değerler de çıkarılır.
    Diğer sütunlar filtreleme için kullanılmaz.
    """
    # Aynı sınır kurallarını tekrar yazmak yerine işaretleme fonksiyonunu kullan.
    df = mark_outliers(df)
    # Her özellik için ilgili fiziksel birimdeki alt ve üst sınırı kullan.
    for column, (lower, upper) in VALID_RANGES.items():
        df[column] = pd.to_numeric(df[column], errors="coerce")
    # Yalnız geçerli satırları seç; source_row korunurken DataFrame indeksi yenilenir.
    return df.loc[df["is_valid"]].reset_index(drop=True)


def load_datasets(
    dataset_dir: Path = DATASET_DIR, *, keep_invalid: bool = False
) -> list[pd.DataFrame]:
    """CSV'leri yükle. keep_invalid=True kalite raporu için ham satırları korur."""
    # String olarak da verilse klasör yolunu Path türüne dönüştür.
    dataset_dir = Path(dataset_dir)
    # Dosyaları sıralamak, liste sırasının her çalıştırmada aynı olmasını sağlar.
    csv_files = sorted(
        path
        for path in dataset_dir.glob("*.csv")
        # Büyük/küçük harften bağımsız ad kontrolüyle empedans CSV dosyalarını dışarıda bırak.
        if "impedance" not in path.stem.lower()
    )
    # Yanlış klasörde boş bir eğitim başlatmamak için erken hata ver.
    if not csv_files:
        raise FileNotFoundError(f"Okunabilecek CSV bulunamadı: {dataset_dir}")

    # Her elemanı bir hücrenin DataFrame tablosu olacak sonuç listesi.
    datasets = []
    # Hücre dosyalarını tek tek oku; bütün ham dosyalar için ek bir ikinci liste oluşturma.
    for path in csv_files:
        # Dosyalar sırayla okunur; ham verilerin ikinci bir listesi tutulmaz.
        # CSV başlığındaki adları sütun adı olarak okuyarak tabloyu oluştur.
        df = pd.read_csv(path)
        # Temizlik raporunda karşılaştırmak için ham satır sayısını sakla.
        original_count = len(df)
        # Eksik sütun hatasına kaynak dosyanın adını ekleyebilmek için yakalama bölgesi.
        try:
            # keep_invalid seçimi işaretli ham tablo ile filtrelenmiş tablo arasında seçim yapar.
            cleaned_df = mark_outliers(df) if keep_invalid else remove_outliers(df)
        # Şema hatasının hangi CSV dosyasında oluştuğunu üst katmana bildir.
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        # Dosya adını model girdisi yapmadan tablonun metadata alanında sakla.
        cleaned_df.attrs["source_file"] = path.name
        # Bu hücreyi sonuç listesine ekle; dosyaları tek büyük tabloda birleştirme.
        datasets.append(cleaned_df)
        # İşaretleme modunda maskeyi say, filtreleme modunda çıkarılan satır farkını hesapla.
        invalid_count = int((~cleaned_df["is_valid"]).sum()) if keep_invalid else original_count - len(cleaned_df)
        print(f"{path.name}: {original_count:,} satır, {invalid_count:,} geçersiz "
              f"({'işaretlendi' if keep_invalid else 'çıkarıldı'})")

    # Sonraki ön işleme adımlarına hücre bazındaki tablo listesini döndür.
    return datasets

