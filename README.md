# AKILLI SULAMA SİSTEMİ

Bu projede, zeytin ağacı için geliştirilen **Q-Learning tabanlı akıllı sulama sistemi**, final çalışması kapsamında gerçek çevresel veriler, gelişmiş bir toprak nemi modeli, çoklu sulama aksiyonları, hiperparametre karşılaştırması ve bağımsız test süreci eklenerek geliştirilmiştir.

Vize çalışmasında çevresel koşullar simülasyonla üretilmiş ve sulama kararı yalnızca **açık / kapalı** şeklinde verilmiştir. Bu çalışmada ise Bursa’ya ait 2020–2025 yılları arasındaki gerçek çevresel yeniden analiz verileri kullanılmış ve agent’ın günlük olarak **0, 3, 6 veya 9 mm** sulama seçeneklerinden birini seçmesi sağlanmıştır.

Sistem; toprak nemi, yağış, sıcaklık, referans evapotranspirasyon ve mevsim bilgilerini değerlendirerek en uygun sulama kararını vermeyi amaçlamaktadır. Temel hedef yalnızca daha az su kullanmak değil, toprağı kabul edilebilir nem aralığında tutarken su stresi, aşırı nem ve gereksiz sulama durumlarını azaltmaktır.

> **Not:** Bu çalışma bir yazılım ve simülasyon uygulamasıdır. Fiziksel sensör, tarla deneyi veya gerçek zamanlı sulama kontrol sistemi içermemektedir. ERA5-Land toprak nemi verileri başlangıç ve karşılaştırma referansı olarak kullanılmıştır.

![Akıllı Sulama Sistemi GIF](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/animasyon_1_akilli_sulama_dashboard_2025.gif)

---

# Bu Sürümde Yapılan Geliştirmeler

Vize projesinde geliştirilen temel Q-Learning yapısı korunmuş, ancak sistem gerçek veri ve daha ayrıntılı karar mekanizmalarıyla geliştirilmiştir.

| Vize Projesi | Final Projesi |
|---|---|
| Simüle edilen çevresel veriler | Bursa’ya ait 2020–2025 gerçek çevresel verileri |
| Sulama açık / kapalı | 0, 3, 6 ve 9 mm sulama |
| Sabit hiperparametreler | 9 farklı hiperparametre deneyi |
| Tek eğitim süreci | Eğitim, doğrulama ve bağımsız test ayrımı |
| Basit çevre geçişi | Yağış, sulama, ET0 ve drenaj içeren su dengesi modeli |
| 3 toprak nemi sınıfı | 5 toprak nemi sınıfı |
| 324 durum | 540 durum |
| 648 Q değeri | 2160 Q değeri |
| Rastgele mevsimsel veri | Open-Meteo ve ERA5-Land verileri |
| Bağımsız test bulunmuyor | Daha önce görülmeyen 2025 yılı testi |
| Tek yöntem değerlendirmesi | 4 farklı sulama yöntemi karşılaştırması |
| Temel grafikler | Eğitim, günlük davranış, yöntem ve yıllık başarı grafikleri |

---

# Sistemin Genel Çalışma Yapısı

Sistem her günü bir karar adımı olarak değerlendirmektedir.

```text
Gerçek çevresel veriler
          ↓
Mevcut state belirlenir
          ↓
Q-Learning agent aksiyon seçer
          ↓
0, 3, 6 veya 9 mm sulama uygulanır
          ↓
Toprak nemi güncellenir
          ↓
Reward hesaplanır
          ↓
Q-table güncellenir
```

Eğitim sırasında agent farklı aksiyonları deneyerek hangi çevresel durumda hangi sulama miktarının daha uygun olduğunu öğrenmektedir. Test aşamasında ise keşif yapılmadan, her state için en yüksek Q değerine sahip aksiyon seçilmektedir.

---

# Kullanılan Gerçek Veriler

Bu çalışmada Bursa iline ait 1 Ocak 2020 ile 31 Aralık 2025 tarihleri arasındaki günlük çevresel veriler kullanılmıştır.

Veriler **Open-Meteo Historical Weather API** üzerinden elde edilmiştir.

Kullanılan veri kaynakları:

- ERA5-Land
- Open-Meteo Best Match
- Günlük yağış verisi
- Referans evapotranspirasyon verisi

Kullanılan temel değişkenler:

