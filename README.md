# Q-Learning Tabanlı Akıllı Sulama Sistemi

Bu projede Bursa iline ait **2020–2025 gerçek çevresel yeniden analiz verileri** kullanılarak günlük sulama kararı veren Q-Learning tabanlı bir akıllı sulama sistemi geliştirilmiştir. Sistem; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon (ET0) ve mevsim bilgilerine göre her gün **0, 3, 6 veya 9 mm** sulama aksiyonlarından birini seçmektedir.

Temel amaç yalnızca su tüketimini azaltmak değil, toprağı uygun nem aralığında tutarken su stresi, aşırı nem ve gereksiz sulama durumlarını azaltmaktır.

> **Not:** Bu çalışma bir yazılım ve simülasyon uygulamasıdır. Fiziksel sensör, tarla deneyi veya gerçek bir sulama kontrolörü içermez. ERA5-Land toprak nemi verisi başlangıç ve karşılaştırma referansı olarak kullanılmıştır.

![Akıllı sulama sistemi dashboard animasyonu](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif)

---

## Projenin Amacı

Geleneksel sulama sistemlerinde sulama zamanı ve miktarı çoğunlukla sabit programlarla veya belirli eşiklerle belirlenmektedir. Bu yaklaşım bazı günlerde gereksiz su kullanımına, bazı günlerde ise bitkinin su stresine girmesine neden olabilmektedir.

Bu projede:

- günlük sulama kararlarının Q-Learning ile verilmesi,
- toprağın uygun nem aralığında tutulması,
- su stresi görülen gün sayısının azaltılması,
- yağış sırasında gereksiz sulamanın önlenmesi,
- farklı sulama yöntemlerinin aynı test yılı üzerinde karşılaştırılması,
- modelin daha önce görmediği 2025 yılı üzerinde bağımsız olarak sınanması

amaçlanmıştır.

---

## Sistemin Genel Çalışma Yapısı

```text
Çevresel veriler
      ↓
Durumun belirlenmesi
      ↓
Q-Learning ajanı
      ↓
0, 3, 6 veya 9 mm sulama kararı
      ↓
Toprak neminin güncellenmesi
      ↓
Ödül hesabı
      ↓
Q-tablosunun güncellenmesi
```

Her gün bir karar adımıdır. Ajan mevcut durumu gözlemlemekte, bir sulama aksiyonu seçmekte, yağış ve ET0 etkileriyle yeni toprak nemi hesaplanmakta ve seçilen karar ödül fonksiyonu ile değerlendirilmektedir.

---

## Kullanılan Veriler

Veriler **Open-Meteo Historical Weather API** üzerinden alınmıştır.

### Veri Kaynakları

- ERA5-Land
- Open-Meteo Best Match
- Günlük yağış verisi
- Referans evapotranspirasyon verisi

### Kullanılan Çevresel Değişkenler

- Ortalama, minimum ve maksimum sıcaklık
- Günlük yağış
- Referans evapotranspirasyon (ET0)
- 0–7 cm ve 7–28 cm toprak nemi
- Toprak sıcaklığı
- Rüzgâr hızı
- Yüzey basıncı
- Mevsim bilgisi

Rüzgâr ve yüzey basıncı veri setinde bulunmakla birlikte nihai Q-Learning durum uzayında doğrudan kullanılmamıştır.

### Veri Ayrımı

| Aşama | Dönem |
|---|---|
| Hiperparametre eğitimi | 2020–2023 |
| Doğrulama | 2024 |
| Nihai eğitim | 2020–2024 |
| Bağımsız test | 2025 |

Toplam veri uzunluğu **2192 gün**, nihai eğitim verisi ise **1827 gün**dür. 2025 yılı hiperparametre seçimi veya eğitim sırasında kullanılmamıştır.

### ET0 Veri Kontrolü

| Ölçüt | Değer |
|---|---:|
| Minimum ET0 | 0.2600 mm |
| Maksimum ET0 | 7.7600 mm |
| Ortalama ET0 | 3.0719 mm |
| Medyan ET0 | 2.6900 mm |
| Sıfır olmayan gün | 1827 / 1827 |
| Eksik değer oranı | %0.00 |

