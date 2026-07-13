# Q-Learning Tabanlı Akıllı Sulama Sistemi

Bu projede, Bursa ili için 2020–2025 dönemine ait günlük çevresel veriler kullanılarak çizelgesel (tabular) **Q-Learning** tabanlı bir akıllı sulama sistemi geliştirilmiştir.

Model; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve mevsim bilgilerini değerlendirerek günlük sulama miktarını belirlemektedir. Temel amaç, toprağı uygun nem aralığında tutarken gereksiz su kullanımını, aşırı sulamayı ve su stresini azaltmaktır.

> **Not:** Bu çalışma bir yazılım ve simülasyon uygulamasıdır. Fiziksel sensör, tarla deneyi veya gerçek bir sulama kontrolörü içermez. ERA5-Land toprak nemi verisi karşılaştırma amacıyla referans olarak kullanılmıştır.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif"
       alt="Akıllı sulama sistemi dashboard animasyonu"
       width="900">
</p>

---

## Öne Çıkan Sonuçlar

| Ölçüt | Q-Learning sonucu |
|:---:|:---:|
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

Çevresel veriler **Open-Meteo Historical Weather API** üzerinden alınmıştır. Toprak nemi için ERA5-Land yeniden analiz verileri, meteorolojik değişkenler için Open-Meteo tarafından sağlanan günlük veriler kullanılmıştır.

### Veri kaynakları

- ERA5-Land
- Open-Meteo Best Match
- Günlük yağış verisi
- Referans evapotranspirasyon verisi

---

## Durum Uzayı

Günlük sulama kararı aşağıdaki durum değişkenlerine göre verilmektedir:

| Durum değişkeni | Sınıf sayısı | Sınıflar |
|:---:|:---:|:---:|
| Toprak nemi | 5 | Çok kuru, kuru, uygun, nemli, çok ıslak |
| Yağış | 3 | Yağış yok, düşük yağış, yüksek yağış |
| Sıcaklık | 3 | Düşük, orta, yüksek |
| ET0 | 3 | Düşük, orta, yüksek |
| Mevsim | 4 | Kış, ilkbahar, yaz, sonbahar |

Toplam durum sayısı:

```text
5 × 3 × 3 × 3 × 4 = 540 durum
```

Dört sulama aksiyonu ile birlikte Q-tablosunda:

```text
540 × 4 = 2160 durum-aksiyon değeri
```

bulunmaktadır.

### Ayrıklaştırma eşikleri

| Değişken | Sınıf | Aralık |
|:---:|:---:|:---:|
| Toprak nemi | Çok kuru | `< 0.1739 m³/m³` |
| Toprak nemi | Kuru | `0.1739 – 0.2688 m³/m³` |
| Toprak nemi | Uygun | `0.2688 – 0.3797 m³/m³` |
| Toprak nemi | Nemli | `0.3797 – 0.4086 m³/m³` |
| Toprak nemi | Çok ıslak | `≥ 0.4086 m³/m³` |
| Sıcaklık | Düşük | `< 11.90 °C` |
| Sıcaklık | Orta | `11.90 – 20.75 °C` |
| Sıcaklık | Yüksek | `≥ 20.75 °C` |
| ET0 | Düşük | `< 1.77 mm` |
| ET0 | Orta | `1.77 – 3.95 mm` |
| ET0 | Yüksek | `≥ 3.95 mm` |

Bütün sayısal eşikler yalnızca **2020–2024 eğitim verisinden** hesaplanmıştır.

---

## Aksiyonlar

Sistemin seçebildiği sulama aksiyonları:

| Aksiyon indeksi | Sulama kararı | Sulama miktarı |
|:---:|:---:|:---:|
| 0 | Sulama yapılmaz | 0 mm |
| 1 | Düşük sulama | 3 mm |
| 2 | Orta sulama | 6 mm |
| 3 | Yüksek sulama | 9 mm |

```text
1 mm sulama = 1 L/m²
```

---

## Ödül Yapısı

### Toprak nemine göre ödüller

| Yeni toprak nemi durumu | Ödül / ceza |
|:---:|:---:|
| İdeal nem | +25 |
| Kabul edilebilir nem | +7 |
| Kuru | -12 |
| Çok kuru | -38 |
| Çok ıslak | -32 |

### Sulama kararına göre ek ödül ve cezalar

