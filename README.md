# Q-Learning Tabanlı Akıllı Sulama Sistemi

Bursa ili için 2020–2025 dönemine ait çevresel verileri kullanarak günlük sulama kararı üreten tabular **Q-Learning** tabanlı akıllı sulama sistemi.

Model; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve mevsim bilgilerini değerlendirerek her gün uygulanacak sulama miktarını belirler. Temel amaç, toprağı uygun nem aralığında tutarken gereksiz su kullanımını ve su stresini azaltmaktır.

> **Not:** Bu çalışma bir yazılım ve simülasyon uygulamasıdır. Fiziksel sensör, tarla deneyi veya gerçek bir sulama kontrolörü içermez. ERA5-Land toprak nemi verisi karşılaştırma amacıyla referans olarak kullanılmıştır.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif"
       alt="Akıllı sulama sistemi dashboard animasyonu"
       width="900">
</p>

---

## Öne Çıkan Sonuçlar

| Ölçüt | Q-Learning sonucu |
|---|---:|
| 2025 toplam sulama | 843 mm |
| İdeal nem oranı | %64.93 |
| Kabul edilebilir nem oranı | %88.22 |
| Su stresi görülen gün | 27 |
| Toplam ödül | 5843.48 |
| Başarı puanı | 97.849 |
| Sulama yapılmayan gün | 220 / 365 |

Q-Learning en az suyu kullanan yöntem değildir. Buna karşın toprağı hedef nem aralığında tutma, su stresini azaltma, toplam ödül ve birleşik başarı puanı bakımından karşılaştırılan yöntemler arasında en iyi sonucu vermiştir.

---

## Projenin Amacı

- Günlük sulama kararlarını Q-Learning ile belirlemek
- Toprak nemini hedef aralıkta tutmak
- Su stresi görülen gün sayısını azaltmak
- Gereksiz ve aşırı sulamayı sınırlamak
- Q-Learning yöntemini geleneksel sulama yöntemleriyle karşılaştırmak
- Modeli eğitimde kullanılmayan 2025 yılı üzerinde bağımsız olarak test etmek

---

## Kullanılan Veriler

Veriler **Open-Meteo Historical Weather API** üzerinden alınmıştır.

### Veri kaynakları

- ERA5-Land
- Open-Meteo Best Match
- Günlük yağış verisi
- Referans evapotranspirasyon verisi

### Kullanılan değişkenler

- Ortalama, minimum ve maksimum sıcaklık
- Günlük yağış
- Referans evapotranspirasyon (ET0)
- 0–7 cm toprak nemi
- 7–28 cm toprak nemi
- Toprak sıcaklığı
- Rüzgâr hızı
- Yüzey basıncı
- Mevsim bilgisi

### Veri ayrımı

| Aşama | Kullanılan dönem |
|---|---|
| Hiperparametre eğitimi | 2020–2023 |
| Doğrulama | 2024 |
| Nihai eğitim | 2020–2024 |
| Bağımsız test | 2025 |

2025 verisi hiperparametre seçimi veya eğitim sırasında kullanılmamıştır.

---

## ET0 Veri Kontrolü

2020–2024 eğitim dönemine ait ET0 verisinin özeti:

| Ölçüt | Değer |
|---|---:|
| Gün sayısı | 1827 |
| Minimum ET0 | 0.2600 mm |
| Maksimum ET0 | 7.7600 mm |
| Ortalama ET0 | 3.0719 mm |
| Medyan ET0 | 2.6900 mm |
| Sıfır olmayan gün | 1827 / 1827 |
| Eksik değer oranı | %0.00 |

---

## Q-Learning Yapısı

### Durum uzayı

Ajanın durumu beş değişkenden oluşmaktadır:

1. Toprak nemi
2. Yağış durumu
3. Sıcaklık seviyesi
4. ET0 seviyesi
5. Mevsim

Toprak nemi aşağıdaki sınıflara ayrılmıştır:

- Çok kuru
- Kuru
- Uygun
- Nemli
- Çok ıslak

### Aksiyonlar

| Aksiyon | Sulama miktarı |
|---|---:|
| Sulama yok | 0 mm |
| Düşük sulama | 3 mm |
| Orta sulama | 6 mm |
| Yüksek sulama | 9 mm |

`1 mm = 1 L/m²` dönüşümü kullanılmıştır.

### Q-tablosu boyutu

```text
5 × 3 × 3 × 3 × 4 × 4
```

Boyutlar sırasıyla toprak nemi, yağış, sıcaklık, ET0, mevsim ve aksiyon sayılarını temsil etmektedir.

---

## Eğitim Verisinden Hesaplanan Sınırlar

Bütün sınırlar yalnızca 2020–2024 eğitim verisinden hesaplanmıştır.

