"""
Q-Learning Tabanlı Akıllı Sulama Sistemi
========================================

Bu proje, Bursa için Open-Meteo Historical Weather API üzerinden sağlanan
ERA5-Land ve Best Match yeniden analiz verilerini kullanarak günlük sulama
kararı üreten tabular Q-Learning modelini uygular.

Veri ayrımı
-----------
- Hiperparametre eğitimi: 2020-2023
- Doğrulama: 2024
- Nihai eğitim: 2020-2024
- Bağımsız test: 2025

Model; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve
mevsim bilgisini ayrık durum değişkenleri olarak kullanır. Ajan her gün
0, 3, 6 veya 9 mm sulama seçeneklerinden birini seçer. Sulama miktarı için
1 mm = 1 L/m² dönüşümü geçerlidir.

Toprak nemi, günlük su dengesi denklemiyle simüle edilir. ERA5-Land toprak
nemi karşılaştırma amacıyla referans olarak gösterilir; çalışma doğrudan
saha sensörü ölçümü veya fiziksel bir sulama kontrolörü içermez.

Kurulum
-------
pip install numpy pandas matplotlib requests pillow

Çalıştırma
----------
python Akilli_Sulama_Sistemi.py

İlk çalıştırmada veriler indirilerek ``veri/`` klasörüne kaydedilir. Sonraki
çalıştırmalarda doğrulanan yerel CSV dosyaları yeniden kullanılır. Üretilen
model, tablo, grafik ve animasyonlar ``sonuclar/`` klasörüne yazılır.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


# =============================================================================
# 1) GENEL AYARLAR
# =============================================================================

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

LATITUDE = 40.1950
LONGITUDE = 29.0600
TIMEZONE = "Europe/Istanbul"

HYPER_TRAIN_YEARS = [2020, 2021, 2022, 2023]
VALIDATION_YEAR = 2024
TRAIN_YEARS = HYPER_TRAIN_YEARS + [VALIDATION_YEAR]
TEST_YEAR = 2025
ALL_YEARS = TRAIN_YEARS + [TEST_YEAR]

# Hiperparametre seçimi L9 deney düzeniyle daha kısa eğitimler üzerinden yapılır.
# Seçilen kombinasyonla nihai model 4000 eğitim bölümü boyunca yeniden eğitilir.
HYPERPARAMETER_EPISODES = 1200
FINAL_EPISODES = 4000
EPSILON_START = 1.00
EPSILON_MIN = 0.05
MOVING_AVERAGE_WINDOW = 100

# Dashboard animasyonu ayarları
ANIMATION_FRAME_STEP = 5
ANIMATION_FPS = 8
ANIMATION_LOCATION = "Bursa, Türkiye"

# Üç faktörlü ve üç seviyeli L9 ortogonal deney düzeni.
HYPERPARAMETER_GRID: list[dict[str, float]] = [
    {"alpha": 0.10, "gamma": 0.90, "epsilon_decay": 0.9975},
    {"alpha": 0.10, "gamma": 0.95, "epsilon_decay": 0.9985},
    {"alpha": 0.10, "gamma": 0.99, "epsilon_decay": 0.9995},
    {"alpha": 0.15, "gamma": 0.90, "epsilon_decay": 0.9985},
    {"alpha": 0.15, "gamma": 0.95, "epsilon_decay": 0.9995},
    {"alpha": 0.15, "gamma": 0.99, "epsilon_decay": 0.9975},
    {"alpha": 0.25, "gamma": 0.90, "epsilon_decay": 0.9995},
    {"alpha": 0.25, "gamma": 0.95, "epsilon_decay": 0.9975},
    {"alpha": 0.25, "gamma": 0.99, "epsilon_decay": 0.9985},
]

ACTION_WATER_MM = np.array([0.0, 3.0, 6.0, 9.0], dtype=float)
ACTION_NAMES = [
    "Sulama yok",
    "Düşük sulama (3 mm)",
    "Orta sulama (6 mm)",
    "Yüksek sulama (9 mm)",
]
ACTION_SHORT_NAMES = ["Sulama yok", "Düşük", "Orta", "Yüksek"]

# Basitleştirilmiş kök bölgesi su dengesi parametreleri
ROOT_ZONE_DEPTH_MM = 280.0
RAIN_INFILTRATION_EFFICIENCY = 0.75
IRRIGATION_EFFICIENCY = 0.85
CROP_COEFFICIENT = 0.85
DRAINAGE_RATE = 0.35
MAX_EFFECTIVE_DAILY_RAIN_MM = 40.0

# Ödül katsayıları
REWARD_IDEAL_MOISTURE = 25.0
REWARD_ACCEPTABLE_MOISTURE = 7.0
PENALTY_DRY = -12.0
PENALTY_TOO_DRY = -38.0
PENALTY_TOO_WET = -32.0
WATER_COST_PER_MM = 0.35
PENALTY_IRRIGATION_DURING_RAIN = -10.0
PENALTY_IRRIGATION_WHEN_WET = -9.0
PENALTY_NO_IRRIGATION_DRY_HIGH_ET0 = -18.0
REWARD_WATER_SAVING = 4.0
PROGRESS_REWARD_SCALE = 300.0
PROGRESS_REWARD_LIMIT = 12.0

# Birleşik başarı skoru katsayıları
MAX_WATER_PENALTY = 20.0
MAX_STRESS_PENALTY = 25.0
MAX_TOO_WET_PENALTY = 20.0
MAX_EXCESSIVE_IRRIGATION_PENALTY = 10.0

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "veri"
RESULT_DIR = BASE_DIR / "sonuclar"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

FULL_DATA_CSV = DATA_DIR / "bursa_2020_2025_gunluk_gercek_veri.csv"
TRAIN_DATA_CSV = DATA_DIR / "bursa_2020_2024_egitim.csv"
TEST_DATA_CSV = DATA_DIR / "bursa_2025_test.csv"

API_URL = "https://archive-api.open-meteo.com/v1/archive"

# ERA5-Land kaynağından alınan saatlik değişkenler
HOURLY_ERA5_LAND_VARIABLES = [
    "temperature_2m",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm",
]

# Best Match kaynağından ayrıca alınan saatlik değişkenler
HOURLY_BEST_MATCH_VARIABLES = [
    "wind_speed_10m",
    "surface_pressure",
]

# Birleştirilecek tüm saatlik değişkenler
HOURLY_BASE_VARIABLES = HOURLY_ERA5_LAND_VARIABLES + HOURLY_BEST_MATCH_VARIABLES

SOIL_LABELS = ["Çok kuru", "Kuru", "Uygun", "Nemli", "Çok ıslak"]
ET0_LABELS = ["Düşük", "Orta", "Yüksek"]
SEASON_LABELS = ["Kış", "İlkbahar", "Yaz", "Sonbahar"]


# =============================================================================
# 2) VERİ EDİNME, GÜNLÜK TOPLULAŞTIRMA VE DOĞRULAMA
# =============================================================================


def request_json(params: dict[str, object], max_retry: int = 3) -> dict[str, object]:
    """Open-Meteo isteğini tekrar deneme ve açık hata mesajıyla yürütür."""
    last_error: Exception | None = None
    for attempt in range(1, max_retry + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload.get("reason", "Bilinmeyen API hatası")))
            return payload
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < max_retry:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Open-Meteo isteği başarısız oldu. Son hata: {last_error}")


def convert_columns_to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """API sütunlarını güvenli biçimde sayısal türe dönüştürür."""
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            raise ValueError(f"API yanıtında beklenen sütun yok: {column}")
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def et0_is_valid(series: pd.Series, require_half_nonzero: bool = True) -> bool:
    """ET0 serisinin Q-Learning durum değişkeni olarak kullanılabilirliğini sınar."""
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.empty:
        return False
    nan_ratio = float(numeric.isna().mean())
    nonzero_ratio = float((numeric.fillna(0.0) > 0.0).mean())
    max_value = float(numeric.max(skipna=True)) if numeric.notna().any() else 0.0
    if nan_ratio > 0.05 or max_value <= 0.0:
        return False
    if require_half_nonzero and nonzero_ratio < 0.50:
        return False
    return True


def download_hourly_base_one_year(year: int) -> pd.DataFrame:
    """ERA5-Land ve Best Match kaynaklarından saatlik çevre/toprak verilerini indirir.

    wind_speed_10m ve surface_pressure ERA5-Land modelinde bulunmadığından
    bu iki değişken ayrı bir Best Match isteğiyle alınıp birleştirilir.
    """
    # ERA5-Land isteği: sıcaklık ve toprak değişkenleri
    params_era5: dict[str, object] = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(HOURLY_ERA5_LAND_VARIABLES),
        "timezone": TIMEZONE,
        "models": "era5_land",
    }
    payload_era5 = request_json(params_era5)
    hourly_era5 = payload_era5.get("hourly")
    if not isinstance(hourly_era5, dict) or "time" not in hourly_era5:
        raise RuntimeError(f"{year} yılı için ERA5-Land saatlik verisi bulunamadı.")
    frame_era5 = pd.DataFrame(hourly_era5)
    frame_era5["time"] = pd.to_datetime(frame_era5["time"], errors="raise")
    frame_era5 = convert_columns_to_numeric(frame_era5, HOURLY_ERA5_LAND_VARIABLES)

    # Best Match isteği: rüzgâr ve yüzey basıncı
    params_bm: dict[str, object] = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(HOURLY_BEST_MATCH_VARIABLES),
        "timezone": TIMEZONE,
    }
    payload_bm = request_json(params_bm)
    hourly_bm = payload_bm.get("hourly")
    if not isinstance(hourly_bm, dict) or "time" not in hourly_bm:
        raise RuntimeError(f"{year} yılı için Best Match saatlik verisi bulunamadı.")
    frame_bm = pd.DataFrame(hourly_bm)
    frame_bm["time"] = pd.to_datetime(frame_bm["time"], errors="raise")
    frame_bm = convert_columns_to_numeric(frame_bm, HOURLY_BEST_MATCH_VARIABLES)

    # Zaman damgasına göre iki veri kaynağını birleştir.
    merged = frame_era5.merge(frame_bm, on="time", how="left")
    return merged


def aggregate_hourly_base_to_daily(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """Saatlik temel çevre verilerini günlük değerlere dönüştürür."""
    required = {"time", *HOURLY_BASE_VARIABLES}
    missing = required.difference(hourly_df.columns)
    if missing:
        raise ValueError("Eksik saatlik sütunlar: " + ", ".join(sorted(missing)))

    df = hourly_df.copy()
    df["tarih"] = pd.to_datetime(df["time"], errors="raise").dt.normalize()

    daily = (
        df.groupby("tarih", as_index=False)
        .agg(
            sicaklik_ortalama_c=("temperature_2m", "mean"),
            sicaklik_maksimum_c=("temperature_2m", "max"),
            sicaklik_minimum_c=("temperature_2m", "min"),
            ruzgar_ortalama_kmh=("wind_speed_10m", "mean"),
            yuzey_basinci_hpa=("surface_pressure", "mean"),
            toprak_nemi_0_7_m3m3=("soil_moisture_0_to_7cm", "mean"),
            toprak_nemi_7_28_m3m3=("soil_moisture_7_to_28cm", "mean"),
            toprak_sicakligi_0_7_c=("soil_temperature_0_to_7cm", "mean"),
        )
        .sort_values("tarih")
        .reset_index(drop=True)
    )

    numeric_columns = [column for column in daily.columns if column != "tarih"]
    daily[numeric_columns] = daily[numeric_columns].apply(pd.to_numeric, errors="coerce")
    daily[numeric_columns] = (
        daily[numeric_columns]
        .interpolate(method="linear", limit_direction="both")
        .ffill()
        .bfill()
    )
    if daily[numeric_columns].isna().any().any():
        counts = daily[numeric_columns].isna().sum()
        raise ValueError(
            "Günlük temel veride doldurulamayan eksik değerler var:\n"
            + counts[counts > 0].to_string()
        )
    return daily


def parse_daily_et0(payload: dict[str, object], variable_name: str) -> pd.DataFrame | None:
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily:
        return None
    available_name = variable_name if variable_name in daily else None
    if available_name is None:
        for candidate in ("et0_fao_evapotranspiration", "et0_fao_evapotranspiration_sum"):
            if candidate in daily:
                available_name = candidate
                break
    if available_name is None:
        return None
    frame = pd.DataFrame({
        "tarih": pd.to_datetime(daily["time"], errors="raise"),
        "et0_mm": pd.to_numeric(pd.Series(daily[available_name]), errors="coerce"),
    })
    return frame


def download_daily_et0_one_year(year: int) -> pd.DataFrame:
    """ET0'ı Best Match ve yedek modeller üzerinden günlük olarak indirir."""
    attempts: list[tuple[str, str | None]] = [
        ("et0_fao_evapotranspiration", None),
        ("et0_fao_evapotranspiration", "era5"),
        ("et0_fao_evapotranspiration", "era5_land"),
        ("et0_fao_evapotranspiration_sum", None),
        ("et0_fao_evapotranspiration_sum", "era5"),
    ]
    errors: list[str] = []

    for variable_name, model_name in attempts:
        params: dict[str, object] = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "daily": variable_name,
            "timezone": TIMEZONE,
        }
        if model_name:
            params["models"] = model_name
        try:
            payload = request_json(params, max_retry=2)
            frame = parse_daily_et0(payload, variable_name)
            if frame is not None and et0_is_valid(frame["et0_mm"]):
                return frame
            errors.append(f"günlük {variable_name}, model={model_name or 'Best Match'} geçersiz")
        except RuntimeError as exc:
            errors.append(str(exc))

    # Günlük ET0 alınamazsa saatlik değerlerden günlük toplam üret.
    for model_name in (None, "era5", "era5_land"):
        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "hourly": "et0_fao_evapotranspiration",
            "timezone": TIMEZONE,
        }
        if model_name:
            params["models"] = model_name
        try:
            payload = request_json(params, max_retry=2)
            hourly = payload.get("hourly")
            if not isinstance(hourly, dict) or "time" not in hourly or "et0_fao_evapotranspiration" not in hourly:
                continue
            frame = pd.DataFrame(hourly)
            frame["time"] = pd.to_datetime(frame["time"], errors="raise")
            frame["et0"] = pd.to_numeric(frame["et0_fao_evapotranspiration"], errors="coerce")
            frame["tarih"] = frame["time"].dt.normalize()
            daily_frame = frame.groupby("tarih", as_index=False).agg(et0_mm=("et0", "sum"))
            if et0_is_valid(daily_frame["et0_mm"]):
                return daily_frame
        except (RuntimeError, ValueError) as exc:
            errors.append(str(exc))

    raise RuntimeError(
        f"{year} yılı için geçerli ET0 verisi alınamadı. "
        + " | ".join(errors[-5:])
    )