| Koşul | Ödül / ceza |
|:---:|:---:|
| Kullanılan her 1 mm sulama suyu | -0.35 |
| Yağış en az 5 mm iken sulama yapılması | -10 |
| Toprak hedef üst sınırındayken sulama yapılması | -9 |
| Toprak kuru ve ET0 yüksekken sulama yapılmaması | -18 |
| Toprak uygun aralıktayken sulama yapılmaması | +4 |
| Hedef nem merkezine yaklaşma veya uzaklaşma | -12 ile +12 arasında |


---

## Q-Learning Karar ve Güncelleme Süreci

Model, mevcut durum için Q-tablosunda bulunan dört sulama aksiyonunu değerlendirir. Eğitim sırasında epsilon-greedy yöntemi kullanılarak rastgele keşif ile öğrenilmiş aksiyonların kullanımı arasında denge kurulur.

```text
ε olasılığıyla rastgele aksiyon
1 - ε olasılığıyla en yüksek Q-değerine sahip aksiyon
```

Epsilon değeri her episode sonunda aşağıdaki şekilde azaltılır:

```text
ε = max(0.05, ε × 0.9975)
```

Seçilen aksiyon ortama uygulandıktan sonra yeni toprak nemi ve günlük ödül hesaplanır. İlgili durum-aksiyon değeri aşağıdaki Q-Learning denklemiyle güncellenir:

$$
Q(s,a) \leftarrow Q(s,a) +
\alpha \left[
r + \gamma \max_{a'} Q(s',a') - Q(s,a)
\right]
$$

| Sembol | Projedeki karşılığı |
|:---:|:---:|
| `s` | Mevcut toprak nemi ve çevresel koşullardan oluşan durum |
| `a` | Seçilen 0, 3, 6 veya 9 mm sulama aksiyonu |
| `r` | Sulama kararı sonucunda hesaplanan günlük ödül |
| `s'` | Bir sonraki günün durumu |
| `α = 0.10` | Öğrenme oranı |
| `γ = 0.90` | İndirim faktörü |
| `max Q(s',a')` | Bir sonraki durumda bulunan en yüksek aksiyon değeri |

Kod içindeki güncelleme:

```python
td_target = reward + gamma * np.max(q_table[next_state])
td_error = td_target - q_table[state + (action,)]
q_table[state + (action,)] += alpha * td_error
```

Q-tablosunun boyutu:

```text
5 × 3 × 3 × 3 × 4 × 4 = 2160 durum-aksiyon değeri
```

Eğitim sonunda oluşturulan Q-tablosu:

```text
sonuclar/q_table.npy
```

dosyasına kaydedilir.

2025 bağımsız testinde keşif yapılmaz. Model, her durumda Q-tablosundaki en yüksek değere sahip sulama aksiyonunu uygular.

---

## Eğitim Süreci

### Veri Ayrımı

| Aşama | Kullanılan dönem |
|:---:|:---:|
| Hiperparametre eğitimi | 2020–2023 |
| Doğrulama | 2024 |
| Nihai eğitim | 2020–2024 |
| Bağımsız test | 2025 |

2025 verisi hiperparametre seçimi veya eğitim sırasında kullanılmamıştır.

---

### ET0 Veri Kontrolü

2020–2024 eğitim dönemine ait ET0 verisinin özeti:

| Ölçüt | Değer |
|:---:|:---:|
| Gün sayısı | 1827 |
| Minimum ET0 | 0.2600 mm |
| Maksimum ET0 | 7.7600 mm |
| Ortalama ET0 | 3.0719 mm |
| Medyan ET0 | 2.6900 mm |
| Sıfır olmayan gün | 1827 / 1827 |
| Eksik değer oranı | %0.00 |

---

### Hiperparametre Optimizasyonu

Hiperparametre seçimi için öğrenme oranı, indirim faktörü ve epsilon azalma katsayısının farklı kombinasyonlarından oluşan dengeli **L9 deney tasarımı** kullanılmıştır. Her deney, 2020–2023 verileri üzerinde 1200 episode boyunca eğitilmiş ve 2024 verileriyle doğrulanmıştır.

| Deney | α | γ | Epsilon | Toplam sulama (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi (gün) | Aşırı sulama (gün) | Toplam ödül | Başarı puanı |
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

#### 2024 Doğrulama Sonucu

| Ölçüt | Değer |
|:---:|:---:|
| Toplam sulama | 723 mm |
| İdeal nem oranı | %70.77 |
| Kabul edilebilir nem oranı | %85.52 |
| Su stresi görülen gün | 34 |
| Aşırı sulama görülen gün | 1 |
| Toplam ödül | 6153.92 |
| Başarı puanı | 104.595 |

---

### Nihai Eğitim Sonucu

Seçilen hiperparametrelerle model, 2020–2024 verisinin tamamında 4000 episode boyunca yeniden eğitilmiştir.

| Episode | Ortalama ödül | Ortalama su | Ortalama mutlak TD hatası | Epsilon |
|:---:|:---:|:---:|:---:|:---:|
| 500 | 3186.08 | 937.56 mm | 23.34 | 0.286 |
| 1000 | 5493.52 | 729.60 mm | 19.39 | 0.082 |
| 2000 | 5988.71 | 681.48 mm | 18.69 | 0.050 |
| 3000 | 5907.94 | 663.42 mm | 19.06 | 0.050 |
| 4000 | 6086.53 | 676.44 mm | 18.22 | 0.050 |

Eğitim sürecinde ödül artmış, kullanılan su azalmış ve TD hatası daha düşük bir aralıkta dengelenmiştir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png"
       alt="Q-Learning eğitim süreci"
       width="650">
</p>

---

### 2025 Bağımsız Test Sonuçları

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

### 2025 Aksiyon Dağılımı

| Aksiyon | Gün sayısı | Toplam su katkısı |
|:---:|:---:|:---:|
| Sulama yok | 220 | 0 mm |
| Düşük sulama | 40 | 120 mm |
| Orta sulama | 74 | 444 mm |
| Yüksek sulama | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Ajan, 365 günün 220'sinde sulama yapmamıştır. Bu değer yılın yaklaşık %60.27'sine karşılık gelmektedir.

---

## Grafikler

### 2025 Günlük Davranış

2025 bağımsız test yılında simüle edilen toprak nemi, ERA5-Land referans toprak nemi, yağış, sulama, sıcaklık ve ET0 değişimleri birlikte gösterilmektedir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png"
       alt="2025 Q-Learning günlük davranışı"
       width="650">
</p>

### Sulama Yöntemlerinin Karşılaştırılması

Q-Learning; ideal nem oranı, kabul edilebilir nem oranı ve toplam ödül bakımından karşılaştırılan yöntemler arasında en iyi sonucu vermiştir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png"
       alt="Sulama yöntemlerinin karşılaştırılması"
       width="650">
</p>

### Aksiyon Dağılımı

Aksiyon dağılımı, ajanın yalnızca gerekli günlerde sulama yaptığını ve sulama miktarını çevresel koşullara göre değiştirdiğini göstermektedir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png"
       alt="Q-Learning aksiyon dağılımı"
       width="650">
</p>

### 2020–2025 Çevresel Veriler

Grafikte 2020–2024 eğitim dönemi ile 2025 bağımsız test dönemi ayrılarak toprak nemi, yağış, sıcaklık ve ET0 verileri gösterilmektedir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png"
       alt="2020–2025 çevresel veriler"
       width="650">
</p>

### Yıllara Göre Nem Başarısı

Yıllık karşılaştırma, Q-Learning yönteminin hem ideal hem de kabul edilebilir nem oranlarında diğer yöntemlerden daha tutarlı sonuç verdiğini göstermektedir.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png"
       alt="Yıllara göre nem başarısı"
       width="650">
</p>

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
pip install -r requirements.txt
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
├── requirements.txt
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

Toprak nemi, yağış, sıcaklık, ET0 ve mevsim durumuna göre Q-tablosundaki en yüksek değere sahip sulama aksiyonunu seçer.

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

Q-Learning tabanlı sistem, 2025 bağımsız test yılında karşılaştırılan yöntemlere göre toprak nemini daha başarılı biçimde yönetmiştir.

Model en düşük su tüketimini sağlamamış olsa da:

- kabul edilebilir nem oranını yükseltmiş,
- su stresi günlerini önemli ölçüde azaltmış,
- toplam ödül ve birleşik başarı puanında en iyi sonucu elde etmiştir.

Sonuçlar, pekiştirmeli öğrenmenin günlük çevresel koşullara uyum sağlayan sulama kararları üretmek için etkili biçimde kullanılabileceğini göstermektedir.

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

## Kaynaklar

- Watkins, C. J. C. H., & Dayan, P. (1992). *Q-Learning*. Machine Learning, 8, 279–292.
- Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction* (2nd ed.). MIT Press.
- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop Evapotranspiration: Guidelines for Computing Crop Water Requirements*. FAO Irrigation and Drainage Paper No. 56.
- Open-Meteo Historical Weather API.
- ERA5-Land Reanalysis Dataset.