| Sınır | Değer |
|---|---:|
| Çok kuru sınırı | 0.1739 m³/m³ |
| İdeal nem alt sınırı | 0.2688 m³/m³ |
| İdeal nem üst sınırı | 0.3796 m³/m³ |
| Çok ıslak sınırı | 0.4086 m³/m³ |
| Düşük/orta sıcaklık sınırı | 11.90 °C |
| Orta/yüksek sıcaklık sınırı | 20.75 °C |
| Düşük/orta ET0 sınırı | 1.77 mm |
| Orta/yüksek ET0 sınırı | 3.95 mm |

---

## Hiperparametre Araması

Hiperparametre seçimi için üç faktörlü ve üç seviyeli dengeli **L9 deney tasarımı** kullanılmıştır. Toplam dokuz kombinasyon denenmiş ve her kombinasyon 1200 episode boyunca eğitilmiştir.

### Seçilen hiperparametreler

| Hiperparametre / Ölçüt | Deney 01 | Deney 02 | Deney 03 | Deney 04 | Deney 05 | Deney 06 | Deney 07 | Deney 08 | Deney 09 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Öğrenme oranı (α) | **0.10** | 0.10 | 0.10 | 0.15 | 0.15 | 0.15 | 0.25 | 0.25 | 0.25 |
| İndirim faktörü (γ) | **0.90** | 0.95 | 0.99 | 0.90 | 0.95 | 0.99 | 0.90 | 0.95 | 0.99 |
| Epsilon azalması | **0.9975** | 0.9985 | 0.9995 | 0.9985 | 0.9995 | 0.9975 | 0.9995 | 0.9975 | 0.9985 |
| Toplam sulama (mm) | **723** | 789 | 1071 | 816 | 843 | 1017 | 903 | 765 | 1119 |
| İdeal nem oranı (%) | **70.77** | 63.39 | 55.46 | 60.66 | 64.48 | 54.10 | 49.73 | 68.58 | 36.34 |
| Kabul edilebilir nem oranı (%) | **85.52** | 83.06 | 81.97 | 83.06 | 89.34 | 83.61 | 77.05 | 84.97 | 63.66 |
| Su stresi görülen gün | **34** | 41 | 16 | 38 | 13 | 14 | 56 | 34 | 77 |
| Aşırı sulama görülen gün | **1** | 9 | 47 | 11 | 19 | 48 | 27 | 6 | 60 |
| Toplam ödül | **6153.92** | 5358.06 | 3384.19 | 5092.81 | 5519.84 | 3474.78 | 3385.10 | 5956.14 | 216.02 |
| Başarı puanı | **104.595** | 96.459 | 85.449 | 94.598 | 103.685 | 87.702 | 79.683 | 101.953 | 51.871 |

### 2024 doğrulama sonucu

| Ölçüt | Değer |
|---|---:|
| Toplam sulama | 723 mm |
| İdeal nem oranı | %70.77 |
| Kabul edilebilir nem oranı | %85.52 |
| Su stresi görülen gün | 34 |
| Aşırı sulama görülen gün | 1 |
| Toplam ödül | 6153.92 |
| Başarı puanı | 104.595 |

---

## Nihai Eğitim Sonucu

Seçilen hiperparametrelerle model, 2020–2024 verisinin tamamında 4000 episode boyunca yeniden eğitilmiştir.

| Episode | Ortalama ödül | Ortalama su | Ortalama mutlak TD hatası | Epsilon |
|---:|---:|---:|---:|---:|
| 500 | 3186.08 | 937.56 mm | 23.34 | 0.286 |
| 1000 | 5493.52 | 729.60 mm | 19.39 | 0.082 |
| 2000 | 5988.71 | 681.48 mm | 18.69 | 0.050 |
| 3000 | 5907.94 | 663.42 mm | 19.06 | 0.050 |
| 4000 | 6086.53 | 676.44 mm | 18.22 | 0.050 |

Eğitim sürecinde ödül artmış, kullanılan su azalmış ve TD hatası daha düşük bir aralıkta dengelenmiştir.

---

## 2025 Bağımsız Test Sonuçları