def download_daily_precipitation_one_year(year: int) -> pd.DataFrame:
    """Günlük yağış verisini (precipitation_sum) Best Match olarak indirir."""
    params: dict[str, object] = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "daily": "precipitation_sum",
        "timezone": TIMEZONE,
    }
    payload = request_json(params)
    daily = payload.get("daily")
    if not isinstance(daily, dict) or "time" not in daily or "precipitation_sum" not in daily:
        raise RuntimeError(f"{year} yılı için günlük yağış verisi bulunamadı.")
    
    frame = pd.DataFrame({
        "tarih": pd.to_datetime(daily["time"], errors="raise"),
        "yagis_mm": pd.to_numeric(pd.Series(daily["precipitation_sum"]), errors="coerce"),
    })
    
    if frame["yagis_mm"].isna().any():
        raise ValueError(f"{year} yılı yağış verisinde eksik (NaN) değerler var!")
        
    return frame


def download_one_year(year: int) -> pd.DataFrame:
    """Bir yılın temel ERA5-Land verisini, günlük yağış ve ayrı doğrulanmış ET0 verisini birleştirir."""
    base_hourly = download_hourly_base_one_year(year)
    base_daily = aggregate_hourly_base_to_daily(base_hourly)
    
    # Günlük yağış serisini temel veriyle birleştir.
    rain_daily = download_daily_precipitation_one_year(year)
    merged = base_daily.merge(rain_daily, on="tarih", how="inner", validate="one_to_one")
    if merged["yagis_mm"].isna().any():
        raise ValueError(f"{year} yılı birleştirilmiş yağış verisinde eksik (NaN) değer var!")
        
    et0_daily = download_daily_et0_one_year(year)
    merged = merged.merge(et0_daily, on="tarih", how="left", validate="one_to_one")
    if not et0_is_valid(merged["et0_mm"]):
        raise RuntimeError(f"{year} yılı birleştirilmiş ET0 verisi geçersiz.")
    return merged


def finalize_daily_data(full_df: pd.DataFrame) -> pd.DataFrame:
    """Tarih, yüzde ve takvim sütunlarını ekleyerek veriyi son hâline getirir."""
    result = full_df.copy()
    result["tarih"] = pd.to_datetime(result["tarih"], errors="raise")
    result = result.drop_duplicates(subset=["tarih"]).sort_values("tarih").reset_index(drop=True)

    numeric_columns = [
        "sicaklik_ortalama_c", "sicaklik_maksimum_c", "sicaklik_minimum_c",
        "yagis_mm", "ruzgar_ortalama_kmh", "yuzey_basinci_hpa", "et0_mm",
        "toprak_nemi_0_7_m3m3", "toprak_nemi_7_28_m3m3", "toprak_sicakligi_0_7_c",
    ]
    result[numeric_columns] = result[numeric_columns].apply(pd.to_numeric, errors="coerce")
    result["toprak_nemi_0_7_yuzde"] = result["toprak_nemi_0_7_m3m3"] * 100.0
    result["toprak_nemi_7_28_yuzde"] = result["toprak_nemi_7_28_m3m3"] * 100.0
    result["yil"] = result["tarih"].dt.year
    result["ay"] = result["tarih"].dt.month
    result["yilin_gunu"] = result["tarih"].dt.dayofyear
    return result


def print_et0_statistics(df: pd.DataFrame, title: str) -> None:
    values = pd.to_numeric(df["et0_mm"], errors="coerce")
    print(f"\nET0 VERİ KONTROLÜ — {title}")
    print("-" * 64)
    print(f"Minimum ET0          : {values.min():.4f} mm")
    print(f"Maksimum ET0         : {values.max():.4f} mm")
    print(f"Ortalama ET0         : {values.mean():.4f} mm")
    print(f"Medyan ET0           : {values.median():.4f} mm")
    print(f"Sıfır olmayan gün    : {int((values > 0).sum())} / {len(values)}")
    print(f"Eksik değer oranı    : %{100.0 * values.isna().mean():.2f}")


