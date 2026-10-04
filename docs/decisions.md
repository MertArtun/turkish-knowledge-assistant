# Teknik kararlar ve bilinen sınırlar

Önce beş ana karar (A–E), sonra ayrıntılı karar notları (K2–K29), değerlendirme bulguları ve bilinen sınırlar gelir. Her not şu sırayı izler: **Seçim · Alternatif · Neden · Bedel · Ne zaman değişir.** Davranışın kendisi ve sözleşme `docs/project-spec.md` içindedir; burada tekrar edilmez.

## Beş ana karar

### A — İki servis: .NET dış API + Python RAG servisi
- **Seçim:** İstemci yalnızca .NET Minimal API ile konuşur. .NET isteği doğrular, request ID'yi yönetir, Python'u tek typed `HttpClient` ile çağırır, süre ve iptali uygular, hataları kapalı bir tabloyla eşler. Belge, sürüm, arama, üretim ve kaynak doğrulama kurallarının hepsi Python'dadır. Ayrıntı: K6, K18–K21, K26.
- **Alternatif:** Tek FastAPI servisi (en basiti); her şeyi .NET'te yazmak.
- **Neden:** İşveren .NET ve FastAPI'yi önerdi; .NET tarafı servis entegrasyonunu (sözleşme doğrulaması, timeout, hata eşleme) ayrı ve küçük bir katman olarak gösterir. Türkçe embedding ve LLM SDK'sı için Python ekosistemi daha doğrudandır. Kurallar tek dilde kaldığı için iki dilde ayrışamaz.
- **Bedel:** İkinci süreç ve imaj, ağ sınırı, iki test ortamı, iki tarafta DTO ve ortak fixture'lar, katmanlı timeout (LLM 25 sn < .NET 45 sn) ve upstream hatalarının ayrı kodlarla eşlenmesi. On belge için teknik bir zorunluluk değildir; "mikroservis ölçeklenir" gerekçesi kullanılmadı.
- **Ne zaman değişir:** .NET katmanı doğrulama ve eşleme dışında değer üretmiyorsa ve inceleme bunu gerektirmiyorsa tek FastAPI servisine inilir.

### B — Markdown tek kaynak, SQLite türetilmiş indeks
- **Seçim:** Belgeler Git'te Markdown + YAML frontmatter'dır ve tek doğruluk kaynağıdır; sürüm kararını taşıyan metadata da oradadır. Bölüm embedding'leri bir SQLite dosyasında türetilmiş veri olarak durur; fingerprint uyuşmazsa başlangıçta yeniden üretilir. Ayrıntı: K8–K11 (belge biçimi), K16 (indeks).
- **Alternatif:** Belgeleri bir veritabanında veya içerik yönetim sisteminde tutmak; ayrı bir vektör veritabanı; her başlangıçta embedding'leri yeniden hesaplamak; pickle veya `.npy` önbelleği.
- **Neden:** Markdown insan tarafından okunur, değişiklik Git diff'inde görünür ve gözden geçirilebilir. 10 belge ve 29 bölüm için ayrı bir sunucu işletmek gereksizdir; SQLite tek dosyadır, ek süreç istemez ve hangi korpus ve modelle üretildiği fingerprint ile izlenir.
- **Bedel:** Yazar katı bölüm sözdizimini bilmelidir. Çalışırken belge güncellemesi yoktur; yeniden başlatma gerekir. Bu boyutta kalıcı indeks zorunlu da değildir (her başlangıçta yeniden hesap 0,4 sn); fingerprint ve doğrulama kodu ek bakım getirir. Belgeyi yerinde düzenlemek sürüm numarasını değiştirmez (bilinen sınırlar).
- **Ne zaman değişir:** Belgeleri teknik olmayan kişiler yazıp onaylayacaksa onay akışı olan bir içerik sistemi; korpus binlerce bölüme büyürse artımlı indeks ve yaklaşık arama.

### C — Yerel çok dilli embedding, sürüm görünümünde tam tarama
- **Seçim:** `intfloat/multilingual-e5-small` sabit bir commit'te, ONNX Runtime ile CPU'da çalışır; soru yerelde embed edilir. Arama, seçili sürümlerin bölümlerinde normalize vektörlerle tam dot product'tır; `top_k=4`, skor eşiği kapalı. Ayrıntı: K15, K17, K22.
- **Alternatif:** Sağlayıcının embedding API'si; daha büyük bir model; BM25, hibrit arama veya reranker; yaklaşık arama (ANN).
- **Neden:** Soru dış sağlayıcıya gitmez ve anahtarsız alıntı modu mümkün olur. 29 bölümde tam tarama milisaniyenin altında, deterministik ve incelenebilir. `TOP_K` hem getirilen hem modele verilen bölüm sayısıdır (varsayılan 4, en fazla 8); bağlamı küçük tutar ve her bölüm 512 token sınırındadır.
- **Bedel:** Skorlar dar bir aralıkta toplanıyor, bu yüzden eşik konamadı ve cevapsız sorularda da 4 aday döner. Değerlendirmede üç soruda (E15, E16, E18) beklenen bölüm ilk 4'te değildi. İlk çalıştırma yaklaşık 490 MB indirme ister; pooling ve normalizasyon bizim kodumuzdadır.
- **Ne zaman değişir:** Ölçülen retrieval hatası bölümleme düzeltmesiyle geliştirme sorularında kapanmazsa BM25/hibrit arama veya reranker, katkısı ölçülerek eklenir. Korpus büyürse yaklaşık arama.

### D — Deterministik sürüm seçimi, aramadan önce
- **Seçim:** Hangi belge sürümünün kullanılabileceğine sunucu, metadata'dan ve sabit kurallarla karar verir: kapsam birebir, yalnızca `approved`, `[valid_from, valid_to)`, her prosedür ve kapsam için en fazla bir geçerli sürüm; çakışma korpus hatasıdır. Arama yalnızca seçilen sürümlerde yapılır; `version_decisions` sunucudan gelir. Ayrıntı: K4, K12–K14.
- **Alternatif:** Tüm korpusta arayıp sonra filtrelemek; en yüksek sürüm numarasını veya en yeni `valid_from`'u seçmek; iki sürümü modele verip seçtirmek; `supersedes` zincirini izlemek.
- **Neden:** Eski sürümün metni modele hiç gitmez. Aynı tarih ve kapsam her zaman aynı sürümü seçer; dışlanan sürüm ve nedeni makinece okunur. Çakışma sessizce çözülmez. Sonradan filtrelemede eski bir sürüm ilk k'yı doldurup geçerli bölümü dışarı itebilir.
- **Bedel:** Tarihsel cevap için `as_of` istekte verilmelidir; serbest metinden tarih okunmaz. Metadata ile bağlanmamış belgeler arasındaki anlamsal çelişki ve belge gövdesindeki tarih ifadeleri denetlenmez. Kapsam birebir karşılaştırılır (`tr` ≠ `TR`).
- **Ne zaman değişir:** Birden çok ülke veya ürün desteklenirse kapsamlar arası kural (ör. genel → özel) açıkça tasarlanır; sürümler belge değil bölüm düzeyinde değişmeye başlarsa.

### E — Yapılandırılmış üretim ve çekimserlik
- **Seçim:** Model katı bir JSON şemasıyla yalnızca `status`, kaynaklı `claims`, `missing_topics` ve `reason_code` döndürür. Sunucu her atfı bu istekte modele verilen bölümlere karşı denetler; ihlali düzeltmez, 502 ile reddeder. Cevap metnini, kaynak bilgisini ve birebir alıntıyı sunucu kurar. Kapsam veya geçerli sürüm yoksa model hiç çağrılmadan `insufficient_evidence` döner; aksi hâlde kanıtın yeterli olup olmadığını model değerlendirir. Sağlayıcı hataları hata kodudur, "belgede yok" sayılmaz. Ayrıntı: K23–K25, K28.
- **Alternatif:** Serbest metin cevap ve sonradan kaynak eşleme; geçersiz atfı silip devam etmek; skor eşiğiyle ret; ikinci bir LLM ile denetim; sağlayıcı hatasında alıntı moduna düşmek.
- **Neden:** Atıf makinece denetlenebilir; uydurma veya bu istekte verilmemiş kaynak sessizce cevaba giremez. Eşik ölçümle desteklenmediği için ret kararını kanıtı gören model verir; durum ve atıf tutarlılığını sunucu zorlar.
- **Bedel:** Kaynak doğrulaması anlamsal değildir: doğru bölüme atıf yapan yanlış bir sayı geçer. Çekimserlik modele bağlıdır ve deterministik değildir. Retrieval doğru bölümü kaçırırsa model konuyu eksik konu olarak yazar; bu, gerçek bilgi yokluğundan ayırt edilemez.
- **Ne zaman değişir:** Eval, bir kuralın doğru cevapları sistematik olarak reddettiğini veya yanlış cevapları kaçırdığını gösterirse kural ya da prompt, ölçülerek değişir. İnsan incelemesi sayı hatalarının sık olduğunu gösterirse, claim'deki sayının atıf yapılan alıntıda geçmesi gibi dar bir kontrol ölçülerek eklenir.

## Ayrıntılı karar notları

### K2 — Tek cevap şekli, durum değişmezleri tek yerde
- **Seçim:** Dört durum için tek `AskResponse`; tüm alanlar her zaman yazılır (`null`/`[]`). Hangi durumun neyi taşıyacağı `app/contracts.py::AskResponse._status_matches_content` içinde bir kez tanımlıdır; ortak fixture'lar her iki dilde round-trip edilir.
- **Alternatif:** Duruma göre ayrı şemalar (discriminated union); ya da değişmezleri yalnızca üretim katmanında kontrol etmek.
- **Neden:** C# DTO'su ve fixture eşitliği basit kalır; sunucu kendi içinde çelişkili bir cevap (ör. `answered` + eksik konu, atıfsız kaynak) üretirse istemciye gitmeden yakalanır.
- **Bedel:** Bazı alanlar çoğu durumda boştur; istemci önce `status` okumalıdır. Model çıktısı önce `validate_answer` ile denetlenir ve ihlal 502 `invalid_generation_output` olur (K25); `AskResponse` doğrulayıcısına kadar ulaşan bir ihlal sunucu hatasıdır (500).
- **Ne zaman değişir:** İstemcide derleme zamanı güvenliği gerekirse durum başına şema.

