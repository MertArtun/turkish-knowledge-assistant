# Teknik kararlar ve bilinen sınırlar

Her karar notu şu sırayı izler: **Seçim · Alternatif · Neden · Bedel · Ne zaman değişir.** Davranışın kendisi ve sözleşme `docs/project-spec.md` içindedir; burada tekrar edilmez.

## Karar notları

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
  - Bu korpus için kalıcı indeks zorunlu değil. 32 bölümün embedding'i geliştirme makinesinde (Apple Silicon, CPU) 0,42 sn sürüyor; her başlangıçta yeniden hesaplamak da yeterli olurdu. Buna karşılık yaklaşık 150 satır kod ve testleri var.
  - `INDEX_FORMAT_VERSION` elle artırılmalıdır. Önek veya başlık yolu biçimi değişirse fingerprint bunu kendiliğinden yakalar, çünkü girdi metni fingerprint'e dâhil. Pooling kodu değişip sürüm artırılmazsa eski vektörler kullanılmaya devam eder.
  - Metadata fingerprint'e dâhil olduğu için yalnızca `valid_to` değişse bile tüm embedding'ler yeniden hesaplanır. 32 bölümde bu önemsizdir.
- **Ne zaman değişir:** Korpus binlerce bölüme büyürse, bölüm hash'ine göre artımlı güncelleme ve yaklaşık arama (ANN) düşünülür.

### K17 — Arama: önce sürüm ve kapsam görünümü, sonra tam dot product; skor eşiği kapalı
- **Seçim:**
  - `retrieve` yalnızca `select_versions`'ın seçtiği belgelerin bölümlerini puanlar.
  - Skor, normalize vektörlerde dot product'tır (yani cosine). Sıralama skora göre azalan; eşit skorda `chunk_id` artan. `top_k=4`.
  - `MIN_RETRIEVAL_SCORE` varsayılan olarak boş, yani eşik kapalı.
- **Alternatif:** Tüm korpusta top-k alıp sonra filtrelemek; BM25, hibrit arama veya reranker; sabit bir eşik (ör. 0,80).
- **Neden:**
  - Sonradan filtrelemede süresi dolmuş bir sürüm daha yüksek skor alırsa top-k'yı doldurur ve geçerli bölümü dışarı iter. Testte `top_k=1` iken D03 en yakın bölüm olsa da D04 dönüyor; sonradan filtreleme burada boş sonuç verirdi.
  - 32 bölümde tam tarama milisaniyenin altında sürer ve incelemesi kolaydır.
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
- **Bedel:**
  - Eşik kapalı olduğu için arama cevapsız sorularda da 4 aday döndürür. Konuya yakın ama cevapsız soruların reddi, üretim aşamasındaki kanıt yeterliliği kontrolüne dayanır. Alıntı modunda bu adaylar cevap olarak değil, aday olarak sunulur.
  - Açıklayıcı bölümler (`kullanim`, `musteri-istegi`) zorunlu bölümlerle aynı ilk 4'ü paylaşıyor. DEV01'de beklenen bölüm 3. sırada. DEV03'te 1. sırada `D05#kullanim` var; bu bölüm iade kargosunun kendi konusu olmadığını söylüyor.
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
- **Seçim:** `create_app`, ayarları, korpusu, embedding modelini ve indeksi bağlantı kabul etmeden önce yükler ve doğrular. Geçersiz korpus, indirilemeyen model veya kullanılamaz indeks süreci durdurur. Servis edilen readiness her zaman `ready`'dir.
- **Alternatif:** Yüklemeyi arka planda yapmak ve bu sürede `/health/ready`'de `not_ready`, `/internal/ask`'te `service_not_ready` dönmek.
- **Neden:** Yarım yüklü servis hiç istek almaz; "hazır değil" durumu kodda değil süreç durumunda tutulur. Arka plan yüklemesinde, başarısız yüklemeden sonra süreci durdurmak için ayrı bir mekanizma gerekirdi.
- **Bedel:** İlk model indirmesi sürerken port kapalıdır: `/health/live` de cevap vermez, .NET 503 `upstream_unavailable` döner. `not_ready` ve `service_not_ready` sözleşmede duruyor ama Python şu an bunları üretmiyor.
- **Ne zaman değişir:** Konteyner ortamı yükleme sürerken canlılık sinyali isterse yükleme arka plana alınır. İstemezse `not_ready` ve `service_not_ready` sözleşmeden çıkarılır.

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
- **Bedel:**
  - OpenRouter ek bir aracıdır ve kendi veri politikası vardır. `store=false`, OpenRouter'ın veya OpenAI'ın kendi saklama politikalarını ortadan kaldırmaz.
  - OpenAI'ın model sayfasında tarihli bir snapshot yok (`gpt-6-luna`). OpenRouter'da `openai/gpt-6-luna` takma adı ileride başka bir snapshot'a geçebilir. Sağlayıcının bildirdiği model her üretimin log satırına yazılır.
  - Reasoning tokenları çıktı bütçesinden yer. İlk üç canlı çağrıda (düşük effort) reasoning tokenı 0, çıktı 50–74 token, süre 1,3–2,8 sn oldu; 1000 token ve 25 sn bu sorularda geniş pay bırakıyor. Üç çağrı genelleme için yeterli değil; eval süreleri ve token sayılarını kaydedecek.
  - SDK zaman aşımı aşama başınadır (bağlantı, okuma, yazma); toplam süre bunu biraz aşabilir. Dış sınır .NET'in 45 sn'sidir.
