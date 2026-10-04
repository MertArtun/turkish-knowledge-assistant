# Teknik tercihler ve bilinen sınırlar

## Teknik tercihler

- **.NET + FastAPI:** .NET dış API, doğrulama ve servis iletişimi için; Python belge işleme, arama ve LLM entegrasyonu için kullanıldı. İki teknoloji proje önerisiyle uyumlu; karşılığında iki servis çalıştırmak gerekiyor.
- **Markdown + SQLite:** 10 doküman Git'te okunabilir dosyalar olarak tutuluyor. SQLite yalnızca türetilen bölüm ve embedding indeksini saklıyor. Bu büyüklükte ayrı bir vektör veritabanına gerek yok; arama bellekte tam taramayla yapılıyor. Belge değişince servis yeniden başlatılarak indeks güncelleniyor.
- **Yerel E5 modeli:** `intfloat/multilingual-e5-small`, sabit model sürümüyle ONNX Runtime üzerinde CPU'da çalışıyor. Embedding için dış API gerekmiyor. İlk açılışta model indirilmesi gerekiyor. Skorlar cevaplanabilirlik için güvenilir bir eşik vermediğinden skor eşiği kapalı; ilk dört bölüm kullanılıyor.
- **Aramadan önce sürüm seçimi:** Kapsam, onay durumu ve geçerlilik tarihleri kontrol ediliyor. Aynı prosedür için iki geçerli sürüm varsa korpus reddediliyor. Eski sürüm modele gönderilmiyor; seçme ve eleme nedenleri `version_decisions` alanında gösteriliyor.
- **Yapılandırılmış LLM cevabı:** OpenRouter üzerinden `openai/gpt-6-luna`, kaynaklı iddialar ve eksik konuları JSON olarak döndürüyor. Sunucu atıfları verilen bölümlere karşı kontrol ediyor; kaynak bilgilerini ve alıntıları kendisi ekliyor. Geçersiz çıktı 502, sağlayıcı hatası 503/504 oluyor. Sağlayıcıya soru ve seçilen bölümler gönderiliyor; `store=false` sağlayıcıların kendi saklama politikalarını ortadan kaldırmıyor.

API alanları ve hata davranışları için [ayrıntılı sözleşme](project-spec.md).

## Değerlendirme notları

20 geliştirme sorusu arama ayarlarında, 18 soruluk ana set regresyon kontrolünde kullanıldı. Holdout setindeki 26 soru son değişikliklerden sonra, sistemin cevaplarına bakılmadan hazırlandı. Beklenen ve gerçek cevaplar, ham HTTP çıktıları ve otomatik kontroller [eval/results](../eval/results) altında tutulur.

| Koşu | Beklenen durumla eşleşen | Beklenen bölümlerin tamamı ilk 4'te | Rapor |
|---|---|---|---|
| Ana set 1 | 18/18 | 15/15 | [Rapor](../eval/results/20261005-000524-generative/report.md) |
| Ana set 2 | 18/18 | 15/15 | [Rapor](../eval/results/20261005-000606-generative/report.md) |
| Holdout 1 | 23/26 | 21/22; bir yanıt ölçülemedi | [Rapor](../eval/results/20261005-005747-generative-holdout/report.md) |
| Holdout 2 | 24/26 | 22/22 | [Rapor](../eval/results/20261005-005836-generative-holdout/report.md) |

Durum eşleşmesi, yanıtın bütün olgularının doğru ve eksiksiz olduğu anlamına gelmez. Ana set ayar sırasında da kullanıldı; bu sonuç bağımsız doğruluk ölçümü değildir. Eski koşular karşılaştırma için korunmuştur.

Bu dört koşudaki **88 cevap insan tarafından incelendi**. İddiaların kaynak alıntısıyla uyumu, eksik veya ek bilgi ve cevabın uygunluğu kontrol edildi. Her sorunun kararı raporda ve `human_review` alanında yer alır; önceki koşular `pending` olarak kalır.

| İnceleme | Doğru | Kabul edilebilir | Yanlış |
|---|---|---|---|
| Ana set, 36 cevap | 36 | 0 | 0 |
| Holdout 1, 26 cevap | 21 | 4 | 1 |
| Holdout 2, 26 cevap | 23 | 3 | 0 |

Holdout'taki başlıca sorunlar:

- **H05:** Destek saatlerini içeren bölüm ilk dört sonuçta bulunmadı; cevap gereksiz yere kısmi kaldı.
- **H09:** İki tarih arasındaki süre hesaplanmadığı için beklenen tam cevap yerine kısmi cevap verildi.
- **H03:** İlk koşuda tutarsız model çıktısı sunucuda reddedildi ve 502 döndü.
- **H02/H23:** Bazı yanıtlarda ikincil bilgiler atlandı. H04'te ise cevap doğru olmasına rağmen otomatik kalıp kontrolü Türkçe eki tanımadı.

İnsan incelemesi bu koşularla sınırlıdır; bütün olası sorular için doğruluk garantisi değildir.

## Bilinen sınırlar

- Kaynak atfının doğrulanması anlamsal doğrulama değildir; doğru bölüme atıf yapan yanlış bir iddia geçebilir. Cevapsız kalma kararı da model davranışına bağlıdır.
- Arama yazım hatalarında, nadir ifadelerde veya çok parçalı sorularda ilgili bölümü kaçırabilir. Getirilmeyen bilgi ile dokümanda hiç bulunmayan bilgi cevapta her zaman ayırt edilemez.
- Tarihsel sorgular için `as_of` açıkça verilmelidir. Gün farkı, son tarih ve resmî tatil hesabı yapılmaz.
- Metadata ile ilişkilendirilmemiş belgeler arasındaki anlamsal çelişkiler otomatik yakalanmaz.
- Canlı model yanıtları değişebilir; sağlayıcı erişimi ve ücretli API anahtarı gerekir. Alıntı modu anahtarsızdır ancak cevap üretmez.
- Bu örnekte kimlik doğrulama, belge bazlı yetkilendirme, canlı müşteri sistemi entegrasyonu ve yük testi bulunmaz. Kapsam filtresi yetkilendirme değildir; prompt enjeksiyonuna dayanıklılık kanıtlanmış değildir.