### K3 — Teşhis ayrıntısı cevapta değil, logda
- **Seçim:** Cevapta `request_id`, `sources`, `version_decisions` ve skorsuz, sıralı `retrieved_chunk_ids` var. Skorlar, süreler, prompt hash'i, model revision'ı ve fingerprint JSON loglarına gider; çalışma sabitleri `/health/ready` → `run_metadata` ile okunur.
- **Alternatif:** Her cevaba büyük bir `diagnostics` nesnesi.
- **Neden:** Cosine skoru cevapta güven yüzdesi gibi okunur; sözleşme küçülür. Eval runner retrieval'ı dış API üzerinden ölçebilmek için yalnızca sıralı ID'lere ihtiyaç duyar.
- **Bedel:** Tek bir isteğin skorlarını görmek için loga bakmak gerekir. Runner, metadata'yı readiness'tan ayrı okuduğu için koşu sırasında yapılandırma değişirse fark edilmeyebilir (bu yüzden runner readiness'ı koşu başında ve sonunda okuyup karşılaştırır).
- **Ne zaman değişir:** İncelemede log erişimi olmadan istek bazlı teşhis gerekirse.

### K4 — `version_decisions` kapsamı
- **Seçim:** Getirilen bölümlerin prosedürleri için, ilk görünme sırasıyla birer karar; tek sürümlü prosedürde `excluded=[]`.
- **Alternatif:** Yalnızca çok sürümlü prosedürler; ya da korpustaki tüm prosedürler.
- **Neden:** Her kaynağın sürüm kontrolünden geçtiği görünür, liste top-k ile sınırlı kalır, ilgisiz prosedürler dökülmez.
- **Bedel:** Tek sürümlü prosedürler için az bilgi taşıyan girdiler.
- **Ne zaman değişir:** Liste incelemede gürültü yaratırsa yalnızca dışlama içeren kararlar gösterilir.

### K5 — Yapılandırma: düz Pydantic modeli + `load_settings(environ)`
- **Seçim:** Ortam değişkeni adları `ENV_TO_FIELD` ile alanlara eşlenir; doğrulama hatası değeri içermeyen `ConfigError`'a çevrilir (`from None`).
- **Alternatif:** `pydantic-settings`.
- **Neden:** Ek bağımlılık yok; testler ortamı sözlük olarak verir; Pydantic'in hata metni ve zincirlenmiş traceback'i ham girdiyi (anahtar dâhil) basabileceği için hata metni bilinçli olarak sadeleştirilir.
- **Bedel:** Eşleme elle tutulur (bir test `.env.example` ile kodun aynı isimleri taşıdığını denetler). Göreli yollar çalışma dizinine göre çözülür; Python komutları `src/rag_service` içinden çalışır.
- **Ne zaman değişir:** Yapılandırma iç içe yapılara veya birden çok kaynağa büyürse.

### K6 — Kapalı hata kodu kümesi
- **Seçim:** İki servis aynı `error.code` kümesini kullanır; .NET Python'un hata gövdesini hiçbir zaman aynen aktarmaz, bilinen kodu kendi güvenli mesajıyla eşler, bilinmeyeni `upstream_invalid_response` (502) sayar. Model reddi (refusal) `invalid_generation_output` (502), sağlayıcının isteği reddetmesi (kimlik, kota, erişim) `provider_unavailable` (503) olur.
- **Alternatif:** Python'un HTTP durumunu ve mesajını olduğu gibi geçirmek.
- **Neden:** İç ayrıntı (dosya yolu, exception) dışarı sızmaz; altyapı hataları "dokümanda bilgi yok" ile karışmaz.
- **Bedel:** Yeni kod eklemek iki tarafta ve fixture'da değişiklik gerektirir.
- **Ne zaman değişir:** Kod sayısı büyür ve eşleme bakım yükü olursa.

### K7 — Araç ve paket seçimleri
- `SupportAssistant.slnx`: SDK 10'da `dotnet new sln` bu biçimi üretiyor; `dotnet build/test/format` doğrudan çalıştı.
- `global.json` 10.0.102 + `rollForward: latestPatch`: aynı özellik bandındaki daha yeni yamalar kabul edilir (ileride Docker SDK imajının yama sürümü farklı olabilir), farklı bant reddedilir.
- Test projesinden `coverlet.collector` çıkarıldı (coverage hedefi yok). `Microsoft.AspNetCore.Mvc.Testing` sürümü `dotnet add package` ile çözüldü ve restore edildi. .NET 10, üst düzey ifadeli `Program` sınıfını public ürettiği için `public partial class Program` eklemeye gerek kalmadı (test bu olmadan derlendi).
- Python test istemcisi için `httpx2`: kurulu Starlette sürümü `httpx` ile `TestClient` kullanımında kullanımdan kaldırma uyarısı veriyor ve kaynak kodu önce `httpx2`'yi arıyor.
- `pydantic` doğrudan import edildiği için açık bağımlılık olarak yazıldı (FastAPI üzerinden dolaylı gelmesine güvenilmedi).

### K8 — Tek bölüm sözdizimi, gövdede bölüm dışı metin yok
- **Seçim:** Tek bölüm biçimi var: `## Başlık {#id}`. Belge başlığı frontmatter'dan gelir. Bunun dışındaki her başlık ve ilk bölümden önceki metin yükleme hatasıdır (tam kural spec §3'te).
- **Alternatif:** ID'yi başlıktan otomatik üretmek; `<a id="...">` HTML çapaları; `###` alt bölümlerle derin başlık yolu; bölüm dışı metni sessizce atlamak.
- **Neden:**
  - Otomatik ID, Türkçe transliterasyon belirsizliği getirir ("süre" `sure` mi, `suere` mi?). Başlık yeniden yazılınca da değişir; o zaman eval'daki `expected_source_ids` ve eski atıflar kırılır.
  - Tek biçimi ayrıştırmak ve testle sabitlemek kolaydır.
  - Bölüm dışı metni sessizce atlamak, aranamayan ve atıf yapılamayan bir kural bırakabilir. Bu yüzden atlanmaz, reddedilir.
- **Bedel:** Yazar giriş paragrafı veya alt başlık kullanamaz. DEMO notu gövdede olamadığı için frontmatter'a YAML yorumu olarak kondu; GitHub'ın Markdown görünümünde bu not görünmez (README ve spec kurguyu ayrıca belirtiyor).
- **Ne zaman değişir:** Belgeler alt bölüm gerektirecek kadar büyürse. O zaman `###` desteklenir ve `heading_path` derinleşir.

### K9 — Dosya seçimi: ad kalıbı, beklenmeyen `.md` reddi, symlink reddi
- **Seçim:** Yalnızca dizinin doğrudan altındaki `NN-slug.md` dosyaları okunur. Kalıba uymayan `.md` hatadır. `.md` olmayan dosyalar ve alt dizinler okunmaz. Her symlink reddedilir.
- **Alternatif:** Repo genelinde `**/*.md` taraması; ayrı bir manifest dosyası; kalıba uymayan dosyaları sessizce atlamak.
- **Neden:** README, eval cevapları veya `.env` korpusa karışamaz. Yanlış adlandırılmış bir belge de sessizce kaybolmaz. Yalnızca doğrudan çocuklar okunduğu ve symlink reddedildiği için ayrıca "çözülmüş yol dizin içinde mi" kontrolüne gerek kalmaz.
- **Bedel:** `data/knowledge/` içine konan bir `README.md` servisi başlatmaz (hata mesajı nedenini söyler). macOS'un `.DS_Store` dosyası ise `.md` olmadığı için sorun çıkarmaz.
- **Ne zaman değişir:** Korpus klasörlere bölünürse veya belge sayısı manifest gerektirecek kadar büyürse.

### K10 — Katı metadata tipleri ve ilk hatada durma
- **Seçim:** Frontmatter Pydantic `strict=True` ile doğrulanır. Tarih yalnızca YAML tarihi, `version` yalnızca tırnaklı metin olabilir. Tüm alanlar zorunludur, `null` açıkça yazılır. Yükleme ilk hatada durur.
- **Alternatif:** Esnek ayrıştırma + normalleştirme; tüm hataları toplayıp birlikte raporlamak.
- **Neden:** Esnek modda `version: 2.10` sessizce `2.1` olur; tırnaklı tarih ise metin olarak kalır. İkisi de sürüm kararını ve gösterimi bozar. `valid_to` alanının unutulması ile "açık uçlu" kararı aynı şey değildir, bu yüzden alan açıkça yazılmalıdır. İlk hatada durmak hem kodu hem testleri basit tutar; on belgelik korpusta tek tek düzeltmek yeterince ucuz.
- **Bedel:** Yazar tırnak kuralını bilmeli. Hata metni Pydantic'in İngilizce teknik mesajıdır (ör. `version: Input should be a valid string`). Birden çok hata varsa düzeltme turu uzar.
- **Ne zaman değişir:** Belgeleri teknik olmayan kişiler yazarsa, tüm hataları birlikte ve Türkçe raporlamak gerekir.

### K11 — Korpusun yazımı
- **Seçim:**
  - Zorunlu bölümler tek kuralı koşuluyla birlikte taşır. D04 `sure`/`kargo` ve D05 `bedel` metinleri, sözleşme fixture'larındaki alıntılarla birebir aynıdır; bir test bunu denetler.
  - Her belgede yalnızca o konuya özgü açıklayıcı bölümler var (`kullanim`, `sinir`, `iletisim` vb.).
  - Bir kuralın tetikleyicisi (hangi durumda, hangi kanalda uygulandığı) kuralla aynı bölümdedir; `kullanim` bölümü yalnızca belgenin konusunu söyler.
  - İade belgelerinde süre kuralı, başlangıç noktası (teslim tarihi) ve kapsamı (TR/B2B/MH-10) tek `sure` bölümündedir; `uygulama` bölümü yalnızca hangi sürümün uygulanacağını (iade talebinin açıldığı tarih) açıklar. D05'te iş günü tanımı `bedel` kuralının içindedir; `kullanim` bölümü yalnızca belgenin konusunu söyler.
  - Politika sayıları (14/30 gün, 5 iş günü, 2 çalışma saati, 09.00–18.00) yalnızca zorunlu bölümde geçer.
- **Alternatif:**
  - Brief'in 120–250 kelime hedefine ulaşmak için yeni kurallar eklemek (iade koşulları, ödeme yöntemi, mesai dışı süreç).
  - Her belgeye aynı "Kapsam: Türkiye/B2B/MH-10" bölümünü koymak.
  - Fixture alıntılarını korpusa göre değiştirmek.
- **Neden:**
  - Yeni kural, cevapsız soruların temelini bozar ve doğrulanamayan bilgi ekler.
  - On belgede tekrarlanan kapsam bölümü, "Almanya'da da 30 gün mü?" gibi sorularda top-4'ü birbirine benzeyen kapsam bölümleriyle doldurup `D04#sure`'u dışarı itebilir.
  - Sayının tek bölümde durması, beklenen kaynağı (`D04#sure`) belirsizleştirmez.
  - Fixture'lar iki dilin ortak sözleşme örneğidir ve alıntıları korpusla birebir aynı olmak zorundadır; bölümleme değişikliğinde alıntılar korpusun yeni metniyle güncellendi (bir test denetler).
- **Bedel:**
  - Belgeler bölüm başlıkları dâhil 97–138 kelimedir (ilk hâlinde 50–122). Uzunluk için yeni kural eklenmedi. D05 97 kelimeyle hâlâ 120'nin altındadır: tek kuralı olan bu belgeye ayrı bir "ödeme süresini aktarma" bölümü denendi; bu bölüm iade sorularında ilk 4'e girip başka belgelerin bölümlerini dışarı itti ve "önce iadenin kabul edilip edilmediğini öğrenin" cümlesi bir geliştirme sorusunda gereksiz `partial` doğurdu. Bu yüzden aktarma notu `bedel` bölümünün içinde kaldı.
  - Açıklayıcı bölümler ek chunk'tır ve aramada zorunlu bölümün önüne geçebilir.
  - Belge metnindeki tarih ifadeleri ("1 Temmuz 2026 ve sonrasında açılan talepler") metadata ile otomatik karşılaştırılmaz.
