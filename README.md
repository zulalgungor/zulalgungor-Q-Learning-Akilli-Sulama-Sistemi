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
|---|---|
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
|---|---|
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
|---|---|
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
|---|---|
| Çok kuru sınırı | 0.1739 m³/m³ |
| İdeal nem alt sınırı | 0.2688 m³/m³ |
| İdeal nem üst sınırı | 0.3796 m³/m³ |
| Çok ıslak sınırı | 0.4086 m³/m³ |
| Düşük/orta sıcaklık sınırı | 11.90 °C |
| Orta/yüksek sıcaklık sınırı | 20.75 °C |
| Düşük/orta ET0 sınırı | 1.77 mm |
| Orta/yüksek ET0 sınırı | 3.95 mm |

---

## Hiperparametre Karşılaştırması

Hiperparametre seçimi için öğrenme oranı, indirim faktörü ve epsilon azalma katsayısının farklı kombinasyonlarından oluşan dengeli **L9 deney tasarımı** kullanılmıştır. Her deney, 2020–2023 verileri üzerinde 1200 episode boyunca eğitilmiş ve 2024 verileriyle doğrulanmıştır.

| Deney | Öğrenme oranı (α) | İndirim faktörü (γ) | Epsilon azalması | Toplam sulama (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi (gün) | Aşırı sulama (gün) | Toplam ödül | Başarı puanı |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **01** | **0.10** | **0.90** | **0.9975** | **723** | **70.77** | **85.52** | **34** | **1** | **6153.92** | **104.595** |
| 02 | 0.10 | 0.95 | 0.9985 | 789 | 63.39 | 83.06 | 41 | 9 | 5358.06 | 96.459 |
| 03 | 0.10 | 0.99 | 0.9995 | 1071 | 55.46 | 81.97 | 16 | 47 | 3384.19 | 85.449 |
| 04 | 0.15 | 0.90 | 0.9985 | 816 | 60.66 | 83.06 | 38 | 11 | 5092.81 | 94.598 |
| 05 | 0.15 | 0.95 | 0.9995 | 843 | 64.48 | 89.34 | 13 | 19 | 5519.84 | 103.685 |
| 06 | 0.15 | 0.99 | 0.9975 | 1017 | 54.10 | 83.61 | 14 | 48 | 3474.78 | 87.702 |
| 07 | 0.25 | 0.90 | 0.9995 | 903 | 49.73 | 77.05 | 56 | 27 | 3385.10 | 79.683 |
| 08 | 0.25 | 0.95 | 0.9975 | 765 | 68.58 | 84.97 | 34 | 6 | 5956.14 | 101.953 |
| 09 | 0.25 | 0.99 | 0.9985 | 1119 | 36.34 | 63.66 | 77 | 60 | 216.02 | 51.871 |


Doğrulama sonuçlarına göre en yüksek başarı puanını elde eden **Deney 01**, nihai modelin eğitimi için seçilmiştir.

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
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | **16** | **5843.48** | **97.849** |
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
|:---:|:---:|:---:|
| Sulama yok | 220 | 0 mm |
| Düşük sulama | 40 | 120 mm |
| Orta sulama | 74 | 444 mm |
| Yüksek sulama | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Ajan, yılın yaklaşık %60'ında sulama yapmamıştır.

---

## Grafikler

### Q-Learning Eğitim Süreci

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png"
       alt="Q-Learning eğitim süreci"
       width="650">
</p>

### 2025 Günlük Davranış

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png"
       alt="2025 Q-Learning günlük davranışı"
       width="650">
</p>

### Sulama Yöntemlerinin Karşılaştırılması

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png"
       alt="Sulama yöntemlerinin karşılaştırılması"
       width="650">
</p>

### Aksiyon Dağılımı

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png"
       alt="Q-Learning aksiyon dağılımı"
       width="650">
</p>

### 2020–2025 Çevresel Veriler

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png"
       alt="2020–2025 çevresel veriler"
       width="650">
</p>

### Yıllara Göre Nem Başarısı

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png"
       alt="Yıllara göre nem başarısı"
       width="650">
</p>

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
