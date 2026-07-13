# Q-Learning Tabanlı Akıllı Sulama Sistemi

Bu proje, **Bursa, Türkiye** için elde edilen günlük çevre verilerini kullanarak sulama kararı veren tabular bir **Q-Learning** modeli geliştirmektedir. Sistem; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET₀) ve mevsim bilgisini değerlendirerek her gün **0, 3, 6 veya 9 mm** sulama seçeneklerinden birini seçmektedir.

Çalışmanın temel amacı, simüle edilen kök bölgesi toprak nemini uygun aralıkta tutarken gereksiz sulamayı ve su stresi oluşan günleri azaltmaktır. Model, **2020–2024** verileriyle eğitilmiş ve eğitim sürecinde kullanılmayan **2025 yılı** üzerinde bağımsız olarak test edilmiştir.

![Akıllı Sulama Sistemi GIF](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif)

*2025 bağımsız test yılı boyunca çevre koşulları, toprak nemi ve Q-Learning sulama kararlarının günlük gösterimi.*

## 1. Projenin Kapsamı

Proje, Open-Meteo Historical Weather API üzerinden sağlanan **ERA5-Land** ve **Best Match** verilerini kullanmaktadır. Günlük karar mekanizmasında aşağıdaki değişkenler değerlendirilir:

- 7–28 cm derinlikte toprak nemi
- Günlük yağış
- Ortalama hava sıcaklığı
- Referans evapotranspirasyon (ET₀)
- Mevsim bilgisi

Toprak nemi, günlük yağış, sulama, evapotranspirasyon ve drenaj bileşenlerini içeren basitleştirilmiş bir kök bölgesi su dengesi modeliyle güncellenmektedir. ERA5-Land toprak nemi, simülasyon sonucunu karşılaştırmak için referans olarak gösterilmektedir.

> **Not:** Bu çalışma fiziksel bir sulama kontrolörü veya saha sensörü uygulaması değildir. Sonuçlar, gerçek çevre verileri kullanılarak oluşturulan yazılım tabanlı bir simülasyona aittir.

---

## 2. Veri Ayrımı ve Deney Tasarımı

Veri sızıntısını önlemek amacıyla eğitim, doğrulama ve test dönemleri birbirinden ayrılmıştır.

| Aşama | Kullanılan dönem | Amaç |
|---|---:|---|
| Hiperparametre eğitimi | 2020–2023 | Dokuz hiperparametre kombinasyonunun eğitilmesi |
| Doğrulama | 2024 | En başarılı hiperparametre kombinasyonunun seçilmesi |
| Nihai eğitim | 2020–2024 | Seçilen değerlerle Q-Learning modelinin yeniden eğitilmesi |
| Bağımsız test | 2025 | Modelin daha önce görmediği yıl üzerinde değerlendirilmesi |

Nihai Q-Learning eğitimi **4000 episode**, hiperparametre deneylerinin her biri ise **1200 episode** boyunca gerçekleştirilmiştir. Deneylerin tekrarlanabilirliği için rastgelelik tohumu **42** olarak belirlenmiştir.

---

## 3. Q-Learning Modeli

### 3.1. Durum Uzayı

Q-Learning ajanının durumu beş bileşenden oluşmaktadır:

| Durum değişkeni | Seviye sayısı |
|---|---:|
| Toprak nemi | 5 |
| Yağış | 3 |
| Sıcaklık | 3 |
| ET₀ | 3 |
| Mevsim | 4 |

Toplam durum sayısı:

\[
5 \times 3 \times 3 \times 3 \times 4 = 540
\]

Dört sulama aksiyonu ile birlikte Q tablosu:

\[
5 \times 3 \times 3 \times 3 \times 4 \times 4
\]

boyutundadır.

### 3.2. Aksiyonlar

| Aksiyon | Sulama miktarı |
|---|---:|
| Sulama yok | 0 mm |
| Düşük sulama | 3 mm |
| Orta sulama | 6 mm |
| Yüksek sulama | 9 mm |

Sulama miktarında **1 mm = 1 L/m²** dönüşümü geçerlidir.

### 3.3. Ödül Yaklaşımı

Ödül fonksiyonu aşağıdaki amaçları birlikte dikkate almaktadır:

- Toprak nemini ideal veya kabul edilebilir aralıkta tutmak
- Çok kuru ve çok ıslak koşulları cezalandırmak
- Kullanılan su miktarına maliyet uygulamak
- Yağış sırasında yapılan gereksiz sulamayı cezalandırmak
- Kuru ve yüksek ET₀ koşullarında sulama yapılmamasını cezalandırmak
- Uygun nem koşullarında sulama yapılmadığında su tasarrufunu ödüllendirmek
- Toprak neminin hedef merkeze yaklaşmasını desteklemek