| Çevresel Parametre | Açıklama |
|---|---|
| Toprak nemi | 0–7 cm ve 7–28 cm toprak nemi |
| Hava sıcaklığı | Günlük ortalama, minimum ve maksimum sıcaklık |
| Yağış | Günlük toplam yağış miktarı |
| ET0 | Referans evapotranspirasyon |
| Toprak sıcaklığı | Yüzeye yakın toprak sıcaklığı |
| Rüzgâr | Günlük rüzgâr hızı |
| Basınç | Yüzey basıncı |
| Mevsim | Tarih bilgisinden hesaplanan mevsim |

Rüzgâr ve basınç verileri veri setinde yer almakla birlikte, nihai Q-Learning state yapısında doğrudan kullanılmamıştır.

## Veri Ayrımı

Model geliştirme sürecinde veri sızıntısını önlemek amacıyla eğitim, doğrulama ve test dönemleri birbirinden ayrılmıştır.

| Aşama | Kullanılan Dönem | Amaç |
|---|---|---|
| Hiperparametre eğitimi | 2020–2023 | 9 farklı kombinasyonun eğitilmesi |
| Doğrulama | 2024 | En uygun hiperparametrelerin seçilmesi |
| Nihai eğitim | 2020–2024 | Seçilen parametrelerle son modelin eğitilmesi |
| Bağımsız test | 2025 | Görülmeyen veri üzerindeki başarının ölçülmesi |

Toplam veri uzunluğu:

```text
2192 gün
```

Nihai eğitim verisi:

```text
1827 gün
```

2025 yılı hiperparametre seçimi veya eğitim sırasında kullanılmamıştır.

## ET0 Veri Kontrolü

2020–2024 eğitim dönemindeki ET0 verileri model eğitimi öncesinde kontrol edilmiştir.

| Ölçüt | Değer |
|---|---:|
| Minimum ET0 | 0.2600 mm |
| Maksimum ET0 | 7.7600 mm |
| Ortalama ET0 | 3.0719 mm |
| Medyan ET0 | 2.6900 mm |
| Sıfır olmayan gün | 1827 / 1827 |
| Eksik değer oranı | %0.00 |

Bu kontrol sonucunda ET0 değişkeninde eksik veya tamamen sıfır değer bulunmadığı doğrulanmıştır.

---

# Agent (Ajan) ve Environment (Ortam) Yapısı

Bu çalışmada Reinforcement Learning yapısına uygun olarak bir agent–environment modeli oluşturulmuştur.

## Agent

Agent, akıllı sulama sisteminin karar verme mekanizmasını temsil etmektedir.

Agent’ın görevi:

- mevcut çevresel state’i gözlemlemek,
- 0, 3, 6 veya 9 mm aksiyonlarından birini seçmek,
- aldığı reward değerine göre Q-table’ı güncellemek,
- zamanla daha uygun sulama politikası öğrenmektir.

## Environment

Environment, zeytin ağacının bulunduğu tarımsal alanı ve günlük çevresel koşulları temsil etmektedir.

Environment içerisinde:

- simüle edilen toprak nemi,
- günlük yağış,
- sıcaklık,
- ET0,
- mevsim bilgisi

bulunmaktadır.

Agent bir aksiyon seçtikten sonra toprak nemi yeni duruma geçmekte ve agent’a reward veya ceza değeri döndürülmektedir.

---

# State (Durum) Yapısı

Q-Learning algoritmasının doğru karar verebilmesi için çevresel koşullar ayrık state sınıflarına dönüştürülmüştür.

Kullanılan state yapısı:

```python
state = (
    soil_moisture_state,
    rain_state,
    temperature_state,
    et0_state,
    season_state
)
```

## Toprak Nemi Durumu

Toprak nemi beş sınıfa ayrılmıştır.

| Durum No | Toprak Nemi Sınıfı |
|---:|---|
| 0 | Çok kuru |
| 1 | Kuru |
| 2 | Uygun |
| 3 | Nemli |
| 4 | Çok ıslak |

## Yağış Durumu

| Yağış Miktarı | Durum |
|---:|---|
| 0–0.1 mm | Yağış yok |
| 0.1–5 mm | Düşük / orta yağış |
| 5 mm ve üzeri | Yüksek yağış |

## Sıcaklık Durumu

Sıcaklık üç sınıfa ayrılmıştır:

- düşük,
- orta,
- yüksek.

## ET0 Durumu

ET0 üç sınıfa ayrılmıştır:

- düşük,
- orta,
- yüksek.