| Yöntem | Toplam su (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi görülen gün | Çok ıslak gün | Toplam ödül | Başarı puanı |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | 16 | **5843.48** | **97.849** |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 15 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | 22 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | 12 | -5382.49 | 45.031 |

Eşik tabanlı yönteme göre Q-Learning:

- Kabul edilebilir nem oranını **27.95 yüzde puan** artırmıştır.
- İdeal nem oranını **23.83 yüzde puan** artırmıştır.
- Su stresi görülen gün sayısını **130'dan 27'ye** düşürmüştür.
- Su stresi günlerinde yaklaşık **%79.2 azalma** sağlamıştır.

---

## 2025 Aksiyon Dağılımı

| Aksiyon | Gün sayısı | Toplam su katkısı |
|---|---:|---:|
| Sulama yok | 220 | 0 mm |
| Düşük sulama | 40 | 120 mm |
| Orta sulama | 74 | 444 mm |
| Yüksek sulama | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Ajan, yılın yaklaşık %60'ında sulama yapmamıştır.

---

## Grafikler

### Q-Learning eğitim süreci

![Q-Learning eğitim süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

### 2025 günlük davranış

![2025 günlük davranış](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png)

### Sulama yöntemlerinin karşılaştırılması

![Sulama yöntemlerinin karşılaştırılması](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png)

### Aksiyon dağılımı

![Q-Learning aksiyon dağılımı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png)

### 2020–2025 çevresel veriler

![2020–2025 çevresel veriler](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png)

### Yıllara göre nem başarısı

![Yıllara göre nem başarısı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png)

---

## Kurulum

### Gereksinimler

- Python 3.10 veya üzeri
- NumPy
- pandas
- Matplotlib
- Requests
- Pillow

### Paketlerin kurulması

```bash
pip install numpy pandas matplotlib requests pillow
```

---

## Çalıştırma

README dosyası depo ana dizinindedir. Ana Python dosyası ise `Akıllı sulama sistemi` klasörü içinde bulunmaktadır.

Öncelikle proje klasörüne girin:

```bash
cd "Akıllı sulama sistemi"
```

Ardından programı çalıştırın:

```bash
python Akilli_Sulama_Sistemi.py
```

İlk çalıştırmada çevresel veriler Open-Meteo API üzerinden indirilerek `veri/` klasörüne kaydedilir. Sonraki çalıştırmalarda doğrulanan yerel CSV dosyaları yeniden kullanılır.

---

## Üretilen Dosyalar

Programın ürettiği sonuçlar `Akıllı sulama sistemi/sonuclar/` klasörüne kaydedilir.

```text
sonuclar/
├── animasyon_1_akilli_sulama_dashboard_2025.gif
├── grafik_1_egitim_paneli.png
├── grafik_2_q_learning_gunluk_davranis.png
├── grafik_3_yontem_karsilastirmasi.png
├── grafik_4_aksiyon_dagilimi.png
├── grafik_5_tum_yillar_cevre_verileri.png
├── grafik_6_yillara_gore_nem_basarisi.png
├── ayriklastirma_esikleri.json
├── hiperparametre_karsilastirmasi.csv
├── q_table.npy
├── secilen_hiperparametreler.json
├── yillik_yontem_karsilastirmasi_2020_2025.csv
└── yontem_karsilastirmasi_2025_test.csv
```

---

## Proje Klasör Yapısı

```text
zulalgungor-Q-Learning-Akilli-Sulama-Sistemi/
├── README.md
├── .gitignore
└── Akıllı sulama sistemi/
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
        ├── q_table.npy
        ├── secilen_hiperparametreler.json
        ├── yillik_yontem_karsilastirmasi_2020_2025.csv
        └── yontem_karsilastirmasi_2025_test.csv
```

---

## Karşılaştırılan Sulama Yöntemleri

### Q-Learning

Toprak nemi, yağış, sıcaklık, ET0 ve mevsim durumuna göre en yüksek Q değerine sahip sulama aksiyonunu seçer.

### Eşik tabanlı sulama

Toprak nemi belirlenen sınırların altına düştüğünde sulama yapar. Yağışın yüksek olduğu günlerde sulama uygulanmaz.

### Sabit zamanlı sulama

Her dört günde bir, yağış yoksa 6 mm sulama uygular.

### Sulama yok

Bütün günlerde 0 mm sulama uygular ve karşılaştırma için alt referans oluşturur.

---

## Başarı Puanı

Yöntemleri tek bir ölçüt altında karşılaştırmak amacıyla birleşik başarı puanı kullanılmıştır.

Puan hesaplanırken aşağıdaki unsurlar birlikte değerlendirilmiştir:

- Kabul edilebilir nem oranı
- İdeal nem oranı
- Toplam su kullanımı
- Su stresi görülen gün sayısı
- Çok ıslak gün sayısı
- Gereksiz veya aşırı sulama sayısı

Bu nedenle başarı puanı yalnızca su tüketimini değil, sulama kalitesini de temsil etmektedir.

---

## Sonuç

Q-Learning tabanlı sistem, 2025 bağımsız test yılında karşılaştırılan yöntemlere göre toprak nemini daha başarılı şekilde yönetmiştir.

Model en düşük su tüketimini sağlamamış olsa da:

- kabul edilebilir nem oranını yükseltmiş,
- su stresi günlerini önemli ölçüde azaltmış,
- toplam ödül ve birleşik başarı puanında en iyi sonucu elde etmiştir.

Sonuçlar, pekiştirmeli öğrenmenin günlük çevresel koşullara göre uyarlanabilir sulama kararları üretmek için kullanılabileceğini göstermektedir.

---

## Kullanılan Teknolojiler

- Python
- NumPy
- pandas
- Matplotlib
- Pillow
- Requests
- Open-Meteo Historical Weather API
- ERA5-Land yeniden analiz verileri

---