---

## 4. Eğitim Verisinden Hesaplanan Ayrıklaştırma Eşikleri

Bütün eşikler yalnızca **2020–2024 eğitim verisi** kullanılarak hesaplanmıştır.

| Değişken | Eşik | Değer |
|---|---|---:|
| Toprak nemi | Çok kuru sınırı | 0.1739 m³/m³ |
| Toprak nemi | Kuru / ideal alt sınırı | 0.2688 m³/m³ |
| Toprak nemi | İdeal üst sınırı | 0.3797 m³/m³ |
| Toprak nemi | Çok ıslak sınırı | 0.4086 m³/m³ |
| Sıcaklık | Düşük eşik | 11.90 °C |
| Sıcaklık | Yüksek eşik | 20.75 °C |
| ET₀ | Düşük eşik | 1.77 mm |
| ET₀ | Yüksek eşik | 3.95 mm |

Bu değerlere göre ideal toprak nemi aralığı yaklaşık olarak **%26.88–%37.97**, kabul edilebilir nem aralığı ise yaklaşık olarak **%26.88–%40.86** düzeyindedir.

---

## 5. Hiperparametre Seçimi

Dokuz kontrollü hiperparametre kombinasyonu, 2020–2023 verileri üzerinde eğitilmiş ve 2024 doğrulama yılı üzerinde karşılaştırılmıştır.

### Seçilen hiperparametreler

| Parametre | Seçilen değer |
|---|---:|
| Öğrenme oranı, α | 0.10 |
| İndirim faktörü, γ | 0.90 |
| Epsilon azalma katsayısı | 0.9975 |
| Başlangıç epsilon değeri | 1.00 |
| Minimum epsilon değeri | 0.05 |
| Nihai eğitim episode sayısı | 4000 |

Seçilen **Deney 01**, 2024 doğrulama döneminde:

- **723 mm** toplam sulama,
- **%70.77** ideal nem oranı,
- **%85.52** kabul edilebilir nem oranı,
- **34** su stresi günü,
- **6153.92** toplam ödül,
- **104.595** birleşik başarı puanı

elde etmiştir.

<details>
<summary><strong>Dokuz hiperparametre deneyinin karşılaştırmasını göster</strong></summary>

| Sıra | Deney | α | γ | Epsilon decay | Su (mm) | Kabul edilebilir nem (%) | Toplam ödül | Başarı puanı |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Deney 01 | 0.10 | 0.90 | 0.9975 | 723 | 85.52 | 6153.92 | 104.595 |
| 2 | Deney 05 | 0.15 | 0.95 | 0.9995 | 843 | 89.34 | 5519.84 | 103.685 |
| 3 | Deney 08 | 0.25 | 0.95 | 0.9975 | 765 | 84.97 | 5956.14 | 101.953 |
| 4 | Deney 02 | 0.10 | 0.95 | 0.9985 | 789 | 83.06 | 5358.06 | 96.459 |
| 5 | Deney 04 | 0.15 | 0.90 | 0.9985 | 816 | 83.06 | 5092.81 | 94.598 |
| 6 | Deney 06 | 0.15 | 0.99 | 0.9975 | 1017 | 83.61 | 3474.78 | 87.702 |
| 7 | Deney 03 | 0.10 | 0.99 | 0.9995 | 1071 | 81.97 | 3384.19 | 85.449 |
| 8 | Deney 07 | 0.25 | 0.90 | 0.9995 | 903 | 77.05 | 3385.10 | 79.683 |
| 9 | Deney 09 | 0.25 | 0.99 | 0.9985 | 1119 | 63.66 | 216.02 | 51.871 |

</details>

---

## 6. 2025 Bağımsız Test Sonuçları

Q-Learning modeli, 2025 yılında eşik tabanlı, sabit zamanlı ve sulamasız yöntemlerle karşılaştırılmıştır.

