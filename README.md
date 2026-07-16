 Q-Learning Tabanlı Akıllı Sulama Sistemi

Bu proje, Bursa ili için 2020–2025 dönemine ait gerçek çevresel verileri kullanarak günlük sulama kararı üreten tablo **Q-Learning** tabanlı bir akıllı sulama sistemi geliştirmeyi amaçlamaktadır.

Sistem; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve mevsim bilgilerini değerlendirerek her gün uygulanacak sulama miktarını belirler. Temel hedef, toprağı uygun nem aralığında tutarken gereksiz sulamayı ve su stresi oluşumunu azaltmaktır.

> **Not:** Proje bir yazılım ve simülasyon çalışmasıdır. Fiziksel sensör, gerçek tarla deneyi veya doğrudan sulama kontrolörü içermemektedir. ERA5-Land toprak nemi verileri karşılaştırma amacıyla referans olarak kullanılmıştır.

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif"
       alt="Akıllı sulama sistemi dashboard animasyonu"
       width="900">
</p>

---

## Projenin Amacı

- Günlük sulama kararlarını Q-Learning ile belirlemek
- Toprak nemini hedeflenen aralıkta tutmak
- Su stresi görülen gün sayısını azaltmak
- Gereksiz ve aşırı sulamayı sınırlandırmak
- Q-Learning yöntemini geleneksel sulama yöntemleriyle karşılaştırmak
- Modeli eğitimde kullanılmayan 2025 yılı verileri üzerinde bağımsız olarak test etmek

---


## Problemin Tanımı

Proje, sulama problemini bir **Markov Karar Süreci (MDP)** olarak ele almaktadır.

| MDP bileşeni | Projedeki karşılığı |
| --- | --- |
| Ajan | Günlük sulama miktarını seçen Q-Learning modeli |
| Çevre | Günlük su dengesiyle güncellenen simülasyon ortamı |
| Durum | Toprak nemi, yağış, sıcaklık, ET0 ve mevsim |
| Aksiyon | 0, 3, 6 veya 9 mm sulama |
| Ödül | Nem durumu, su tüketimi ve sulama kararının uygunluğu |
| Geçiş | Yağış, sulama, ET0 ve drenaja bağlı yeni toprak nemi |
| Politika | Duruma göre en yüksek Q değerine sahip aksiyon |

Ajan, çevreden aldığı ödüller aracılığıyla uzun vadede en yüksek toplam ödülü sağlayan sulama politikasını öğrenmektedir.

---

## Kullanılan Veriler

Veriler **Open-Meteo Historical Weather API** üzerinden alınmıştır.

Projede kullanılan başlıca veri kaynakları:

- ERA5-Land
- Open-Meteo Best Match
- Günlük yağış verisi
- Referans evapotranspirasyon verisi

### Ajanın Durumunda Kullanılan Değişkenler

- 7–28 cm toprak nemi
- Günlük yağış
- Ortalama sıcaklık
- Referans evapotranspirasyon (ET0)
- Mevsim bilgisi

### Veri Setinde Bulunan Diğer Değişkenler

Aşağıdaki değişkenler veri kontrolü, karşılaştırma ve grafiklerde kullanılmaktadır; ancak Q-Learning durum uzayına doğrudan verilmemektedir:

- 0–7 cm toprak nemi
- Minimum ve maksimum sıcaklık
- Toprak sıcaklığı
- Rüzgâr hızı
- Yüzey basıncı

### Veri Ayrımı

| Aşama | Kullanılan dönem |
| --- | --- |
| Hiperparametre eğitimi | 2020–2023 |
| Doğrulama | 2024 |
| Nihai eğitim | 2020–2024 |
| Bağımsız test | 2025 |

2025 yılı verileri hiperparametre seçimi, ayrıklaştırma sınırlarının hesaplanması veya model eğitimi sırasında kullanılmamıştır. Model, eğitimde görülmeyen 2025 çevresel verileri üzerinde **simülasyon ortamında** test edilmiştir.

---

## ET0 Veri Kontrolü

2020–2024 eğitim dönemine ait ET0 verisinin özeti:

| Ölçüt | Değer |
| --- | --- |
| Gün sayısı | 1827 |
| Minimum ET0 | 0.2600 mm |
| Maksimum ET0 | 7.7600 mm |
| Ortalama ET0 | 3.0719 mm |
| Medyan ET0 | 2.6900 mm |
| Sıfır olmayan gün | 1827 / 1827 |
| Eksik değer oranı | %0.00 |

---

## Sistem Yapısı

Model her gün mevcut çevresel koşulları değerlendirerek dört farklı sulama kararından birini seçmektedir.