def validate_full_data(full_df: pd.DataFrame) -> None:
    """Eğitim öncesi veri sızıntısı, eksik veri ve sabit sütun kontrollerini yapar."""
    if full_df.empty:
        raise ValueError("Gerçek veri seti boş.")

    required_columns = {
        "tarih", "yil", "ay", "yilin_gunu", "sicaklik_ortalama_c", "yagis_mm",
        "ruzgar_ortalama_kmh", "et0_mm", "toprak_nemi_7_28_m3m3",
    }
    missing = required_columns.difference(full_df.columns)
    if missing:
        raise ValueError("Gerçek veride eksik sütunlar: " + ", ".join(sorted(missing)))

    numeric_columns = [
        "sicaklik_ortalama_c", "yagis_mm", "ruzgar_ortalama_kmh", "et0_mm",
        "toprak_nemi_7_28_m3m3",
    ]
    for column in numeric_columns:
        converted = pd.to_numeric(full_df[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"{column} sütununda eksik veya sayı olmayan değer var.")

    years = sorted(full_df["yil"].astype(int).unique().tolist())
    if years != ALL_YEARS:
        raise ValueError(f"Beklenen yıllar {ALL_YEARS}, bulunan yıllar {years}.")
    if float(full_df["toprak_nemi_7_28_m3m3"].std()) < 1e-8:
        raise ValueError("Toprak nemi değerleri sabit; veri kullanılamaz.")
    if not et0_is_valid(full_df["et0_mm"]):
        raise RuntimeError("Geçerli ET0 verisi alınamadı.")
    rain = pd.to_numeric(full_df["yagis_mm"], errors="coerce").fillna(0.0)
    if float(rain.max()) < 1e-6:
        raise ValueError(
            "Yağış verisi tamamen sıfır — CSV bozuk ya da eksik indirme var. "
            "Veri yeniden indirilecek."
        )

    train_dates = set(full_df.loc[full_df["yil"].isin(TRAIN_YEARS), "tarih"])
    test_dates = set(full_df.loc[full_df["yil"] == TEST_YEAR, "tarih"])
    if train_dates.intersection(test_dates):
        raise ValueError("Eğitim ve test tarihleri çakışıyor.")
    if (full_df.loc[full_df["yil"].isin(TRAIN_YEARS), "yil"] == TEST_YEAR).any():
        raise ValueError("2025 verisi eğitim dönemine karışmış.")


def load_or_download_data(
    force_download: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Geçerli kayıtlı veriyi yükler; geçersizse otomatik olarak yeniden indirir."""
    full_df: pd.DataFrame | None = None

    if FULL_DATA_CSV.exists() and not force_download:
        try:
            print(f"Kayıtlı gerçek veri kontrol ediliyor: {FULL_DATA_CSV}")
            cached = pd.read_csv(FULL_DATA_CSV, parse_dates=["tarih"])
            cached = finalize_daily_data(cached)
            validate_full_data(cached)
            full_df = cached
            print("Kayıtlı veri doğrulandı ve kullanılacak.")
        except (ValueError, RuntimeError, KeyError) as exc:
            print(f"Kayıtlı veri geçersiz: {exc}")
            print("Gerçek veriler yeniden indirilecek.")

    if full_df is None:
        print("Bursa 2020-2025 gerçek verileri indiriliyor...")
        annual_frames: list[pd.DataFrame] = []
        for year in ALL_YEARS:
            print(f"  {year} yılı indiriliyor...")
            annual_frames.append(download_one_year(year))
        full_df = finalize_daily_data(pd.concat(annual_frames, ignore_index=True))
        validate_full_data(full_df)
        full_df.to_csv(FULL_DATA_CSV, index=False, encoding="utf-8-sig")

    train_df = full_df[full_df["yil"].isin(TRAIN_YEARS)].copy().reset_index(drop=True)
    test_df = full_df[full_df["yil"] == TEST_YEAR].copy().reset_index(drop=True)
    if train_df.empty or test_df.empty:
        raise ValueError("Eğitim veya test verisi boş.")
    if int(train_df["yil"].max()) >= TEST_YEAR:
        raise ValueError("2025 verisi eğitim verisine karışmış.")

    train_df.to_csv(TRAIN_DATA_CSV, index=False, encoding="utf-8-sig")
    test_df.to_csv(TEST_DATA_CSV, index=False, encoding="utf-8-sig")

    print_et0_statistics(train_df, "2020-2024 Eğitim Verisi")
    print(f"\nEğitim verisi: {len(train_df)} gün (2020-2024)")
    print(f"Test verisi   : {len(test_df)} gün (2025)")
    return full_df, train_df, test_df


# =============================================================================
# 3) DURUM UZAYI VE AYRIKLAŞTIRMA EŞİKLERİ
# =============================================================================


@dataclass(frozen=True)
class Thresholds:
    soil_very_dry: float
    soil_dry: float
    soil_target_high: float
    soil_very_wet: float
    soil_min: float
    soil_max: float
    temp_low: float
    temp_high: float
    et0_low: float
    et0_high: float


def calculate_thresholds(train_df: pd.DataFrame) -> Thresholds:
    """Bütün sınırları yalnızca 2020-2024 eğitim verisinden hesaplar."""
    if (train_df["yil"] == TEST_YEAR).any():
        raise ValueError("Eşik hesaplamasına 2025 test verisi karıştı.")

    soil = pd.to_numeric(train_df["toprak_nemi_7_28_m3m3"], errors="raise")
    temp = pd.to_numeric(train_df["sicaklik_ortalama_c"], errors="raise")
    et0 = pd.to_numeric(train_df["et0_mm"], errors="raise")

    th = Thresholds(
        soil_very_dry=float(soil.quantile(0.10)),
        soil_dry=float(soil.quantile(0.30)),
        soil_target_high=float(soil.quantile(0.70)),
        soil_very_wet=float(soil.quantile(0.90)),
        soil_min=max(0.01, float(soil.min()) - 0.04),
        soil_max=min(0.70, float(soil.max()) + 0.04),
        temp_low=float(temp.quantile(1 / 3)),
        temp_high=float(temp.quantile(2 / 3)),
        et0_low=float(et0.quantile(1 / 3)),
        et0_high=float(et0.quantile(2 / 3)),
    )
    if not (th.et0_high > th.et0_low >= 0.0):
        raise RuntimeError(
            f"ET0 eşikleri geçersiz: {th.et0_low:.4f} / {th.et0_high:.4f} mm"
        )
    if not (th.soil_very_dry < th.soil_dry < th.soil_target_high < th.soil_very_wet):
        raise RuntimeError("Toprak nemi eşikleri birbirinden ayrışmıyor.")
    return th


def soil_to_state(value: float, th: Thresholds) -> int:
    return int(np.digitize(
        value,
        [th.soil_very_dry, th.soil_dry, th.soil_target_high, th.soil_very_wet],
        right=False,
    ))


def rain_to_state(value_mm: float) -> int:
    if value_mm < 0.1:
        return 0
    if value_mm < 5.0:
        return 1
    return 2


def temperature_to_state(value_c: float, th: Thresholds) -> int:
    if value_c < th.temp_low:
        return 0
    if value_c < th.temp_high:
        return 1
    return 2


def et0_to_state(value_mm: float, th: Thresholds) -> int:
    if value_mm < th.et0_low:
        return 0
    if value_mm < th.et0_high:
        return 1
    return 2


def month_to_season(month: int) -> int:
    if month in (12, 1, 2):
        return 0
    if month in (3, 4, 5):
        return 1
    if month in (6, 7, 8):
        return 2
    return 3


def make_state(
    soil_moisture: float,
    row: pd.Series,
    th: Thresholds,
) -> tuple[int, int, int, int, int]:
    return (
        soil_to_state(soil_moisture, th),
        rain_to_state(float(row["yagis_mm"])),
        temperature_to_state(float(row["sicaklik_ortalama_c"]), th),
        et0_to_state(float(row["et0_mm"]), th),
        month_to_season(int(row["ay"])),
    )


# =============================================================================
# 4) SU DENGESİ GEÇİŞİ VE ÖDÜL FONKSİYONU
# =============================================================================


def update_soil_moisture(
    current_moisture: float,
    row: pd.Series,
    irrigation_mm: float,
    th: Thresholds,
) -> float:
    """Yağış, sulama, ET0 ve drenaja göre sonraki toprak nemini hesaplar."""
    rain_mm = max(0.0, float(row["yagis_mm"]))
    et0_mm = max(0.0, float(row["et0_mm"]))

    effective_rain = min(rain_mm, MAX_EFFECTIVE_DAILY_RAIN_MM) * RAIN_INFILTRATION_EFFICIENCY
    effective_irrigation = irrigation_mm * IRRIGATION_EFFICIENCY
    evapotranspiration_loss = et0_mm * CROP_COEFFICIENT

    delta_theta = (
        effective_rain + effective_irrigation - evapotranspiration_loss
    ) / ROOT_ZONE_DEPTH_MM
    next_moisture = current_moisture + delta_theta

    if next_moisture > th.soil_target_high:
        excess = next_moisture - th.soil_target_high
        next_moisture -= DRAINAGE_RATE * excess

    return float(np.clip(next_moisture, th.soil_min, th.soil_max))


def calculate_reward(
    current_moisture: float,
    next_moisture: float,
    row: pd.Series,
    irrigation_mm: float,
    th: Thresholds,
) -> float:
    """Nem durumu, su maliyeti ve hedef merkeze ilerlemeyi birlikte puanlar."""
    next_state = soil_to_state(next_moisture, th)
    state_rewards = {
        0: PENALTY_TOO_DRY,
        1: PENALTY_DRY,
        2: REWARD_IDEAL_MOISTURE,
        3: REWARD_ACCEPTABLE_MOISTURE,
        4: PENALTY_TOO_WET,
    }
    reward = float(state_rewards[next_state])
    reward -= WATER_COST_PER_MM * irrigation_mm

    rain_mm = float(row["yagis_mm"])
    et0_mm = float(row["et0_mm"])

    if rain_mm >= 5.0 and irrigation_mm > 0.0:
        reward += PENALTY_IRRIGATION_DURING_RAIN
    if current_moisture >= th.soil_target_high and irrigation_mm > 0.0:
        reward += PENALTY_IRRIGATION_WHEN_WET
    if current_moisture < th.soil_dry and et0_mm >= th.et0_high and irrigation_mm == 0.0:
        reward += PENALTY_NO_IRRIGATION_DRY_HIGH_ET0
    if th.soil_dry <= current_moisture <= th.soil_target_high and irrigation_mm == 0.0:
        reward += REWARD_WATER_SAVING

    target_center = (th.soil_dry + th.soil_target_high) / 2.0
    previous_distance = abs(current_moisture - target_center)
    next_distance = abs(next_moisture - target_center)
    progress = previous_distance - next_distance
    progress_reward = float(np.clip(
        progress * PROGRESS_REWARD_SCALE,
        -PROGRESS_REWARD_LIMIT,
        PROGRESS_REWARD_LIMIT,
    ))
    reward += progress_reward
    return float(reward)


# =============================================================================
# 5) Q-LEARNING EĞİTİMİ VE İZLEME METRİKLERİ
# =============================================================================


def random_argmax(values: np.ndarray, rng: np.random.Generator) -> int:
    max_value = np.max(values)
    candidates = np.flatnonzero(np.isclose(values, max_value))
    return int(rng.choice(candidates))


def moving_average(values: list[float] | pd.Series, window: int = 100) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if len(array) < window:
        return array
    return np.convolve(array, np.ones(window) / window, mode="valid")


def train_q_learning(
    train_df: pd.DataFrame,
    th: Thresholds,
    *,
    alpha: float,
    gamma: float,
    epsilon_decay: float,
    episodes: int,
    training_years: list[int],
    seed: int = SEED,
    verbose: bool = True,
    run_label: str = "Q-Learning eğitimi",
) -> tuple[np.ndarray, pd.DataFrame]:
    """Belirtilen yıllar ve hiperparametrelerle Q-Learning modelini eğitir."""
    if episodes <= 0:
        raise ValueError("Episode sayısı sıfırdan büyük olmalıdır.")
    if not (0.0 < alpha <= 1.0):
        raise ValueError(f"Geçersiz öğrenme oranı alpha={alpha}")
    if not (0.0 <= gamma <= 1.0):
        raise ValueError(f"Geçersiz indirim faktörü gamma={gamma}")
    if not (0.0 < epsilon_decay <= 1.0):
        raise ValueError(f"Geçersiz epsilon decay={epsilon_decay}")

    years = sorted({int(year) for year in training_years})
    if not years:
        raise ValueError("Q-Learning eğitimi için en az bir yıl gereklidir.")
    if TEST_YEAR in years or (train_df["yil"] == TEST_YEAR).any():
        raise ValueError("2025 bağımsız test yılı Q-Learning eğitimine karıştı.")

    yearly_data: dict[int, pd.DataFrame] = {}
    for year in years:
        year_df = train_df[train_df["yil"] == year].copy().reset_index(drop=True)
        if year_df.empty:
            raise ValueError(f"Eğitim verisinde {year} yılı bulunamadı.")
        yearly_data[year] = year_df

    q_table = np.zeros((5, 3, 3, 3, 4, len(ACTION_WATER_MM)), dtype=float)
    history: list[dict[str, float | int | str]] = []
    epsilon = EPSILON_START
    rng = np.random.default_rng(seed)

    if verbose:
        print(f"\n{run_label} başlıyor...")
        print(
            f"Yıllar: {years} | episode: {episodes} | "
            f"alpha: {alpha:.4f} | gamma: {gamma:.4f} | "
            f"epsilon decay: {epsilon_decay:.4f}"
        )

    print_interval = 500 if episodes >= 500 else max(1, episodes // 4)

    for episode in range(episodes):
        selected_year = int(rng.choice(years))
        episode_df = yearly_data[selected_year]
        initial_real = float(episode_df.iloc[0]["toprak_nemi_7_28_m3m3"])
        soil_moisture = float(np.clip(
            initial_real + rng.normal(0.0, 0.008),
            th.soil_min,
            th.soil_max,
        ))

        total_reward = 0.0
        total_water = 0.0
        ideal_days = 0
        acceptable_days = 0
        stress_days = 0
        too_wet_days = 0
        abs_td_errors: list[float] = []

        for index in range(len(episode_df)):
            row = episode_df.iloc[index]
            state = make_state(soil_moisture, row, th)
            if rng.random() < epsilon:
                action = int(rng.integers(0, len(ACTION_WATER_MM)))
            else:
                action = random_argmax(q_table[state], rng)

            irrigation_mm = float(ACTION_WATER_MM[action])
            next_moisture = update_soil_moisture(soil_moisture, row, irrigation_mm, th)
            reward = calculate_reward(soil_moisture, next_moisture, row, irrigation_mm, th)

            terminal = index == len(episode_df) - 1
            current_q = float(q_table[state + (action,)])
            if terminal:
                target_q = reward
            else:
                next_row = episode_df.iloc[index + 1]
                next_state = make_state(next_moisture, next_row, th)
                target_q = reward + gamma * float(np.max(q_table[next_state]))

            td_error = target_q - current_q
            q_table[state + (action,)] = current_q + alpha * td_error

            total_reward += reward
            total_water += irrigation_mm
            abs_td_errors.append(abs(td_error))
            soil_state = soil_to_state(next_moisture, th)
            ideal_days += int(soil_state == 2)
            acceptable_days += int(soil_state in (2, 3))
            stress_days += int(soil_state in (0, 1))
            too_wet_days += int(soil_state == 4)
            soil_moisture = next_moisture

        days = len(episode_df)
        history.append({
            "egitim_adi": run_label,
            "episode": episode + 1,
            "secilen_yil": selected_year,
            "alpha": alpha,
            "gamma": gamma,
            "epsilon_decay": epsilon_decay,
            "toplam_odul": total_reward,
            "toplam_su_mm": total_water,
            "ideal_nem_orani_yuzde": 100.0 * ideal_days / days,
            "kabul_edilebilir_nem_orani_yuzde": 100.0 * acceptable_days / days,
            "stresli_gun": stress_days,
            "cok_islak_gun": too_wet_days,
            "ortalama_mutlak_td_hatasi": float(np.mean(abs_td_errors)),
            "epsilon": epsilon,
        })

        epsilon = max(EPSILON_MIN, epsilon * epsilon_decay)
        if verbose and ((episode + 1) % print_interval == 0 or episode + 1 == episodes):
            recent = pd.DataFrame(history[-min(100, len(history)):])
            print(
                f"Episode {episode + 1:4d}/{episodes} | "
                f"Ödül: {recent['toplam_odul'].mean():8.2f} | "
                f"Su: {recent['toplam_su_mm'].mean():7.2f} mm | "
                f"TD: {recent['ortalama_mutlak_td_hatasi'].mean():6.2f} | "
                f"epsilon: {epsilon:.3f}"
            )

    if verbose:
        print(f"{run_label} tamamlandı.")
    return q_table, pd.DataFrame(history)


# =============================================================================
# 6) REFERANS SULAMA POLİTİKALARI
# =============================================================================


PolicyFunction = Callable[[float, pd.Series, int, Thresholds], int]


def q_learning_policy_factory(q_table: np.ndarray) -> PolicyFunction:
    """Testte keşif yapmadan deterministik en iyi aksiyonu seçer."""
    def policy(soil_moisture: float, row: pd.Series, day_index: int, th: Thresholds) -> int:
        del day_index
        state = make_state(soil_moisture, row, th)
        return int(np.argmax(q_table[state]))
    return policy


def threshold_policy(
    soil_moisture: float,
    row: pd.Series,
    day_index: int,
    th: Thresholds,
) -> int:
    del day_index
    if float(row["yagis_mm"]) >= 5.0:
        return 0
    if soil_moisture < th.soil_very_dry:
        return 3
    if soil_moisture < th.soil_dry:
        return 2
    return 0


def fixed_schedule_policy(
    soil_moisture: float,
    row: pd.Series,
    day_index: int,
    th: Thresholds,
) -> int:
    del soil_moisture, th
    if day_index % 4 == 0 and float(row["yagis_mm"]) < 5.0:
        return 2
    return 0


def no_irrigation_policy(
    soil_moisture: float,
    row: pd.Series,
    day_index: int,
    th: Thresholds,
) -> int:
    del soil_moisture, row, day_index, th
    return 0


# =============================================================================
# 7) SİMÜLASYON, PERFORMANS METRİKLERİ VE BAŞARI SKORU
# =============================================================================


def simulate_policy(
    name: str,
    policy: PolicyFunction,
    year_df: pd.DataFrame,
    th: Thresholds,
    period_label: str,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Bir politikayı verilen yılın gerçek dışsal çevre verileri üzerinde çalıştırır."""
    if year_df.empty:
        raise ValueError(f"{name} için simülasyon verisi boş.")

    year = int(year_df.iloc[0]["yil"])
    soil_moisture = float(year_df.iloc[0]["toprak_nemi_7_28_m3m3"])
    logs: list[dict[str, object]] = []
    cumulative_reward = 0.0

    for index, row in year_df.reset_index(drop=True).iterrows():
        current_moisture = soil_moisture
        action = int(policy(current_moisture, row, index, th))
        if action < 0 or action >= len(ACTION_WATER_MM):
            raise ValueError(f"Geçersiz aksiyon: {action}")
        irrigation_mm = float(ACTION_WATER_MM[action])
        next_moisture = update_soil_moisture(current_moisture, row, irrigation_mm, th)
        reward = calculate_reward(current_moisture, next_moisture, row, irrigation_mm, th)
        cumulative_reward += reward
        state = soil_to_state(next_moisture, th)
        excessive_irrigation = bool(
            irrigation_mm > 0.0
            and (
                current_moisture >= th.soil_target_high
                or next_moisture > th.soil_very_wet
                or float(row["yagis_mm"]) >= 5.0
            )
        )
        logs.append({
            "tarih": row["tarih"],
            "yil": year,
            "ay": int(row["ay"]),
            "veri_donemi": period_label,
            "yontem": name,
            "gercek_toprak_nemi_m3m3": float(row["toprak_nemi_7_28_m3m3"]),
            "simule_toprak_nemi_m3m3": next_moisture,
            "simule_toprak_nemi_yuzde": next_moisture * 100.0,
            "toprak_durumu_no": state,
            "toprak_durumu": SOIL_LABELS[state],
            "sicaklik_c": float(row["sicaklik_ortalama_c"]),
            "yagis_mm": float(row["yagis_mm"]),
            "et0_mm": float(row["et0_mm"]),
            "ruzgar_kmh": float(row["ruzgar_ortalama_kmh"]),
            "aksiyon": ACTION_NAMES[action],
            "aksiyon_no": action,
            "sulama_mm": irrigation_mm,
            "sulama_litre_m2": irrigation_mm,
            "asiri_sulama": excessive_irrigation,
            "gunluk_odul": reward,
            "kumulatif_odul": cumulative_reward,
        })
        soil_moisture = next_moisture

    log_df = pd.DataFrame(logs)
    states = log_df["toprak_durumu_no"]
    day_count = len(log_df)
    very_dry_days = int((states == 0).sum())
    dry_days = int((states == 1).sum())
    ideal_days = int((states == 2).sum())
    moist_days = int((states == 3).sum())
    very_wet_days = int((states == 4).sum())
    acceptable_days = ideal_days + moist_days

    metrics: dict[str, float | int | str] = {
        "Yıl": year,
        "Veri dönemi": period_label,
        "Yöntem": name,
        "Toplam sulama (mm = L/m²)": round(float(log_df["sulama_mm"].sum()), 2),
        "Sulama yapılan gün": int((log_df["sulama_mm"] > 0).sum()),
        "İdeal nem oranı (%)": round(100.0 * ideal_days / day_count, 2),
        "Kabul edilebilir nem oranı (%)": round(100.0 * acceptable_days / day_count, 2),
        "Çok kuru gün": very_dry_days,
        "Kuru gün": dry_days,
        "İdeal nemli gün": ideal_days,
        "Kabul edilebilir nemli gün": acceptable_days,
        "Nemli gün": moist_days,
        "Çok ıslak gün": very_wet_days,
        "Su stresi görülen gün": very_dry_days + dry_days,
        "Aşırı sulama görülen gün": int(log_df["asiri_sulama"].sum()),
        "Ortalama toprak nemi (%)": round(float(log_df["simule_toprak_nemi_yuzde"].mean()), 2),
        "Toplam ödül": round(float(log_df["gunluk_odul"].sum()), 2),
    }
    return log_df, metrics


def add_success_scores(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Aynı yıl içindeki yöntemleri karşılaştırmak için birleşik başarı skoru ekler."""
    result = metrics_df.copy()
    result["Normalize edilmiş su cezası"] = 0.0
    result["Stres cezası"] = 0.0
    result["Çok ıslak gün cezası"] = 0.0
    result["Aşırı sulama cezası"] = 0.0
    result["Başarı puanı"] = 0.0

    for year, indices in result.groupby("Yıl").groups.items():
        subset = result.loc[indices]
        max_water = max(float(subset["Toplam sulama (mm = L/m²)"].max()), 1.0)
        days = 366.0 if int(year) % 4 == 0 else 365.0

        water_penalty = MAX_WATER_PENALTY * subset["Toplam sulama (mm = L/m²)"] / max_water
        stress_penalty = MAX_STRESS_PENALTY * subset["Su stresi görülen gün"] / days
        wet_penalty = MAX_TOO_WET_PENALTY * subset["Çok ıslak gün"] / days
        excessive_irrigation_penalty = (
            MAX_EXCESSIVE_IRRIGATION_PENALTY
            * subset["Aşırı sulama görülen gün"]
            / days
        )
        score = (
            subset["Kabul edilebilir nem oranı (%)"]
            + 0.5 * subset["İdeal nem oranı (%)"]
            - water_penalty
            - stress_penalty
            - wet_penalty
            - excessive_irrigation_penalty
        )
        result.loc[indices, "Normalize edilmiş su cezası"] = water_penalty.round(3)
        result.loc[indices, "Stres cezası"] = stress_penalty.round(3)
        result.loc[indices, "Çok ıslak gün cezası"] = wet_penalty.round(3)
        result.loc[indices, "Aşırı sulama cezası"] = excessive_irrigation_penalty.round(3)
        result.loc[indices, "Başarı puanı"] = score.round(3)
    return result


# =============================================================================
# 8) HİPERPARAMETRE SEÇİMİ VE DOĞRULAMA
# =============================================================================


def run_hyperparameter_search(
    full_df: pd.DataFrame,
    *,
    episodes: int = HYPERPARAMETER_EPISODES,
) -> tuple[dict[str, float], pd.DataFrame]:
    """2020-2023 ile eğitir, 2024 doğrulamasıyla en iyi kombinasyonu seçer."""
    hyper_train_df = full_df[
        full_df["yil"].isin(HYPER_TRAIN_YEARS)
    ].copy().reset_index(drop=True)
    validation_df = full_df[
        full_df["yil"] == VALIDATION_YEAR
    ].copy().reset_index(drop=True)

    if hyper_train_df.empty or validation_df.empty:
        raise ValueError("Hiperparametre eğitimi veya doğrulama verisi boş.")
    if (hyper_train_df["yil"] >= VALIDATION_YEAR).any():
        raise ValueError("2024 doğrulama verisi hiperparametre eğitimine karıştı.")
    if (validation_df["yil"] == TEST_YEAR).any():
        raise ValueError("2025 test verisi hiperparametre seçimine karıştı.")

    # Veri sızıntısını önlemek için doğrulama eşikleri yalnızca 2020-2023 döneminden hesaplanır.
    validation_thresholds = calculate_thresholds(hyper_train_df)
    records: list[dict[str, float | int | str]] = []

    print("\n" + "=" * 104)
    print("HİPERPARAMETRE ARAMASI — 2020-2023 EĞİTİM / 2024 DOĞRULAMA")
    print("=" * 104)
    print(
        f"Dengeli L9 deney tasarımı: {len(HYPERPARAMETER_GRID)} kombinasyon, "
        f"her kombinasyon {episodes} episode."
    )

    for trial_no, config in enumerate(HYPERPARAMETER_GRID, start=1):
        alpha = float(config["alpha"])
        gamma = float(config["gamma"])
        epsilon_decay = float(config["epsilon_decay"])
        label = f"Deney {trial_no:02d}"

        q_table, _ = train_q_learning(
            hyper_train_df,
            validation_thresholds,
            alpha=alpha,
            gamma=gamma,
            epsilon_decay=epsilon_decay,
            episodes=episodes,
            training_years=HYPER_TRAIN_YEARS,
            seed=SEED,
            verbose=False,
            run_label=label,
        )
        _, metrics = simulate_policy(
            label,
            q_learning_policy_factory(q_table),
            validation_df,
            validation_thresholds,
            "Doğrulama dönemi",
        )
        metrics.update({
            "Deney": label,
            "Alpha": alpha,
            "Gamma": gamma,
            "Epsilon decay": epsilon_decay,
            "Hiperparametre episode sayısı": episodes,
            "Seed": SEED,
        })
        records.append(metrics)
        print(
            f"{label} | alpha={alpha:.2f} | gamma={gamma:.2f} | "
            f"decay={epsilon_decay:.4f} | ödül={float(metrics['Toplam ödül']):8.2f} | "
            f"kabul edilebilir nem=%{float(metrics['Kabul edilebilir nem oranı (%)']):5.2f} | "
            f"su={float(metrics['Toplam sulama (mm = L/m²)']):6.1f} mm"
        )

    comparison = add_success_scores(pd.DataFrame(records))
    comparison = comparison.sort_values(
        by=[
            "Başarı puanı",
            "Toplam ödül",
            "Kabul edilebilir nem oranı (%)",
            "Su stresi görülen gün",
            "Toplam sulama (mm = L/m²)",
        ],
        ascending=[False, False, False, True, True],
    ).reset_index(drop=True)
    comparison["Sıra"] = np.arange(1, len(comparison) + 1)
    comparison["Seçildi"] = comparison["Sıra"].eq(1)

    ordered_columns = [
        "Sıra", "Seçildi", "Deney", "Alpha", "Gamma", "Epsilon decay",
        "Hiperparametre episode sayısı", "Seed", "Yıl", "Veri dönemi",
        "Toplam sulama (mm = L/m²)", "Sulama yapılan gün",
        "İdeal nem oranı (%)", "Kabul edilebilir nem oranı (%)",
        "Su stresi görülen gün", "Çok ıslak gün", "Aşırı sulama görülen gün",
        "Toplam ödül",
        "Normalize edilmiş su cezası", "Stres cezası",
        "Çok ıslak gün cezası", "Aşırı sulama cezası", "Başarı puanı",
    ]
    comparison = comparison[ordered_columns]
    comparison.to_csv(
        RESULT_DIR / "hiperparametre_karsilastirmasi.csv",
        index=False,
        encoding="utf-8-sig",
    )

    best = comparison.iloc[0]
    selected = {
        "alpha": float(best["Alpha"]),
        "gamma": float(best["Gamma"]),
        "epsilon_decay": float(best["Epsilon decay"]),
    }
    selected_payload: dict[str, object] = {
        "secim_yontemi": "2024 doğrulama yılında en yüksek birleşik başarı puanı",
        "deney_tasarimi": "Dokuz kontrollü hiperparametre kombinasyonu",
        "hiperparametre_egitim_yillari": HYPER_TRAIN_YEARS,
        "dogrulama_yili": VALIDATION_YEAR,
        "nihai_egitim_yillari": TRAIN_YEARS,
        "bagimsiz_test_yili": TEST_YEAR,
        "denenen_kombinasyon_sayisi": len(HYPERPARAMETER_GRID),
        "her_deney_episode_sayisi": episodes,
        "nihai_egitim_episode_sayisi": FINAL_EPISODES,
        "seed": SEED,
        "secilen_deney": str(best["Deney"]),
        "alpha": selected["alpha"],
        "gamma": selected["gamma"],
        "epsilon_decay": selected["epsilon_decay"],
        "dogrulama_basarisi": {
            "toplam_sulama_mm": float(best["Toplam sulama (mm = L/m²)"]),
            "ideal_nem_orani_yuzde": float(best["İdeal nem oranı (%)"]),
            "kabul_edilebilir_nem_orani_yuzde": float(best["Kabul edilebilir nem oranı (%)"]),
            "su_stresi_gun": int(best["Su stresi görülen gün"]),
            "cok_islak_gun": int(best["Çok ıslak gün"]),
            "asiri_sulama_gun": int(best["Aşırı sulama görülen gün"]),
            "toplam_odul": float(best["Toplam ödül"]),
            "birlesik_basari_puani": float(best["Başarı puanı"]),
        },
        "not": (
            "2025 verisi hiperparametre seçimi sırasında kullanılmamıştır. "
            "Seçilen değerlerle model 2020-2024 verisinin tamamında yeniden eğitilir."
        ),
    }
    (RESULT_DIR / "secilen_hiperparametreler.json").write_text(
        json.dumps(selected_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nHİPERPARAMETRE KARŞILAŞTIRMA SONUCU")
    print("-" * 104)
    print(
        comparison[[
            "Sıra", "Deney", "Alpha", "Gamma", "Epsilon decay",
            "Toplam sulama (mm = L/m²)", "Kabul edilebilir nem oranı (%)",
            "Su stresi görülen gün", "Aşırı sulama görülen gün",
            "Toplam ödül", "Başarı puanı",
        ]].to_string(index=False)
    )
    print("-" * 104)
    print(
        f"Seçilen kombinasyon: {best['Deney']} | alpha={selected['alpha']:.2f} | "
        f"gamma={selected['gamma']:.2f} | epsilon decay={selected['epsilon_decay']:.4f}"
    )
    print("2025 bağımsız test verisi seçim aşamasında kullanılmadı.")
    return selected, comparison


# =============================================================================
# 9) SONUÇLARIN KAYDI VE GÖRSELLEŞTİRME
# =============================================================================


def cleanup_old_results() -> None:
    """Önceki çalıştırmadan kalan sonuç dosyalarını temizler."""
    for pattern in ("grafik_*.png", "animasyon_*.gif", "*.csv", "*.npy", "*.json"):
        for path in RESULT_DIR.glob(pattern):
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass

    # Eski sürümlerden kalmış ayrıntılı veri klasörünü de temizle.
    old_detail_dir = RESULT_DIR / "ayrintili_veriler"
    if old_detail_dir.exists():
        for path in old_detail_dir.glob("*"):
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass
        try:
            old_detail_dir.rmdir()
        except OSError:
            pass

def save_thresholds(th: Thresholds) -> None:
    payload = asdict(th)
    payload.update({
        "birim": "Toprak nemi m3/m3, sıcaklık °C, ET0 mm",
        "not": "Bütün eşikler yalnızca 2020-2024 eğitim verisinden hesaplanmıştır.",
    })
    (RESULT_DIR / "ayriklastirma_esikleri.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_training_graph(training_history: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    x = training_history["episode"]

    graph_specs = [
        (axes[0, 0], "toplam_odul", "Toplam Ödül", "Ödül"),
        (axes[0, 1], "toplam_su_mm", "Toplam Kullanılan Su", "Su (mm)"),
        (axes[1, 0], "epsilon", "Epsilon (Keşif Oranı)", "Epsilon"),
        (axes[1, 1], "ortalama_mutlak_td_hatasi", "Ortalama Mutlak TD Hatası", "TD Hatası"),
    ]
    for axis, column, title, ylabel in graph_specs:
        axis.plot(x, training_history[column], alpha=0.25, label="Episode değeri")
        if column != "epsilon":
            smooth = moving_average(training_history[column], MOVING_AVERAGE_WINDOW)
            start = len(training_history) - len(smooth)
            axis.plot(x.iloc[start:], smooth, label="100 episode hareketli ortalama")
        axis.set_title(title)
        axis.set_xlabel("Episode")
        axis.set_ylabel(ylabel)
        axis.grid(True)
        axis.legend()
    fig.suptitle("Q-Learning Eğitim Süreci (2020-2024)")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_1_egitim_paneli.png", dpi=300)
    plt.close(fig)


def save_2025_daily_behavior(log_df: pd.DataFrame, th: Thresholds) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(17, 12), sharex=True)
    axes[0].plot(log_df["tarih"], log_df["simule_toprak_nemi_yuzde"], label="Simüle toprak nemi")
    axes[0].plot(log_df["tarih"], 100.0 * log_df["gercek_toprak_nemi_m3m3"], linestyle="--", alpha=0.7, label="ERA5-Land referans toprak nemi")
    axes[0].axhline(th.soil_dry * 100.0, linestyle=":", label="İdeal nem alt sınırı")
    axes[0].axhline(th.soil_target_high * 100.0, linestyle=":", label="İdeal nem üst sınırı")
    axes[0].axhline(th.soil_very_wet * 100.0, linestyle=":", label="Çok ıslak sınırı")
    axes[0].set_ylabel("Toprak Nemi (%)")
    axes[0].set_title("Toprak Nemi Değişimi")
    axes[0].grid(True)
    axes[0].legend(ncol=2)

    axes[1].bar(log_df["tarih"], log_df["yagis_mm"], alpha=0.55, label="Yağış")
    axes[1].bar(log_df["tarih"], log_df["sulama_mm"], alpha=0.55, label="Sulama")
    axes[1].set_ylabel("Miktar (mm)")
    axes[1].set_title("Yağış ve Sulama Miktarı")
    axes[1].grid(True)
    axes[1].legend()

    axes[2].plot(log_df["tarih"], log_df["sicaklik_c"], label="Sıcaklık (°C)")
    axes[2].plot(log_df["tarih"], log_df["et0_mm"], linestyle="--", label="ET0 (mm)")
    axes[2].set_ylabel("Değer")
    axes[2].set_xlabel("Tarih")
    axes[2].set_title("Sıcaklık ve Referans Evapotranspirasyon")
    axes[2].grid(True)
    axes[2].legend()

    fig.suptitle("Q-Learning Ajanı 2025 Görülmemiş Test Yılı Günlük Davranışı")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_2_q_learning_gunluk_davranis.png", dpi=300)
    plt.close(fig)



def save_visual_irrigation_dashboard(
    log_df: pd.DataFrame,
    th: Thresholds,
) -> None:
    """2025 test yılı için kırpılmış ve kart tabanlı sulama dashboard animasyonu üretir."""
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Polygon, Rectangle

    df = log_df.sort_values("tarih").reset_index(drop=True).copy()
    if df.empty:
        raise ValueError("Görsel GIF için 2025 günlük kayıtları bulunamadı.")

    dates = pd.to_datetime(df["tarih"])
    moisture = df["simule_toprak_nemi_yuzde"].to_numpy(dtype=float)
    temperature = df["sicaklik_c"].to_numpy(dtype=float)
    et0 = df["et0_mm"].to_numpy(dtype=float)
    rainfall = df["yagis_mm"].to_numpy(dtype=float)
    irrigation = df["sulama_mm"].to_numpy(dtype=float)
    actions = df["aksiyon"].astype(str).to_numpy()

    frames = list(range(0, len(df), ANIMATION_FRAME_STEP))
    if frames[-1] != len(df) - 1:
        frames.append(len(df) - 1)

    # Boş gökyüzünü azaltan kompakt kadraj; alt toprak zemini tüm genişlikte sürer.
    # Çıktı boyutu 1600x800 yerine yaklaşık 1420x700 pikseldir.
    fig = plt.figure(figsize=(14.2, 7.0), facecolor="#eef8ff")
    axis = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    axis.set_xlim(0.75, 14.92)
    axis.set_ylim(1.45, 8.45)
    axis.axis("off")

    scene_right = 10.8
    SHOW_BOTTOM_CARDS = False  # Bilgi kutucukları sağ panele taşındı; alt panel kapalı.

    # ------------------------------------------------------------------
    # Yardımcı ikon çizimleri
    # ------------------------------------------------------------------
    def add_icon(kind: str, cx: float, cy: float, scale: float = 1.0) -> list[object]:
        artists: list[object] = []
        navy = "#1b4f91"
        blue = "#2d8ee8"
        orange = "#f2a11f"
        green = "#3f9d4c"
        red = "#e4593f"
        dark = "#25384a"

        if kind == "calendar":
            body = FancyBboxPatch(
                (cx - 0.17 * scale, cy - 0.15 * scale),
                0.34 * scale, 0.30 * scale,
                boxstyle=f"round,pad=0.01,rounding_size={0.03 * scale}",
                facecolor="#ffffff", edgecolor=navy, linewidth=1.5,
            )
            axis.add_patch(body)
            axis.add_patch(Rectangle(
                (cx - 0.17 * scale, cy + 0.04 * scale),
                0.34 * scale, 0.08 * scale,
                facecolor=blue, edgecolor=navy, linewidth=1.0,
            ))
            for dx in (-0.09, 0.0, 0.09):
                for dy in (-0.06, 0.0):
                    axis.add_patch(Rectangle(
                        (cx + dx * scale - 0.018 * scale, cy + dy * scale - 0.018 * scale),
                        0.036 * scale, 0.036 * scale,
                        facecolor=navy, edgecolor="none",
                    ))
            artists.append(body)

        elif kind == "droplet":
            # Toprak nemi ikonu: zemin kesiti ve nem dalgası
            soil_brown = "#8B5E3C"
            soil_dark  = "#5C3A1E"
            wave_blue  = "#3aa3e8"
            w2 = 0.20 * scale
            h_top = 0.09 * scale
            h_bot = 0.17 * scale
            # Zemin yüzeyi
            axis.add_patch(FancyBboxPatch(
                (cx - w2, cy),
                2 * w2, h_top,
                boxstyle=f"round,pad=0.004,rounding_size={0.012 * scale}",
                facecolor="#d6edd9", edgecolor=soil_dark, linewidth=1.1,
            ))
            # Toprak katmanı
            axis.add_patch(FancyBboxPatch(
                (cx - w2, cy - h_bot),
                2 * w2, h_bot,
                boxstyle=f"round,pad=0.004,rounding_size={0.012 * scale}",
                facecolor=soil_brown, edgecolor=soil_dark, linewidth=1.1,
            ))
            # Katman sınırı
            axis.plot([cx - w2, cx + w2], [cy, cy], color=soil_dark, linewidth=1.0)
            # Toprak içindeki nem dalgası
            wave_xs = np.linspace(cx - w2 + 0.015 * scale, cx + w2 - 0.015 * scale, 30)
            wave_ys = (cy - 0.09 * scale) + 0.025 * scale * np.sin(np.linspace(0, 2.5 * np.pi, 30))
            axis.plot(wave_xs, wave_ys, color=wave_blue, linewidth=1.6)
            # Nem damlaları
            for ddx, ddy in [(-0.08 * scale, -0.04 * scale), (0.06 * scale, -0.12 * scale)]:
                axis.add_patch(Circle((cx + ddx, cy + ddy), 0.022 * scale, facecolor=wave_blue, edgecolor="none"))
            # Çimen şeridi
            for grass_dx in (-0.10 * scale, -0.02 * scale, 0.07 * scale):
                axis.plot(
                    [cx + grass_dx, cx + grass_dx + 0.01 * scale],
                    [cy, cy + 0.07 * scale],
                    color="#3f8f3a", linewidth=1.5,
                )
            artists.append(axis.add_patch(Circle((cx, cy), 0.001, alpha=0.0)))

        elif kind == "thermometer":
            axis.add_patch(Circle((cx, cy - 0.14 * scale), 0.10 * scale, facecolor=red, edgecolor=dark, linewidth=1.2))
            axis.add_patch(FancyBboxPatch(
                (cx - 0.04 * scale, cy - 0.10 * scale),
                0.08 * scale, 0.30 * scale,
                boxstyle=f"round,pad=0.01,rounding_size={0.04 * scale}",
                facecolor="#ffffff", edgecolor=dark, linewidth=1.2,
            ))
            axis.add_patch(Rectangle((cx - 0.02 * scale, cy - 0.10 * scale), 0.04 * scale, 0.22 * scale, facecolor=red, edgecolor="none"))

        elif kind == "sun":
            axis.add_patch(Circle((cx, cy), 0.12 * scale, facecolor="#ffbf36", edgecolor="#df8a00", linewidth=1.1))
            for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
                axis.plot(
                    [cx + 0.16 * scale * np.cos(angle), cx + 0.24 * scale * np.cos(angle)],
                    [cy + 0.16 * scale * np.sin(angle), cy + 0.24 * scale * np.sin(angle)],
                    color=orange, linewidth=1.5,
                )

        elif kind == "rain":
            for ox, oy, radius in [(-0.12, 0.03, 0.12), (0.02, 0.09, 0.15), (0.17, 0.02, 0.11)]:
                axis.add_patch(Circle((cx + ox * scale, cy + oy * scale), radius * scale, facecolor="#5d84ae", edgecolor="none"))
            axis.add_patch(Rectangle((cx - 0.20 * scale, cy - 0.02 * scale), 0.40 * scale, 0.11 * scale, facecolor="#5d84ae", edgecolor="none"))
            for ox in (-0.12, 0.0, 0.12):
                axis.plot([cx + ox * scale, cx + (ox - 0.03) * scale], [cy - 0.11 * scale, cy - 0.22 * scale], color=blue, linewidth=1.6)

        elif kind == "brain":
            # Q-Learning karar ikonu
            brain_fill  = "#dce8ff"
            brain_edge  = navy
            fold_color  = "#5a7ab5"

            # Sol yarım küre
            axis.add_patch(Ellipse(
                (cx - 0.10 * scale, cy + 0.01 * scale),
                0.28 * scale, 0.36 * scale,
                facecolor=brain_fill, edgecolor=brain_edge, linewidth=1.3, zorder=2,
            ))
            # Sağ yarım küre
            axis.add_patch(Ellipse(
                (cx + 0.10 * scale, cy + 0.01 * scale),
                0.28 * scale, 0.36 * scale,
                facecolor=brain_fill, edgecolor=brain_edge, linewidth=1.3, zorder=2,
            ))
            # Orta ayırıcı çizgi
            axis.plot(
                [cx, cx],
                [cy - 0.18 * scale, cy + 0.18 * scale],
                color=brain_edge, linewidth=1.6, zorder=3,
            )
            # Sol yarım küre kıvrımları
            for arc_cy, arc_r, arc_start, arc_end in [
                (cy + 0.12 * scale, 0.09 * scale, np.pi * 0.55, np.pi * 1.05),
                (cy + 0.00 * scale, 0.07 * scale, np.pi * 0.60, np.pi * 1.10),
                (cy - 0.11 * scale, 0.08 * scale, np.pi * 0.50, np.pi * 1.00),
            ]:
                angles = np.linspace(arc_start, arc_end, 20)
                xs = (cx - 0.10 * scale) + arc_r * np.cos(angles)
                ys = arc_cy + arc_r * np.sin(angles)
                axis.plot(xs, ys, color=fold_color, linewidth=1.0, zorder=4)
            # Sağ yarım küre kıvrımları
            for arc_cy, arc_r, arc_start, arc_end in [
                (cy + 0.12 * scale, 0.09 * scale, np.pi * 0.00, np.pi * 0.45),
                (cy + 0.00 * scale, 0.07 * scale, np.pi * -0.10, np.pi * 0.40),
                (cy - 0.11 * scale, 0.08 * scale, np.pi * 0.00, np.pi * 0.50),
            ]:
                angles = np.linspace(arc_start, arc_end, 20)
                xs = (cx + 0.10 * scale) + arc_r * np.cos(angles)
                ys = arc_cy + arc_r * np.sin(angles)
                axis.plot(xs, ys, color=fold_color, linewidth=1.0, zorder=4)
            # Alt bağlantı
            axis.add_patch(Ellipse(
                (cx, cy - 0.19 * scale),
                0.14 * scale, 0.07 * scale,
                facecolor=brain_fill, edgecolor=brain_edge, linewidth=1.0, zorder=2,
            ))

        elif kind == "watering":
            # Sulama bidonu ikonu
            can_color = "#6baef1"
            # Gövde
            axis.add_patch(Ellipse(
                (cx - 0.04 * scale, cy - 0.04 * scale),
                0.30 * scale, 0.24 * scale,
                facecolor=can_color, edgecolor=navy, linewidth=1.2,
            ))
            # Sap
            handle_angles = np.linspace(0, np.pi, 18)
            hx = (cx - 0.04 * scale) + 0.12 * scale * np.cos(handle_angles)
            hy = (cy - 0.04 * scale) + 0.12 * scale * np.sin(handle_angles) + 0.08 * scale
            axis.plot(hx, hy, color=navy, linewidth=1.5, solid_capstyle="round")
            # Sulama borusu
            axis.add_patch(Polygon(
                [
                    (cx + 0.11 * scale, cy - 0.01 * scale),
                    (cx + 0.28 * scale, cy + 0.10 * scale),
                    (cx + 0.31 * scale, cy + 0.06 * scale),
                    (cx + 0.14 * scale, cy - 0.05 * scale),
                ],
                closed=True, facecolor=can_color, edgecolor=navy, linewidth=1.0,
            ))
            # Sulama başlığı ve delikleri
            axis.add_patch(FancyBboxPatch(
                (cx + 0.27 * scale, cy + 0.04 * scale),
                0.07 * scale, 0.09 * scale,
                boxstyle=f"round,pad=0.005,rounding_size={0.015 * scale}",
                facecolor=can_color, edgecolor=navy, linewidth=1.0,
            ))
            for ddx, ddy in [(-0.01, 0.14), (0.02, 0.14), (0.05, 0.14),
                              (0.00, 0.10), (0.03, 0.10)]:
                axis.plot(
                    cx + (0.27 + ddx) * scale, cy + ddy * scale,
                    marker=".", markersize=2.0 * scale, color=blue,
                )
            # Su seviyesi
            axis.plot(
                [cx - 0.16 * scale, cx + 0.08 * scale],
                [cy - 0.04 * scale, cy - 0.04 * scale],
                color="#3a7fc1", linewidth=1.0, alpha=0.7,
            )

        elif kind == "plant":
            axis.plot([cx, cx], [cy - 0.16 * scale, cy + 0.09 * scale], color=green, linewidth=2.1)
            axis.add_patch(Ellipse((cx - 0.08 * scale, cy + 0.02 * scale), 0.18 * scale, 0.10 * scale, angle=35, facecolor="#66b94e", edgecolor=green, linewidth=1.0))
            axis.add_patch(Ellipse((cx + 0.08 * scale, cy + 0.08 * scale), 0.18 * scale, 0.10 * scale, angle=-35, facecolor="#66b94e", edgecolor=green, linewidth=1.0))
            axis.add_patch(Ellipse((cx, cy + 0.18 * scale), 0.14 * scale, 0.08 * scale, angle=90, facecolor="#66b94e", edgecolor=green, linewidth=1.0))

        elif kind == "shield":
            axis.add_patch(Polygon(
                [(cx, cy + 0.22 * scale), (cx - 0.18 * scale, cy + 0.12 * scale), (cx - 0.15 * scale, cy - 0.12 * scale), (cx, cy - 0.24 * scale), (cx + 0.15 * scale, cy - 0.12 * scale), (cx + 0.18 * scale, cy + 0.12 * scale)],
                closed=True, facecolor="#62b551", edgecolor="#2f7d38", linewidth=1.2,
            ))
            axis.plot([cx - 0.07 * scale, cx - 0.01 * scale, cx + 0.09 * scale], [cy - 0.01 * scale, cy - 0.08 * scale, cy + 0.07 * scale], color="#ffffff", linewidth=2.0)

        return artists

    def normalized_series(values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        if len(values) == 0:
            return np.zeros(1)
        vmin = float(np.nanmin(values))
        vmax = float(np.nanmax(values))
        if vmax - vmin < 1e-9:
            return np.full(len(values), 0.5)
        return (values - vmin) / (vmax - vmin)

    # ------------------------------------------------------------------
    # Sabit arka plan
    # ------------------------------------------------------------------
    axis.add_patch(Rectangle((0.0, 1.05), 14.92, 7.95, facecolor="#e8f5ff", edgecolor="none"))
    axis.add_patch(Rectangle((0.0, 1.05), 14.92, 1.98, facecolor="#9f6838", edgecolor="none"))
    axis.add_patch(Rectangle((0.0, 2.75), scene_right, 0.28, facecolor="#4f943f", edgecolor="none"))
    axis.add_patch(Polygon([(0.0, 3.03), (1.4, 4.0), (2.9, 3.35), (4.6, 4.18), (6.2, 3.45), (8.1, 4.15), (scene_right, 3.03)], closed=True, facecolor="#bfd9cc", edgecolor="none", alpha=0.78))

    if SHOW_BOTTOM_CARDS:
        bottom_panel = FancyBboxPatch((0.18, 0.10), 15.64, 1.18, boxstyle="round,pad=0.03,rounding_size=0.16", facecolor="#ffffff", edgecolor="#b9cde3", linewidth=1.2)
        axis.add_patch(bottom_panel)
    right_panel = FancyBboxPatch(
        (10.72, 1.88), 4.15, 5.72,
        boxstyle="round,pad=0.045,rounding_size=0.18",
        facecolor="#ffffff", edgecolor="#b9cde3", linewidth=1.2,
    )
    axis.add_patch(right_panel)

    axis.text(8.0, 8.18, "Akıllı Sulama Sistemi — Q-Learning Günlük Davranış", ha="center", va="center", fontsize=20, fontweight="bold", color="#10264a")
    axis.text(8.0, 7.82, f"Konum: {ANIMATION_LOCATION}", ha="center", va="center", fontsize=12.5, fontweight="bold", color="#245a45")
    date_text = axis.text(8.0, 7.51, "", ha="center", va="center", fontsize=12, fontweight="bold", color="#173a72")

    # ------------------------------------------------------------------
    # Sahne nesneleri
    # ------------------------------------------------------------------
    sun = Circle((9.45, 6.92), 0.42, facecolor="#f8b533", edgecolor="#e69713", linewidth=1.2)
    axis.add_patch(sun)
    sun_rays = []
    for angle in np.linspace(0.0, 2.0 * np.pi, 12, endpoint=False):
        x0 = 9.45 + 0.52 * np.cos(angle)
        y0 = 6.92 + 0.52 * np.sin(angle)
        x1 = 9.45 + 0.73 * np.cos(angle)
        y1 = 6.92 + 0.73 * np.sin(angle)
        line, = axis.plot([x0, x1], [y0, y1], linewidth=1.8, color="#f8b533")
        sun_rays.append(line)

    cloud_parts = [
        Circle((1.35, 6.9), 0.36, facecolor="#8b98a7", edgecolor="none"),
        Circle((1.72, 7.06), 0.46, facecolor="#8b98a7", edgecolor="none"),
        Circle((2.10, 6.90), 0.34, facecolor="#8b98a7", edgecolor="none"),
        Ellipse((1.72, 6.72), 1.58, 0.50, facecolor="#8b98a7", edgecolor="none"),
    ]
    for patch in cloud_parts:
        axis.add_patch(patch)

    rain_drops = []
    for i, x_value in enumerate(np.linspace(1.08, 2.30, 9)):
        phase = 0.12 * (i % 3)
        line, = axis.plot([x_value, x_value - 0.04], [6.28 - phase, 5.99 - phase], color="#2e8fe6", linewidth=2.0, solid_capstyle="round")
        rain_drops.append(line)

    # ------------------------------------------------------------------
    # Bitki çizimi
    # ------------------------------------------------------------------
    PLANT_BASE_X = 5.00
    PLANT_BASE_Y = 2.96

    # Kök bölgesini temsil eden nem alanı.
    moisture_zone = Ellipse(
        (PLANT_BASE_X, 2.02), 2.70, 0.88,
        facecolor="#5a3925", edgecolor="none", alpha=0.34, zorder=1,
    )
    axis.add_patch(moisture_zone)

    # Toprak yüzeyi
    soil_shadow = Ellipse(
        (PLANT_BASE_X, 2.63), 3.15, 0.34,
        facecolor="#110b07", edgecolor="none", alpha=0.24, zorder=1.35,
    )
    axis.add_patch(soil_shadow)
    soil_mound = Polygon(
        [
            (3.45, 2.66), (3.85, 2.86), (4.32, 2.99), (4.76, 3.08),
            (5.10, 3.10), (5.50, 3.02), (5.95, 2.90), (6.43, 2.68),
            (5.90, 2.51), (5.10, 2.46), (4.25, 2.50), (3.62, 2.58),
        ],
        closed=True, facecolor="#1e120b", edgecolor="#0c0704", linewidth=0.8,
        alpha=0.98, zorder=2.15,
    )
    axis.add_patch(soil_mound)

    rng_soil = np.random.default_rng(7)
    for _ in range(76):
        px = float(rng_soil.uniform(3.60, 6.25))
        center = PLANT_BASE_X
        width_at_x = max(0.0, 1.0 - abs(px - center) / 1.48)
        py = float(rng_soil.uniform(2.55, 2.66 + 0.42 * width_at_x))
        r = float(rng_soil.uniform(0.008, 0.022))
        grain = Circle(
            (px, py), r,
            facecolor=rng_soil.choice(["#2b1a10", "#3a2416", "#4a2e1c", "#160d08"]),
            edgecolor="none", alpha=0.76, zorder=2.35,
        )
        axis.add_patch(grain)

    root_origin = (PLANT_BASE_X, PLANT_BASE_Y)
    root_lines = []
    for angle, length in zip(np.linspace(-2.55, -0.60, 11), np.linspace(0.72, 0.44, 11)):
        end_x = root_origin[0] + length * np.cos(angle)
        end_y = root_origin[1] + 0.48 * length * np.sin(angle)
        line, = axis.plot(
            [root_origin[0], end_x], [root_origin[1], end_y],
            color="#b68b5f", linewidth=0.85, alpha=0.55, zorder=2.05,
        )
        root_lines.append(line)

    stem_lines = []
    plant_patches = []
    leaf_detail_lines = []

    def draw_curved_stem(x0: float, y0: float, x1: float, y1: float, bend: float, lw: float):
        """Kısa ve yumuşak kıvrımlı ıspanak sapı çizer."""
        t = np.linspace(0.0, 1.0, 26)
        cx = (x0 + x1) / 2.0 + bend
        cy = (y0 + y1) / 2.0 + 0.07
        xs = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        ys = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        line, = axis.plot(
            xs, ys, color="#2a7e42", linewidth=lw,
            solid_capstyle="round", alpha=0.95, zorder=4,
        )
        stem_lines.append(line)
        return line

    def add_spinach_leaf(
        cx: float,
        cy: float,
        length: float,
        width: float,
        angle: float,
        base_color: str = "#58b750",
        z: float = 5.0,
    ) -> Ellipse:
        """Yuvarlak, geniş ve damarlı ıspanak yaprağı çizer."""
        leaf = Ellipse(
            (cx, cy), width=width, height=length, angle=angle,
            facecolor=base_color, edgecolor="#236b38", linewidth=0.95,
            alpha=0.98, zorder=z,
        )
        axis.add_patch(leaf)
        plant_patches.append(leaf)

        theta = np.deg2rad(angle + 90.0)
        vx, vy = np.cos(theta), np.sin(theta)
        x0, y0 = cx - 0.39 * length * vx, cy - 0.39 * length * vy
        x1, y1 = cx + 0.39 * length * vx, cy + 0.39 * length * vy
        main_vein, = axis.plot(
            [x0, x1], [y0, y1],
            color="#d7f3b4", linewidth=0.72, alpha=0.74, zorder=z + 0.03,
        )
        leaf_detail_lines.append(main_vein)

        perp = theta + np.pi / 2.0
        for frac in (-0.22, 0.0, 0.22):
            bx = cx + frac * length * vx
            by = cy + frac * length * vy
            side_len = width * 0.20
            for sign in (-1, 1):
                side, = axis.plot(
                    [bx, bx + sign * side_len * np.cos(perp + sign * 0.28)],
                    [by, by + sign * side_len * np.sin(perp + sign * 0.28)],
                    color="#bce995", linewidth=0.46, alpha=0.56, zorder=z + 0.04,
                )
                leaf_detail_lines.append(side)
        return leaf

    # Bitki sapları
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y, 4.78, 4.34, -0.12, 3.6)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y, 5.22, 4.34, 0.12, 3.6)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y + 0.06, 4.48, 4.02, -0.24, 2.8)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y + 0.06, 5.52, 4.02, 0.24, 2.8)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y + 0.12, 5.00, 4.62, 0.00, 3.2)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y + 0.10, 4.86, 4.78, -0.06, 2.6)
    draw_curved_stem(PLANT_BASE_X, PLANT_BASE_Y + 0.10, 5.14, 4.76, 0.06, 2.6)

    # Geniş yapraklar
    add_spinach_leaf(4.40, 4.00, length=0.94, width=0.48, angle=42,  base_color="#3f9144", z=5.05)
    add_spinach_leaf(5.60, 4.00, length=0.94, width=0.48, angle=-42, base_color="#6cc85f", z=5.08)
    add_spinach_leaf(4.72, 4.40, length=0.86, width=0.43, angle=18,  base_color="#58b750", z=5.30)
    add_spinach_leaf(5.28, 4.40, length=0.86, width=0.43, angle=-18, base_color="#72d365", z=5.32)
    add_spinach_leaf(5.00, 4.70, length=0.78, width=0.42, angle=0,   base_color="#8be047", z=5.55)
    add_spinach_leaf(4.56, 3.70, length=0.78, width=0.40, angle=78,  base_color="#3b873e", z=5.12)
    add_spinach_leaf(5.44, 3.70, length=0.78, width=0.40, angle=-78, base_color="#75cc67", z=5.14)
    add_spinach_leaf(4.88, 4.18, length=0.72, width=0.38, angle=72,  base_color="#4ca64b", z=5.38)
    add_spinach_leaf(5.12, 4.18, length=0.72, width=0.38, angle=-72, base_color="#67c65c", z=5.40)

    axis.add_patch(Ellipse(
        (PLANT_BASE_X, PLANT_BASE_Y + 0.01), 0.44, 0.13,
        facecolor="#1f5c2c", edgecolor="#143f1f", linewidth=0.8, zorder=4.5,
    ))

    grass_blades = []
    for blade_index, x_value in enumerate(np.linspace(3.65, 6.35, 24)):
        height = 0.055 + 0.055 * ((blade_index % 5) / 4.0)
        lean = 0.020 * ((blade_index % 3) - 1)
        line, = axis.plot(
            [x_value, x_value + lean], [2.82, 2.82 + height],
            linewidth=0.95, color="#3f8f3a", alpha=0.56, zorder=3.0,
        )
        grass_blades.append(line)

    axis.add_patch(Rectangle((8.15, 2.74), 0.32, 0.57, facecolor="#263746", edgecolor="#0f1820"))
    axis.add_patch(Rectangle((8.07, 3.26), 0.48, 0.11, facecolor="#1b2630", edgecolor="#0f1820"))

    spray_lines = []
    spray_targets = [(7.4, 4.3), (7.0, 4.15), (6.6, 4.0), (6.2, 3.85), (5.8, 3.70), (5.4, 3.55)]
    for tx, ty in spray_targets:
        line, = axis.plot([8.24, tx], [3.32, ty], color="#3ba5ea", linewidth=1.4, alpha=0.88, solid_capstyle="round", clip_on=True)
        spray_lines.append(line)

    # ------------------------------------------------------------------
    # Sağ bilgi paneli
    # ------------------------------------------------------------------
    # Toprak nemi göstergesi solda, günlük değer kartları sağda yer alır.
    gauge_x = 10.96
    gauge_y = 2.22
    gauge_width = 0.46
    gauge_height = 4.15

    axis.text(
        gauge_x + gauge_width / 2.0, 6.82, "Toprak Nemi\nGöstergesi",
        ha="center", va="center", fontsize=8.2,
        fontweight="bold", color="#16233c",
    )

    gauge_min = th.soil_min * 100.0
    gauge_max = th.soil_max * 100.0

    def gauge_position(value: float) -> float:
        normalized = (value - gauge_min) / max(gauge_max - gauge_min, 1e-9)
        return gauge_y + gauge_height * float(np.clip(normalized, 0.0, 1.0))

    dry_top = gauge_position(th.soil_dry * 100.0)
    ideal_top = gauge_position(th.soil_target_high * 100.0)
    wet_top = gauge_position(th.soil_very_wet * 100.0)
    gauge_bands = [
        (gauge_y, dry_top, "#d77b31"),
        (dry_top, ideal_top, "#69ad55"),
        (ideal_top, wet_top, "#4ba59b"),
        (wet_top, gauge_y + gauge_height, "#4a9ed8"),
    ]
    for y0, y1, color in gauge_bands:
        axis.add_patch(Rectangle(
            (gauge_x, y0), gauge_width, max(y1 - y0, 0.01),
            facecolor=color, edgecolor="none", alpha=0.84,
        ))
    axis.add_patch(Rectangle(
        (gauge_x, gauge_y), gauge_width, gauge_height,
        facecolor="none", edgecolor="#5c7391", linewidth=1.2,
    ))
    label_x = gauge_x + gauge_width + 0.05
    axis.text(label_x, gauge_y + 0.16, "Kuru", fontsize=6.3, color="#b95b19", ha="left", va="center")
    axis.text(label_x, (dry_top + ideal_top) / 2.0, "İdeal", fontsize=6.3, color="#2c7c39", ha="left", va="center")
    axis.text(label_x, gauge_y + gauge_height - 0.12, "Çok\nıslak", fontsize=6.1, color="#246ca1", ha="left", va="center", linespacing=0.9)

    gauge_pointer, = axis.plot(
        [gauge_x - 0.04, gauge_x + gauge_width + 0.04],
        [gauge_y, gauge_y], color="#172133", linewidth=2.2,
    )
    gauge_value_text = axis.text(
        gauge_x + gauge_width / 2.0, gauge_y + 0.12, "",
        ha="center", va="bottom", fontsize=9.2,
        fontweight="bold", color="#172133",
    )

    # ------------------------------------------------------------------
    # Günlük gösterge kartları
    # ------------------------------------------------------------------
    # Kartlar sağ panelde dikey olarak sıralanır.
    card_specs = [
        {"left": 11.76, "bottom": 6.56, "height": 0.54, "title": "Toprak nemi", "icon": "droplet", "kind": "moisture", "tcolor": "#2c7c39", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 5.91, "height": 0.54, "title": "Sıcaklık", "icon": "thermometer", "kind": "temperature", "tcolor": "#8a3321", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 5.26, "height": 0.54, "title": "ET₀", "icon": "sun", "kind": "et0", "tcolor": "#d27300", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 4.61, "height": 0.54, "title": "Yağış", "icon": "rain", "kind": "rain", "tcolor": "#214f8a", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 3.83, "height": 0.62, "title": "Q-Learning Kararı", "icon": "brain", "kind": "decision_only", "tcolor": "#173a72", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 3.10, "height": 0.56, "title": "Sulama miktarı", "icon": "watering", "kind": "irrigation_only", "tcolor": "#173a72", "vcolor": "#173a72"},
        {"left": 11.76, "bottom": 2.38, "height": 0.56, "title": "Sistem durumu", "icon": "shield", "kind": "status_only", "tcolor": "#2d7d3c", "vcolor": "#2d7d3c"},
    ]
    card_width = 2.72

    card_value_texts = []
    card_graph_artists: list[dict[str, object]] = []

    for spec in card_specs:
        left = float(spec["left"])
        bottom = float(spec["bottom"])
        card_height = float(spec["height"])
        title = str(spec["title"])
        icon = str(spec["icon"])
        kind = str(spec["kind"])
        tcolor = str(spec["tcolor"])
        vcolor = str(spec["vcolor"])

        # Sulama kararı için genişletilmiş kart.
        card_face = "#f5f8ff" if kind == "water_decision" else "#ffffff"
        card_edge = "#9fb6d8" if kind == "water_decision" else "#d0dcea"
        card = FancyBboxPatch(
            (left, bottom), card_width, card_height,
            boxstyle="round,pad=0.014,rounding_size=0.075",
            facecolor=card_face, edgecolor=card_edge, linewidth=1.0,
            alpha=0.98,
        )
        axis.add_patch(card)

        # İkon ve metin alanlarını ayrı hizala.
        icon_x = left + 0.24
        text_x = left + 0.56
        if kind in ("decision_only", "irrigation_only", "status_only"):
            icon_x = left + 0.23
            icon_y = bottom + card_height / 2.0
            icon_scale = 0.34
        else:
            icon_y = bottom + card_height / 2.0
            icon_scale = 0.34

        add_icon(icon, icon_x, icon_y, icon_scale)

        title_y = bottom + card_height - 0.15
        title_font = 6.35 if kind == "decision_only" else 7.15
        axis.text(
            text_x, title_y, title,
            fontsize=title_font, color=tcolor, fontweight="bold",
            ha="left", va="center", linespacing=1.18 if kind == "water_decision" else 1.05,
        )

        value_font = 8.15 if kind in ("decision_only", "irrigation_only", "status_only") else 8.7
        value_y = bottom + 0.15
        value_text = axis.text(
            text_x, value_y, "",
            fontsize=value_font, color=vcolor, fontweight="bold",
            ha="left", va="center", linespacing=1.20,
        )
        card_value_texts.append(value_text)

        gx0 = left + 1.72
        gx1 = left + 3.34
        gy0 = bottom + 0.15
        gy1 = bottom + min(card_height - 0.34, 0.48)
        # Kartlarda yalnızca güncel değerler gösterilir.
        card_graph_artists.append({
            "type": "empty",
        })

    def state_colors(value: float) -> tuple[str, str]:
        if value < th.soil_dry * 100.0:
            return "#93a73b", "#8fbe48"
        if value <= th.soil_target_high * 100.0:
            return "#46a84f", "#52a84f"
        if value <= th.soil_very_wet * 100.0:
            return "#2f9381", "#45a190"
        return "#2f83bd", "#53a0d6"

    def short_action_name(value: str) -> str:
        if value.startswith("Düşük"):
            return "Düşük sulama"
        if value.startswith("Orta"):
            return "Orta sulama"
        if value.startswith("Yüksek"):
            return "Yüksek sulama"
        return "Sulama yok"

    def update_card_bars(artists: dict[str, object], history: np.ndarray) -> None:
        values = np.asarray(history, dtype=float)
        bars = artists["bars"]
        if len(values) == 0:
            values = np.zeros(len(bars))
        values = values[-len(bars):]
        if len(values) < len(bars):
            values = np.pad(values, (len(bars) - len(values), 0), constant_values=0.0)
        norm = normalized_series(values)
        x0 = float(artists["x0"])
        x1 = float(artists["x1"])
        y0 = float(artists["y0"])
        y1 = float(artists["y1"])
        bar_space = (x1 - x0) / len(bars)
        for j, (bar, nv) in enumerate(zip(bars, norm)):
            height = 0.03 + nv * (y1 - y0 - 0.05)
            bar.set_x(x0 + j * bar_space + 0.04)
            bar.set_y(y0)
            bar.set_width(bar_space * 0.48)
            bar.set_height(height)
        artists["dot"].set_data([x0 + (len(bars) - 0.5) * bar_space], [y0 + (0.03 + norm[-1] * (y1 - y0 - 0.05))])

    def update_card_line(artists: dict[str, object], history: np.ndarray) -> None:
        values = np.asarray(history, dtype=float)
        if len(values) == 0:
            values = np.zeros(1)
        values = values[-7:]
        norm = normalized_series(values)
        x0 = float(artists["x0"])
        x1 = float(artists["x1"])
        y0 = float(artists["y0"])
        y1 = float(artists["y1"])
        xs = np.linspace(x0, x1, len(norm))
        ys = y0 + 0.03 + norm * (y1 - y0 - 0.06)
        artists["line"].set_data(xs, ys)
        artists["dot"].set_data([xs[-1]], [ys[-1]])

    def update_decision_indicator(artists: dict[str, object], action_no: float) -> None:
        """Q-Learning karar kartında seçilen aksiyonu ayrı bir gösterge olarak vurgular."""
        active_index = int(np.clip(round(float(action_no)), 0, len(artists["boxes"]) - 1))
        active_colors = ["#d9e2ec", "#8fc8ff", "#f2a11f", "#e4593f"]
        for j, (box, label) in enumerate(zip(artists["boxes"], artists["labels"])):
            is_active = j == active_index
            box.set_facecolor(active_colors[j] if is_active else "#eef3f8")
            box.set_edgecolor("#173a72" if is_active else "#c3d4e4")
            box.set_linewidth(1.35 if is_active else 0.8)
            box.set_alpha(1.0 if is_active else 0.55)
            label.set_color("#10264a" if is_active else "#516274")
            label.set_fontsize(5.6 if is_active else 5.0)

    def update(frame_index: int):
        index = int(frame_index)
        current_date = dates.iloc[index]
        current_moisture = float(moisture[index])
        current_rain = float(rainfall[index])
        current_irrigation = float(irrigation[index])
        current_temperature = float(temperature[index])
        current_et0 = float(et0[index])

        grass_color, leaf_color = state_colors(current_moisture)
        for blade in grass_blades:
            blade.set_color(grass_color)
        for patch in plant_patches:
            patch.set_facecolor(leaf_color)
            patch.set_edgecolor("#236b38")
        # Bitki rengini toprak nemi durumuna göre güncelle.
        stem_green = "#1d6b32" if current_moisture < th.soil_dry * 100.0 else "#2a7e42"
        for sline in stem_lines:
            sline.set_color(stem_green)

        normalized_m = float(np.clip((current_moisture - gauge_min) / max(gauge_max - gauge_min, 1e-9), 0.0, 1.0))
        moisture_zone.set_width(3.4 + 2.0 * normalized_m)
        moisture_zone.set_alpha(0.24 + 0.38 * normalized_m)

        rainy = current_rain > 0.1
        irrigating = current_irrigation > 0.0
        for patch in cloud_parts:
            patch.set_visible(rainy)
        for drop in rain_drops:
            drop.set_visible(rainy)
        sun.set_visible(not rainy)
        for ray in sun_rays:
            ray.set_visible(not rainy)
        for spray in spray_lines:
            spray.set_visible(irrigating)
            spray.set_linewidth(1.0 + current_irrigation / 5.0)

        pointer_y = gauge_position(current_moisture)
        gauge_pointer.set_ydata([pointer_y, pointer_y])
        gauge_value_text.set_position((gauge_x + gauge_width / 2.0, min(pointer_y + 0.10, gauge_y + gauge_height - 0.02)))
        gauge_value_text.set_text(f"%{current_moisture:.1f}")

        # Tarihi konum bilgisinin altında göster.
        date_text.set_text(f"Tarih: {current_date:%d.%m.%Y}")

        # Kart sırası: toprak nemi, sıcaklık, ET0, yağış, karar, sulama ve sistem durumu.
        current_action = short_action_name(str(actions[index]))

        card_value_texts[0].set_text(f"%{current_moisture:.1f}")
        card_value_texts[1].set_text(f"{current_temperature:.1f} °C")
        card_value_texts[2].set_text(f"{current_et0:.1f} mm")
        card_value_texts[3].set_text(f"{current_rain:.1f} mm")
        card_value_texts[4].set_text(current_action)
        card_value_texts[5].set_text(f"{current_irrigation:.1f} mm")
        card_value_texts[6].set_text("Aktif")

        dynamic = [moisture_zone, gauge_pointer, gauge_value_text, date_text, *card_value_texts]
        dynamic.extend(plant_patches)
        dynamic.extend(spray_lines)
        return tuple(dynamic)

    animation = FuncAnimation(fig, update, frames=frames, interval=1000 / ANIMATION_FPS, blit=False, repeat=True)
    output_path = RESULT_DIR / "animasyon_1_akilli_sulama_dashboard_2025.gif"
    try:
        animation.save(output_path, writer=PillowWriter(fps=ANIMATION_FPS), dpi=100)
    except Exception as exc:
        plt.close(fig)
        raise RuntimeError(
            "Görsel GIF oluşturulamadı. Pillow kurulumu için "
            "'pip install pillow' komutunu çalıştırın. "
            f"Orijinal hata: {exc}"
        ) from exc
    plt.close(fig)

def add_bar_labels(axis: plt.Axes) -> None:
    for container in axis.containers:
        axis.bar_label(container, fmt="%.1f", padding=2, fontsize=8)


def save_2025_method_comparison(comparison_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    specs = [
        ("Toplam sulama (mm = L/m²)", "Toplam Kullanılan Su", "Su (mm)"),
        ("İdeal nem oranı (%)", "İdeal Nem Oranı", "%"),
        ("Kabul edilebilir nem oranı (%)", "Kabul Edilebilir Nem Oranı", "%"),
        ("Toplam ödül", "Toplam Ödül", "Ödül"),
    ]
    for axis, (column, title, ylabel) in zip(axes.flat, specs):
        axis.bar(comparison_df["Yöntem"], comparison_df[column])
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.tick_params(axis="x", rotation=15)
        axis.grid(axis="y")
        add_bar_labels(axis)
    fig.suptitle("Sulama Yöntemlerinin Karşılaştırılması — 2025 Test Yılı")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_3_yontem_karsilastirmasi.png", dpi=300)
    plt.close(fig)

def save_2025_action_distribution(q_log: pd.DataFrame) -> None:
    counts = q_log["aksiyon_no"].value_counts().reindex(range(4), fill_value=0)
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.bar(ACTION_SHORT_NAMES, counts.to_numpy())
    axis.set_title("Q-Learning Aksiyon Dağılımı — 2025 Test Yılı")
    axis.set_xlabel("Aksiyon")
    axis.set_ylabel("Gün Sayısı")
    axis.grid(axis="y")
    add_bar_labels(axis)
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_4_aksiyon_dagilimi.png", dpi=300)
    plt.close(fig)

def save_all_years_environment(full_df: pd.DataFrame) -> None:
    test_start = pd.Timestamp(f"{TEST_YEAR}-01-01")
    fig, axes = plt.subplots(4, 1, figsize=(17, 13), sharex=True)
    columns = [
        ("toprak_nemi_7_28_yuzde", "ERA5-Land Referans Toprak Nemi (%)", "ERA5-Land 7-28 cm Toprak Nemi"),
        ("yagis_mm", "Yağış (mm)", "Günlük Yağış"),
        ("sicaklik_ortalama_c", "Sıcaklık (°C)", "Ortalama Sıcaklık"),
        ("et0_mm", "ET0 (mm)", "Referans Evapotranspirasyon"),
    ]
    for axis, (column, ylabel, title) in zip(axes, columns):
        axis.plot(full_df["tarih"], full_df[column])
        axis.axvline(test_start, linestyle="--", label="2025 test başlangıcı")
        axis.set_ylabel(ylabel)
        axis.set_title(title)
        axis.grid(True)
    axes[-1].set_xlabel("Tarih")
    axes[0].text(pd.Timestamp("2022-06-01"), axes[0].get_ylim()[1], "Eğitim dönemi: 2020-2024", va="top")
    axes[0].text(pd.Timestamp("2025-04-01"), axes[0].get_ylim()[1], "Test dönemi: 2025", va="top")
    axes[0].legend()
    fig.suptitle("Bursa 2020-2025 Gerçek Çevre Verileri")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_5_tum_yillar_cevre_verileri.png", dpi=300)
    plt.close(fig)


def pivot_metric(metrics_df: pd.DataFrame, column: str) -> pd.DataFrame:
    return metrics_df.pivot(index="Yıl", columns="Yöntem", values=column).sort_index()


def mark_test_year(axis: plt.Axes) -> None:
    axis.axvline(TEST_YEAR, linestyle="--", label="2025 bağımsız test")

def save_annual_moisture_success(metrics_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    for axis, column, title in [
        (axes[0], "İdeal nem oranı (%)", "İdeal Nem Oranı"),
        (axes[1], "Kabul edilebilir nem oranı (%)", "Kabul Edilebilir Nem Oranı"),
    ]:
        pivot = pivot_metric(metrics_df, column)
        for method in pivot.columns:
            axis.plot(pivot.index, pivot[method], marker="o", label=method)
        mark_test_year(axis)
        axis.set_ylabel("Oran (%)")
        axis.set_title(title)
        axis.grid(True)
        axis.legend()
    axes[1].set_xticks(ALL_YEARS)
    axes[1].set_xlabel("Yıl")
    fig.suptitle("Yıllara Göre Toprak Nemi Başarısı")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "grafik_6_yillara_gore_nem_basarisi.png", dpi=300)
    plt.close(fig)


def create_all_graphs(
    full_df: pd.DataFrame,
    training_history: pd.DataFrame,
    all_logs: dict[tuple[int, str], pd.DataFrame],
    yearly_metrics: pd.DataFrame,
    th: Thresholds,
) -> None:
    """Analiz grafiklerini ve 2025 dashboard animasyonunu oluşturur."""
    logs_2025 = {
        method: all_logs[(TEST_YEAR, method)]
        for method in yearly_metrics["Yöntem"].unique()
    }
    comparison_2025 = yearly_metrics[yearly_metrics["Yıl"] == TEST_YEAR].copy()

    save_training_graph(training_history)
    save_2025_daily_behavior(logs_2025["Q-Learning"], th)
    save_visual_irrigation_dashboard(logs_2025["Q-Learning"], th)
    save_2025_method_comparison(comparison_2025)
    save_2025_action_distribution(logs_2025["Q-Learning"])
    save_all_years_environment(full_df)
    save_annual_moisture_success(yearly_metrics)

# =============================================================================
# 10) KONSOL RAPORLAMA
# =============================================================================


def print_thresholds(th: Thresholds) -> None:
    print("\nEĞİTİM VERİSİNDEN HESAPLANAN SINIRLAR")
    print("-" * 66)
    print(f"Çok kuru sınırı       : {th.soil_very_dry:.4f} m³/m³")
    print(f"İdeal nem alt sınırı  : {th.soil_dry:.4f} m³/m³")
    print(f"İdeal nem üst sınırı  : {th.soil_target_high:.4f} m³/m³")
    print(f"Çok ıslak sınırı      : {th.soil_very_wet:.4f} m³/m³")
    print(f"Sıcaklık sınırları    : {th.temp_low:.2f} / {th.temp_high:.2f} °C")
    print(f"ET0 sınırları         : {th.et0_low:.2f} / {th.et0_high:.2f} mm")



def print_test_comparison(yearly_metrics: pd.DataFrame) -> None:
    """Konsolda yalnızca görülmemiş 2025 test yılı karşılaştırmasını gösterir."""
    selected_columns = [
        "Yöntem",
        "Toplam sulama (mm = L/m²)",
        "İdeal nem oranı (%)",
        "Kabul edilebilir nem oranı (%)",
        "Su stresi görülen gün",
        "Çok ıslak gün",
        "Toplam ödül",
        "Başarı puanı",
    ]
    test_results = yearly_metrics[yearly_metrics["Yıl"] == TEST_YEAR][selected_columns]
    separator = "-" * 155

    print("\n" + "=" * 155)
    print("  2025 BAĞIMSIZ TEST YILI — SULAMA YÖNTEMLERİ KARŞILAŞTIRMASI")
    print("=" * 155)
    print(test_results.to_string(index=False))
    print(separator)



def main() -> None:
    """Veri hazırlama, eğitim, değerlendirme ve görselleştirme iş akışını yürütür."""
    cleanup_old_results()

    # 1) Yeniden analiz verilerini yükle veya indir ve doğrula.
    full_df, train_df, _test_df = load_or_download_data()

    # 2) 2020-2023 eğitim ve 2024 doğrulama dönemleriyle hiperparametreleri seç.
    selected_params, _hyperparameter_results = run_hyperparameter_search(
        full_df,
        episodes=HYPERPARAMETER_EPISODES,
    )

    # 3) Nihai durum eşiklerini yalnızca 2020-2024 verisinden hesapla.
    thresholds = calculate_thresholds(train_df)
    save_thresholds(thresholds)
    print_thresholds(thresholds)

    # 4) Seçilen hiperparametrelerle nihai modeli 2020-2024 döneminde eğit.
    q_table, training_history = train_q_learning(
        train_df,
        thresholds,
        alpha=float(selected_params["alpha"]),
        gamma=float(selected_params["gamma"]),
        epsilon_decay=float(selected_params["epsilon_decay"]),
        episodes=FINAL_EPISODES,
        training_years=TRAIN_YEARS,
        seed=SEED,
        verbose=True,
        run_label="Nihai Q-Learning eğitimi",
    )
    np.save(RESULT_DIR / "q_table.npy", q_table)

    # 5) Q-Learning ve referans politikaları tüm yıllar için değerlendir.
    policies: dict[str, PolicyFunction] = {
        "Q-Learning": q_learning_policy_factory(q_table),
        "Eşik tabanlı": threshold_policy,
        "Sabit zamanlı": fixed_schedule_policy,
        "Sulama yok": no_irrigation_policy,
    }

    all_logs: dict[tuple[int, str], pd.DataFrame] = {}
    metric_records: list[dict[str, float | int | str]] = []

    for year in ALL_YEARS:
        year_df = full_df[full_df["yil"] == year].copy().reset_index(drop=True)
        if year_df.empty:
            raise ValueError(f"{year} yılına ait simülasyon verisi bulunamadı.")

        period_label = (
            "Test dönemi"
            if year == TEST_YEAR
            else "Eğitim dönemi — geriye dönük analiz"
        )

        for method_name, policy in policies.items():
            log_df, metrics = simulate_policy(
                method_name,
                policy,
                year_df,
                thresholds,
                period_label,
            )
            all_logs[(year, method_name)] = log_df
            metric_records.append(metrics)

    # 6) Performans metriklerini hesapla ve özet tabloları kaydet.
    yearly_metrics = add_success_scores(pd.DataFrame(metric_records))
    method_order = {name: index for index, name in enumerate(policies)}
    yearly_metrics["_method_order"] = yearly_metrics["Yöntem"].map(method_order)
    yearly_metrics = (
        yearly_metrics
        .sort_values(["Yıl", "_method_order"])
        .drop(columns="_method_order")
        .reset_index(drop=True)
    )

    yearly_metrics.to_csv(
        RESULT_DIR / "yillik_yontem_karsilastirmasi_2020_2025.csv",
        index=False,
        encoding="utf-8-sig",
    )

    test_metrics = yearly_metrics[yearly_metrics["Yıl"] == TEST_YEAR].copy()
    test_metrics.to_csv(
        RESULT_DIR / "yontem_karsilastirmasi_2025_test.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # 7) Grafik ve dashboard animasyonunu üret.
    create_all_graphs(
        full_df,
        training_history,
        all_logs,
        yearly_metrics,
        thresholds,
    )

    # 8) Bağımsız test sonuçlarını konsola yazdır.
    print_test_comparison(yearly_metrics)

if __name__ == "__main__":
    main()