---

## Agent ve Environment Yapısı

### Agent

Agent, çevresel durumu değerlendirerek günlük sulama miktarını seçen karar mekanizmasıdır.

### Environment

Environment; yağış, sıcaklık, ET0, mevsim ve simüle edilen toprak neminden oluşan tarımsal çevreyi temsil etmektedir. Agent bir aksiyon seçtikten sonra ortam yeni bir toprak nemi durumuna geçmekte ve agent’a ödül veya ceza döndürmektedir.

---

## State Yapısı

Durum vektörü beş değişkenden oluşmaktadır:

```python
state = (
    soil_moisture_state,
    rain_state,
    temperature_state,
    et0_state,
    season_state
)
```

### Toprak Nemi

| Durum | Sınıf |
|---:|---|
| 0 | Çok kuru |
| 1 | Kuru |
| 2 | Uygun |
| 3 | Nemli |
| 4 | Çok ıslak |

### Yağış

| Yağış | Sınıf |
|---:|---|
| 0–0.1 mm | Yağış yok |
| 0.1–5 mm | Düşük/orta |
| 5 mm ve üzeri | Yüksek |

Sıcaklık ve ET0 düşük, orta ve yüksek olmak üzere üçer sınıfa; yıl ise kış, ilkbahar, yaz ve sonbahar olmak üzere dört mevsime ayrılmıştır.

### Nihai Eğitim Sınırları

| Sınır | Değer |
|---|---:|
| Çok kuru | 0.1739 m³/m³ |
| İdeal nem alt sınırı | 0.2688 m³/m³ |
| İdeal nem üst sınırı | 0.3796 m³/m³ |
| Çok ıslak | 0.4086 m³/m³ |
| Düşük/orta sıcaklık | 11.90 °C |
| Orta/yüksek sıcaklık | 20.75 °C |
| Düşük/orta ET0 | 1.77 mm |
| Orta/yüksek ET0 | 3.95 mm |

Bu sınırlar yalnızca eğitim verilerinden hesaplanmıştır.

---

## Action Yapısı

```python
actions = [0, 3, 6, 9]
```

| Aksiyon | Sulama miktarı |
|---|---:|
| Sulama yok | 0 mm |
| Düşük sulama | 3 mm |
| Orta sulama | 6 mm |
| Yüksek sulama | 9 mm |

`1 mm = 1 L/m²` dönüşümü kullanılmıştır.

---

## Toprak Nemi Geçiş Modeli

Toprak nemi; etkili yağış, etkili sulama, ET0 kaynaklı su kaybı ve drenaja göre güncellenmektedir.

| Parametre | Değer |
|---|---:|
| Kök bölgesi derinliği | 280 mm |
| Yağış infiltrasyon verimi | 0.75 |
| Sulama verimi | 0.85 |
| Bitki katsayısı | 0.85 |
| Drenaj oranı | 0.35 |
| Maksimum etkili günlük yağış | 40 mm |

```text
Yeni nem = Mevcut nem
         + Etkili yağış
         + Etkili sulama
         - ET0 kaybı
         - Drenaj
```

---

## Reward Mekanizması

Reward mekanizması toprağı uygun nem aralığında tutmayı ve gereksiz su kullanımını azaltmayı birlikte amaçlamaktadır.

| Durum | Ödül / ceza |
|---|---:|
| Çok kuru toprak | -38 |
| Kuru toprak | -12 |
| Uygun toprak nemi | +25 |
| Kabul edilebilir nem | +7 |
| Çok ıslak toprak | -32 |
| Her 1 mm sulama | -0.35 |
| Yüksek yağışta sulama | -10 |
| Nemli toprağa sulama | -9 |
| Kuru ve yüksek ET0 koşulunda sulama yapmama | -18 |
| Uygun nemde sulama yapmama | +4 |
| Hedef neme yaklaşma | En fazla ±12 |