### Kullanılan Durum Bilgileri

1. Toprak nemi
2. Yağış durumu
3. Sıcaklık seviyesi
4. ET0 seviyesi

Toprak nemi aşağıdaki sınıflara ayrılmıştır:

- Çok kuru
- Kuru
- Uygun
- Nemli
- Çok ıslak

### Sulama Aksiyonları

| Sulama kararı | Sulama miktarı |
| --- | ---: |
| Sulama yok | 0 mm |
| Düşük sulama | 3 mm |
| Orta sulama | 6 mm |
| Yüksek sulama | 9 mm |

Projede `1 mm = 1 L/m²` dönüşümü kullanılmıştır.

### Q-Tablosu Boyutu

```text
5 × 3 × 3 × 3 × 4 × 4
```

Bu boyutlar sırasıyla toprak nemi, yağış, sıcaklık, ET0, mevsim ve aksiyon sayılarını temsil etmektedir. Toplam Q değeri sayısı **2160**'tır.

---


## Çevre Geçiş Modeli

Aksiyon uygulandıktan sonra bir sonraki günün toprak nemi basitleştirilmiş kök bölgesi su dengesiyle hesaplanmaktadır:

```text
Yeni nem =
Mevcut nem + (Etkili yağış + Etkili sulama - ET0 kaybı) / Kök bölgesi derinliği - Drenaj
```

| Parametre | Değer |
| --- | ---: |
| Kök bölgesi derinliği | 280 mm |
| Yağış infiltrasyon verimi | 0.75 |
| Sulama verimi | 0.85 |
| Bitki katsayısı | 0.85 |
| Drenaj oranı | 0.35 |
| En yüksek etkili günlük yağış | 40 mm |

Bu model fiziksel tarla sisteminin sadeleştirilmiş bir temsilidir.

---

## Ödül Fonksiyonu

Ödül fonksiyonu; toprağın ulaştığı nem durumunu, kullanılan su miktarını, yağış koşullarını ve hedef neme doğru ilerlemeyi birlikte değerlendirmektedir.

### Nem Durumuna Bağlı Temel Ödüller

| Sonraki toprak nemi durumu | Ödül |
| --- | ---: |
| Uygun | +25 |
| Nemli / kabul edilebilir | +7 |
| Kuru | -12 |
| Çok kuru | -38 |
| Çok ıslak | -32 |

### Ek Ödül ve Cezalar

| Koşul | Ödül / ceza |
| --- | ---: |
| Kullanılan her 1 mm su | -0.35 |
| Yağış ≥ 5 mm iken sulama | -10 |
| Toprak zaten ıslakken sulama | -9 |
| Toprak kuru ve ET0 yüksekken sulama yapmama | -18 |
| Nem uygunken sulama yapmayarak su tasarrufu | +4 |
| Hedef nem merkezine yaklaşma | -12 ile +12 arası |

Toplam günlük ödül genel olarak şu yapıya sahiptir:

```text
Toplam ödül =
 Nem durumu ödülü - Su maliyeti + Koşula bağlı ek ödül ve cezalar + Hedefe ilerleme ödülü
```

Bu yapı sayesinde ajan yalnızca daha fazla sulama yapmayı değil, doğru zamanda ve gerekli miktarda sulama yapmayı öğrenmektedir.

---

## Q-Learning Algoritması

Q-tablosu başlangıçta sıfır değerleriyle oluşturulmaktadır. Her günlük geçişten sonra Q değeri aşağıdaki denklemle güncellenir:

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') - Q(s,a)]
```

Burada:

- `s`: mevcut durum
- `a`: seçilen sulama aksiyonu
- `r`: aksiyon sonrası elde edilen ödül
- `s'`: sonraki durum
- `α`: öğrenme oranı
- `γ`: indirim faktörü
- `max Q(s',a')`: sonraki durumdaki en yüksek beklenen değer

Yılın son günü terminal durum kabul edilir. Terminal durumda gelecekteki Q değeri kullanılmaz ve hedef değer yalnızca günlük ödüle eşit olur.

---

## Keşif ve Sömürü: ε-Greedy Politika

Eğitim sırasında aksiyonlar **ε-greedy** yöntemle seçilmektedir:

- `ε` olasılıkla rastgele bir aksiyon seçilerek keşif yapılır.
- `1-ε` olasılıkla en yüksek Q değerine sahip aksiyon seçilerek mevcut bilgi kullanılır.

Epsilon başlangıçta `1.00` değerindedir ve her episode sonunda azaltılır. En düşük epsilon değeri `0.05` olarak sınırlandırılmıştır.

Test aşamasında keşif yapılmaz. Ajan her durumda doğrudan en yüksek Q değerine sahip aksiyonu seçer:

