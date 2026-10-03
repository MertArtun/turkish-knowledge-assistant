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

## Bilinen sınırlar

- **İlk indirme.** İlk başlangıç internet ister: model yaklaşık 470 MB, tokenizer yaklaşık 17 MB olarak `MODEL_CACHE_DIR` altına iner. Önbellek dolduktan sonra sabit commit sayesinde ağ isteği yapılmaz. Sıfırdan internetsiz kurulum desteklenmez.
- **Revision kodda sabit.** Embedding revision'ı `app/settings.py` içinde tam commit hash'i olarak sabittir; ortam değişkeniyle değiştirilemez. `EMBEDDING_MODEL` değiştirilirse aynı commit o repoda bulunmaz ve başlangıç hata verir.
- **Soru uzunluğu.** Sorgu da 512 token sınırına tabidir. Sınırı aşan soru kesilmez, 400 `invalid_request` olur. 2.000 karakterlik sınır bunu garanti etmez: normal Türkçe metinde 2.000 karakter yaklaşık 470 token tutarken 600 emoji sınırı aşıyor (gerçek tokenizer ile ölçüldü).
- **Skorların taşınabilirliği.** Skorlar farklı CPU mimarilerinde son basamaklarda (yaklaşık 1e-6) farklı çıkabilir. Eşit skorda `chunk_id` sıralaması yalnızca birebir eşit skorlar için devreye girer.
- **Küçük ölçüm.** Eşik kararı 4 geliştirme sorusuna dayanır; genellenebilir bir sonuç iddia edilmez.
- **Tarihsel soruda zorunlu bölüm ilk 4'ün dışında kaldı.** `as_of=2026-06-01` ile "1 Haziran 2026'da iade süresi neydi?" sorusunda gerçek modelle `D03#sure` 5. sırada çıktı (0,8147). İlk 4: `D03#uygulama` 0,8241, `D05#bedel` 0,8230, `D05#kullanim` 0,8201, `D03#tarihler` 0,8187. Açıklayıcı bölümlerin zorunlu bölümü dışarı itme riski (K17) burada gerçekleşti. Bölümleme bu soruya göre ayarlanmadı; olası düzeltme önce geliştirme sorularında denenip ölçülecek.
- **Üretim yolu henüz yok.** `generative` istek her durumda 503 `generation_not_configured` döner. Readiness'taki `generation_configured` yalnızca anahtarın tanımlı olduğunu gösterir.
- **İptal Python'a ulaşmaz.** .NET'in süresi dolduğunda veya istemci koptuğunda .NET'ten Python'a giden çağrı iptal edilir, ama Python'daki istek kendi işini bitirene kadar çalışır. Alıntı modunda bu birkaç milisaniyedir.