## Mevsim Durumu

| Aylar | Mevsim |
|---|---|
| Aralık–Ocak–Şubat | Kış |
| Mart–Nisan–Mayıs | İlkbahar |
| Haziran–Temmuz–Ağustos | Yaz |
| Eylül–Ekim–Kasım | Sonbahar |

## Ayrıklaştırma Sınırları

Nihai modelde kullanılan eşikler yalnızca 2020–2024 eğitim verisinden hesaplanmıştır.

| Sınır | Değer |
|---|---:|
| Çok kuru sınırı | 0.1739 m³/m³ |
| İdeal nem alt sınırı | 0.2688 m³/m³ |
| İdeal nem üst sınırı | 0.3796 m³/m³ |
| Çok ıslak sınırı | 0.4086 m³/m³ |
| Düşük / orta sıcaklık | 11.90 °C |
| Orta / yüksek sıcaklık | 20.75 °C |
| Düşük / orta ET0 | 1.77 mm |
| Orta / yüksek ET0 | 3.95 mm |

Hiperparametre araması sırasında eşikler yalnızca 2020–2023 verisinden hesaplanmış, nihai eğitimde ise 2020–2024 verileri kullanılarak yeniden oluşturulmuştur.

---

# Action (Aksiyon) Yapısı

Vize projesinde yalnızca sulama açık ve sulama kapalı aksiyonları bulunmaktaydı. Final projesinde ise sulama miktarı dört seviyeye çıkarılmıştır.

```python
actions = [0, 3, 6, 9]
```

| Aksiyon No | Aksiyon | Sulama Miktarı |
|---:|---|---:|
| 0 | Sulama yok | 0 mm |
| 1 | Düşük sulama | 3 mm |
| 2 | Orta sulama | 6 mm |
| 3 | Yüksek sulama | 9 mm |

Sulama miktarlarında:

```text
1 mm = 1 L/m²
```

dönüşümü kullanılmıştır.

Bu yapı sayesinde agent yalnızca sulama yapılıp yapılmayacağına değil, ne kadar sulama yapılacağına da karar vermektedir.

---

# Environment Transition (Ortam Geçişi)

Agent tarafından seçilen her aksiyondan sonra toprak nemi yeni bir duruma geçmektedir.

Toprak nemi güncellenirken:

- etkili yağış,
- etkili sulama,
- ET0 kaynaklı su kaybı,
- drenaj

dikkate alınmaktadır.

```text
Yeni nem = Mevcut nem
         + Etkili yağış
         + Etkili sulama
         - ET0 kaybı
         - Drenaj
```

Modelde kullanılan temel parametreler:

| Parametre | Değer |
|---|---:|
| Kök bölgesi derinliği | 280 mm |
| Yağış infiltrasyon verimi | 0.75 |
| Sulama verimi | 0.85 |
| Bitki katsayısı | 0.85 |
| Drenaj oranı | 0.35 |
| Maksimum etkili günlük yağış | 40 mm |

Bu yapı sayesinde environment, vize çalışmasındaki basit geçiş modeline göre daha gerçekçi hâle getirilmiştir.

---

# Reward (Ödül) Mekanizması

Reward mekanizmasının temel amacı agent’ın doğru sulama davranışlarını öğrenmesini sağlamaktır.

Doğru kararlar pozitif reward ile desteklenirken yanlış kararlar negatif ceza ile değerlendirilmiştir.

## Toprak Nemine Göre Temel Reward Değerleri

| Sonraki Toprak Durumu | Reward / Ceza |
|---|---:|
| Çok kuru | -38 |
| Kuru | -12 |
| Uygun | +25 |
| Nemli / kabul edilebilir | +7 |
| Çok ıslak | -32 |

## Ek Reward ve Cezalar

| Durum | Reward / Ceza |
|---|---:|
| Kullanılan her 1 mm sulama | -0.35 |
| 5 mm ve üzeri yağışta sulama | -10 |
| Nemli toprağa sulama | -9 |
| Kuru toprak ve yüksek ET0 varken sulama yapmama | -18 |
| Toprak uygun aralıktayken sulama yapmama | +4 |
| Hedef nem merkezine yaklaşma | En fazla ±12 |

Bu reward yapısı sayesinde agent:

- çok kuru toprağı sulamayı,
- yağış sırasında gereksiz sulama yapmamayı,
- toprağı aşırı ıslak hâle getirmemeyi,
- yüksek ET0 koşullarında su stresini önlemeyi,
- hedef nem merkezine yaklaşmayı