---

## Q-Table Yapısı

Durum sayısı:

```text
5 × 3 × 3 × 3 × 4 = 540 durum
```

Dört aksiyonla birlikte:

```python
Q = np.zeros((5, 3, 3, 3, 4, 4))
```

Toplam **2160 durum–aksiyon değeri** öğrenilmektedir.

---

## Q-Learning Eğitimi

Q değerleri aşağıdaki eşitlikle güncellenmektedir:

$$
Q(s_t,a_t) \leftarrow Q(s_t,a_t) +
\alpha [r_t + \gamma \max_{a'}Q(s_{t+1},a') - Q(s_t,a_t)]
$$

Aksiyon seçiminde epsilon-greedy yaklaşımı kullanılmıştır. Eğitim başlangıcında epsilon `1.00`, minimum epsilon ise `0.05` olarak belirlenmiştir.

---

## Hiperparametre Araması

Öğrenme oranı, indirim faktörü ve epsilon azalma katsayısı için üç faktörlü ve üç seviyeli dengeli **L9 deney tasarımı** uygulanmıştır. Dokuz kombinasyonun her biri 2020–2023 verileriyle **1200 episode** eğitilmiş ve 2024 yılı üzerinde doğrulanmıştır.

### Dokuz Deneyin Karşılaştırılması

