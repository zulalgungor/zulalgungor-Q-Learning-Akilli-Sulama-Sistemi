# Q-Learning Tabanlı Akıllı Sulama Sistemi: Gerçek Verilerle Python Uygulaması

Bu proje, Bursa için Open-Meteo Historical Weather API üzerinden sağlanan ERA5-Land ve Best Match yeniden analiz verilerini kullanarak günlük sulama kararı üreten tabular Q-Learning modelini uygular.

Sistem; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve mevsim bilgisine göre her gün **0, 3, 6 veya 9 mm** sulama seçeneklerinden birini seçer. Sulama miktarı için **1 mm = 1 L/m²** dönüşümü geçerlidir.

> Bu çalışma doğrudan saha sensörü ölçümü veya fiziksel bir sulama kontrolörü içermez. Toprak nemi, günlük su dengesi modeliyle simüle edilir. ERA5-Land toprak nemi karşılaştırma amacıyla referans olarak gösterilir.

![Akıllı Sulama Sistemi GIF](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif)

## Projenin Amacı

Amaç, toprak nemini uygun aralıkta tutarken su stresi, aşırı ıslaklık ve gereksiz sulamayı azaltan bir sulama politikası öğrenmektir.

Q-Learning modeli aşağıdaki yöntemlerle karşılaştırılmıştır:

- Eşik tabanlı sulama
- Sabit zamanlı sulama
- Sulama yapılmayan senaryo

## Veri Kaynağı

Veriler Open-Meteo Historical Weather API üzerinden alınmaktadır.

Kullanılan değişkenler:

- Ortalama, minimum ve maksimum hava sıcaklığı
- Günlük yağış
- Referans evapotranspirasyon (ET0)
- Ortalama rüzgâr hızı
- Yüzey basıncı
- 0–7 cm toprak nemi
- 7–28 cm toprak nemi
- 0–7 cm toprak sıcaklığı

ERA5-Land kaynağı sıcaklık ve toprak değişkenleri için, Best Match kaynağı ise rüzgâr ve yüzey basıncı için kullanılmaktadır.

## Veri Ayrımı

| Aşama | Kullanılan dönem |
|---|---|
| Hiperparametre eğitimi | 2020–2023 |
| Doğrulama | 2024 |
| Nihai eğitim | 2020–2024 |
| Bağımsız test | 2025 |

2025 verisi hiperparametre seçimi ve nihai eğitim sırasında kullanılmamıştır.

## Durum Uzayı

Modelin durumu aşağıdaki ayrık değişkenlerden oluşur:

| Değişken | Durum sayısı |
|---|---:|
| Toprak nemi | 5 |
| Yağış | 3 |
| Sıcaklık | 3 |
| ET0 | 3 |
| Mevsim | 4 |

Toplam durum sayısı:

```text
5 × 3 × 3 × 3 × 4 = 540
```

Dört sulama aksiyonu ile Q tablosunun boyutu:

```text
540 × 4 = 2160 Q değeri
```

## Ayrıklaştırma Eşikleri

Eşikler yalnızca 2020–2024 eğitim verisinden hesaplanmıştır.

### Toprak nemi

| Sınır | Değer |
|---|---:|
| Çok kuru sınırı | 0.1739 m³/m³ |
| İdeal nem alt sınırı | 0.2688 m³/m³ |
| İdeal nem üst sınırı | 0.3797 m³/m³ |
| Çok ıslak sınırı | 0.4086 m³/m³ |

### Sıcaklık ve ET0

| Değişken | Alt sınır | Üst sınır |
|---|---:|---:|
| Sıcaklık | 11.90 °C | 20.75 °C |
| ET0 | 1.77 mm | 3.95 mm |

## Aksiyon Uzayı

| Aksiyon | Sulama miktarı |
|---|---:|
| Sulama yok | 0 mm |
| Düşük sulama | 3 mm |
| Orta sulama | 6 mm |
| Yüksek sulama | 9 mm |

## Toprak Nemi Geçiş Modeli