öğrenmektedir.

---

# Q-Table Yapısı

Q-table her state–action kombinasyonu için öğrenilen değeri saklamaktadır.

State sayısı:

```text
5 toprak nemi
× 3 yağış
× 3 sıcaklık
× 3 ET0
× 4 mevsim
= 540 farklı state
```

Q-table:

```python
Q = np.zeros((5, 3, 3, 3, 4, 4))
```

Toplam değer sayısı:

```text
540 state × 4 action = 2160 state–action değeri
```

Q-table eğitim başlangıcında sıfır olarak oluşturulmuş ve eğitim süreci boyunca güncellenmiştir.

---

# Q-Learning Eğitimi

Q-Learning, modelden bağımsız bir Reinforcement Learning algoritmasıdır.

Q değeri aşağıdaki eşitlikle güncellenmektedir:

```text
Q(s,a) ← Q(s,a) + α [r + γ max Q(s',a') - Q(s,a)]
```

Burada:

| Sembol | Açıklama |
|---|---|
| s | Mevcut state |
| a | Seçilen action |
| r | Elde edilen reward |
| s' | Sonraki state |
| α | Öğrenme oranı |
| γ | İndirim faktörü |

## Epsilon-Greedy Yaklaşımı

Eğitimin başlangıcında:

```text
epsilon = 1.00
```

olarak belirlenmiştir.

Eğitim ilerledikçe epsilon değeri azaltılmış ve:

```text
minimum epsilon = 0.05
```

seviyesinde sınırlandırılmıştır.

Bu sayede başlangıçta keşif, ilerleyen aşamalarda ise öğrenilen en iyi aksiyonların kullanımı ön plana çıkmıştır.

---

# Hiperparametre Araması

Vize çalışmasında hiperparametreler doğrudan belirlenmişti. Final çalışmasında ise modelin daha dengeli öğrenebilmesi için sistematik bir hiperparametre karşılaştırması yapılmıştır.

Karşılaştırılan hiperparametreler:

- öğrenme oranı (α),
- indirim faktörü (γ),
- epsilon azalma katsayısı.

Üç parametrenin üç farklı seviyesi için dengeli **L9 deney tasarımı** uygulanmış ve toplam dokuz kombinasyon oluşturulmuştur.

Her kombinasyon:

```text
2020–2023 eğitim verisi
1200 episode
seed = 42
```

koşullarında eğitilmiş ve 2024 doğrulama verisi üzerinde değerlendirilmiştir.

## Dokuz Hiperparametre Deneyi

| Deney | α | γ | ε Azalma | Su (mm) | İdeal Nem (%) | Kabul Edilebilir Nem (%) | Stresli Gün | Çok Islak Gün | Aşırı Sulama | Toplam Ödül | Başarı Puanı |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **01** | **0.10** | **0.90** | **0.9975** | **723** | **70.77** | **85.52** | **34** | **19** | **1** | **6153.92** | **104.595** |
| 02 | 0.10 | 0.95 | 0.9985 | 789 | 63.39 | 83.06 | 41 | 21 | 9 | 5358.06 | 96.459 |
| 03 | 0.10 | 0.99 | 0.9995 | 1071 | 55.46 | 81.97 | 16 | 50 | 47 | 3384.19 | 85.449 |
| 04 | 0.15 | 0.90 | 0.9985 | 816 | 60.66 | 83.06 | 38 | 24 | 11 | 5092.81 | 94.598 |
| 05 | 0.15 | 0.95 | 0.9995 | 843 | 64.48 | 89.34 | 13 | 26 | 19 | 5519.84 | 103.685 |
| 06 | 0.15 | 0.99 | 0.9975 | 1017 | 54.10 | 83.61 | 14 | 46 | 48 | 3474.78 | 87.702 |
| 07 | 0.25 | 0.90 | 0.9995 | 903 | 49.73 | 77.05 | 56 | 28 | 27 | 3385.10 | 79.683 |
| 08 | 0.25 | 0.95 | 0.9975 | 765 | 68.58 | 84.97 | 34 | 21 | 6 | 5956.14 | 101.953 |
| 09 | 0.25 | 0.99 | 0.9985 | 1119 | 36.34 | 63.66 | 77 | 56 | 60 | 216.02 | 51.871 |