| Deney | α | γ | ε azalma | Su (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Stresli gün | Aşırı sulama | Ödül | Başarı |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **01** | **0.10** | **0.90** | **0.9975** | **723** | **70.77** | **85.52** | **34** | **1** | **6153.92** | **104.595** |
| 02 | 0.10 | 0.95 | 0.9985 | 789 | 63.39 | 83.06 | 41 | 9 | 5358.06 | 96.459 |
| 03 | 0.10 | 0.99 | 0.9995 | 1071 | 55.46 | 81.97 | 16 | 47 | 3384.19 | 85.449 |
| 04 | 0.15 | 0.90 | 0.9985 | 816 | 60.66 | 83.06 | 38 | 11 | 5092.81 | 94.598 |
| 05 | 0.15 | 0.95 | 0.9995 | 843 | 64.48 | 89.34 | 13 | 19 | 5519.84 | 103.685 |
| 06 | 0.15 | 0.99 | 0.9975 | 1017 | 54.10 | 83.61 | 14 | 48 | 3474.78 | 87.702 |
| 07 | 0.25 | 0.90 | 0.9995 | 903 | 49.73 | 77.05 | 56 | 27 | 3385.10 | 79.683 |
| 08 | 0.25 | 0.95 | 0.9975 | 765 | 68.58 | 84.97 | 34 | 6 | 5956.14 | 101.953 |
| 09 | 0.25 | 0.99 | 0.9985 | 1119 | 36.34 | 63.66 | 77 | 60 | 216.02 | 51.871 |

Deney 05 kabul edilebilir nem oranında en yüksek başarıyı göstermesine rağmen, Deney 01 su tüketimi, aşırı sulama sayısı, toplam ödül ve birleşik başarı puanı birlikte değerlendirildiğinde daha dengeli sonuçlar üretmiştir. Bu nedenle nihai eğitim aşamasında Deney 01'e ait hiperparametreler kullanılmıştır.

---

## Nihai Eğitim Sonuçları

Seçilen parametrelerle model 2020–2024 verilerinin tamamında 4000 episode eğitilmiştir.

| Episode | Ortalama ödül | Ortalama su | TD hatası | Epsilon |
|---:|---:|---:|---:|---:|
| 500 | 3186.08 | 937.56 mm | 23.34 | 0.286 |
| 1000 | 5493.52 | 729.60 mm | 19.39 | 0.082 |
| 2000 | 5988.71 | 681.48 mm | 18.69 | 0.050 |
| 3000 | 5907.94 | 663.42 mm | 19.06 | 0.050 |
| 4000 | 6086.53 | 676.44 mm | 18.22 | 0.050 |

![Q-Learning eğitim süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

---

## 2025 Bağımsız Test Sonuçları

| Yöntem | Su (mm) | İdeal nem (%) | Kabul edilebilir nem (%) | Stresli gün | Çok ıslak gün | Ödül | Başarı |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | 16 | **5843.48** | **97.849** |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 15 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | 22 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | 12 | -5382.49 | 45.031 |

Q-Learning en az su kullanan yöntem değildir. Buna karşın kabul edilebilir nem oranı, ideal nem oranı, stresli gün sayısı, toplam ödül ve birleşik başarı puanı bakımından en iyi sonucu vermiştir.

### Aksiyon Dağılımı

| Aksiyon | Gün sayısı | Su katkısı |
|---|---:|---:|
| Sulama yok | 220 | 0 mm |
| 3 mm | 40 | 120 mm |
| 6 mm | 74 | 444 mm |
| 9 mm | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Ajan yılın yaklaşık %60’ında sulama yapmamıştır.

---

## Grafik Çıktıları

### Q-Learning Eğitim Süreci

![Q-Learning eğitim süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

### 2025 Günlük Davranış

![2025 günlük davranış](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png)

### Sulama Yöntemlerinin Karşılaştırılması

![Sulama yöntemlerinin karşılaştırılması](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png)

### Aksiyon Dağılımı

![Q-Learning aksiyon dağılımı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png)

### 2020–2025 Çevresel Verileri

![2020–2025 çevresel veriler](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png)

### Yıllara Göre Nem Başarısı

![Yıllara göre nem başarısı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png)

---

## Kurulum ve Çalıştırma

```bash
pip install numpy pandas matplotlib requests pillow
cd "Akıllı sulama sistemi"
python Akilli_Sulama_Sistemi.py
```

İlk çalıştırmada veriler Open-Meteo API üzerinden indirilerek `veri/` klasörüne kaydedilir. Sonraki çalıştırmalarda yerel CSV dosyaları kullanılır.

---

## Sonuç

Bu projede gerçek çevresel veriler kullanılarak günlük sulama kararı veren Q-Learning tabanlı bir sistem geliştirilmiştir. Dokuz hiperparametre kombinasyonu doğrulama verisi üzerinde karşılaştırılmış, seçilen parametrelerle nihai model eğitilmiş ve görülmeyen 2025 yılı üzerinde test edilmiştir.

Q-Learning modeli 2025 yılında:

- %88.22 kabul edilebilir nem oranına ulaşmış,
- su stresi gününü 27 ile sınırlandırmış,
- 5843.48 toplam ödül elde etmiş,
- 97.849 başarı puanına ulaşmıştır.

Sonuçlar, Q-Learning yönteminin günlük çevresel koşullara uyum sağlayarak dengeli sulama kararları üretebildiğini göstermektedir.

---

## Kaynaklar

1. R. S. Sutton and A. G. Barto, *Reinforcement Learning: An Introduction*, MIT Press, 2018.  
   https://incompleteideas.net/book/the-book-2nd.html

2. C. J. C. H. Watkins and P. Dayan, “Q-learning,” *Machine Learning*, 1992.  
   https://doi.org/10.1007/BF00992698

3. R. G. Allen et al., *Crop Evapotranspiration—FAO Irrigation and Drainage Paper 56*, 1998.  
   https://www.fao.org/4/x0490e/x0490e00.htm

4. J. Muñoz-Sabater et al., “ERA5-Land,” *Earth System Science Data*, 2021.  
   https://doi.org/10.5194/essd-13-4349-2021

5. Open-Meteo Historical Weather API.  
   https://open-meteo.com/en/docs/historical-weather-api

6. S. Kansal and B. Martin, “Reinforcement Q-Learning from Scratch in Python with OpenAI Gym.”  
   https://www.learndatasci.com/tutorials/reinforcement-q-learning-scratch-python-openai-gym/

---

## Lisans

Bu proje eğitim ve akademik çalışma amacıyla hazırlanmıştır.