```text
a = argmax Q(s,a)
```

---

## Episode Yapısı

Bu projede bir **episode**, eğitim yıllarından rastgele seçilen bir yılın bütün günlerinin sırayla işlenmesidir.

Her episode sırasında:

1. Eğitim yıllarından biri rastgele seçilir.
2. İlk toprak nemine küçük bir rastgele değişim eklenir.
3. Seçilen yılın günleri kronolojik olarak işlenir.
4. Ajan her gün bir sulama aksiyonu seçer.
5. Toprak nemi su dengesiyle güncellenir.
6. Ödül hesaplanır.
7. Q-tablosu güncellenir.
8. Yılın son günü terminal durum kabul edilir.
9. Episode sonunda epsilon değeri azaltılır.

Bu yapı, ajanın farklı yıllardaki çevresel koşullar üzerinde tekrar tekrar deneyim kazanmasını sağlamaktadır.

---


## Eğitim Verisinden Hesaplanan Sınırlar

Bütün ayrıklaştırma sınırları yalnızca 2020–2024 eğitim verileri kullanılarak hesaplanmıştır.

| Sınır | Değer |
| --- | --- |
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

Hiperparametre seçimi için öğrenme oranı, indirim faktörü ve epsilon azalma katsayısının farklı kombinasyonlarından oluşan dengeli **L9 deney tasarımı** kullanılmıştır.

Her deney, 2020–2023 verileri üzerinde 1200 episode boyunca eğitilmiş ve 2024 verileriyle doğrulanmıştır. Karşılaştırmaların aynı rastgelelik koşullarında yapılabilmesi için deneylerde `seed=42` kullanılmıştır.