Tablo incelendiğinde her hiperparametre kombinasyonunun farklı bir sulama davranışı oluşturduğu görülmektedir. Bazı deneyler daha yüksek nem başarısı sağlarken daha fazla su tüketmiş, bazı deneyler ise düşük su kullanımına rağmen stresli gün sayısını artırmıştır. Bunlardan Deney 01 veya Deney 05  en uygun hiperparametrelere sahiptir.Deney 05 nem oranında en yüksek sonucu elde etmiştir. Ancak Deney 01; daha düşük su tüketimi, daha az aşırı sulama, daha yüksek toplam ödül ve en yüksek birleşik başarı puanı ile daha dengeli bir performans göstermiştir. Bu nedenle nihai modelde Deney 01’e ait hiperparametreler kullanılmıştır.

---

# Nihai Eğitim

Seçilen hiperparametrelerle model, 2020–2024 yıllarına ait 1827 günlük verinin tamamı kullanılarak 4000 episode boyunca yeniden eğitilmiştir.

| Episode | Ortalama Ödül | Ortalama Su | TD Hatası | Epsilon |
|---:|---:|---:|---:|---:|
| 500 | 3186.08 | 937.56 mm | 23.34 | 0.286 |
| 1000 | 5493.52 | 729.60 mm | 19.39 | 0.082 |
| 2000 | 5988.71 | 681.48 mm | 18.69 | 0.050 |
| 3000 | 5907.94 | 663.42 mm | 19.06 | 0.050 |
| 4000 | 6086.53 | 676.44 mm | 18.22 | 0.050 |

Eğitim ilerledikçe:

- ortalama reward artmış,
- toplam su kullanımı azalmış,
- epsilon minimum değere ulaşmış,
- TD hatası daha düşük bir aralıkta dengelenmiştir.

