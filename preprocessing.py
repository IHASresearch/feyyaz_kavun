"""Ham ölçümler için kalite, Ns ve kesintisiz bölüm raporları.

Bölümler deney türü veya gerçek çevrim etiketi değildir. Ns/çevrim değişimi,
geçersiz ölçüm, tekrar veya zaman kesintisi bölüm sınırı oluşturur.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# Yükleyiciyle aynı sınırları kullan; farklı modüllerde eşiklerin ayrışmasını önle.
from load_dataset import VALID_RANGES


def create_preprocessing_reports(datasets, output_dir, gap_factor=5.0):
    """Raporları kaydet; ölçüm verilerini doldurma, sıralama veya yumuşatma.

    Büyük boşluk eşiği dosyanın pozitif zaman farklarının %95 yüzdeliğinin
    gap_factor katıdır. Bu, protokol doğrulaması gerektiren bir sezgiseldir.
    """
    # Boşluk eşiğinin normal örnekleme aralığından büyük olmasını şart koş.
    if gap_factor <= 1:
        raise ValueError("gap_factor 1'den büyük olmalı")
    output_dir = Path(output_dir)
    # Üst klasörler yoksa oluştur; zaten varsa hata çıkarma.
    output_dir.mkdir(parents=True, exist_ok=True)
    # Dört raporun satırlarını ayrı listelerde biriktir.
    quality, columns, ns_reports, segment_reports = [], [], [], []

    # İstatistikleri her hücre için ayrı hesapla; hücrelerin zamanlarını karıştırma.
    for df in datasets:
        # Rapor satırlarının hangi hücreye ait olduğunu metadata üzerinden al.
        source = df.attrs["source_file"]
        # Sonradan eklenen yardımcı alanları ham ölçüm tekrarına ve sütun özetine katma.
        raw_columns = [c for c in df.columns if c not in ("source_row", "is_valid")]
        # Zaman ve bölümleme hesabı için bulunması gereken yardımcı/ham sütunlar.
        required = {"time_s", "Ns", "cycleNumber", "is_valid"}
        if not required.issubset(df.columns):
            raise ValueError(f"{source}: eksik sütunlar {required - set(df.columns)}")
        # Ham değerleri değiştirmeden sayısal bir analiz tablosu üret; bozuk metinler NaN olur.
        numeric = df[raw_columns].apply(pd.to_numeric, errors="coerce")
        for col in raw_columns:
            values = numeric[col]
            # Min/max hesabında NaN ve sonsuzların sonuçları bozmasını önle.
            finite = values[np.isfinite(values)]
            # Sınırı tanımlanmamış sütunlarda aralık ihlali raporlanmaz; diğer kalite kontrolleri sürer.
            lower, upper = VALID_RANGES.get(col, (-np.inf, np.inf))
            # Eksik, metinsel, sonsuz ve aralık dışı kategorilerini ayrı sütunlarda raporla.
            columns.append(dict(
                source_file=source, column=col, missing=int(df[col].isna().sum()),
                non_numeric=int((df[col].notna() & values.isna()).sum()),
                infinite=int(np.isinf(values).sum()),
                outside_range=int(((values < lower) | (values > upper)).sum()),
                minimum=finite.min(), maximum=finite.max(),
            ))

        time = numeric["time_s"]
        # Her ölçümle bir öncekinin zaman farkı; ilk satırın farkı doğal olarak NaN olur.
        dt = time.diff()
        # Örnekleme istatistiğine yalnız pozitif ve sonlu zaman farklarını al.
        positive_dt = dt[(dt > 0) & np.isfinite(dt)]
        median_dt = positive_dt.median()
        # Hız değişen kayıtlarda medyan yerine %95 yüzdelik × katsayı ile büyük boşluk adayı bul.
        gap_threshold = positive_dt.quantile(.95) * gap_factor
        # Bu eşikten uzun aralıklar ayrı bölüm sınırı sayılacaktır.
        gaps = dt > gap_threshold
        # Yalnız zamana değil bütün ham sütunlara göre aynı olan sonraki kayıtları işaretle.
        duplicates = df.duplicated(subset=raw_columns)
        # Sınır kontrolü, sonlu zaman, mevcut Ns/çevrim ve tekrar olmama koşullarını birleştir.
        usable = (df["is_valid"] & np.isfinite(time)
                  & numeric["Ns"].notna() & numeric["cycleNumber"].notna()
                  & ~duplicates)
        # Ham sıra korunur. Şüpheli zaman aralıklarından integral hesaplanmaz.
        # Ns/çevrim değişimi, geçersiz komşu veya zaman sorunu yeni bölüm başlatır.
        boundary = (
            numeric["Ns"].ne(numeric["Ns"].shift())
            | numeric["cycleNumber"].ne(numeric["cycleNumber"].shift())
            | ~usable | ~usable.shift(fill_value=False)
            | (dt <= 0) | gaps | ~np.isfinite(dt)
        )
        # Ham sıra ve kullanılabilirlik maskesini sayısal tabloya ekle.
        work = numeric.assign(
            source_row=df["source_row"], usable=usable,
            # True değerlerini kümülatif toplayarak her kesintisiz parçaya kimlik ver.
            segment_id=boundary.cumsum(),
        )
        # Dosyanın kalite sayılarını ve örnekleme dağılımını tek rapor satırında sakla.
        quality.append(dict(
            source_file=source, rows=len(df), invalid_rows=int((~df["is_valid"]).sum()),
            duplicate_rows=int(duplicates.sum()), usable_rows=int(usable.sum()),
            invalid_time=int((~np.isfinite(time)).sum()),
            backward_time_steps=int((dt < 0).sum()), repeated_time_steps=int((dt == 0).sum()),
            dt_min_s=positive_dt.min(), dt_median_s=median_dt,
            dt_p95_s=positive_dt.quantile(.95), dt_max_s=positive_dt.max(),
            gap_threshold_s=gap_threshold, large_gap_count=int(gaps.sum()),
        ))
        # Ns özeti tüm ham satırları kapsar; süre farklı bölümler arasında toplanmaz.
        # Aynı Ns kodunun bütün tekrarlarını birleştir; bu tablo tek bir fiziksel bölüm değildir.
        ns_summary = work.groupby("Ns", dropna=False).agg(
            rows=("Ns", "size"), usable_rows=("usable", "sum"),
            current_min_mA=("I_mA", "min"), current_mean_mA=("I_mA", "mean"),
            current_max_mA=("I_mA", "max"), voltage_min_V=("Ecell_V", "min"),
            voltage_max_V=("Ecell_V", "max"), temperature_min_C=("Temperature__C", "min"),
            temperature_max_C=("Temperature__C", "max"),
        ).reset_index()
        # Her Ns özeti için dosya adını ilk sütuna koy.
        ns_summary.insert(0, "source_file", source)
        ns_reports.append(ns_summary)
        # Yalnız kullanılabilir satırları bölüm kimliğine göre grupla; aradaki boşlukları birleştirme.
        segments = work.loc[usable].groupby("segment_id").agg(
            Ns=("Ns", "first"), recorded_cycle=("cycleNumber", "first"),
            start_row=("source_row", "first"), end_row=("source_row", "last"),
            rows=("time_s", "size"), start_s=("time_s", "first"), end_s=("time_s", "last"),
            current_mean_mA=("I_mA", "mean"), current_min_mA=("I_mA", "min"),
            current_max_mA=("I_mA", "max"), voltage_start_V=("Ecell_V", "first"),
            voltage_end_V=("Ecell_V", "last"),
        ).reset_index()
        # Bölüm süresi son zaman eksi ilk zamandır; bölümler arası dinlenmeler eklenmez.
        segments["duration_s"] = segments["end_s"] - segments["start_s"]
        segments.insert(0, "source_file", source)
        segment_reports.append(segments)
        print(f"{source}: kalite raporu hazır, {len(segments):,} bölüm adayı")

    # Bütün hücrelerin raporlarını dört ayrı DataFrame olarak bir araya getir.
    reports = {
        "data_quality": pd.DataFrame(quality),
        "column_quality": pd.DataFrame(columns),
        "ns_summary": pd.concat(ns_reports, ignore_index=True) if ns_reports else pd.DataFrame(),
        "segments": pd.concat(segment_reports, ignore_index=True) if segment_reports else pd.DataFrame(),
    }
    # Her raporu adıyla CSV olarak kaydet; DataFrame indeksini dosyaya yazma.
    for name, report in reports.items():
        report.to_csv(output_dir / f"{name}.csv", index=False)
    # Kaydedilen tabloları isteyen çağıranların bellekte de kullanabilmesi için döndür.
    return reports