- **Ne zaman değişir:** Canlı ölçüm 1000 tokenın veya 25 sn'nin yetmediğini gösterirse değer gerekçesiyle değişir. Model değişirse ve yeni model reasoning modeli değilse `reasoning` parametresi kaldırılır.

### K24 — Modele giden veri: yalnızca JSON veri, sürümlü prompt dosyası
- **Seçim:**
  - Sistem talimatı ayrı dosyadadır: `app/prompts/answer.txt`. Sürümü `PROMPT_VERSION` (`answer-v1`); dosyanın SHA-256 değeri readiness'ta (`prompt_version`, `prompt_hash`) ve üretim loglarında görünür. Bir test her sürümün hash'ini sabitler; prompt değişince sürüm de değişmek zorundadır. Prompt'ta hiç rakam yoktur (bir test denetler), politika sayıları yalnızca korpusta durur.
  - Kullanıcı mesajı tek bir JSON nesnesidir: etkin tarih, etkin kapsam, soru ve en fazla 4 bölüm (`id`, `heading_path`, `text`). Eski sürümler zaten sürüm görünümünde elendiği için modele gitmez.
- **Alternatif:** Soruyu ve bölümleri XML benzeri etiketlerle düz metne gömmek; prompt'u kodda sabit metin olarak tutmak; tüm top-k'yı göndermek.
- **Neden:**
  - JSON string kaçışı sayesinde soru veya belge kendi alanını kapatıp talimat ya da başka bir kaynak gibi görünemez. Düz metin etiketlerinde `</soru>` yazan bir soru bunu yapabilirdi. Test, tırnak ve köşeli parantezle alanı kapatmaya çalışan bir soruyla bunu denetler.
  - Prompt dosyası incelenebilir ve sürümlenebilir; eval sonuçları hangi prompt'la alındığını kaydeder.
  - 4 bölüm ve 512 tokenlık bölüm/soru sınırı, modele giden bağlamı sınırlar.
- **Bedel:** Talimatların veri olarak ele alınması modelin uyumuna bağlıdır. Sahte generator testleri yalnızca talimatın doğru yere gittiğini gösterir, canlı modelin enjeksiyona dayanıklı olduğunu göstermez. `TOP_K` 4'ten büyük ayarlanırsa 5. ve sonraki bölümler `retrieved_chunk_ids`'te görünür ama modele gitmez.
- **Ne zaman değişir:** Bölümler uzarsa veya 4 bölüm yetmezse bağlam bütçesi token sayısıyla ayrıca sınırlanır.

### K25 — Model çıktısı reddedilir, düzeltilmez; cevap sunucuda kurulur
- **Seçim:**
  - `validate_answer` model çıktısındaki her ihlali toplar ve 502 `invalid_generation_output` döner: boş veya kaynaksız claim, bu istekte verilmemiş kaynak ID'si (korpusta olsa bile), boş eksik konu, durumla çelişen claim/`missing_topics`/`reason_code`.
  - Cevap metnini sunucu kurar: claim metinleri, `insufficient_evidence` için `reason_code`'un standart açıklaması ve eksik konular için standart bir cümle. Kaynak başlığı, sürüm, tarihler ve birebir alıntı korpustan eklenir.
  - Sağlayıcı hataları (bağlantı, HTTP hatası, zaman aşımı, ret, kesilmiş çıktı) ayrı kodlarla hata olur; hiçbiri "belgede bilgi yok" sayılmaz ve alıntı moduna düşülmez.
- **Alternatif:** Geçersiz ID'leri atıp kalan claim'lerle devam etmek; modelden ayrıca serbest bir cevap metni almak; ikinci bir LLM ile anlamsal kontrol (LLM-as-judge).
- **Neden:** Sessizce temizlenen bir cevap, doğrulanmamış bir modeli doğrulanmış gibi gösterir. Hata, eval'da "generation" veya "validation" kök nedeni olarak görünür. Atıfsız ikinci bir cevap alanı, doğrulamanın dışında kalan metin yayımlamak demektir.
- **Bedel:** Kaynak ID doğrulaması anlamsal doğruluk garantisi değildir: verilen bir bölüme atıf yapan yanlış bir claim (ör. "60 gün") geçer. Bu bilinçli olarak bir testle görünür tutuldu. Katı kurallar, canlı modelin küçük biçim hatalarında da 502 doğurur.
- **Ne zaman değişir:** Eval, belirli bir kuralın doğru cevapları sistematik olarak reddettiğini gösterirse kural veya prompt, ölçülerek değişir.