![Q-Learning Eğitim Grafiği](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

---

# Karşılaştırılan Sulama Yöntemleri

Nihai Q-Learning modeli, 2025 bağımsız test verisi üzerinde üç farklı yöntemle karşılaştırılmıştır.

## Q-Learning

Mevcut state için en yüksek Q değerine sahip aksiyonu seçmektedir.

## Eşik Tabanlı Sulama

- Yağış 5 mm veya üzerindeyse sulama yapmaz.
- Toprak çok kuruysa 9 mm sulama yapar.
- Toprak kuruysa 6 mm sulama yapar.
- Diğer durumlarda sulama yapmaz.

## Sabit Zamanlı Sulama

Her dört günde bir, yağış 5 mm’nin altındaysa 6 mm sulama yapar.

## Sulama Yok

Bütün günlerde 0 mm sulama uygular ve alt referans olarak kullanılır.

---

# 2025 Bağımsız Test Sonuçları

Nihai model eğitim sırasında hiç görmediği 2025 yılı verisi üzerinde herhangi bir ek öğrenme yapılmadan test edilmiştir.

| Yöntem | Toplam Su (mm) | İdeal Nem (%) | Kabul Edilebilir Nem (%) | Su Stresi Günü | Çok Islak Gün | Toplam Ödül | Başarı Puanı |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Q-Learning** | **843** | **64.93** | **88.22** | **27** | 16 | **5843.48** | **97.849** |
| Eşik tabanlı | 786 | 41.10 | 60.27 | 130 | 15 | 2242.01 | 52.446 |
| Sabit zamanlı | 456 | 24.38 | 55.07 | 142 | 22 | -4255.09 | 44.989 |
| Sulama yok | 0 | 31.51 | 43.29 | 195 | 12 | -5382.49 | 45.031 |

Q-Learning en az su kullanan yöntem değildir. Buna rağmen:

- en yüksek kabul edilebilir nem oranına,
- en yüksek ideal nem oranına,
- en düşük su stresi gün sayısına,
- en yüksek toplam reward değerine,
- en yüksek başarı puanına

ulaşmıştır.

Eşik tabanlı yönteme göre Q-Learning:

- kabul edilebilir nem oranını 27.95 yüzde puan artırmış,
- ideal nem oranını 23.83 yüzde puan artırmış,
- su stresi görülen gün sayısını 130’dan 27’ye düşürmüştür.

Bu sonuçlar yalnızca toplam su miktarının değil, sulamanın doğru zamanda ve uygun miktarda yapılmasının da önemli olduğunu göstermektedir.

## 2025 Aksiyon Dağılımı

| Aksiyon | Gün Sayısı | Toplam Su Katkısı |
|---|---:|---:|
| Sulama yok | 220 | 0 mm |
| 3 mm | 40 | 120 mm |
| 6 mm | 74 | 444 mm |
| 9 mm | 31 | 279 mm |
| **Toplam** | **365** | **843 mm** |

Agent, 2025 yılının yaklaşık %60’ında sulama yapmamıştır.

---

# Grafik Çıktıları

Sistem eğitimi ve test süreci tamamlandıktan sonra performans analizleri için çeşitli grafikler oluşturulmuştur.

## Q-Learning Eğitim Süreci

Bu grafik reward, su kullanımı, TD hatası ve epsilon değerinin 4000 episode boyunca değişimini göstermektedir.

![Q-Learning Eğitim Süreci](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_1_egitim_paneli.png)

## Q-Learning Agent’ın 2025 Günlük Davranışı

Bu grafik simüle edilen toprak nemi, gerçek veri referansı, yağış, sulama, sıcaklık ve ET0 değerlerini birlikte göstermektedir.

![2025 Günlük Davranış](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_2_q_learning_gunluk_davranis.png)

## Sulama Yöntemlerinin Karşılaştırılması

Bu grafik Q-Learning, eşik tabanlı, sabit zamanlı ve sulamasız yöntemleri su kullanımı, nem başarısı, su stresi ve başarı puanı açısından karşılaştırmaktadır.

![Yöntem Karşılaştırması](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_3_yontem_karsilastirmasi.png)

## Aksiyon Dağılımı

Bu grafik agent’ın 2025 yılı boyunca 0, 3, 6 ve 9 mm aksiyonlarını kaç gün seçtiğini göstermektedir.

![Aksiyon Dağılımı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_4_aksiyon_dagilimi.png)

## 2020–2025 Çevresel Verileri

Bu grafik sıcaklık, yağış, toprak nemi ve ET0 değişkenlerinin altı yıllık değişimini göstermektedir.

![Çevresel Veriler](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_5_tum_yillar_cevre_verileri.png)

## Yıllara Göre Nem Başarısı

Bu grafik karşılaştırılan yöntemlerin 2020–2025 yılları boyunca kabul edilebilir nem oranlarını göstermektedir.

![Yıllara Göre Nem Başarısı](Ak%C4%B1ll%C4%B1%20sulama%20sistemi/sonuclar/grafik_6_yillara_gore_nem_basarisi.png)

---

# Kullanılan Kütüphaneler

| Kütüphane | Kullanım Amacı |
|---|---|
| NumPy | Q-table ve sayısal işlemler |
| pandas | Veri işleme ve CSV çıktıları |
| Matplotlib | Grafik üretimi |
| Pillow | GIF animasyonu |
| Requests | Open-Meteo API bağlantısı |

---

# Kurulum ve Çalıştırma

Gerekli paketler:

```bash
pip install numpy pandas matplotlib requests pillow
```

Projeyi çalıştırmak için:

```bash
cd "Akıllı sulama sistemi"
python Akilli_Sulama_Sistemi.py
```

İlk çalıştırmada veriler Open-Meteo API üzerinden indirilerek `veri/` klasörüne kaydedilir. Sonraki çalıştırmalarda doğrulanan yerel CSV dosyaları kullanılır.

---

# Üretilen Dosyalar

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

# Sonuç

Bu çalışmada, vize projesinde geliştirilen Q-Learning tabanlı akıllı sulama sistemi gerçek çevresel veriler ve daha ayrıntılı bir karar mekanizması kullanılarak geliştirilmiştir.

Dokuz farklı hiperparametre kombinasyonu 2020–2023 eğitim verisiyle eğitilmiş ve 2024 doğrulama verisi üzerinde karşılaştırılmıştır. En dengeli sonucu veren Deney 01 seçildikten sonra model 2020–2024 verileriyle 4000 episode boyunca yeniden eğitilmiş ve daha önce görülmeyen 2025 yılı verisi üzerinde test edilmiştir.

Q-Learning modeli 2025 testinde:

- %88.22 kabul edilebilir nem oranı,
- %64.93 ideal nem oranı,
- 27 su stresi günü,
- 5843.48 toplam reward,
- 97.849 başarı puanı

elde etmiştir.

Sonuçlar, Q-Learning yönteminin günlük çevresel koşullara uyum sağlayarak daha dengeli sulama kararları üretebildiğini göstermektedir.

---