| Deney | α | γ | Epsilon | Toplam sulama (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi (gün) | Aşırı sulama (gün) | Toplam ödül | Başarı puanı |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **01** | **0.10** | **0.90** | **0.9975** | **723** | **70.77** | **85.52** | **34** | **1** | **6153.92** | **104.595** |
| 02 | 0.10 | 0.95 | 0.9985 | 789 | 63.39 | 83.06 | 41 | 9 | 5358.06 | 96.459 |
| 03 | 0.10 | 0.99 | 0.9995 | 1071 | 55.46 | 81.97 | 16 | 47 | 3384.19 | 85.449 |
| 04 | 0.15 | 0.90 | 0.9985 | 816 | 60.66 | 83.06 | 38 | 11 | 5092.81 | 94.598 |
| 05 | 0.15 | 0.95 | 0.9995 | 843 | 64.48 | 89.34 | 13 | 19 | 5519.84 | 103.685 |
| 06 | 0.15 | 0.99 | 0.9975 | 1017 | 54.10 | 83.61 | 14 | 48 | 3474.78 | 87.702 |
| 07 | 0.25 | 0.90 | 0.9995 | 903 | 49.73 | 77.05 | 56 | 27 | 3385.10 | 79.683 |
| 08 | 0.25 | 0.95 | 0.9975 | 765 | 68.58 | 84.97 | 34 | 6 | 5956.14 | 101.953 |
| 09 | 0.25 | 0.99 | 0.9985 | 1119 | 36.34 | 63.66 | 77 | 60 | 216.02 | 51.871 |

Doğrulama sonuçlarına göre en yüksek başarı puanını elde eden **Deney 01** seçilmiştir.

### Seçilen Hiperparametreler

```text
alpha = 0.10
gamma = 0.90
epsilon_decay = 0.9975
minimum_epsilon = 0.05
```

---

## Nihai Eğitim Sonucu

Seçilen hiperparametrelerle model, 2020–2024 verilerinin tamamı üzerinde 4000 episode boyunca yeniden eğitilmiştir.

| Episode | Ortalama ödül | Ortalama su | Ortalama mutlak TD hatası | Epsilon |
| :---: | :---: | :---: | :---: | :---: |
| 500 | 3186.08 | 937.56 mm | 23.34 | 0.286 |
| 1000 | 5493.52 | 729.60 mm | 19.39 | 0.082 |
| 2000 | 5988.71 | 681.48 mm | 18.69 | 0.050 |
| 3000 | 5907.94 | 663.42 mm | 19.06 | 0.050 |
| 4000 | 6086.53 | 676.44 mm | 18.22 | 0.050 |

Eğitim ilerledikçe ortalama ödül yükselmiş, kullanılan su miktarı azalmış ve model daha kararlı bir öğrenme davranışı göstermiştir.

---

## 2025 Bağımsız Test Sonuçları

| Yöntem | Toplam su (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Su stresi görülen gün | Çok ıslak gün | Toplam ödül | Başarı puanı |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | **16** | **5843.48** | **97.849** |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 15 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | 22 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | 12 | -5382.49 | 45.031 |

Q-Learning en az suyu kullanan yöntem değildir. Buna rağmen toprağı hedef nem aralığında tutma, su stresini azaltma, toplam ödül ve birleşik başarı puanı bakımından karşılaştırılan yöntemler arasında en iyi sonucu vermiştir.

Eşik tabanlı yönteme göre Q-Learning:

- Kabul edilebilir nem oranını **27.95 yüzde puan** artırmıştır.
- İdeal nem oranını **23.83 yüzde puan** artırmıştır.
- Su stresi görülen gün sayısını **130'dan 27'ye** düşürmüştür.
- Su stresi görülen günlerde yaklaşık **%79.2 azalma** sağlamıştır.

---

## 2025 Aksiyon Dağılımı

| Aksiyon | Gün sayısı | Toplam su katkısı |
| :---: | :---: | :---: |
| Sulama yok | 220 | 0 mm |
| Düşük sulama | 40 | 120 mm |
| Orta sulama | 74 | 444 mm |
| Yüksek sulama | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Model, 2025 yılı boyunca 220 gün sulama yapmamış ve yılın yaklaşık %60'ında sulamaya ihtiyaç olmadığına karar vermiştir.

---


## Başarı Puanı

Yöntemleri tek bir ölçüt altında karşılaştırmak amacıyla birleşik başarı puanı kullanılmıştır:

```text
Başarı puanı =
Kabul edilebilir nem oranı
+ 0.5 × İdeal nem oranı
- Normalize edilmiş su cezası
- Su stresi cezası
- Çok ıslak gün cezası
- Aşırı sulama cezası
```

Su cezası, aynı yıl içinde en fazla su kullanan yönteme göre normalize edilmektedir.

> **Önemli:** Başarı puanı yüzde değildir ve 0–100 aralığıyla sınırlandırılmamıştır. Bu nedenle puan 100 değerinin üzerine çıkabilir.

---

## Grafikler

### Q-Learning Eğitim Süreci

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png"
       alt="Q-Learning eğitim süreci"
      width="750">
</p>

### 2025 Günlük Davranış

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png"
       alt="2025 Q-Learning günlük davranışı"
       width="750">
</p>

### Sulama Yöntemlerinin Karşılaştırılması

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png"
       alt="Sulama yöntemlerinin karşılaştırılması"
       width="750">
</p>

### Aksiyon Dağılımı

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png"
       alt="Q-Learning aksiyon dağılımı"
       width="750">
</p>

### 2020–2025 Çevresel Veriler

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png"
       alt="2020–2025 çevresel veriler"
       width="700">
</p>

### Yıllara Göre Nem Başarısı

<p align="center">
  <img src="Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png"
       alt="Yıllara göre nem başarısı"
       width="700">
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

### Paketlerin Kurulması

```bash
pip install -r requirements.txt
```

---

## Çalıştırma

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

Toprak nemi, yağış, sıcaklık, ET0 ve mevsim bilgilerine göre öğrenilmiş Q-tablosundan en uygun sulama miktarını seçmektedir.

### Eşik Tabanlı Sulama

Toprak nemi belirlenen sınırların altına düştüğünde sulama yapmaktadır. Yağışın yüksek olduğu günlerde sulama uygulanmamaktadır.

### Sabit Zamanlı Sulama

Her dört günde bir, yağış olmadığı durumda 6 mm sulama uygulamaktadır.

### Sulama Yok

Bütün günlerde 0 mm sulama uygulanarak karşılaştırma için alt referans oluşturulmaktadır.

---

## Sonuç

Q-Learning tabanlı sistem, 2025 bağımsız test yılında karşılaştırılan yöntemlere göre toprak nemini daha başarılı biçimde yönetmiştir.

Model en düşük su tüketimini sağlamamış olsa da kabul edilebilir nem oranını yükseltmiş, su stresi görülen günleri önemli ölçüde azaltmış ve toplam ödül ile birleşik başarı puanında en iyi sonucu elde etmiştir.

Sonuçlar, pekiştirmeli öğrenmenin değişen çevresel koşullara göre günlük ve uyarlanabilir sulama kararları üretmek için kullanılabileceğini göstermektedir.

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

- Watkins, C. J. C. H., & Dayan, P. (1992). Q-Learning.
- Sutton, R. S., & Barto, A. G. Reinforcement Learning: An Introduction.
- Allen, R. G. et al. FAO-56 Crop Evapotranspiration.
- Open-Meteo Historical Weather API.
- ERA5-Land Reanalysis Dataset.