## Bilinen sınırlar

- **İlk indirme.** İlk başlangıç internet ister: model yaklaşık 470 MB, tokenizer yaklaşık 17 MB olarak `MODEL_CACHE_DIR` altına iner. Önbellek dolduktan sonra sabit commit sayesinde ağ isteği yapılmaz. Sıfırdan internetsiz kurulum desteklenmez.
- **Embedding revision.** `EMBEDDING_REVISION` yalnızca tam commit hash'i kabul eder; boşsa sabitlenmiş commit kullanılır. `EMBEDDING_MODEL` revision'sız değiştirilirse aynı commit o repoda bulunmaz ve başlangıç hata verir. Başka bir revision için model testleri ve `measure_retrieval.py` yeniden çalıştırılmalıdır.
- **Soru uzunluğu.** Sorgu da 512 token sınırına tabidir. Sınırı aşan soru kesilmez, 400 `invalid_request` olur. 2.000 karakterlik sınır bunu garanti etmez: normal Türkçe metinde 2.000 karakter yaklaşık 470 token tutarken 600 emoji sınırı aşıyor (gerçek tokenizer ile ölçüldü).
- **Skorların taşınabilirliği.** Skorlar farklı CPU mimarilerinde son basamaklarda (yaklaşık 1e-6) farklı çıkabilir. Eşit skorda `chunk_id` sıralaması yalnızca birebir eşit skorlar için devreye girer.
- **Küçük ölçüm.** Eşik kararı 4 geliştirme sorusuna dayanır; genellenebilir bir sonuç iddia edilmez.
- **Tarihsel soruda zorunlu bölüm ilk 4'ün dışında kaldı.** `as_of=2026-06-01` ile "1 Haziran 2026'da iade süresi neydi?" sorusunda gerçek modelle `D03#sure` 5. sırada çıktı (0,8147). İlk 4: `D03#uygulama` 0,8241, `D05#bedel` 0,8230, `D05#kullanim` 0,8201, `D03#tarihler` 0,8187. Açıklayıcı bölümlerin zorunlu bölümü dışarı itme riski (K17) burada gerçekleşti. Bölümleme bu soruya göre ayarlanmadı; olası düzeltme önce geliştirme sorularında denenip ölçülecek.
- **Canlı üretim yalnızca smoke düzeyinde doğrulandı.** OpenRouter üzerinden üç gerçek çağrı yapıldı (biri .NET üzerinden uçtan uca, ikisi `smoke_generation.py` ile): iki cevaplanabilir soru doğru bölüme atıfla `answered`, bir cevapsız soru `insufficient_evidence` + `not_in_documents` döndü; yapılandırılmış çıktı OpenRouter'ın Responses API'si üzerinden çalıştı. Daha önceki iki deneme, OpenRouter'da etkin olan sıfır veri saklama (ZDR) kısıtı OpenAI uç noktasını dışladığı için 404 aldı; servis bunu doğru biçimde 503 `provider_unavailable` olarak döndü. Bu bir değerlendirme değildir; kalite iddiası eval'a kalır.
- **Model sürümü logda takma adla görünür.** OpenRouter yanıtta modeli `openai/gpt-6-luna` olarak bildiriyor, tarihli slug'ı değil. Hangi snapshot'ın kullanıldığı ancak OpenRouter'ın public models API'sinden (o gün `openai/gpt-6-luna-20260922`) ayrıca kaydedilebilir.
- **Enjeksiyon dayanıklılığı kanıtlanmadı.** Testler, talimat içeren soru ve belgenin modele yalnızca veri olarak gittiğini ve sunucu doğrulamasının sürdüğünü gösterir; canlı modelin talimata uyup uymadığını göstermez.
- **Kaynak doğrulaması anlamsal değildir** (K25). Doğru bölüme atıf yapan yanlış bir süre geçebilir; bunu yalnızca eval ve insan incelemesi yakalar.
- **İptal Python'a ulaşmaz.** .NET'in süresi dolduğunda veya istemci koptuğunda .NET'ten Python'a giden çağrı iptal edilir, ama Python'daki istek kendi işini bitirene kadar çalışır. Üretimde bu, model çağrısının (ve maliyetinin) `LLM_TIMEOUT_SECONDS`'a kadar sürmesi demektir. .NET'in 45 sn'si, 25 sn'lik model süresinden uzun olduğu için normal akışta .NET önce zaman aşımına düşmez.