Bir sonraki günün toprak nemi; etkili yağış, etkili sulama, evapotranspirasyon ve drenaj dikkate alınarak hesaplanır.

```text
Δθ = (etkili yağış + etkili sulama − ET kaybı) / kök bölgesi derinliği
```

Kullanılan temel parametreler:

| Parametre | Değer |
|---|---:|
| Kök bölgesi derinliği | 280 mm |
| Yağış infiltrasyon verimi | 0.75 |
| Sulama verimi | 0.85 |
| Bitki katsayısı | 0.85 |
| Drenaj oranı | 0.35 |
| Maksimum etkili günlük yağış | 40 mm |

## Ödül Fonksiyonu

Ödül fonksiyonu aşağıdaki hedefleri birlikte değerlendirir:

- Toprak nemini ideal veya kabul edilebilir aralıkta tutmak
- Çok kuru ve çok ıslak koşulları azaltmak
- Kullanılan sulama miktarını sınırlamak
- Yağış sırasında gereksiz sulamayı önlemek
- Nemli toprağa sulama yapılmasını engellemek
- Kuru ve yüksek ET0 koşullarında sulama yapılmamasını cezalandırmak
- Toprak neminin hedef merkeze yaklaşmasını ödüllendirmek

## Q-Learning Güncellemesi

Q tablosu aşağıdaki denklemle güncellenir:

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') − Q(s,a)]
```

Burada:

- `s`: mevcut durum
- `a`: seçilen aksiyon
- `r`: alınan ödül
- `s'`: sonraki durum
- `α`: öğrenme oranı
- `γ`: indirim faktörü

Aksiyon seçimi epsilon-greedy yöntemiyle gerçekleştirilir. Epsilon değeri eğitim sırasında `1.00` değerinden başlayarak en az `0.05` değerine kadar azaltılır.

## Hiperparametre Seçimi

Üç faktörlü ve üç seviyeli dokuz kontrollü hiperparametre kombinasyonu denenmiştir. Her kombinasyon 2020–2023 verisiyle 1200 bölüm eğitilmiş ve 2024 doğrulama yılı üzerinde değerlendirilmiştir.

<!-- HİPERPARAMETRE_TABLOSU_BAŞLANGIÇ -->

### Hiperparametre Karşılaştırma Tablosu