| Yöntem | Su (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi günü | Toplam ödül | Başarı puanı |
|---|---:|---:|---:|---:|---:|---:|
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | **5843.48** | **97.849** |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | -5382.49 | 45.031 |

Q-Learning yöntemi, dört yöntem arasında en yüksek ideal nem oranını, kabul edilebilir nem oranını, toplam ödülü ve birleşik başarı puanını elde etmiştir. Bununla birlikte Q-Learning, eşik tabanlı yöntemden daha fazla su kullanmıştır. Bu nedenle çalışmanın temel başarısı yalnızca su miktarını azaltmak değil, kullanılan su karşılığında toprak nemi kararlılığını ve su stresi kontrolünü belirgin biçimde geliştirmektir.

### 2025 aksiyon dağılımı

| Aksiyon | Gün sayısı |
|---|---:|
| Sulama yok | 220 |
| Düşük sulama — 3 mm | 40 |
| Orta sulama — 6 mm | 74 |
| Yüksek sulama — 9 mm | 31 |

Model, 365 günlük test döneminin **220 gününde sulama yapmamış**, **145 gününde** ise farklı miktarlarda sulama kararı vermiştir.

---

## 7. Görsel Sonuçlar

### Q-Learning eğitim süreci

![Q-Learning Eğitim Süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

Grafik; toplam ödül, kullanılan su, epsilon değeri ve ortalama mutlak TD hatasının 4000 episode boyunca değişimini göstermektedir.

### 2025 günlük davranış

![2025 Günlük Davranış](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png)

Grafikte simüle toprak nemi, ERA5-Land referans nemi, yağış, sulama, sıcaklık ve ET₀ değerleri birlikte sunulmaktadır.

### Sulama yöntemlerinin karşılaştırılması

![Yöntem Karşılaştırması](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png)

### Q-Learning aksiyon dağılımı

![Aksiyon Dağılımı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png)

### 2020–2025 çevre verileri

![Çevresel Veriler](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png)

### Yıllara göre toprak nemi başarısı

![Yıllara Göre Nem Başarısı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png)

## 8. Kurulum

### Gereksinimler

- Python 3.10 veya üzeri
- İnternet bağlantısı — verilerin ilk kez indirilmesi için

Gerekli paketler:

```bash
pip install numpy pandas matplotlib requests pillow
```

---

## 9. Çalıştırma

Ana Python dosyasını proje klasöründe çalıştırın:

```bash
python Akilli_Sulama_Sistemi.py
```

İlk çalıştırmada 2020–2025 verileri Open-Meteo API üzerinden indirilerek `veri/` klasörüne kaydedilir. Daha sonraki çalıştırmalarda doğrulanmış yerel CSV dosyaları yeniden kullanılır.

Program sırasıyla:

1. Çevre verilerini indirir veya kayıtlı verileri doğrular.
2. Eğitim verisinden ayrıklaştırma eşiklerini hesaplar.
3. Dokuz hiperparametre kombinasyonunu karşılaştırır.
4. Seçilen hiperparametrelerle nihai Q-Learning modelini eğitir.
5. 2020–2025 döneminde yöntem karşılaştırmalarını oluşturur.
6. 2025 bağımsız test sonuçlarını kaydeder.
7. Grafik ve dashboard animasyonunu üretir.

---

## 10. Proje Yapısı

```text
.
├── Akilli_Sulama_Sistemi.py
├── README.md
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

---

## 11. Üretilen Dosyalar

| Dosya | İçerik |
|---|---|
| `q_table.npy` | Eğitilmiş Q-Learning tablosu |
| `ayriklastirma_esikleri.json` | Eğitim verisinden hesaplanan durum eşikleri |
| `secilen_hiperparametreler.json` | Seçilen hiperparametreler ve doğrulama sonuçları |
| `hiperparametre_karsilastirmasi.csv` | Dokuz hiperparametre deneyinin sonuçları |
| `yontem_karsilastirmasi_2025_test.csv` | 2025 bağımsız test yöntemi karşılaştırması |
| `yillik_yontem_karsilastirmasi_2020_2025.csv` | Bütün yıllar için yöntem sonuçları |
| `grafik_*.png` | Eğitim, test ve karşılaştırma grafikleri |
| `animasyon_*.gif` | Günlük sulama dashboard animasyonu |

---

## 12. Sonuç

Elde edilen sonuçlar, Q-Learning ajanının daha önce görmediği 2025 test yılında geleneksel karşılaştırma yöntemlerine göre toprak nemini daha istikrarlı biçimde yönettiğini göstermektedir. Model, yılın büyük bölümünde toprağı kabul edilebilir nem aralığında tutmuş ve su stresi görülen gün sayısını önemli ölçüde azaltmıştır.

Çalışma; gerçek çevre verilerinin, su dengesi modelinin ve pekiştirmeli öğrenmenin birlikte kullanıldığı, tekrarlanabilir bir akıllı sulama simülasyonu sunmaktadır.