- **Değişiklik (2026-10-04):** İlk değerlendirmede üç soruda (E15, E16, E18) beklenen `sure` bölümü ilk 4'te değildi. D03/D04'te ayrı duran `tarihler` bölümü `sure` ile, D05'te `is-gunu` bölümü `bedel` ile birleştirildi; D05#kullanim'deki, belgenin iade süresini ve kargoyu anlatmadığını söyleyen yönlendirme cümlesi çıkarıldı. Bölüm sayısı 32'den 29'a indi. Etki önce 9 geliştirme sorusunda ölçüldü (K17), ardından değerlendirme yeniden koşuldu.
- **İkinci değişiklik (2026-10-04):** Geliştirme seti 20 soruya çıkınca (K17) iki soruda beklenen bölüm ilk 4'te değildi: "müşteri beni duymuyor" sorusunda `D02#ses-yok` 8. sırada, yeni temsilcinin kurulum sorusunda `D01#baglanti` 5. sıradaydı. İkisinde de tetikleyici (müşterinin temsilciyi duyamaması; yeni temsilci veya başka bilgisayar) yalnızca `kullanim` bölümünde yazıyordu; kural bölümüne taşındı. Aynı ilkeyle D10'da paylaşma kuralı kanalını (görüşme, destek talebi) söyler ve müşterinin kodu yazması ya da görüşmede okuması da "müşteri paylaşmak isterse" bölümünde yer alır. Belgelerin örtük bıraktığı üç şey açıkça yazıldı: hafta sonu destek saatlerinin dışındadır, cumartesi ve pazar iş günü değildir, P1 dışındaki öncelik seviyeleri tanımlı değildir. Ayrıca müşteriye aktarma notları eklendi (sayı tekrar edilmeden). D03'ün metni 1.0'ın bitişini de söyler ("1 Temmuz 2026'dan önce açılan iade talepleri", D04'ün kendi ifadesiyle); önceden bitiş yalnızca metadata'daydı ve 30 Haziran'da "yarın açılacak talep" sorulunca model açık uçlu cümleyi uyguladı. Yeni süre, ücret veya koşul yoktur; D04 değişmedi, bölüm sayısı 29. Etki önce geliştirme sorularında ölçüldü (K17), sonra değerlendirme koşuldu.
- **Ne zaman değişir:** Yeni ölçüm beklenen bölümün yine ilk k dışında kaldığını gösterirse önce aynı yöntemle (kuralı ve tetikleyicisini tek bölümde tutmak, yönlendirme metnini azaltmak) devam edilir; bu yetmezse K17'deki alternatifler ölçülerek denenir.

### K12 — Sürüm çakışması: yüklemede ret, seçimde ayrıca koruma
- **Seçim:** Onaylı sürümlerin tarih çakışması `load_corpus` içinde reddedilir; asıl kontrol budur. `select_versions` ise bir tarihte birden çok geçerli sürüm görürse seçim yapmaz, `CorpusError` verir.
- **Alternatif:** Yalnızca yükleme kontrolü; ya da çakışmada en yüksek sürümü veya en yeni `valid_from`'u seçmek.
- **Neden:**
  - `select_versions` yalnızca metadata alan açık bir fonksiyondur. Testler, bir v3 provası veya ileride başka bir çağıran onu doğrulanmamış veriyle çağırabilir.
  - Korumasız hâlde ilk belge sessizce seçilirdi; bu, "dosya sırasıyla çözme" yasağını gizlice çiğnemek olurdu.
  - En yüksek sürümü seçmek, onaylanmamış bir takvim hatasını tahminle örter.
- **Bedel:** Aynı kural iki biçimde var: yüklemede aralık kesişimi, seçimde "bu tarihte birden çok geçerli". İkisi ayrı testlerle sabit (`test_overlapping_approved_versions_are_rejected`, `test_two_valid_approved_versions_are_an_error_not_a_choice`).
- **Ne zaman değişir:** Seçim yalnızca doğrulanmış korpus tipini kabul edecek şekilde daraltılırsa koruma gereksizleşir.

### K13 — Dışlama nedeni: tek neden, kural sırasıyla
- **Seçim:** Her dışlanan sürüm tek bir neden taşır: kapsam → status → tarih sırasıyla ilk başarısız kontrol (tablo spec §4'te). Taslak ve geri çekilmiş belgeler aynı `not_approved` nedenini alır. Karar korpustaki **her** prosedür için üretilir; cevapta hangilerinin gösterileceğini K4 belirler.
- **Alternatif:** Başarısız tüm kontrolleri liste olarak vermek; `draft` ve `withdrawn` için ayrı nedenler; yalnızca getirilen prosedürler için karar hesaplamak.
- **Neden:**
  - Sözleşme tek `reason` alanı ve dört değer tanımlar; onu büyütmeye gerek görülmedi.
  - Sıra, brief §7'deki seçim adımlarıyla aynıdır, bu yüzden nedeni okuyan kişi hangi adımda elendiğini anlar.
  - Tüm prosedürler için karar hesaplamak ucuzdur (10 belge). Servisin `unsupported_scope` (tüm nedenler `scope_mismatch`) ile `no_valid_version` (kapsam tutuyor ama geçerli sürüm yok) ayrımını yapabilmesi için de gereklidir.
- **Bedel:**
  - Cevapta geri çekilmiş bir belge ile taslak ayırt edilemez.
  - Başka kapsamdaki bir taslak yalnızca `scope_mismatch` olarak görünür.
  - Bu korpusta tüm belgeler TR kapsamında olduğu için `scope_mismatch` yalnızca TR dışı isteklerde ortaya çıkar.
- **Ne zaman değişir:** İnceleyen kişinin geri çekilme ile taslağı ayırması gerekirse yeni bir neden değeri eklenir (spec, fixture ve C# birlikte güncellenir).

### K14 — Etkin tarih ve kapsam
- **Seçim:**
  - `effective_as_of`, istekte tarih yoksa enjekte edilen saatin anını (varsayılan `datetime.now(UTC)`) `ZoneInfo("Europe/Istanbul")` ile yerel tarihe çevirir.
  - Varsayılan kapsam `versioning.py` içinde sabittir.
  - Kapsam karşılaştırması birebirdir (büyük/küçük harf dâhil).
- **Alternatif:** Sabit `+03:00` ofseti; sunucunun yerel saatini kullanmak; kapsamı büyük/küçük harfe duyarsız karşılaştırmak; varsayılan kapsamı ortam değişkeni yapmak.
- **Neden:**
  - Tarih UTC'den alınsaydı, her gün 00.00–03.00 (İstanbul) arasında bir önceki gün kullanılırdı. 1 Temmuz 2026'nın ilk üç saatinde D04 yerine D03 seçilirdi. Test, 20:59/21:00 UTC gün dönümünü sabitliyor.
  - Sunucunun yerel saati konteynerde UTC'dir.
  - `ZoneInfo`, saat dilimi kuralı değişse de doğru kalır. `python:3.12-slim` imajında `Europe/Istanbul` çözüldü (`docker run` ile denendi), ek `tzdata` paketi gerekmedi.
  - Harf duyarsız karşılaştırma bir tür örtük fallback olurdu.
  - Varsayılan kapsamı yapılandırmaya taşımak bugün hiçbir gereksinime hizmet etmiyor.
- **Bedel:** İstemci `"tr"` gönderirse `TR` belgeleri seçilmez (`unsupported_scope`). Saat enjeksiyonu yalnızca fonksiyon parametresiyle yapılır; servis katmanı bu parametreyi taşımalıdır.
- **Ne zaman değişir:** Birden çok ülke/ürün desteklenirse varsayılan kapsam yapılandırmaya ya da isteğe zorunlu alana dönüşür.

### K15 — Embedding: modelin kendi ONNX dosyası + ONNX Runtime (CPU)
- **Seçim:**
  - Model `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3`'e sabit. Commit, Hugging Face API'sinden alındı.
  - Model reposundaki `onnx/model.onnx` ve `onnx/tokenizer.json` dosyaları `onnxruntime` ve `tokenizers` ile CPU'da çalışır.
  - Mean pooling ve L2 normalizasyonu `app/embeddings.py` içinde, birkaç satırlık kod.
  - Yeni bağımlılıklar: `onnxruntime`, `tokenizers`, `huggingface-hub` (indirme ve önbellek), `numpy`.
- **Alternatif:** `sentence-transformers` + PyTorch (CPU). Kod daha kısa olurdu, çünkü pooling ve normalizasyon kütüphanede hazır.
- **Neden:**
  - Linux imaj boyutu. PyPI'daki torch 2.14.1 Linux wheel'i 454 MB (aarch64) ve 555 MB (x86_64); x86_64'te ayrıca CUDA paketleri iner. CPU-only indeksteki wheel 159 / 196 MB'tır ve onu kullanmak için uv'de ayrı bir paket indeksi tanımlamak gerekir. `onnxruntime` 1.30.0 wheel'i 21–24 MB, `tokenizers` yaklaşık 3,5 MB. (Bunlar indirme boyutlarıdır; kurulu boyut daha büyüktür.)
  - Daha az dolaylı bağımlılık: transformers, scipy, scikit-learn ve Pillow gelmez.
  - ONNX dosyası modelin kendi reposunda ve aynı commit'te. Ayrı bir dönüştürme adımına veya başkasının yüklediği bir kopyaya gerek yok.
- **Doğrulama:**
  - Aynı commit'te `sentence-transformers` 6.1.0 + torch 2.14.1 ile üretilen vektörlerle karşılaştırıldı. Karşılaştırma ayrı, geçici bir ortamda yapıldı; bu paketler projeye eklenmedi.
  - 5 Türkçe sorgu ve bölüm girdisinde en büyük mutlak fark 1,5e-7, iki girdi arasındaki skor farkı en fazla 3,6e-7 çıktı.
  - Yüklenen model 384 boyutlu vektör üretiyor. Model dosyası 512 tokenlık girdiyi çalıştırıyor, 513 tokenda hata veriyor (`tests/test_embeddings_model.py`).
- **Bedel:**
  - Pooling ve normalizasyon bizim kodumuzda. Yanlış yazılırsa sessizce kötü vektör üretilebilir. Buna karşı birim testler (padding ortalamaya girmez; sıfır veya NaN vektör hatadır) ve gerçek model testleri (boyut, birim norm, basit bir sıralama kontrolü) var.
  - Başka bir model veya revision için ONNX dosyasının varlığı, boyut, token sınırı ve sıralama yeniden doğrulanmalıdır.
- **Ne zaman değişir:** ONNX dosyası olmayan bir modele geçilirse ya da pooling kodunun bakımı sorun olursa `sentence-transformers` + CPU torch kullanılır; imaj büyür. Revision değişirse `uv run pytest -m model` ve `uv run python measure_retrieval.py` yeniden çalıştırılır.

### K16 — Türetilmiş indeks: SQLite, fingerprint ve başlangıçta yeniden üretim
- **Seçim:**
  - Bölüm embedding'leri `INDEX_PATH` altındaki SQLite dosyasında little-endian float32 bayt olarak saklanır. Çalışırken bellekte tek bir NumPy matrisi olarak durur.
  - Fingerprint şunları kapsar: belge dosya adı, metadata, embedding girdisi (önek + başlık yolu + içerik), model adı ve revision, indeks biçim sürümü.
  - Kayıtlı indeks şu kontrollerden geçmezse kullanılmaz: fingerprint, bölüm listesi, vektör boyutu, NaN veya sonsuz değer, birim norm. O zaman uyarı loglanır ve indeks yeniden üretilir.
  - Yeniden üretim geçici bir dosyaya yazılır, aynı kontrollerle geri okunur ve `os.replace` ile yerine konur.
  - Yeni üretilen vektörler geçersizse servis başlamaz ve eski dosya olduğu gibi kalır.
- **Alternatif:** Her başlangıçta embedding'leri yeniden hesaplamak (kalıcı dosya yok); `.npy` veya pickle önbelleği; ayrı vektör veritabanı; bozuk indekste başlangıcı durdurmak.
- **Neden:**
  - Hangi korpus ve modelle üretildiği tek bir değerle (fingerprint) izlenebilir. Readiness ve değerlendirme koşusu bu değeri kaydedebilir.
  - Pickle keyfî kod çalıştırabilir. Float32 bayt ve boyut kontrolü yalnızca sayı okur.
  - İndeks Markdown'dan her zaman yeniden üretilebilir. Bu yüzden bozuk bir dosyada başlangıcı durdurmak yerine yeniden üretmek ve nedenini loglamak yeterli. Bozuk dosya sessizce kullanılmaz.
- **Bedel:**
  - Bu korpus için kalıcı indeks zorunlu değil. Bölümlerin embedding'i geliştirme makinesinde (Apple Silicon, CPU) 32 bölümle ölçüldüğünde 0,42 sn sürdü; her başlangıçta yeniden hesaplamak da yeterli olurdu. Buna karşılık yaklaşık 150 satır kod ve testleri var.
  - `INDEX_FORMAT_VERSION` elle artırılmalıdır. Önek veya başlık yolu biçimi değişirse fingerprint bunu kendiliğinden yakalar, çünkü girdi metni fingerprint'e dâhil. Pooling kodu değişip sürüm artırılmazsa eski vektörler kullanılmaya devam eder.
  - Metadata fingerprint'e dâhil olduğu için yalnızca `valid_to` değişse bile tüm embedding'ler yeniden hesaplanır. Bu korpus boyutunda bu önemsizdir.
- **Ne zaman değişir:** Korpus binlerce bölüme büyürse, bölüm hash'ine göre artımlı güncelleme ve yaklaşık arama (ANN) düşünülür.

### K17 — Arama: önce sürüm ve kapsam görünümü, sonra tam dot product; skor eşiği kapalı
- **Seçim:**
  - `retrieve` yalnızca `select_versions`'ın seçtiği belgelerin bölümlerini puanlar.
  - Skor, normalize vektörlerde dot product'tır (yani cosine). Sıralama skora göre azalan; eşit skorda `chunk_id` artan. `top_k=4`.
  - `MIN_RETRIEVAL_SCORE` varsayılan olarak boş, yani eşik kapalı.
- **Alternatif:** Tüm korpusta top-k alıp sonra filtrelemek; BM25, hibrit arama veya reranker; sabit bir eşik (ör. 0,80).
- **Neden:**
  - Sonradan filtrelemede süresi dolmuş bir sürüm daha yüksek skor alırsa top-k'yı doldurur ve geçerli bölümü dışarı iter. Testte `top_k=1` iken D03 en yakın bölüm olsa da D04 dönüyor; sonradan filtreleme burada boş sonuç verirdi.
  - 29 bölümde tam tarama milisaniyenin altında sürer ve incelemesi kolaydır.
- **Eşik ölçümü:**
  - 4 geliştirme sorusu kullanıldı (`eval/dev_questions.jsonl`); 18 değerlendirme sorusu bu karar için kullanılmadı.
  - Komut: `uv run python measure_retrieval.py` (`src/rag_service` içinden). Model `intfloat/multilingual-e5-small@614241f…`, `top_k=4`.

  | Soru | Tür | Beklenen bölüm (sıra, skor) | 1. sonuç (skor) | 4. sonuç (skor) |
  |---|---|---|---|---|
  | DEV01 hata görseli paylaşımı | normal | `D10#paylasim` (3, 0,8686) | `D10#musteri-istegi` (0,8817) | `D10#kullanim` (0,8660) |
  | DEV02 sıfırlama bağlantısının adresi | normal | `D09#eposta` (1, 0,9130) | `D09#eposta` (0,9130) | `D10#musteri-istegi` (0,8654) |
  | DEV03 Şubat'ta açılan iadede kargo bedeli (`as_of=2026-02-16`) | sürüm | `D03#kargo` (2, 0,8593) | `D05#kullanim` (0,8657) | `D03#tarihler` (0,8228) |
  | DEV04 şarj süresi | cevapsız | — | `D01#kullanim` (0,8610) | `D02#kullanim` (0,8395) |

  - Beklenen üç bölümün üçü de ilk 4 içinde.
  - Cevapsız sorunun en yüksek skoru (0,8610), cevaplanabilir bir sorunun beklenen bölümünün skorundan (DEV03: 0,8593) daha yüksek. İlk 4'teki tüm skorlar 0,82–0,91 arasında sıkışık.
  - DEV04'ü eleyecek bir eşik, DEV03'ün doğru bölümünü de eler. Bu nedenle eşik kapalı kalır.
- **Bölümleme ölçümü (K11 değişikliği):** Geliştirme setine eval sorularından farklı ifadelerle 5 soru eklendi (DEV05–DEV09: tarihsel süre, "iade" kelimesi geçmeyen süre sorusu, iki kaynaklı soru, para iadesi). Aynı komutla değişiklikten önce ve sonra:

  | Soru | Beklenen | Önce (sıra, skor) | Sonra (sıra, skor) | Sonra 1. sonuç |
  |---|---|---|---|---|
  | DEV01 | `D10#paylasim` | 3, 0,8686 | 3, 0,8686 | `D10#musteri-istegi` (0,8817) |
  | DEV02 | `D09#eposta` | 1, 0,9130 | 1, 0,9130 | `D09#eposta` (0,9130) |
  | DEV03 | `D03#kargo` | 2, 0,8593 | 1, 0,8593 | `D03#kargo` (0,8593) |
  | DEV04 | — | — | — | `D01#kullanim` (0,8610) |
  | DEV05 | `D03#sure` | 1, 0,8626 | 1, 0,8701 | `D03#sure` (0,8701) |
  | DEV06 | `D04#sure`, `D05#bedel` | 3, 0,8511; 1, 0,8911 | 2, 0,8834; 1, 0,8940 | `D05#bedel` (0,8940) |
  | DEV07 | `D04#sure` | 1, 0,8873 | 1, 0,8826 | `D04#sure` (0,8826) |
  | DEV08 | `D03#sure` | 1, 0,8865 | 1, 0,8907 | `D03#sure` (0,8907) |
  | DEV09 | `D05#bedel` | 1, 0,8745 | 1, 0,8741 | `D05#bedel` (0,8741) |

  - Hiçbir soruda beklenen bölümün sırası düşmedi; DEV03 ve DEV06'da yükseldi. Geliştirme setinde önce de sonra da beklenen bölümlerin tamamı ilk 4'teydi; asıl etki değerlendirme koşusunda ölçülür. Eşik kararı değişmedi: cevapsız DEV04'ün en yüksek skoru (0,8610) hâlâ cevaplanabilir soruların skor aralığında.
- **İkinci bölümleme ölçümü (K11 ikinci değişiklik):** Geliştirme seti 11 soruyla 20'ye çıktı (DEV10–DEV20: kurulum, ses sorunu, ticket yazımı, P1, destek saatleri ve saat dilimi, sıfırlama e-postası, OTP okuma, 2.0 sürümünde kargo etiketi ve iki kaynaklı bir soru); her belgenin zorunlu bölümü en az bir soruyla ölçülür. Aynı komutla değişiklikten önce ve sonra:

  | Soru | Beklenen | Önce (sıra, skor) | Sonra (sıra, skor) | Sonra 1. sonuç |
  |---|---|---|---|---|
  | DEV01 | `D10#paylasim` | 3, 0,8686 | 3, 0,8722 | `D10#musteri-istegi` (0,8786) |
  | DEV02 | `D09#eposta` | 1, 0,9130 | 1, 0,9135 | `D09#eposta` (0,9135) |
  | DEV03 | `D03#kargo` | 1, 0,8593 | 1, 0,8850 | `D03#kargo` (0,8850) |
  | DEV04 | — | — | — | `D01#kullanim` (0,8607) |
  | DEV05 | `D03#sure` | 1, 0,8701 | 1, 0,8701 | `D03#sure` (0,8701) |
  | DEV06 | `D04#sure`, `D05#bedel` | 2, 0,8834; 1, 0,8940 | 2, 0,8834; 1, 0,8950 | `D05#bedel` (0,8950) |
  | DEV07 | `D04#sure` | 1, 0,8826 | 1, 0,8826 | `D04#sure` (0,8826) |
  | DEV08 | `D03#sure` | 1, 0,8907 | 1, 0,8907 | `D03#sure` (0,8907) |
  | DEV09 | `D05#bedel` | 1, 0,8741 | 1, 0,8784 | `D05#bedel` (0,8784) |
  | DEV10 | `D01#baglanti` | 5, 0,8305 | 4, 0,8374 | `D01#tamamlama` (0,8656) |
  | DEV11 | `D02#ses-yok` | 8, 0,8086 | 1, 0,8646 | `D02#ses-yok` (0,8646) |
  | DEV12 | `D06#dogruluk` | 1, 0,8812 | 1, 0,8813 | `D06#dogruluk` (0,8813) |
  | DEV13 | `D07#p1` | 3, 0,8323 | 2, 0,8379 | `D07#kullanim` (0,8416) |
  | DEV14 | `D07#p1` | 1, 0,8870 | 1, 0,8859 | `D07#p1` (0,8859) |
  | DEV15 | `D08#saatler` | 2, 0,8485 | 2, 0,8510 | `D08#kullanim` (0,8697) |
  | DEV16 | `D08#saat-dilimi` | 2, 0,8837 | 1, 0,8911 | `D08#saat-dilimi` (0,8911) |
  | DEV17 | `D09#eposta` | 1, 0,8909 | 1, 0,8900 | `D09#eposta` (0,8900) |
  | DEV18 | `D10#musteri-istegi` | 2, 0,8647 | 2, 0,8731 | `D06#dogruluk` (0,8810) |
  | DEV19 | `D04#kargo` | 1, 0,8672 | 1, 0,8672 | `D04#kargo` (0,8672) |
  | DEV20 | `D02#ses-yok`, `D06#alanlar` | 4, 0,8607; 3, 0,8625 | 4, 0,8612; 1, 0,8827 | `D06#alanlar` (0,8827) |

  - Önce 2 soruda (DEV10, DEV11) beklenen bölüm ilk 4'ün dışındaydı; sonra 20 sorunun tamamında ilk 4'te. Hiçbir soruda beklenen bölümün sırası düşmedi; DEV11 8'den 1'e, DEV10 5'ten 4'e, DEV20'de `D06#alanlar` 3'ten 1'e çıktı.
  - Eşik kararı değişmedi: cevapsız DEV04'ün en yüksek skoru (0,8607) cevaplanabilir soruların skor aralığında.
  - Denenip bırakılanlar da aynı yöntemle ölçüldü: D05'e ayrı bir aktarma bölümü ve D07/D10 `kullanim` bölümlerine "destek temsilcisi bu belgeyi … kullanır" cümlesi. Bu bölümler başka belgelerin sorularında ilk 4'e girdi; çıkarıldı (K11).
- **Bedel:**
  - Eşik kapalı olduğu için arama cevapsız sorularda da 4 aday döndürür. Konuya yakın ama cevapsız soruların reddi, üretim aşamasındaki kanıt yeterliliği kontrolüne dayanır. Alıntı modunda bu adaylar cevap olarak değil, aday olarak sunulur.
  - Açıklayıcı bölümler (`kullanim`, `musteri-istegi`) zorunlu bölümlerle aynı ilk 4'ü paylaşıyor. DEV01'de beklenen bölüm 3. sırada. Bölümleme değişikliğinden önce DEV03'te 1. sırada, iade kargosunun kendi konusu olmadığını söyleyen `D05#kullanim` vardı; bu cümle çıkarıldıktan sonra beklenen bölüm 1. sırada.
- **Ne zaman değişir:**
  - Geliştirme veya değerlendirme ölçümü beklenen bölümün ilk k dışında kaldığını gösterirse önce bölümleme ve girdi düzeltilir (ör. açıklayıcı bölümü zorunlu bölümle birleştirmek). Ölçüm ve değişiklik kaydedilir.
  - Eşik ancak cevaplanabilir ve cevapsız soruları ayıran, ölçülmüş bir değer bulunursa açılır.

### K18 — .NET dış API: katı sözleşme, ince aktarım
- **Seçim:**
  - .NET yalnızca isteği doğrular, request ID'yi yönetir, Python'u tek typed `HttpClient` ile çağırır, süre ve iptali uygular, hataları eşler. RAG kuralları (varsayılan kapsam ve tarih, sürüm seçimi, token sınırı, kapsam alanlarının uzunluğu) .NET'te yoktur; verilmemiş alanlar Python'a `null` olarak gider.
  - Gövde, Minimal API'nin `[FromBody]` bağlamasıyla değil handler içinde okunur. Bağlamanın kendi 400/413 cevabı hata sözleşmesine çevrilemiyor.
  - Tek `JsonSerializerOptions` kullanılır: snake_case, bilinmeyen alan reddi, eksik veya `null` zorunlu alanda hata. Enum'lar için yalnızca tam adı kabul eden küçük bir converter yazıldı. Yerleşik `JsonStringEnumConverter`, `"Generative"`, `"EVIDENCEONLY"` ve `"generative, evidence_only"` değerlerini de kabul ediyordu; bu testte görüldü.
  - Python cevabı C# tiplerine okunur ve yeniden yazılır; ham gövde aktarılmaz. Hangi durumun neyi taşıdığı yalnızca Python'da (`AskResponse`) denetlenir.
- **Alternatif:** Minimal API bağlaması ve yerleşik converter; Python cevabını bayt olarak aktarmak; durum kurallarını C#'ta da denetlemek; varsayılanları .NET'te doldurmak.
- **Neden:** Sözleşme kayması (yeni alan, yeni enum değeri, eksik alan) sessizce geçmez, 400 veya 502 olur. İç hata metni dışarı sızmaz. RAG kuralları tek yerde kalır.
- **Bedel:** Python'a eklenen her alan C# tipine de eklenmeli (ortak fixture testi bunu zorlar); eklenene kadar .NET 502 döner. .NET logunda etkin kapsam ve tarih görünmez.
- **Ne zaman değişir:** Sözleşme sık değişirse veya framework, bağlama hatalarının cevabını özelleştirmeye izin verirse.

### K19 — Zaman aşımı, iptal ve hata eşleme
- **Seçim:**
  - `HttpClient.Timeout` sonsuzdur. Her çağrı, istemci bağlantısına (`RequestAborted`) bağlı bir `CancellationTokenSource` ve `CancelAfter` kullanır: `/api/ask` için `RAG_TIMEOUT_SECONDS` (45 sn), readiness için 3 sn. Otomatik retry yoktur.
  - Hata eşlemesi kapalı bir tablodur (spec §5): HTTP durumu ve Türkçe mesaj `error.code`'dan, .NET'in tablosundan gelir. Python'dan gelen `invalid_request` ayrı bir mesajla döner, çünkü .NET şemayı zaten denetlemiştir ve geriye yalnızca token sınırı ile kapsam alan uzunluğu kalır.
- **Alternatif:** `HttpClient.Timeout` veya Polly/resilience handler; Python'un HTTP durumunu ve mesajını aynen geçirmek.
- **Neden:** İki uç farklı süre ister. "Bizim süremiz doldu" (504) ile "istemci gitti" (cevap yazılmaz, iptal Python çağrısına taşınır) ayrımı açık kalır. Retry olmadığı için süre bütçesi katlanmaz: LLM için 25 sn, Python çağrısı için 45 sn.
- **Bedel:** Ayrım elle yazılmış bir `when` filtresine dayanır; logdaki "timeout" ve "iptal" sınıflandırması testle doğrulanmıyor. Python'un özgün hata mesajı istemciye ulaşmaz; teşhis Python logundan `request_id` ile yapılır. Yeni bir hata kodu spec, Python ve C#'ta birlikte eklenmelidir.
- **Ne zaman değişir:** Retry gerekirse; o zaman toplam süre bütçesi yeniden hesaplanır.

### K20 — Tek request ID, iki serviste aynı kural
- **Seçim:** Kural spec §5'tedir. .NET değeri `TraceIdentifier`'a yazar, cevap başlığını `OnStarting`'de ekler (hata yakalayıcı başlıkları temizlese de kalır). Python aynı kuralla gelen değeri aynen kullanır. .NET, Python cevabındaki `request_id`'nin gönderilenle aynı olduğunu denetler. Desen iki dilde de tam eşleşmeyle uygulanır (`\z`, `fullmatch`).
- **Alternatif:** Başlığı olduğu gibi kullanmak; ID'yi yalnızca .NET'te üretip Python'da hiç doğrulamamak; W3C `traceparent`.
- **Neden:** İki servisin loglarını birleştiren tek anahtar budur. Doğrulanmamış başlık log enjeksiyonuna yol açar. Düz `$`, sondaki satır sonunu kabul eder; bu tuzak .NET ve Python'da aynıdır.
- **Bedel:** Desen iki dilde ayrı yazılıdır. Python başlığı aynen kullanmazsa her cevap 502 olur.
- **Ne zaman değişir:** Dağıtık izleme (OpenTelemetry) eklenirse.

### K21 — Python başlangıcı: önce yükle, sonra dinle
- **Seçim:** `create_app`, ayarları, korpusu, embedding modelini ve indeksi bağlantı kabul etmeden önce yükler ve doğrular. Geçersiz korpus, indirilemeyen model veya kullanılamaz indeks süreci durdurur. Bu yüzden sözleşmede "hazır değil" durumu yoktur: readiness gövdesi yalnızca `ready` olabilir.
- **Alternatif:** Yüklemeyi arka planda yapmak ve bu sürede `/health/ready`'de `not_ready`, `/internal/ask`'te `service_not_ready` dönmek.
- **Neden:** Yarım yüklü servis hiç istek almaz; "hazır değil" durumu kodda değil süreç durumunda tutulur. Arka plan yüklemesinde, başarısız yüklemeden sonra süreci durdurmak için ayrı bir mekanizma gerekirdi.
- **Bedel:** İlk model indirmesi sürerken port kapalıdır: `/health/live` de cevap vermez, .NET 503 `upstream_unavailable` döner. "Yükleniyor" ile "durdu" dışarıdan ayırt edilemez; ayrım `docker compose logs rag` ile yapılır.
- **Ne zaman değişir:** Konteyner ortamı yükleme sürerken canlılık sinyali isterse yükleme arka plana alınır ve "hazır değil" durumu sözleşmeye geri eklenir. Compose'da bu gerekmedi (aşağıda). Bu yüzden ilk sözleşmedeki `not_ready` durumu, `checks` nesnesi ve `service_not_ready` hata kodu, hiçbir zaman üretilmedikleri için çıkarıldı.
- **Docker Compose'da (K26):** Sağlık kontrolü readiness'ı kullanır ve yükleme süresini `start_period` ile bekler. Yükleme sürerken canlılık sinyali gerekmedi, çünkü canlılığa bakıp konteyneri yeniden başlatan bir orkestratör yok.

### K22 — Alıntı modu akışı ve sorgu embedding'inin çalıştırılması
- **Seçim:**
  - Kontrol sırası spec §5'teki "İstek akışı"dır. `generative` istek her işten önce reddedilir. Seçili belge yoksa embedding ve arama yapılmaz.
  - `evidence`, sıralı top-k adaylardır. Alıntı ve metadata sunucunun yüklediği korpustan gelir. `answer=null`, `claims` ve `sources` boştur, yani adaylar cevap gibi sunulmaz.
  - Soru embedding'i `anyio.to_thread.run_sync` ile ayrı bir thread'de, `CapacityLimiter(1)` ile aynı anda tek çağrı olarak çalışır.
  - 512 tokenı aşan soru kesilmez, 400 `invalid_request` olur.
- **Alternatif:** Senkron FastAPI ucu (ortak thread havuzu, 40 thread); `asyncio.to_thread` (event loop'un başka işlerle paylaşılan varsayılan havuzu); ayrı `ThreadPoolExecutor` (açma/kapama yönetimi gerekir); görev kuyruğu. Soruyu modelin sınırına kesmek.
- **Neden:** Üretim yolu async istemci kullanacağı için uç async kalır; bloklayıcı iş tek yerde thread'e alınır. ONNX Runtime tek çağrıda zaten çekirdekleri kullanır, paralel çağrılar CPU'yu yalnızca paylaşırdı. Gerçek çalıştırmada sorgu embedding'i 4–5 ms sürdü (ilk çağrı 19 ms; Apple Silicon CPU), bu yüzden sırada beklemek ihmal edilebilir. Kesilmiş soru, sorulmamış bir sorunun adaylarını getirebilir.
- **Bedel:**
  - Eşik kapalı olduğu için cevabı belgelerde olmayan sorularda da 4 aday döner. Gerçek çalıştırmada garanti sorusu `D04#sure` dâhil 4 aday aldı. Adayları okuyan kişi bunların cevap olmadığını bilmelidir.
  - `anyio` doğrudan bağımlılık olarak yazıldı; FastAPI onu zaten getiriyordu.
- **Ne zaman değişir:** Yük ölçümü tek çağrılık sıranın darboğaz olduğunu gösterirse sınır artırılır.

### K23 — Üretim: tek adaptör, Responses API, katı şema, OpenRouter üzerinden OpenAI
- **Seçim:**
  - `app/generation.py` içinde küçük bir `Generator` arayüzü (testlerde sahte generator için) ve tek gerçek uygulama: `OpenAIGenerator`. Resmî `openai` Python SDK'sı (kilitteki 3.24.0), async istemci, `responses.parse` ile Pydantic modelinden üretilen katı JSON şeması.
  - `store=false`, `max_output_tokens=1000`, istemci zaman aşımı `LLM_TIMEOUT_SECONDS` (25 sn), `max_retries=0`.
  - Model `gpt-6-luna`. Değerlendirme yapılandırması OpenRouter üzerinden `openai/gpt-6-luna` (OpenRouter'ın kalıcı slug'ı `openai/gpt-6-luna-20260922`). Başlangıç planındaki `gpt-4.1-mini-2025-04-14`'ün yerini aldı. Bu bir reasoning modeli, bu yüzden istek `reasoning.effort=low` gönderir ve `temperature` göndermez; model bu parametreyi kabul etmiyor.
  - `OPENAI_BASE_URL` OpenRouter ise istek `provider: {only: ["openai"], allow_fallbacks: false, require_parameters: true}` taşır. Bu alan api.openai.com'a gönderilmez.
- **Alternatif:** Chat Completions; serbest metin cevap + sonradan ayrıştırma; birden çok sağlayıcı adaptörü; OpenRouter'ın modeli başka bir sağlayıcıda (Azure, Bedrock) çalıştırmasına izin vermek; SDK'nın varsayılan retry'ı (2 deneme).
- **Neden:**
  - Katı şema, çıktının biçimini sağlayıcı tarafında sınırlar; sunucu yine de her kuralı kendisi denetler (K25).
  - Model, OpenAI'ın model sayfasında Responses API ve yapılandırılmış çıktı desteğiyle listeleniyor. OpenRouter'ın public models API'si de OpenAI uç noktası için `structured_outputs`, `reasoning` ve `reasoning_effort` parametrelerini listeliyor.
  - Yönlendirme sabitlenmezse aynı model ID'si, sessizce başka bir altyapıya veya parametreyi yok sayan bir sağlayıcıya gidebilir.
  - Retry, 25 sn'lik bütçeyi ve maliyeti katlar; .NET'in 45 sn'lik üst süresi de aşılabilir.
  - Model değişikliğinin gerekçesi maliyet ve güncelliktir. OpenRouter'ın public models API'sinde (2026-10-04) 1M giriş/çıkış token için `openai/gpt-6-luna` 0,10 / 0,50 USD, `openai/gpt-4.1-mini` 0,40 / 1,60 USD. Snapshot tarihleri 2026-09-22 ve 2025-04-14 (kalıcı slug'lar `openai/gpt-6-luna-20260922`, `openai/gpt-4.1-mini-2025-04-14`).
- **Bedel:**
  - OpenRouter ek bir aracıdır ve kendi veri politikası vardır. `store=false`, OpenRouter'ın veya OpenAI'ın kendi saklama politikalarını ortadan kaldırmaz.
  - Daha yeni model bu görevde daha iyi olduğu anlamına gelmez; kaliteyi yalnızca eval gösterir. Başlangıç modeli sabit bir snapshot olduğu için seçilmişti; sağlayıcının yanıtta yalnızca takma adı bildirmesi bu güvenceyi zayıflatır (aşağıda).
  - OpenAI'ın model sayfasında tarihli bir snapshot yok (`gpt-6-luna`). OpenRouter'da `openai/gpt-6-luna` takma adı ileride başka bir snapshot'a geçebilir. Sağlayıcının bildirdiği model her üretimin log satırına yazılır.
  - Reasoning tokenları çıktı bütçesinden yer. Değerlendirmenin 18 çağrısında (düşük effort) reasoning tokenı 15 çağrıda 0, en zor üç soruda 46–105; çıktı en fazla 237 token, üretim en fazla 2,8 sn sürdü. 1000 token ve 25 sn bu sorularda geniş pay bırakıyor.
  - SDK zaman aşımı aşama başınadır (bağlantı, okuma, yazma). Toplam süreyi K28'deki üst sınır keser.
- **Ne zaman değişir:** Canlı ölçüm 1000 tokenın veya 25 sn'nin yetmediğini gösterirse değer gerekçesiyle değişir. Model değişirse ve yeni model reasoning modeli değilse `reasoning` parametresi kaldırılır.

### K24 — Modele giden veri: yalnızca JSON veri, sürümlü prompt dosyası
- **Seçim:**
  - Sistem talimatı ayrı dosyadadır: `app/prompts/answer.txt`. Sürümü `PROMPT_VERSION` (`answer-v5`); dosyanın SHA-256 değeri readiness'ta (`prompt_version`, `prompt_hash`) ve üretim loglarında görünür. Bir test her sürümün hash'ini sabitler; prompt değişince sürüm de değişmek zorundadır. Prompt'ta hiç rakam yoktur (bir test denetler), politika sayıları yalnızca korpusta durur.
  - `answer-v2` (2026-10-04): Canlı denemelerde, yalnızca Almanya'yı soran bir soruda Türkiye kuralının kapsamı söylenmeden claim olarak eklendiği ve bir cevabın eksik konu olmadan `partial` döndüğü (sunucu bunu 502 ile reddetti) görüldü. Prompt'a üç kural eklendi: soru yalnızca kapsam dışını soruyorsa claim yok, `insufficient_evidence`/`unsupported_scope`; kapsam içi kural yazılırken kapsamı claim cümlesinde söylenir; `partial` yalnızca hem claim hem eksik konu varken kullanılır ve sorulmayan kural claim olarak eklenmez. Ülke adına özel kod veya yönlendirici eklenmedi; etkisi yalnızca canlı değerlendirmede görülür.
  - `answer-v3` (2026-10-04): `answer-v2` ile aynı soruların tekrar tekrar sorulması şunları gösterdi: başlangıç noktası söylenip sürenin kendisi atlanıyordu ("5 iş günü"), süre verilip koşulu atlanıyordu ("P1"); soru "geri yollamak" deyince modelin bazen "fiziksel gönderim süresi belgede yok" diye sorulmayan bir eksik konu eklemesi `partial` doğuruyordu; soru tarihi `effective_as_of` ile aynıyken ("1 Haziran 2026" ve `2026-06-01`) farklı tarih sayılıyordu. Ayrıca bölümde olmayan hesaplanmış değerler (aritmetik, tarih hesabı) kaynaklı claim olarak yazılabiliyor, iç alan adları (`effective_scope`) ve soruda geçen bir e-posta adresi cevap metnine girebiliyordu. `answer-v3` bunları genel kural olarak yazar: sorulan kural değeri, birimi, başlangıç noktası ve koşuluyla birlikte verilir; eksik konu yalnızca sorunun açıkça sorduğu kısımdır; sorudaki tarih önce `effective_as_of` ile karşılaştırılır; hesaplanmış değer claim olmaz; kişisel bilgi ve alan adı metne yazılmaz; düzeltilmiş bir yanlış ön kabul cevaplanmış sayılır. Soru ID'sine veya belge adına özel kural yoktur. Modelin durumu claim'lerden sonra seçmesi için şemada `status` alanını sona almak da denendi; tutarsız `partial` azaldı ama gereksiz `partial` belirgin biçimde arttı, şema değişmedi.
  - `answer-v4` ve `answer-v5` (2026-10-05): `answer-v3`'ün "metinde alan adı kullanma" listesinde `sources` ve `id` de vardı; tekrarlarda model kaynak ID'lerini daha az güvenilir kopyaladı. `answer-v4` listeyi `effective_scope` ve `effective_as_of` ile sınırlar. `answer-v3`'ün tarih kuralı yalnızca geçmiş ifadeleri sayıyordu: 30 Haziran'da "yarın açılacak talep" sorulunca bugünün kuralı verildi, "geçen hafta teslim almış" ise eski bir kuralı sormak sanıldı. `answer-v5` önce tarihin kuralın tarihi mi (bölümlerin söylediği olay, ör. talebin açıldığı tarih) yoksa başka bir olayın tarihi mi (ör. teslim) olduğuna baktırır ve gelecek ifadelerini de sayar. Aynı denemede D03'ün metni de metadata ile eşitlendi (K11). Bir de "tanımı sorudaki duruma uygula" kuralı denendi; hedeflediği sorulara yardım etmedi ve belgede yazmayan ters bir çıkarım ("tüm temsilcileri durdurmayan olay P1 değildir") doğurdu, eklenmedi.
  - Kullanıcı mesajı tek bir JSON nesnesidir: etkin tarih, etkin kapsam, soru ve getirilen `TOP_K` bölüm (`id`, `heading_path`, `text`). `id` bölüm ID'si değil, bu isteğe özel bir etikettir (`S1`, `S2`, … getirilme sırasıyla); sunucu modelin atıflarını doğrulamadan sonra bölüm ID'lerine çevirir (K25). Eski sürümler zaten sürüm görünümünde elendiği için modele gitmez.
- **Alternatif:** Soruyu ve bölümleri XML benzeri etiketlerle düz metne gömmek; prompt'u kodda sabit metin olarak tutmak; tüm top-k'yı göndermek.
- **Neden:**
  - JSON string kaçışı sayesinde soru veya belge kendi alanını kapatıp talimat ya da başka bir kaynak gibi görünemez. Düz metin etiketlerinde `</soru>` yazan bir soru bunu yapabilirdi. Test, tırnak ve köşeli parantezle alanı kapatmaya çalışan bir soruyla bunu denetler.
  - Prompt dosyası incelenebilir ve sürümlenebilir; eval sonuçları hangi prompt'la alındığını kaydeder.
  - `TOP_K` (en fazla 8) ve 512 tokenlık bölüm/soru sınırı, modele giden bağlamı sınırlar. Getirilen ve modele verilen bölümler aynı küme olduğu için retrieval ölçümü modelin gördüğü kanıtı da ölçer; `TOP_K` artırmak gerekli bölümün gelmesini garanti etmez.
- **Bedel:** Talimatların veri olarak ele alınması modelin uyumuna bağlıdır. Sahte generator testleri yalnızca talimatın doğru yere gittiğini gösterir, canlı modelin enjeksiyona dayanıklı olduğunu göstermez.
- **Ne zaman değişir:** Bölümler uzarsa veya 8 bölüm yetmezse bağlam bütçesi token sayısıyla ayrıca sınırlanır.

### K25 — Model çıktısı reddedilir, düzeltilmez; cevap sunucuda kurulur
- **Seçim:**
  - `validate_answer` model çıktısındaki her ihlali toplar ve 502 `invalid_generation_output` döner: boş veya kaynaksız claim, bu istekte verilmemiş kaynak etiketi (bölüm ID'si, korpusta olsa ve getirilmiş olsa bile, kabul edilmez), boş eksik konu, durumla çelişen claim/`missing_topics`/`reason_code`.
  - Cevap metnini sunucu kurar: claim metinleri, `insufficient_evidence` için `reason_code`'un standart açıklaması ve eksik konular için standart bir cümle. Kaynak başlığı, sürüm, tarihler ve birebir alıntı korpustan eklenir.
  - Sağlayıcı hataları (bağlantı, HTTP hatası, zaman aşımı, ret, kesilmiş çıktı) ayrı kodlarla hata olur; hiçbiri "belgede bilgi yok" sayılmaz ve alıntı moduna düşülmez.
- **Alternatif:** Geçersiz ID'leri atıp kalan claim'lerle devam etmek; modelden ayrıca serbest bir cevap metni almak; ikinci bir LLM ile anlamsal kontrol (LLM-as-judge).
- **Neden:** Sessizce temizlenen bir cevap, doğrulanmamış bir modeli doğrulanmış gibi gösterir. Hata, eval'da "generation" veya "validation" kök nedeni olarak görünür. Atıfsız ikinci bir cevap alanı, doğrulamanın dışında kalan metin yayımlamak demektir.
- **Bedel:** Kaynak ID doğrulaması anlamsal doğruluk garantisi değildir: verilen bir bölüme atıf yapan yanlış bir claim (ör. "60 gün") geçer. Bu bilinçli olarak bir testle görünür tutuldu. Katı kurallar, canlı modelin küçük biçim hatalarında da 502 doğurur. Depo dışındaki tekrar denemelerinde iki tür ret görüldü: durumla çelişen alanlar (ör. eksik konu olmadan `partial`) ve verilen iki bölüm ID'sinin karışımı olan bir kaynak (`D06#dogruluk` ve D10 bölümleri verilmişken `D10#dogruluk`). İkincisi bir geliştirme sorusunda (DEV01) `answer-v3` ile 20 denemede 10 kez oldu. Modele bölüm ID'si yerine istek etiketi (`S1`…) verildikten sonra karışık kaynak hiç görülmedi (DEV01'in etiketlerle yerelde 20, API üzerinden 10 denemesinin hepsi cevaplandı); durum tutarsızlığı seyrek sürüyor (yerel bir denemede 112 çağrıda 2).
- **Ne zaman değişir:** Eval, belirli bir kuralın doğru cevapları sistematik olarak reddettiğini gösterirse kural veya prompt, ölçülerek değişir. Durum tutarsızlığından gelen ret oranı kullanıcıyı etkileyecek düzeye çıkarsa ilk aday, aynı isteği bir kez daha sormaktır (kuralı gevşetmez, süreyi ve maliyeti artırır; ilk ret logda kalır).

### K26 — Yerel çalıştırma: Compose, iki imaj, dışarıya yalnızca API
- **Seçim:**
  - `compose.yaml` iki servis tanımlar: `rag` ve `api`. Host'a yalnızca `api` açılır (`127.0.0.1:8080`). `rag` port yayımlamaz ve projenin bridge ağında kalır. Bu ağın dış bağlantısı açıktır: ilk model indirmesi ve LLM sağlayıcısı bunu kullanır.
  - `rag` imajı `python:3.12.12-slim-trixie` üzerine kurulur. Bu, testlerin koştuğu ve `.python-version`'da yazan yorumlayıcıdır. Bağımlılıklar `uv sync --locked --no-dev` ile `uv.lock`'tan kurulur. uv (`ghcr.io/astral-sh/uv:0.9.2`) yalnızca bu adım için mount edilir, imaja girmez. İmaj yalnızca CPU kullanır: PyTorch veya CUDA paketi yoktur. Süreç `app` kullanıcısıyla (UID 10001) çalışır.
  - `api` imajı iki aşamalıdır: `dotnet/sdk:10.0.102-noble` ile derlenir (`global.json`), `dotnet/aspnet:10.0.12-noble-chiseled` üzerinde çalışır. Chiseled imajda kabuk ve paket yöneticisi yoktur; süreç imajın kendi root olmayan kullanıcısıyla (UID 1654) çalışır.
  - Dört etiket `docker manifest inspect` ile doğrulandı; hiçbiri `latest` değil.
  - Belgeler `./data/knowledge:/knowledge:ro` olarak bağlanır. İndeks ve model önbelleği ayrı named volume'lerdedir: `rag-index`, `rag-models`. Mount noktaları imajda `app` kullanıcısına aittir; yeni bir volume bu sahiplikle başlar.
  - `rag`'e yalnızca listelenen değişkenler (anahtar dâhil) kabuktan veya `.env`'den aktarılır. `api` yalnızca `RAG_SERVICE_URL=http://rag:8000` ve `RAG_TIMEOUT_SECONDS` alır. Konteyner yolları rag'in Dockerfile'ında sabittir; `.env`'deki yerel göreli yollar konteynere gitmez.
  - Sağlık kontrolü yalnızca `rag`'dedir: Python'un `urllib`'i ile `/health/ready`, `start_period: 10m`, `start_interval: 5s`. `api`, `depends_on: service_healthy` ile `rag`'i bekler.
- **Alternatif:**
  - `env_file: .env`. Dosyadaki her şeyi aktarır: yerel göreli yolları ve .NET değişkenlerini de. Aynı satır `api`'ye de yazılırsa anahtar oraya da gider.
  - `rag`'i `internal: true` bir ağa almak.
  - `api` için Ubuntu tabanlı aspnet imajına curl kurup sağlık kontrolü yazmak.
  - İmajları digest ile sabitlemek.
  - Korpusu imaja kopyalamak.
- **Neden:**
  - Açık liste, hangi değişkenin hangi servise gittiğini compose dosyasında gösterir. Anahtar `api`'ye hiç ulaşmaz (çalışan konteynerde doğrulandı).
  - `internal: true` dış bağlantıyı da keser; model indirilemez ve LLM çağrılamaz. Port yayımlamamak yeterlidir.
  - Chiseled imajda kabuk olmadığı için `api`'ye Docker sağlık kontrolü yazılmadı. `api`'nin hazır olması `rag`'in hazır olmasına bağlıdır ve `rag`'in kontrolü bunu kapsar. Dışarıdan `GET /health/ready` aynı bilgiyi verir.
  - Korpus imaja gömülmez, bağlanır. Böylece repodaki Markdown tek kaynak kalır ve belge değişikliği imaj yeniden derlenmeden `restart` ile indekse yansır (gerçek çalıştırmada denendi).
- **Bedel:**
  - Etiket sabittir ama içerik değişmez değildir: resmî imajlar aynı etiketi güvenlik güncellemeleriyle yeniden yayımlayabilir. Digest sabitlemesi yapılmadı.
  - Python yama sürümü iki yerde birlikte güncellenmelidir: Dockerfile ve `.python-version`. 3.12.12, 3.12'nin en yeni yaması değildir (Docker Hub'da 3.12.15 var).
  - `docker compose config` ve `docker inspect`, `.env`'den gelen anahtarı açık metin gösterir.
  - Proje yolunda ASCII olmayan bir karakter varsa (bu repoda `ı`), Compose'un bake derlemesi gRPC başlık hatası verir; `COMPOSE_BAKE=false` gerekir (README, sorun giderme).
- **Ne zaman değişir:** İmajlar bir kayıt deposuna gönderilip başka ortamlarda çalıştırılacaksa digest sabitlemesi ve düzenli güncelleme gelir. `api` için bir orkestratör sağlık kontrolü isterse küçük bir HTTP istemcisi olan imaja geçilir.

### K27 — JSON loglar: ne yazılır, ne yazılmaz
- **Seçim:**
  - Python'da `app/logs.py::JsonFormatter`, uvicorn'a `--log-config log_config.json` ile verilir. uvicorn'un kendi satırları dâhil her kayıt tek satır JSON olur. İstek olaylarının alanları `extra={"fields": …}` ile verilir. Olaylar `ask`, `generation`, `refused` ve `invalid_request`'tir; alanları spec §5'te.
  - Bir istisna türü ve yığın konumlarıyla yazılır, mesajı yazılmaz.
  - .NET yerleşik JSON console formatter'ını kullanır (`appsettings.json`); ek kod yoktur. HttpClient fabrikasının çağrı başına dört satırı `Warning` seviyesine çekildi. `RagServiceClient`'ın satırı aynı bilgiyi request ID ile birlikte taşıyor.
  - Gelen request ID kurala uymuyorsa iki serviste de loga hiç yazılmaz; onun yerine üretilen ID yazılır. JSON kaçışı ayrıca bir değerin yeni bir log satırı sahteleyememesini sağlar.
- **Alternatif:**
  - structlog veya python-json-logger.
  - uvicorn'u Python kodundan başlatıp logging'i orada kurmak.
  - .NET'te Serilog.
  - Düz metin loglar.
- **Neden:**
  - Ek bağımlılık yoktur: formatter tek, küçük bir sınıftır ve uvicorn'un kendi seçeneğiyle bağlanır.
  - Pydantic doğrulama hataları girdiyi mesajda tekrarlar (testte gösterildi). Cevap kurulurken beklenmeyen bir hata, cevap veya belge metnini istisna mesajıyla loga taşıyabilirdi.
  - Her satırda `request_id` olduğu için iki servisin logu tek anahtarla birleşir.
- **Bedel:**
  - Beklenmeyen bir hatada istisna mesajı loga gelmez. Teşhis tür, yığın ve `request_id` ile yapılır; gerekirse hata yeniden üretilir.
  - Her satır JSON değildir. Başlangıçta süreci durduran yapılandırma veya korpus hatası düz Python traceback'i olarak çıkar; bu bilerek bırakıldı, çünkü dosya ve alan adını söyleyen mesaj o anda gereklidir. Hugging Face kütüphanesi de kendi uyarılarını ikinci kez düz metin yazar (ilk indirmede bir satır).
  - uvicorn'un erişim satırları request ID taşımaz. Sağlık kontrolü 30 saniyede bir erişim satırı üretir.
- **Ne zaman değişir:** Bir log toplama sistemi eklenirse alan adları ona uyarlanır. Tam istisna mesajı gerekirse erişimi sınırlı ayrı bir kanala yazılır.

### K28 — `LLM_TIMEOUT_SECONDS` bütün çağrının üst sınırı
- **Seçim:** `Assistant._call_model`, generator çağrısını `anyio.fail_after(LLM_TIMEOUT_SECONDS)` içine alır; süre dolarsa 504 `generation_timeout` döner. SDK'nın kendi zaman aşımı da yerinde kalır.
- **Alternatif:**
  - Yalnızca SDK'nın zaman aşımı (önceki durum).
  - İstemci bağlantısı koptuğunda Python'daki işi de iptal etmek.
- **Neden:** SDK'nın zaman aşımı bağlantı, okuma ve yazma aşaması başına işler. Yavaş akan bir cevap 25 saniyeyi aşıp .NET'in 45 saniyesine yaklaşabilirdi. O durumda hata .NET'ten `upstream_timeout` olarak görünür ve hangi katmanın geciktiği belirsizleşirdi. Artık sıra sabittir: LLM en fazla 25 sn, .NET 45 sn. Toplam sınır sahte bir generator ile test ediliyor; `.env.example`'daki iki değerin sırası da testte.
- **Bedel:** İstemci koptuğunda veya .NET'in süresi dolduğunda Python'daki istek kendi işini bitirir. Model çağrısı ve maliyeti en fazla `LLM_TIMEOUT_SECONDS` kadar sürer. Kopmayı Python'a taşımak, her isteğin yanında bağlantıyı izleyen ayrı bir görev gerektirirdi.
- **Ne zaman değişir:** Kopan isteklerin model maliyeti ölçülebilir hâle gelirse bağlantı kopmasını izleyen iptal eklenir.

### K29 — Değerlendirme: dış API üzerinden, ayrı paydalar, sınırlı otomatik kontrol
- **Seçim:**
  - Runner (`eval/run_eval.py`), .NET'in `POST /api/ask` ucunu bir istemci gibi çağırır; Python fonksiyonlarını doğrudan çağırmaz. Yalnızca Python standart kütüphanesini kullanır.
  - Her HTTP cevabı, hata ve bağlantı hatası dâhil, önce `actual.jsonl`'a yazılır; kontroller sonra hesaplanır. Hiçbir soru tekrar sorulmaz.
  - Her kontrolün kendi paydası vardır. Uygulanmayan (`n/a`) ve cevap gelmediği için ölçülemeyen (`not_evaluable`) sorular ayrı sayılır. Tek bir başarı yüzdesi verilmez.
  - Bilgi kontrolleri, claim metinlerinde aranan birkaç düzenli ifadedir (ör. "30 geçiyor, 14 geçmiyor"). Sürüm beklentisi soruda açıkça yazılır (`expected_versions`).
  - Alıntı modunda yalnızca cevabı belgelerde olan sorular için `evidence_only` beklenir. Bu mod cevaplanabilirliğe karar vermediği için cevapsız sorularda durum ölçülmez.
  - Her gerekli kalıp beklenen bölümün kendi metnine uymak, her yasak kalıp ona uymamak zorundadır; bir test bunu denetler. E05, E06 ve E08'de görülen "belgenin kendi ifadesini tanımayan kalıp" hatası böylece soru yazılırken yakalanır.
- **Alternatif:** pytest + HTTP istemcisiyle ayrı bir eval projesi; servis fonksiyonlarını doğrudan çağırmak; metin eşitliği; ikinci bir LLM ile puanlama; tek başarı yüzdesi.
- **Neden:**
  - .NET doğrulaması, request ID, hata eşleme ve timeout ölçümün içinde kalır.
  - Ek bağımlılık veya ortam gerekmez; runner Python kurulu her makinede çalışır.
  - Bir altyapı hatası retrieval veya üretim hatası gibi sayılmaz; "başarısız" ve "ölçülemedi" ayrı görünür.
  - Düzenli ifadeler ucuzdur ve neyi yakaladıkları okunabilir. Anlamsal doğruluk iddiası taşımazlar.
- **Bedel:**
  - Kalıp kontrolleri anlamsal değildir. "Beş iş günü" diye yazan doğru bir cevap `\b5 iş günü` kalıbını kaçırır; kalıp olumsuz bir cümlede geçerse yanlış alarm verir. Doğru bölüme atıf yapan yanlış bir cümle ancak kalıp tutarsa yakalanır.
  - Dış API yalnızca ilk k bölümü döndürür. İlk k'nın dışındaki sıra için servis logu veya `measure_retrieval.py` gerekir.
  - Koşu metadata'sı readiness'tan okunur. Sağlayıcı uç noktası (`OPENAI_BASE_URL`) readiness'ta olmadığı için koşu notunda ayrıca yazılır.
  - **18 soru artık bağımsız bir ölçüm değildir.** İlk koşudan sonra başarısız soruların kök nedeni arandı ve prompt ile korpus değişikliklerinin bir kısmı E05, E07, E12, E14, E15 ve E16'da görülen hatalardan çıktı. Değişiklikler önce 20 geliştirme sorusunda ve tekrar denemelerinde ölçüldü, ama son koşulardaki 18/18 yine de bu sorulara göre ayarlanmış bir sistemin regresyon sonucudur; yeni ifadelerde ne kadar doğru olduğunu söylemez.
- **Ne zaman değişir:** Soru ve kalıp sayısı bakım yükü olacak kadar büyürse insan etiketli bir değerlendirmeye geçilir. Bağımsız ölçüm için holdout seti (`eval/holdout_questions.jsonl`, 26 soru) eklendi: son değişiklikten sonra, prompt'a ve sistemin cevaplarına bakılmadan yazıldı, beklentileri iki ayrı gözden geçirmeden geçti ve ilk koşudan önce commit edildi. Sonucuna bakılarak sistem değişirse set kullanılmış sayılır ve yenisi yazılır. Runner başka bir soru dosyasını `--questions` ile alır ve koşu kimliğine dosyanın adını ekler.

## Değerlendirme bulguları

### İlk koşular

İlk koşular 2026-10-04'te, commit `50518bc` üzerinde yapıldı (gerçek çalıştırma zamanı her raporun başında); çalışma ağacında koşu girdileri commit'ten farklı değildi. Her mod bir kez koşuldu. İki koşu arasında yalnızca anahtarın varlığı değişti; corpus fingerprint, prompt, embedding revision, `top_k=4` ve kapalı eşik aynıydı. Üretken koşu OpenRouter üzerinden `openai/gpt-6-luna` ile yapıldı. Sağlayıcı yanıtlarda modeli takma adla bildirdi; OpenRouter'ın public models API'si koşudan hemen sonra kalıcı slug olarak `openai/gpt-6-luna-20260922` gösterdi. Ayrıntılar ve her sorunun beklenen/gerçek çıktısı:
- [`eval/results/20261004-200050-evidence_only/report.md`](../eval/results/20261004-200050-evidence_only/report.md)
- [`eval/results/20261004-200118-generative/report.md`](../eval/results/20261004-200118-generative/report.md)

Teslim öncesi temiz kopya denetiminde alıntı modu koşusu bir kez daha, anahtarsız ve commit `78af7e7` üzerinde çalıştırıldı (sonuçları commit edilmedi): 18 sorunun durumu, ilk 4 listesi, sürüm kararları ve aday alıntıları ilk koşuyla birebir aynıydı. Üretken koşu tekrarlanmadı.

Sayılar (üretken koşu): HTTP 18/18; beklenen durum 14/18; beklenen bölümler ilk 4'te 12/15 ve kaynak gösterildi 12/15; sürüm kararı 6/6; kaynak kimliği geçerli 18/18; gereksiz ret yok 14/15; cevapsız soruda iddia yok 2/3; yasak kalıp yok 10/10. Alıntı modu koşusunda ilk 4 listeleri üretken koşuyla birebir aynı çıktı.

Başarısız otomatik kontroller (üretken koşu; liste `checks.json`'dan):
- Beklenen durum: E12, E15, E16, E18.
- Beklenen bölüm ilk 4'te / kaynak gösterildi / gerekli kalıp: E15, E16, E18.
- Gereksiz ret: E15. Cevapsız soruda iddia: E12.

Alıntı modu koşusunda tek başarısız kontrol, aynı üç soruda beklenen bölümün ilk 4'te olmamasıdır (E15, E16, E18).

- Süre ve token: üretim 1,3–2,8 sn; giriş 1.692–1.808, çıktı 46–237 token. Reasoning tokenı 15 çağrıda 0, E15/E16/E18'de 105/83/46. OpenRouter'ın listelediği fiyatla 18 çağrı yaklaşık 0,004 USD (tahmin, fatura değil).
- Beklenen değerler değiştirilmedi ve bu koşulardan sonra bölümleme veya ayar değiştirilmedi.

Bu koşular sonraki kontrol değişikliğinden önceki runner ile yapıldı: kaynak kontrolü alıntıyı belgenin tamamında arıyor ve kaynak göstermeyen cevapları da geçti sayıyordu; alıntı modunda ret ve claim kontrolleri de sayılıyordu. Raporlar üretildikleri gibi duruyor.

### Bölümleme, prompt ve kontrol değişikliklerinden sonraki koşular

Değişiklikler: iade kuralının tek bölümde toplanması (K11, ölçüm K17), prompt `answer-v2` (K24), tek bağlam bütçesi (`TOP_K` bölümün tamamı modele gider), bölüm düzeyinde kaynak kontrolü ve E15'in sürüm 2 metni (soru setinin SHA-256'sı koşu bilgisinde). Koşular commit `545f0d0` üzerinde, temiz çalışma ağacıyla yapıldı; corpus fingerprint `01385416…`, 29 bölüm. Alıntı modu bir kez, üretken mod aynı ayarlarla iki kez koşuldu:
- [`eval/results/20261004-221837-evidence_only/report.md`](../eval/results/20261004-221837-evidence_only/report.md)
- [`eval/results/20261004-221838-generative/report.md`](../eval/results/20261004-221838-generative/report.md) (üretken #1)
- [`eval/results/20261004-221915-generative/report.md`](../eval/results/20261004-221915-generative/report.md) (üretken #2)

| Ölçüm (üretken) | İlk koşu | #1 | #2 |
|---|---|---|---|
| HTTP | 18/18 | 18/18 | 18/18 |
| Beklenen durum | 14/18 | 17/18 | 17/18 |
| Beklenen bölüm ilk 4'te | 12/15 | 15/15 | 15/15 |
| Beklenen bölüm kaynak gösterildi | 12/15 | 15/15 | 15/15 |
| Çok kaynaklı soru (E18): ilk 4 / kaynak | 0/1 / 0/1 | 1/1 / 1/1 | 1/1 / 1/1 |
| Sürüm kararı | 6/6 | 6/6 | 6/6 |
| Kaynak geçerliliği | 18/18 (eski kontrol) | 15/15 | 16/16 |
| Cevaplanabilir soruda `insufficient_evidence` dönmedi | 14/15 | 15/15 | 15/15 |
| Cevapsız soruda claim üretilmedi | 2/3 | 3/3 | 2/3 |
| Gerekli kalıp | 12/15 | 15/15 | 13/15 |
| Yasak kalıp yok | 10/10 | 10/10 | 10/10 |

Alıntı modu: HTTP 18/18, beklenen durum 15/15, beklenen bölüm ilk 4'te 15/15 (ilk koşuda 12/15), sürüm kararı 6/6, kaynak geçerliliği 18/18.

Başarısız otomatik kontroller (liste `checks.json`'dan):
- Üretken #1: beklenen durum E14 (`partial`, beklenen `answered`).
- Üretken #2: beklenen durum ve cevapsız soruda claim E12 (`partial`, beklenen `insufficient_evidence`); gerekli kalıp E05, E07.

İki üretken koşu aynı commit ve ayarlarla 18 sorunun 16'sında aynı HTTP durumunu ve iş durumunu verdi (farklı: E12, E14); gösterilen kaynaklar da eşleşince 12/18 (aynı durumla farklı kaynak: E02, E05, E06, E07). Üretim 1,2–4,0 sn; giriş 1.855–1.973, çıktı 45–276 token.

Beklenen değerler değiştirilmedi; yalnızca E15'in soru metni sürümlendi. Kök neden analizi ve insan incelemesi henüz yapılmadı; her sorunun `human_review` alanı `pending`.

### Belge uzatma, `answer-v5` ve kaynak etiketleri sonrası koşular

Değişiklikler: belgelerin uzatılması ve tetikleyicilerin kural bölümlerine taşınması (K11, ölçüm K17), prompt `answer-v3`→`answer-v5` (K24), modele bölüm ID'si yerine istek etiketi verilmesi (K25), E05/E06/E08 kalıplarının sürümlenmesi (§7, `revisions` alanı).

Ara koşular commit `3b5a89f` (`answer-v3`, etiketsiz) üzerinde yapıldı; ikisi de 18/18 çıktı ama sonraki tekrar denemeleri bir geliştirme sorusunda yarı yarıya reddedilen çıktı ve bir tarih hatası gösterdi (K24, K25). İki koşunun bir oranı ölçmediğinin örneği olarak duruyorlar:
- [`eval/results/20261004-234403-evidence_only/report.md`](../eval/results/20261004-234403-evidence_only/report.md)
- [`eval/results/20261004-234404-generative/report.md`](../eval/results/20261004-234404-generative/report.md) (üretken #3), [`eval/results/20261004-234453-generative/report.md`](../eval/results/20261004-234453-generative/report.md) (üretken #4)

Son koşular commit `c192230` üzerinde, temiz çalışma ağacıyla yapıldı; corpus fingerprint `24568519…`, 29 bölüm, prompt `answer-v5`:
- [`eval/results/20261005-000524-evidence_only/report.md`](../eval/results/20261005-000524-evidence_only/report.md)
- [`eval/results/20261005-000524-generative/report.md`](../eval/results/20261005-000524-generative/report.md) (üretken #5), [`eval/results/20261005-000606-generative/report.md`](../eval/results/20261005-000606-generative/report.md) (üretken #6)

| Ölçüm (üretken) | İlk koşu | #1, #2 (`answer-v2`) | #3, #4 (`answer-v3`) | #5, #6 (`answer-v5`) |
|---|---|---|---|---|
| Beklenen durum | 14/18 | 17/18, 17/18 | 18/18, 18/18 | 18/18, 18/18 |
| Beklenen bölüm ilk 4'te | 12/15 | 15/15, 15/15 | 15/15, 15/15 | 15/15, 15/15 |
| Beklenen bölüm kaynak gösterildi | 12/15 | 15/15, 15/15 | 15/15, 15/15 | 15/15, 15/15 |
| Cevaplanabilir soruda `insufficient_evidence` dönmedi | 14/15 | 15/15, 15/15 | 15/15, 15/15 | 15/15, 15/15 |
| Cevapsız soruda claim üretilmedi | 2/3 | 3/3, 2/3 | 3/3, 3/3 | 3/3, 3/3 |
| Gerekli kalıp | 12/15 | 15/15, 13/15 | 15/15, 15/15 | 15/15, 15/15 |
| Yasak kalıp yok | 10/10 | 10/10, 10/10 | 10/10, 10/10 | 10/10, 10/10 |

HTTP 18/18, sürüm kararı 6/6 ve kaynak geçerliliği 15/15 son iki koşuda da tam. #3–#6 sürümlenmiş kalıplarla kontrol edildi; #3 ve #4'ün cevapları eski kalıplarla kontrol edildiğinde de gerekli kalıp 15/15'tir. Son alıntı modu koşusu: HTTP 18/18, beklenen durum 15/15, beklenen bölüm ilk 4'te 15/15, sürüm kararı 6/6, kaynak geçerliliği 18/18.

Son iki üretken koşu 18 sorunun 18'inde aynı iş durumunu, 17'sinde aynı kaynak kümesini verdi (farklı: E06). Üretim 1,4–4,8 sn; giriş 2.482–2.658 token (prompt uzadı), çıktı 56–278 token, reasoning tokenı en fazla 156. OpenRouter'ın listelediği fiyatla koşu başına yaklaşık 0,006 USD (tahmin, fatura değil).

İki koşu bir başarı oranı değildir ve 18 soru ayar sırasında kullanıldığı için bağımsız bir ölçüm de değildir (K29). Son sürümle API üzerinden ayrıca yapılan tekrarlarda E05, E07, E12, E14, E16 ve E17 onar kez soruldu; 60 cevabın hepsi beklenen durumda ve otomatik kontrollerin hiçbiri başarısız değil. Aynı sorular `answer-v2` ile tekrarlandığında E14 20 denemede 9 kez `partial`, E05/E07/E08 zaman zaman eksik olgu veriyordu. Bu tekrarların ham çıktıları depoda değildir. Kök neden analizi ve insan incelemesi henüz yapılmadı; her sorunun `human_review` alanı `pending`.

## Bilinen sınırlar

- **İlk indirme.** İlk başlangıç internet ister: model yaklaşık 470 MB, tokenizer yaklaşık 17 MB olarak `MODEL_CACHE_DIR` altına iner (Docker'da `rag-models` volume'ü). Önbellek dolduktan sonra sabit commit sayesinde model için ağ isteği yapılmaz. Dolu volume'lerle `--network none` başlatılan rag konteyneri hazır oldu. `huggingface_hub` yeni bir konteynerde bir kez (sonra en fazla günde bir) Hub'dan kendi istemci bilgisi için küçük bir liste ister. Bu, kütüphanenin hatasını yuttuğu ve 3 sn ile sınırladığı bir denemedir; ağsız başlatmayı bozmadı. Sıfırdan internetsiz kurulum desteklenmez.
- **Embedding revision.** `EMBEDDING_REVISION` yalnızca tam commit hash'i kabul eder; boşsa sabitlenmiş commit kullanılır. `EMBEDDING_MODEL` revision'sız değiştirilirse aynı commit o repoda bulunmaz ve başlangıç hata verir. Başka bir revision için model testleri ve `measure_retrieval.py` yeniden çalıştırılmalıdır.
- **Soru uzunluğu.** Sorgu da 512 token sınırına tabidir. Sınırı aşan soru kesilmez, 400 `invalid_request` olur. 2.000 karakterlik sınır bunu garanti etmez: normal Türkçe metinde 2.000 karakter yaklaşık 470 token tutarken 600 emoji sınırı aşıyor (gerçek tokenizer ile ölçüldü).
- **Skorların taşınabilirliği.** Skorlar farklı CPU mimarilerinde son basamaklarda (yaklaşık 1e-6) farklı çıkabilir. Eşit skorda `chunk_id` sıralaması yalnızca birebir eşit skorlar için devreye girer.
- **Küçük ölçüm.** Eşik ve bölümleme kararları 20 geliştirme sorusuna dayanır. 18 soruluk değerlendirme de aynı kurgu korpus için yazılmış küçük bir Türkçe regresyon setidir; genellenebilir bir doğruluk oranı vermez.
- **Retrieval bu küçük sette tam, genelde garanti değil.** İlk koşuda 15 cevaplanabilir sorunun 3'ünde (E15, E16, E18) beklenen `sure` bölümü ilk 4'te yoktu; bölümleme değişikliklerinden sonra değerlendirmede 15/15, geliştirme setinde 20/20 (K11, K17). Denemelerde beklenen bölümün ilk 4'ün dışında kaldığı ifade türleri: modelin tanımadığı eş anlamlılar ("nakliye masrafı" için `D03#kargo` 17. sırada; "kargo ücreti" ile 1.), yazım hatalı veya Türkçe karaktersiz yazılmış sorular, beş ayrı soruyu tek mesajda soran istekler (4 bölüm hepsine yetmez) ve uzun bir anlatımın sonuna eklenmiş soru. Bu durumlarda model getirilmeyen konuyu eksik konu olarak yazar.
- **Canlı üretim deterministik değil.** Her üretken istek ücretli bir model çağrısıdır. `answer-v2` ile aynı commit ve ayarlarla iki üretken koşu 18 sorunun 2'sinde farklı iş durumu verdi; son iki koşu 18'inde aynı durumu verdi. Birkaç koşu bir başarı oranı vermez. Tekrarlarda kalan zayıflıklar: tanımla birebir aynı kelimeleri kullanmayan durumlarda temkinli cevap ("bütün ekip sisteme bağlanamıyor" sorusu P1 tanımı "tüm temsilcilerin çalışmasını durduran olay" ile 4 denemede 2 kez eşleştirilmedi) ve seyrek durum tutarsızlığı (K25). Sonuçlara insan incelemesi henüz yapılmadı (`pending`). Eval'dan önceki deneme çağrılarından ikisi, OpenRouter'da etkin olan sıfır veri saklama (ZDR) kısıtı OpenAI uç noktasını dışladığı için 404 aldı; servis bunu doğru biçimde 503 `provider_unavailable` olarak döndü, "belgede yok" saymadı.
- **Model sürümü logda takma adla görünür.** OpenRouter yanıtta modeli `openai/gpt-6-luna` olarak bildiriyor, tarihli slug'ı değil. Hangi snapshot'ın kullanıldığı ancak OpenRouter'ın public models API'sinden (o gün `openai/gpt-6-luna-20260922`) ayrıca kaydedilebilir.
- **Enjeksiyon dayanıklılığı kanıtlanmadı.** Testler, talimat içeren soru ve belgenin modele yalnızca veri olarak gittiğini ve sunucu doğrulamasının sürdüğünü gösterir; canlı modelin talimata uyup uymadığını göstermez.
- **Kaynak doğrulaması anlamsal değildir** (K25). Doğru bölüme atıf yapan yanlış bir süre geçebilir; bunu yalnızca eval ve insan incelemesi yakalar.
- **Retrieval kaçırması "belgede yok" gibi görünür.** İlk k'ya girmeyen bir bölümü model hiç görmez; o konuyu eksik konu olarak yazar. Sunucunun cümlesi "bu istekteki belgelerle yanıtlanamayan konular" der; yine de okuyan kişi retrieval hatasını gerçek bilgi yokluğundan ayıramaz. Teşhis için `retrieved_chunk_ids` ve logdaki skorlar gerekir.
- **Belgeler arası anlamsal denetim yok.** Loader yalnızca yapıyı ve metadata tutarlılığını denetler. Belge gövdesinde yanlış yazılmış bir kuralı (ör. D04'te "30" yerine "40") veya metadata ile ilişkilendirilmemiş iki belge arasındaki çelişkiyi yakalamaz; gövdedeki tarih ifadeleri de metadata ile karşılaştırılmaz.
- **Belgeyi yerinde düzenlemek sürümü değiştirmez.** Bir provada `D04#sure` metni yerinde değiştirildi: fingerprint değişti, indeks yeniden üretildi, yeni alıntı döndü; ama cevaptaki `version` yine `2.0` idi. Hangi metnin kullanıldığını o zaman yalnızca fingerprint (readiness, eval metadata) gösterir. Politika değişikliği yeni bir sürüm ve tarihlerle yapılmalıdır; yerinde düzenleme yazım düzeltmesi içindir.
- **Tarih hesabı yapılmaz.** Model, bölümde yazmayan bir değeri hesaplamaz (K24): "geçen hafta teslim aldı, yetişir mi?" sorusunda 30 takvim günü kuralını verir, kesin tarih verilmediği için sonucu eksik konu olarak bırakır. Resmî tatil ve gün sayma kuralı (ilk gün dâhil mi) belgelerde tanımlı değildir.
- **Tarihsel soru `as_of` ister.** Serbest metinden tarih okunmaz. Soru başka bir tarihi soruyor ama istek o tarihe ayarlı değilse modelin `as_of_required` ile bunu söylemesi beklenir; bu davranış prompt'a bağlıdır. `answer-v5` gelecek ifadelerini ("yarın") da sayar ve teslim gibi başka bir olayın tarihini kuralın tarihi saymaz. Değerlendirme setinde böyle bir soru yok (E16 doğru `as_of` ile sorulur); teslim öncesi uçtan uca denemede `as_of` verilmeden "1 Haziran 2026'da iade süresi neydi?" sorusu `as_of_required` döndü. Bu tek gözlemdir, oran değildir.
- **Üretim için eksik olanlar.** Kimlik doğrulama ve belge bazlı yetkilendirme yoktur; kapsam filtresi yetkilendirme değildir. Tenant izolasyonu, TLS ve ağ kontrolleri, saklama ve silme politikası, sağlayıcı ve veri aktarımı değerlendirmesi, güvenlik incelemesi ve yük/ölçek testi yapılmadı.
- **ASCII olmayan HTTP başlığı.** Kestrel, ASCII olmayan bir başlık değerini (ör. `X-Request-ID: accept.çok`) uygulama koduna ulaşmadan gövdesiz 400 ile reddeder; bu durumda hata sözleşmesi ve request ID dönmez (temiz kopya denetiminde görüldü).
- **rag durduktan sonraki ilk çağrı.** Temiz kopya provasında rag konteyneri korpus hatasıyla durduktan sonra ilk `/health/ready` çağrısı, `rag` adının çözümlenmesi 3 sn'yi aştığı için 504 `upstream_timeout` döndü; sonraki çağrılar hemen 503 `upstream_unavailable` döndü. "Durdu" ile "yavaş" ayrımı `docker compose ps` ve loglarla yapılır.
- **İptal Python'a ulaşmaz.** .NET'in süresi dolduğunda veya istemci koptuğunda .NET'ten Python'a giden çağrı iptal edilir, ama Python'daki istek kendi işini bitirene kadar çalışır. Üretimde bu, model çağrısının (ve maliyetinin) en fazla `LLM_TIMEOUT_SECONDS` sürmesi demektir (K28).