| Sıra | Deney | Alpha | Gamma | Epsilon decay | Sulama (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Stres günü | Toplam ödül | Başarı puanı |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **Deney 01** | **0.10** | **0.90** | **0.9975** | **723.0** | **70.77** | **85.52** | **34** | **6153.92** | **104.595** |
| 2 | Deney 05 | 0.15 | 0.95 | 0.9995 | 843.0 | 64.48 | 89.34 | 13 | 5519.84 | 103.685 |
| 3 | Deney 08 | 0.25 | 0.95 | 0.9975 | 765.0 | 68.58 | 84.97 | 34 | 5956.14 | 101.953 |
| 4 | Deney 02 | 0.10 | 0.95 | 0.9985 | 789.0 | 63.39 | 83.06 | 41 | 5358.06 | 96.459 |
| 5 | Deney 04 | 0.15 | 0.90 | 0.9985 | 816.0 | 60.66 | 83.06 | 38 | 5092.81 | 94.598 |
| 6 | Deney 06 | 0.15 | 0.99 | 0.9975 | 1017.0 | 54.10 | 83.61 | 14 | 3474.78 | 87.702 |
| 7 | Deney 03 | 0.10 | 0.99 | 0.9995 | 1071.0 | 55.46 | 81.97 | 16 | 3384.19 | 85.449 |
| 8 | Deney 07 | 0.25 | 0.90 | 0.9995 | 903.0 | 49.73 | 77.05 | 56 | 3385.10 | 79.683 |
| 9 | Deney 09 | 0.25 | 0.99 | 0.9985 | 1119.0 | 36.34 | 63.66 | 77 | 216.02 | 51.871 |

<!-- HİPERPARAMETRE_TABLOSU_BİTİŞ -->

Seçilen kombinasyon:

| Hiperparametre | Değer |
|---|---:|
| Öğrenme oranı (`alpha`) | 0.10 |
| İndirim faktörü (`gamma`) | 0.90 |
| Epsilon azalma katsayısı | 0.9975 |
| Nihai eğitim bölüm sayısı | 4000 |
| Rastgelelik tohumu | 42 |

Seçilen deneyin 2024 doğrulama sonucu:

| Metrik | Sonuç |
|---|---:|
| Toplam sulama | 723 mm |
| İdeal nem oranı | %70.77 |
| Kabul edilebilir nem oranı | %85.52 |
| Su stresi görülen gün | 34 |
| Çok ıslak gün | 19 |
| Toplam ödül | 6153.92 |
| Başarı puanı | 104.595 |

## 2025 Bağımsız Test Sonuçları

| Yöntem | Sulama (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi günü | Çok ıslak gün | Toplam ödül | Başarı puanı |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q-Learning | 843 | 64.93 | 88.22 | 27 | 16 | 5843.48 | 97.849 |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 15 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | 22 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | 12 | -5382.49 | 45.031 |

Q-Learning, 2025 bağımsız test yılında en yüksek ideal nem oranını, kabul edilebilir nem oranını, toplam ödülü ve birleşik başarı puanını elde etmiştir.

## 2025 Aksiyon Dağılımı

| Aksiyon | Gün sayısı |
|---|---:|
| Sulama yok | 220 |
| Düşük sulama | 40 |
| Orta sulama | 74 |
| Yüksek sulama | 31 |

## Kurulum

Gerekli paketleri yükleyin:

```bash
pip install numpy pandas matplotlib requests pillow
```

## Çalıştırma

```bash
python Akilli_Sulama_Sistemi.py
```

İlk çalıştırmada veriler indirilerek `veri/` klasörüne kaydedilir. Sonraki çalıştırmalarda doğrulanan yerel CSV dosyaları yeniden kullanılır.

## Proje Yapısı

```text
.
├── Akilli_Sulama_Sistemi.py
├── veri/
│   ├── bursa_2020_2025_gunluk_gercek_veri.csv
│   ├── bursa_2020_2024_egitim.csv
│   └── bursa_2025_test.csv
└── sonuclar/
    ├── animasyon_1_akilli_sulama_dashboard_2025.gif
    ├── grafik_1_egitim_paneli.png
    ├── grafik_2_q_learning_gunluk_davranis.png
    ├── grafik_3_yontem_karsilastirmasi.png
    ├── grafik_4_aksiyon_dagilimi.png
    ├── grafik_5_tum_yillar_cevre_verileri.png
    ├── grafik_6_yillara_gore_nem_basarisi.png
    ├── ayriklastirma_esikleri.json
    ├── hiperparametre_karsilastirmasi.csv
    ├── secilen_hiperparametreler.json
    ├── q_table.npy
    ├── yillik_yontem_karsilastirmasi_2020_2025.csv
    └── yontem_karsilastirmasi_2025_test.csv
```

## Görseller

### Q-Learning Eğitim Süreci

![Q-Learning Eğitim Süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

### 2025 Günlük Davranış

![2025 Günlük Davranış](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png)

### Sulama Yöntemlerinin Karşılaştırılması

![Yöntem Karşılaştırması](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png)

### Q-Learning Aksiyon Dağılımı

![Aksiyon Dağılımı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png)

### 2020–2025 Çevresel Veriler

![Çevresel Veriler](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png)

### Yıllara Göre Toprak Nemi Başarısı

![Yıllara Göre Nem Başarısı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png)

## Çıktılar

Program çalıştırıldığında:

- API verilerini indirir ve doğrular.
- Saatlik verileri günlük değerlere dönüştürür.
- Hiperparametre araması gerçekleştirir.
- Nihai Q-Learning modelini eğitir.
- Q tablosunu kaydeder.
- Dört sulama yöntemini karşılaştırır.
- 2025 bağımsız test sonuçlarını üretir.
- Grafik ve GIF animasyonu oluşturur.

