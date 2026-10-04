# Proje spesifikasyonu

Kurgu bir şirketin destek çalışanına, onaylı bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur API. Genel amaçlı chatbot, işlem platformu veya üretime hazır sistem değildir. Kararların gerekçeleri ve bilinen sınırlar `docs/decisions.md` içindedir; burada yalnızca davranış ve sözleşme yer alır.

## 1. İşveren gereksinimleri ve karşılanma yeri

| # | Gereksinim (özet) | Nerede karşılanır |
|---|---|---|
| R1 | 8–10 kısa kurgu doküman | `data/knowledge/` — tam 10 dosya |
| R2 | En az bir prosedürün eski ve güncel sürümü | `returns`: D03 (v1.0) ve D04 (v2.0) |
| R3 | Aranabilir dokümanlar, Türkçe soruları yanıtlayan API | `POST /api/ask` (.NET) → `POST /internal/ask` (Python) |
| R4 | Kullanılan doküman ve bölümün gösterilmesi | `sources[]` (doküman, sürüm, bölüm, birebir alıntı) |
| R5 | Bilgi yoksa açıkça belirtmek, uydurmamak | `insufficient_evidence` / `partial`, `missing_topics`, `reason_code` |
| R6 | Çelişen kaynaklarda güncel sürüm seçiminin gösterilmesi | `version_decisions[]` (sunucu üretir) |
| R7 | Normal, cevapsız ve çelişkili en az 10 soruyla değerlendirme | `eval/` — 18 soru |
| R8 | Kaynak kod, README, örnek ortam değişkenleri | repo, `README.md`, `.env.example` |
| R9 | Beklenen ve gerçek çıktıların karşılaştırılması | `eval/results/<run_id>/` |
| R10 | Teknik tercihler, gerekçeler, bilinen sınırlar | `docs/decisions.md` |
| R11 | API anahtarının kodda ve Git geçmişinde olmaması | `.gitignore`, `.env.example` boş anahtar, commit öncesi tarama |

İşveren .NET ve FastAPI'yi **önermiştir**; ikisi de zorunlu değildir. Arayüz ve çok ajanlı yapı istenmemiştir.

**Bizim tercihlerimiz (zorunlu değil):** .NET + FastAPI iki servis; 18 soruluk eval ve 4 geliştirme sorusu; alıntı modu (`evidence_only`); readiness/loglama/timeout gibi işletim ayrıntıları; Docker Compose; `retrieved_chunk_ids` ile dış API üzerinden retrieval ölçümü.

## 2. Korpus

Şirket: **Yardım bende Destek Teknolojileri** (tamamen hayalî). Tüm süreler ve koşullar demo kurgusudur; her dosyanın frontmatter'ı `# DEMO KURGUSU` YAML yorumuyla başlar. Her belgenin kapsamı `country=TR`, `customer_type=B2B`, `product=MH-10`. Belgeler kısadır; uzunluk için yeni iş kuralı eklenmez. Zorunlu bölümlerin yanında yalnızca konuyu açıklayan bölümler vardır (ör. `kullanim`; iade belgelerinde `uygulama` ve `tarihler`).

| ID | Dosya | procedure_id | Zorunlu bölümler (section_id: içerik) | Sürüm / geçerlilik |
|---|---|---|---|---|
| D01 | `01-mh10-setup.md` | `mh10-setup` | `baglanti`: USB bağlantısı; panelde MH-10'un giriş ve çıkış aygıtı seçilmesi | 1.0, 2026-01-01 → açık |
| D02 | `02-audio-troubleshooting.md` | `audio-troubleshooting` | `ses-yok`: USB, panel aygıt seçimi, test çağrısı, sürerse ticket | 1.0, 2026-01-01 → açık |
| D03 | `03-returns-v1.md` | `returns` | `sure`: teslimden sonra 14 takvim günü; `kargo`: kargoyu müşteri öder | 1.0, 2026-01-01 → 2026-07-01 |
| D04 | `04-returns-v2.md` | `returns` | `sure`: teslimden sonra 30 takvim günü; `kargo`: şirket iade etiketi sağlar, etiketli gönderimin bedelini karşılar | 2.0, 2026-07-01 → açık, `supersedes=D03` |
| D05 | `05-refund-payment.md` | `refund-payment` | `bedel`: iade kabulünden sonra 5 iş günü; kargoya verme tarihinden başlamaz | 1.0, 2026-01-01 → açık |
| D06 | `06-support-ticket.md` | `support-ticket` | `alanlar`: seri numarası, varsa hata kodu, yeniden üretme adımları | 1.0, 2026-01-01 → açık |
| D07 | `07-priority-sla.md` | `priority-sla` | `p1`: tüm temsilcileri durduran olay P1; ilk yanıt hedefi 2 çalışma saati, çözüm garantisi değil | 1.0, 2026-01-01 → açık |
| D08 | `08-support-hours.md` | `support-hours` | `saatler`: hafta içi 09.00–18.00, Europe/Istanbul | 1.0, 2026-01-01 → açık |
| D09 | `09-account-access.md` | `account-access` | `sifre`: kayıtlı e-postaya parola sıfırlama bağlantısı | 1.0, 2026-01-01 → açık |
| D10 | `10-safe-support-sharing.md` | `safe-support-sharing` | `paylasim`: parola/OTP paylaşılmaz; hata görsellerindeki kişisel bilgiler gizlenir | 1.0, 2026-01-01 → açık |

Tüm belgeler `status=approved`; D04 dışında `supersedes=null`. İade belgelerinde sürümü belirleyen olay **iade talebinin açıldığı tarihtir** (`as_of`); süre penceresi ise **teslim tarihinden** sayılır. Bu iki tarih karıştırılmaz; hak hesaplayan bir motor yapılmaz.

**Korpusta hiç yer almayacak bilgiler** (cevapsız testlerin temeli): garanti süresi, Almanya iade koşulu, herhangi bir gerçek ticket'ın durumu. Resmî tatil/son tarih hesabı ve canlı ticket entegrasyonu yoktur.

## 3. Metadata ve bölümleme kuralları

Uygulama: `src/rag_service/app/documents.py::load_corpus`; sözdizimi `tests/test_documents.py` ile sabitlenmiştir.

**Dosyalar.** Yalnızca `KNOWLEDGE_DIR`'in doğrudan altındaki `NN-slug.md` dosyaları okunur (ör. `04-returns-v2.md`). Bu kalıba uymayan `.md` dosyası (ör. `README.md`) yükleme hatasıdır: yanlış adlı belge sessizce kaybolmaz, not dosyası sessizce kaynağa dönüşmez. `.md` olmayan dosyalar ve alt dizinler hiç okunmaz. Symlink, dizin içini gösterse bile reddedilir; böylece dizin dışındaki hiçbir dosya okunamaz. Dosyalar UTF-8 olmalıdır.

**Frontmatter.** Dosya `---` satırıyla başlar, YAML bloğu `---` ile kapanır ve `yaml.safe_load` ile okunur (Python nesnesi kuran YAML etiketleri hatadır). Alanlar: `doc_id`, `procedure_id`, `title`, `version`, `valid_from`, `valid_to`, `status`, `scope` (`country`, `customer_type`, `product`), `supersedes`.
- Hepsi zorunludur. `valid_to` ve `supersedes` `null` olabilir ama yazılmaları gerekir. Bilinmeyen alan reddedilir.
- Tipler katıdır: tarihler tırnaksız YAML tarihi (`2026-07-01`), `version` tırnaklı metindir (`"2.0"`).
- `doc_id` `D` + iki rakamdır. `procedure_id` ve bölüm ID'leri `[a-z0-9]+(-[a-z0-9]+)*` kalıbına uyar.
- `status`: `approved` | `draft` | `withdrawn`. `valid_to` verilmişse `valid_from`'dan sonra olmalıdır.

**Gövde ve bölümler.** Gövde yalnızca bölümlerden oluşur. Bölüm başlığı satır başında tam olarak `## Başlık {#bolum-id}` biçimindedir: `##`, boşluk, başlık metni, boşluk, `{#id}`. ID başlıktan türetilmez; Türkçe karakter ve büyük harf içermez.
- Belge başlığı gövdede yazılmaz; frontmatter'daki `title`'dan gelir.
- Şunlar hatadır, çünkü aranamayacak veya atıf yapılamayacak metin ya da başlık yolunda görünmeyen bir başlık bırakırlar: başka her ATX başlığı (`#`, `###`, ID'siz veya girintili `##`) ve ilk bölümden önceki metin.
- Bölüm içeriği, başlık satırından sonraki satırlardır. Baştaki ve sondaki boşluklar kırpılır; geri kalanı Unicode normalleştirmesi olmadan birebir saklanır. Boş bölüm ve aynı belgede tekrar eden bölüm ID'si hatadır.
- Bölüm alanları:
  - `chunk_id`: `D04#sure` biçiminde, belge ve bölüm ID'si.
  - `doc_id`, `section_id`.
  - `heading_path`: `[title, bölüm başlığı]`.
  - `content`: kaynaklarda `quote` olarak gösterilen birebir metin.
  - `content_hash`: içeriğin SHA-256 değeri.
- Bir kuralın koşulu veya istisnası ayrı bölüme bölünmez. Başlık yolu embedding girdisine ve kaynak gösterimine taşınır.
- Tokenizer sınırını aşan bölüm sessizce kesilmez, açıklayıcı hata verir. Bu kontrol tokenizer gerektirdiği için loader'da değil, indeks yüklenirken yapılır (aşağıda).

**Korpus düzeyindeki kontroller.** Belgeler arası kurallar:
- Aynı `doc_id` iki dosyada olamaz.
- Aynı `(procedure_id, scope)` içinde aynı `version` iki belgede olamaz.
- `supersedes` var olan bir belgeyi göstermeli; o belge aynı prosedürde ve aynı kapsamda olmalı. Zincir döngü içeremez; belgenin kendini göstermesi de döngüdür.
- Aynı `(procedure_id, scope)` içindeki `approved` belgelerin `[valid_from, valid_to)` aralıkları kesişemez. Taslak ve geri çekilmiş belgeler bu kontrole girmez. Bitiş hariç olduğu için bir sürüm, öncekinin bittiği gün başlayabilir.

Her ihlal, dosya adını (bölüm sözdiziminde satır numarasını da) içeren bir `CorpusError`'dır. İlk hatada durulur ve servis bu korpusla başlamaz.

**Embedding girdisi.** Uygulama: `src/rag_service/app/embeddings.py`.
- Model `intfloat/multilingual-e5-small`, commit `614241f622f53c4eeff9890bdc4f31cfecc418b3`; modelin kendi `onnx/model.onnx` ve `onnx/tokenizer.json` dosyaları, ONNX Runtime, CPU.
- Bölüm girdisi: `passage: ` + `heading_path` öğeleri ` > ` ile birleşik + satır sonu + birebir içerik. Sorgu girdisi: `query: ` + soru.
- Vektör: gerçek tokenlar üzerinde mean pooling, ardından L2 normalizasyonu; 384 boyut, float32. Sıfır veya sonlu olmayan vektör `EmbeddingError`'dır.
- Sınır 512 token; önek, başlık yolu ve özel tokenlar (`<s>`, `</s>`) dâhil sayılır, tokenizer kesme yapmaz. Sınırı aşan bölüm, `chunk_id` ve token sayısını içeren `CorpusError`'dır (`check_passage_lengths`). Sınırı aşan sorgu `EmbeddingError`'dır; sorgu da kesilmez.

**İndeks.** Uygulama: `src/rag_service/app/index_store.py::load_or_build_index`. Markdown tek doğruluk kaynağıdır; SQLite indeks (`INDEX_PATH`) türetilmiştir.
- Tablolar: `meta(key, value)` yalnızca `fingerprint` satırını, `chunks(position, chunk_id, embedding)` her bölümün vektörünü tutar. Vektör little-endian float32 bayttır; pickle kullanılmaz.
- Fingerprint, şu bilgilerin SHA-256 özetidir: indeks biçim sürümü (`INDEX_FORMAT_VERSION`), `model@revision`, her belge için dosya adı ve metadata, her bölüm için `chunk_id` ve embedding girdisinin SHA-256 değeri. Belge sırası sonucu değiştirmez.
- Her yüklemede sıra şöyledir: token sınırı kontrolü → fingerprint → kayıtlı indeksin doğrulanması.
- Kayıtlı indeks yalnızca şu koşulların hepsi sağlanırsa kullanılır: fingerprint aynı, bölüm listesi ve sırası korpusla aynı, her vektör model boyutunda, NaN/sonsuz değer yok, norm 1 (±0,001).
- Aksi hâlde (dosya yok, eski, okunamıyor veya geçersiz) neden loglanır ve indeks yeniden üretilir: yeni vektörler aynı kontrollerden geçer, geçici dosyaya yazılır, geri okunarak doğrulanır ve `os.replace` ile yerine konur. Yarım veya doğrulanmamış indeks hiçbir zaman servis edilmez.
- Yeni üretilen vektörler geçersizse `IndexStoreError` verilir; eski dosya değişmeden kalır.
- Çalışırken belge güncellemesi yoktur; belgeler değişince indeks bir sonraki yüklemede yeniden üretilir.

## 4. Sürüm seçimi

1. İstek kapsamı ve etkin `as_of` bir kez çözülür (`as_of` yoksa Europe/Istanbul'a göre bugün; saat enjekte edilebilir).
2. Yalnızca kapsama tam uyan belgeler; kapsamlar arası fallback yok.
3. `approved` olmayanlar elenir.
4. `valid_from <= as_of` ve (`valid_to` null veya `as_of < valid_to`). Başlangıç dâhil, bitiş hariç.
5. Her `(procedure_id, scope)` için en fazla bir geçerli sürüm; birden fazlası korpus hatasıdır (dosya sırası, sürüm numarası veya LLM ile çözülmez).
6. Arama yalnızca bu geçerli belge kümesinde yapılır.

Beklenen sınırlar: 2026-06-30 → D03; 2026-07-01 ve 2026-10-04 → D04. Geçerli sürüm olmayan tarihte başka tarihli belge seçilmez. Yeni onaylı v3 eklenirken önceki sürümün `valid_to` değeri v3'ün `valid_from` değerine çekilmelidir; açık uçlu önceki sürümle örtüşen v3 reddedilir. `supersedes` açıklayıcıdır, geçerlilik kurallarını geçersiz kılmaz.

Uygulama: `src/rag_service/app/versioning.py`.
- `effective_as_of(as_of, clock)`: İstekte `as_of` varsa onu kullanır. Yoksa enjekte edilen saatin anını Europe/Istanbul'a çevirip tarihini alır.
- `effective_scope(scope)`: İstekte `scope` yoksa `TR`/`B2B`/`MH-10` kullanılır. Kapsam büyük/küçük harf dâhil birebir karşılaştırılır; normalleştirme veya fallback yoktur (`tr` ≠ `TR`).
- `select_versions(belgeler, scope, as_of)`: Korpustaki her prosedür için tek bir `VersionDecision` üretir (`procedure_id` anahtarlı). Belgeler `doc_id` sırasıyla işlenir; sonuç dosya veya girdi sırasına bağlı değildir. `selected`, tek geçerli belgedir; geçerli belge yoksa `null`. Geri kalan her belge `excluded` içinde tek bir nedenle `doc_id` sırasıyla yer alır.
- Aynı tarihte birden çok geçerli sürüm görülürse (yükleme kontrolü atlanmışsa) seçim yapılmaz; `CorpusError` verilir.
- Arama yalnızca `selected` belgelerin bölümlerinde yapılır. Cevaptaki `version_decisions` bu sözlükten, getirilen bölümlerin prosedürleri için seçilir (§5).

**Arama.** Uygulama: `src/rag_service/app/retrieval.py::retrieve(index, query_vector, decisions, top_k, min_score)`.
1. Adaylar yalnızca `decisions` içindeki `selected` belgelerin bölümleridir. Filtre skorlamadan ve top-k'dan **önce** uygulanır. Desteklenmeyen kapsamda hiçbir belge seçilmediği için sonuç boştur.
2. Skor, sorgu vektörü ile bölüm vektörünün dot product'ıdır; vektörler normalize olduğu için cosine'a eşittir. Tam tarama yapılır.
3. Sıralama skora göre azalan; eşit skorda `chunk_id` artan.
4. `MIN_RETRIEVAL_SCORE` boşsa eşik yoktur; doluysa altındaki adaylar düşer. Ardından ilk `TOP_K` (varsayılan 4) döner.

Skor bir güven değeri değildir ve cevapta yer almaz; yalnızca log ve ölçüm içindir. Eşiğin neden kapalı olduğu ve ölçüm `docs/decisions.md` K17'dedir.

Dışlama nedenleri (`excluded[].reason`). Kontroller kural sırasıyla yapılır ve **ilk** başarısız kontrol nedeni belirler:

| Sıra | Neden | Koşul |
|---|---|---|
| 1 | `scope_mismatch` | Belgenin kapsamı istek kapsamıyla birebir aynı değil |
| 2 | `not_approved` | `status` `draft` veya `withdrawn` |
| 3 | `future_effective` | `as_of < valid_from` |
| 4 | `expired` | `valid_to` dolu ve `as_of >= valid_to` |

Serbest metinden tarih çıkarılmaz; soru başka bir tarihi soruyor ama istek o tarihe ayarlı değilse cevap `as_of_required` ile bunu belirtir.

## 5. API sözleşmesi

### Uçlar

| Servis | Uç | Açıklama |
|---|---|---|
| .NET (dış, `127.0.0.1:8080`) | `POST /api/ask` | Soru sorma |
| .NET | `GET /health/live` | Süreç çalışıyor mu: `{"status":"live"}` |
| .NET | `GET /health/ready` | Python readiness'ının tipli kopyası (3 sn timeout; ham gövde aktarılmaz). HTTP durumu gövdedeki `status`'tan gelir: `ready` 200, `not_ready` 503. Python'a ulaşılamazsa, süre dolarsa veya gövde bozuksa hata sözleşmesi döner: 503 `upstream_unavailable`, 504 `upstream_timeout`, 502 `upstream_invalid_response` |
| Python (iç, `rag:8000`, host'a port açılmaz) | `POST /internal/ask`, `GET /health/live`, `GET /health/ready` | Aynı gövde şekilleri |

JSON alanları snake_case; tarihler `YYYY-MM-DD`; boş değerler `null` veya `[]` olarak her zaman yazılır (alan atlanmaz).

### İstek

| Alan | Kural |
|---|---|
| `question` | Zorunlu. Trim sonrası boş olamaz, en fazla 2000 karakter (Unicode kod noktası; iki serviste aynı sayım). Ayrıca embedding modelinin 512 token sınırına sığmalıdır (`query: ` öneki ve özel tokenlar dâhil). Sığmayan soru kesilmez; Python 400 `invalid_request` döner. Normal Türkçe metinde 2000 karakter yaklaşık 470 token tutar; emoji gibi karakterler sınırı daha kısa metinde aşabilir. |
| `as_of` | Opsiyonel, yalnızca `YYYY-MM-DD`. Boşsa Europe/Istanbul'a göre bugün. |
| `scope` | Opsiyonel; verilirse `country`, `customer_type`, `product` üçü de zorunlu, her biri 1–64 karakter (uzunluğu yalnızca Python denetler). Varsayılan `TR` / `B2B` / `MH-10`. Desteklenmeyen kapsam 400 değil, `insufficient_evidence` + `unsupported_scope` üretir. Scope filtresi yetkilendirme değildir. |
| `mode` | Opsiyonel: `generative` veya `evidence_only`; boşsa `APP_MODE`. |

Tanınmayan alan veya enum değeri 400 ile reddedilir. Alan adları ve enum değerleri büyük/küçük harfe duyarlıdır ve yalnızca tam yazımıyla kabul edilir (`Question`, `Generative`, `EVIDENCEONLY` reddedilir). HTTP gövde sınırı 16 KiB (aşılırsa 413).

.NET, Python'a her zaman dört alanı yazar: trim edilmiş `question`; verilmemiş `as_of`, `scope` ve `mode` açıkça `null`. Varsayılanları yalnızca Python çözer.

**Request ID.** `X-Request-ID` başlığıyla gelir. Tek değer değilse veya `^[A-Za-z0-9._-]{1,64}$` kalıbına (satır sonu dâhil hiçbir ek karakter olmadan) uymuyorsa .NET yenisini üretir ve Python'a aynı başlıkla taşır. Python aynı kuralla geçerli başlığı aynen kullanır, yoksa kendisi üretir (doğrudan çağrı). Python cevabındaki `request_id` gönderilenle aynı değilse .NET 502 `upstream_invalid_response` döner. `X-Request-ID` iki servisin her cevabında, sağlık uçları ve hatalar dâhil, döner.

### İstek akışı (Python)

Uygulama: `src/rag_service/app/service.py::Assistant.ask`. Sıra:

1. `as_of`, `scope` ve `mode` çözülür (`mode` yoksa `APP_MODE`).
2. `mode=generative` ise ve generator yoksa (`OPENAI_API_KEY` tanımlı değil) hiçbir iş yapılmadan 503 `generation_not_configured` döner; istek alıntı moduna düşürülmez, sahte cevap üretilmez.
3. Sürüm görünümü hesaplanır (§4). Hiçbir prosedürde seçili belge yoksa arama yapılmaz ve `insufficient_evidence` döner: tüm dışlama nedenleri `scope_mismatch` ise `reason_code=unsupported_scope`, değilse `no_valid_version`.
4. Soru embedding'i ayrı bir thread'de, aynı anda tek çağrı olarak hesaplanır (event loop bloke olmaz). Token sınırı burada denetlenir.
5. Arama yapılır (§4). Eşik tüm adayları elerse `insufficient_evidence` + `not_in_documents` döner (eşik kapalıyken bu olmaz).
6. `evidence_only` cevabında `evidence`, sıralı top-k bölümlerdir; `quote` ve metadata yüklü korpustan gelir. `version_decisions` getirilen bölümlerin prosedürleri için, ilk görünme sırasıyladır. Eşik kapalı olduğu için belgelerde cevabı olmayan bir soruda da adaylar döner; adaylar cevap değildir.
7. `generative` istekte ilk en fazla 4 bölüm (`GENERATION_SECTION_LIMIT`; `TOP_K` daha büyük olsa da) modele gider ve model çıktısı aşağıdaki kurallarla doğrulanır (Üretim).

3 ve 5. adımlardaki `insufficient_evidence` cevaplarında `evidence`, `retrieved_chunk_ids` ve `version_decisions` boştur; `answer` sunucunun yazdığı standart Türkçe açıklamadır. Model `insufficient_evidence` derse arama yapılmış olduğu için `retrieved_chunk_ids` ve `version_decisions` doludur.

### Üretim (`generative`)

Uygulama: `src/rag_service/app/generation.py`, akış `service.py::Assistant._generate`.

- **Modele gidenler:** sistem talimatı (`app/prompts/answer.txt`, sürüm `PROMPT_VERSION`) ve yalnızca veri içeren bir JSON kullanıcı mesajı: `effective_as_of`, `effective_scope`, `question`, `sources[{id, heading_path, text}]`. `sources`, bu isteğin sürüm/kapsam görünümünden gelen en fazla 4 bölümdür; eski sürüm metni, korpusun geri kalanı, geçmiş, ortam değişkenleri veya kimlik gitmez. Her bölüm ve soru embedding modelinin 512 token sınırı içindedir; bağlam bu yüzden sınırlıdır.
- **Model çağrısı:** OpenAI Responses API, resmî Python SDK'sı, `responses.parse` ile katı JSON şeması (yapılandırılmış çıktı), `store=false`, `max_output_tokens=1000`, `reasoning.effort=low`, `temperature` yok. İstemci zaman aşımı `LLM_TIMEOUT_SECONDS`, otomatik retry yok. `OPENAI_BASE_URL` OpenRouter ise istek `provider: {only: ["openai"], allow_fallbacks: false, require_parameters: true}` ile OpenAI'ın kendi uç noktasına sabitlenir; bu alan api.openai.com'a hiç gönderilmez.
- **Model çıktısı:** `status` (`answered` | `partial` | `insufficient_evidence`), `claims[{text, source_chunk_ids}]`, `missing_topics[]`, `reason_code` (`not_in_documents` | `unsupported_scope` | `as_of_required` | `null`). Başlık, sürüm, tarih, skor veya alıntı alanı yoktur.
- **Sunucu doğrulaması** (`validate_answer`; ihlal varsa hiçbir şey silinip düzeltilmez, 502 `invalid_generation_output`):
  - her claim'in metni boş değil ve en az bir kaynak ID'si var;
  - her kaynak ID'si bu istekte modele verilen bölümlerden biri (korpusta olan ama bu istekte verilmeyen ID de reddedilir);
  - `missing_topics` öğeleri boş değil;
  - `answered`: claim var, `missing_topics` boş, `reason_code` null; `partial`: claim ve `missing_topics` var; `insufficient_evidence`: claim yok, `reason_code` dolu.
- **Cevabın kurulması** (`compose_answer`): `answered`/`partial` için claim metinleri sırayla; `insufficient_evidence` için `reason_code`'un standart açıklaması. `missing_topics` doluysa sona "Bu istekteki belgelerle yanıtlanamayan konular: …" cümlesi eklenir. `sources`, claim'lerin atıf yaptığı bölümlerdir (ilk atıf sırasıyla); başlık, sürüm, tarihler ve birebir alıntı yüklü korpustan gelir.
- **Sağlayıcı hataları** cevap değil hatadır; hiçbiri `insufficient_evidence` olmaz ve alıntı moduna düşülmez: zaman aşımı → `generation_timeout`; bağlantı hatası ve sağlayıcının her HTTP hatası (kimlik, kota/hız sınırı, model erişimi, yönlendirme reddi, 5xx) → `provider_unavailable`; JSON olmayan/kesilmiş/şemaya uymayan çıktı, `completed` olmayan yanıt (ör. `max_output_tokens`), model reddi (refusal) → `invalid_generation_output`.
- Kaynak ID doğrulaması anlamsal doğruluk garantisi değildir: verilen bölüme atıf yapan yanlış bir claim geçer (`tests/test_service.py::test_source_check_is_not_a_meaning_check`).

### Başarılı cevap

| Alan | Anlam |
|---|---|
| `request_id` | Log satırlarıyla eşleştirme anahtarı |
| `status` | `answered` \| `partial` \| `insufficient_evidence` \| `evidence_only` |
| `mode` | Uygulanan mod |
| `effective_as_of`, `effective_scope` | Sürüm seçiminde gerçekten kullanılan tarih ve kapsam |
| `answer` | Doğrulanmış claim'lerden sunucunun birleştirdiği Türkçe metin; `insufficient_evidence` için standart Türkçe açıklama; `evidence_only` için `null` |
| `claims[]` | `{text, source_chunk_ids[≥1]}` |
| `sources[]` | Yalnızca claim'lerin atıf yaptığı bölümler (kümeler birebir eşit) |
| `evidence[]` | Yalnızca `evidence_only` durumunda aday bölümler; cevabı desteklediği onaylanmış sayılmaz |
| `missing_topics[]` | Desteklenemeyen alt sorular |
| `reason_code` | `not_in_documents` \| `unsupported_scope` \| `as_of_required` \| `no_valid_version` \| `null` |
| `version_decisions[]` | Getirilen bölümlerin prosedürleri için, ilk görünme sırasıyla: `{procedure_id, selected, excluded[{…, reason}]}`; `selected`/`excluded` öğeleri `doc_id`, `version`, `valid_from`, `valid_to` taşır |
| `retrieved_chunk_ids[]` | Sürüm/kapsam filtresinden sonra sıralı top-k bölüm ID'leri; **skor yok** |

Kaynak/evidence nesnesi: `chunk_id`, `doc_id`, `document_title`, `version`, `section_id`, `heading_path[]`, `quote` (kayıtlı bölümün birebir metni; modelin yazdığı alıntı kullanılmaz), `valid_from`, `valid_to`.

### Durum değişmezleri (`app/contracts.py::AskResponse` tek tanım yeridir)

| Durum | Koşul |
|---|---|
| `answered` | ≥1 kaynaklı claim, `answer` dolu, `missing_topics` boş (üretimde ayrıca `reason_code` null) |
| `partial` | ≥1 kaynaklı claim, `answer` dolu, `missing_topics` dolu; `reason_code` opsiyonel |
| `insufficient_evidence` | claim/sources boş, `answer` Türkçe açıklama, `reason_code` dolu |
| `evidence_only` | yalnızca `mode=evidence_only`; claim/sources boş, `answer=null`, `evidence` dolu (aday yoksa `insufficient_evidence`) |

`mode=evidence_only` hiçbir zaman claim üretmez. Model durum/claim çelişkisi üretirse sunucu bunu düzeltip başarıya çevirmez; `invalid_generation_output` döner (kurallar: Üretim).

### Hata cevabı

`{"request_id": "...", "error": {"code": "...", "message": "..."}}`. `message` güvenli Türkçe metindir; ham exception, anahtar, dosya yolu veya kullanıcı sorusu içermez. .NET, Python'un hata gövdesini aktarmaz; HTTP durumunu ve mesajı Python'un durum kodundan değil `error.code`'dan, kendi tablosundan belirler. Python'un üretebileceği kodlar yalnızca tabloda "Python" yazanlardır; Python'dan gelen başka bir kod (`payload_too_large`, `upstream_*` veya bilinmeyen) ya da sözleşmeye uymayan gövde .NET'te 502 `upstream_invalid_response` olur.

| `error.code` | Üreten | HTTP | Ne zaman |
|---|---|---|---|
| `invalid_request` | .NET, Python | 400 | Şema/doğrulama hatası. Python'da FastAPI'nin varsayılan 422'si 400'e çevrilir; Python ayrıca token sınırını aşan soruyu bu kodla reddeder. .NET şemayı zaten denetlediği için Python'dan gelen `invalid_request`'i "soru veya kapsam sınırı aşıldı" mesajıyla döner |
| `payload_too_large` | .NET | 413 | Gövde 16 KiB'den büyük |
| `service_not_ready` | Python | 503 | İndeks veya embedding modeli hazır değil. Şu an üretilmez: Python her şeyi bağlantı kabul etmeden önce yükler (Readiness) |
| `generation_not_configured` | Python | 503 | `generative` istendi ama anahtar/yapılandırma yok (mock cevap yok, sessiz fallback yok) |
| `provider_unavailable` | Python | 503 | Sağlayıcıya bağlanılamadı veya sağlayıcı HTTP hatası döndü: kimlik doğrulama, kota, hız sınırı, model erişimi, OpenRouter yönlendirme reddi, 5xx |
| `generation_timeout` | Python | 504 | LLM çağrısı `LLM_TIMEOUT_SECONDS` içinde bitmedi |
| `upstream_timeout` | .NET | 504 | Python `RAG_TIMEOUT_SECONDS` içinde cevap vermedi |
| `upstream_unavailable` | .NET | 503 | Python'a bağlanılamadı |
| `invalid_generation_output` | Python | 502 | Model çıktısı şemaya/değişmezlere uymuyor, uydurma veya istekte verilmemiş kaynak ID'si, kaynaksız claim, model reddi (refusal) |
| `upstream_invalid_response` | .NET | 502 | Python cevabı sözleşmeye uymuyor |
| `internal_error` | .NET, Python | 500 | Beklenmeyen hata (ayrıntı yalnızca logda) |

### Readiness

`GET /health/ready` → hazırsa 200, değilse 503; gövde her iki durumda aynı şekilde:
`status` (`ready`|`not_ready`), `checks` (`corpus_index`, `embedding_model`), `run_metadata` (`app_mode`, `generation_configured`, `llm_model`, `embedding_model`, `embedding_revision`, `corpus_fingerprint`, `prompt_version`, `prompt_hash`, `top_k`, `min_retrieval_score`). Readiness hiçbir zaman ücretli LLM çağrısı yapmaz; `generation_configured=true` yalnızca anahtarla bir generator kurulduğunu söyler, anahtarın, kotanın veya model erişiminin çalıştığını kanıtlamaz. `llm_model` yapılandırılan model ID'sidir; sağlayıcının bildirdiği model her üretimin log satırındadır.

Python servisi ayarları, korpusu, embedding modelini ve indeksi bağlantı kabul etmeden önce yükler ve doğrular (`app/main.py::create_app`). Herhangi biri başarısız olursa süreç hata koduyla durur. Bu yüzden Python'un servis ettiği readiness her zaman `ready`'dir; yükleme sürerken (ilk model indirmesi dâhil) port kapalıdır ve .NET 503 `upstream_unavailable` döner. `not_ready` gövdesi sözleşmede durur ama Python şu an bunu üretmez. `corpus_fingerprint` yüklenen indeksin fingerprint'idir; `prompt_hash`, prompt dosyasının SHA-256 değeridir.

### Cevapta olmayan, logda olan

Skorlar, arama/üretim/toplam süreleri, prompt hash'i, model revision'ı ve corpus fingerprint'i her cevaba eklenmez; `request_id` ile loglarda bulunur. Çalışma bazındaki sabit metadata readiness'tan alınır. Loglarda ham soru, cevap, belge gövdesi, auth başlığı ve anahtar yer almaz.

Şu anki log satırları (düz metin; JSON log yapılandırması henüz yok):
- Python, her `/internal/ask` için: `request_id`, mod, sonuç, getirilen chunk ID'leri ve skorları, embedding ve arama süresi (ms), fingerprint'in ilk 12 karakteri. Reddedilen istekte `request_id` ve hata kodu; geçersiz istekte yalnızca hatalı alanların adları.
- Python, her üretim için ikinci bir satır: sonuç, atıf yapılan chunk ID'leri, `reason_code`, eksik konu sayısı, sağlayıcının bildirdiği model, prompt sürümü ve hash'in ilk 12 karakteri, üretim süresi, `input/output/reasoning` token sayıları. Hata durumunda hata kodu ve güvenli ayrıntı (HTTP durumu, sağlayıcı hata kodu, OpenRouter yönlendirme nedeni, şema hatası türü); sağlayıcının mesaj metni, soru ve model çıktısının metni loglanmaz.
- .NET, her Python çağrısı için: `request_id`, Python'un HTTP durumu, süre (ms); hata eşlemesinde eşlenen kod; sözleşmeye uymayan cevapta yalnızca JSON yolu.

### Fixture'lar

`tests/contracts/` altındaki dosyalar **sözleşme örnekleridir, gerçek değerlendirme çıktısı değildir.** Alıntı metinleri örnektir ve listeler okunabilirlik için kısaltılmıştır. Python (`app/contracts.py`) ve C# testleri her fixture'ı kayıpsız okuyup aynı JSON'a geri yazabilmelidir.

| Dosya | Model |
|---|---|
| `ask-request.json` | İstek |
| `ask-response-answered.json`, `-partial.json`, `-insufficient-evidence.json`, `-evidence-only.json` | Başarılı cevap (her durum için bir örnek) |
| `error-response.json` | Hata cevabı |
| `readiness-not-ready.json` | Readiness |

## 6. Yapılandırma

İsimler `.env.example`, kod ve README'de birebir aynıdır. Python: `APP_MODE` (`evidence_only` varsayılan | `generative`), `OPENAI_API_KEY` (baştaki/sondaki boşluk kırpılır), `OPENAI_BASE_URL` (http/https; boşsa `https://api.openai.com/v1`; OpenRouter: `https://openrouter.ai/api/v1`), `OPENAI_MODEL` (uç noktanın beklediği model ID'si; boşsa OpenAI'ın `gpt-6-luna`'sı, OpenRouter'da `openai/gpt-6-luna`; istek bir reasoning effort gönderdiği için reasoning modeli olmalıdır), `EMBEDDING_MODEL`, `EMBEDDING_REVISION` (tam 40 haneli commit hash'i; boşsa `614241f622f53c4eeff9890bdc4f31cfecc418b3`; kısa hash veya dal adı reddedilir), `KNOWLEDGE_DIR`, `INDEX_PATH`, `MODEL_CACHE_DIR`, `TOP_K` (1–20, varsayılan 4), `MIN_RETRIEVAL_SCORE` (boş = kapalı; −1..1), `LLM_TIMEOUT_SECONDS` (0–120, varsayılan 25). .NET: `RAG_SERVICE_URL` (mutlak http/https adresi; boşsa `http://rag:8000`; yol kısmı kullanılmaz) ve `RAG_TIMEOUT_SECONDS` (0 < x ≤ 300, ondalık olabilir; boşsa 45). .NET `.env` dosyasını okumaz; yerelde bu değişkenler kabuktan verilir. Readiness çağrısının 3 sn timeout'u sabittir. Geçersiz değer veya `APP_MODE=generative` + boş anahtar başlangıçta açık hata verir; hata mesajı değişken adını söyler, değerini asla yazmaz. Boş değer iki serviste de "verilmemiş" sayılır.

## 7. Değerlendirme beklentileri

- `eval/questions.jsonl`: 18 soru (E01–E18); her kayıtta `id`, `category`, `request`, `expected_status`, `required_facts`, `forbidden_facts`, `expected_source_ids`, `rubric`. Varsayılan kapsam TR/B2B/MH-10, `as_of=2026-10-04` (E16: `2026-06-01`). Ayrıca 4 geliştirme sorusu (`eval/dev_questions.jsonl`: `id`, `category`, `request`, `expected_source_ids`); eşik/bölümleme kararları önce onlarda denenir (`src/rag_service/measure_retrieval.py`).
- Runner dış .NET API'sini HTTP ile çağırır (timeout'lu); hatalı HTTP cevapları da gerçek çıktı olarak kaydedilir.
- Çıktı: `eval/results/<run_id>/actual.jsonl`, makinece okunur kontroller, Markdown karşılaştırma raporu. Run metadata: gerçek çalıştırma zamanı, commit SHA + dirty bayrağı, readiness'tan alınan `run_metadata`, soru sayısı.
- Ölçümler payda ve sayılarla: beklenen bölüm top-k'da mı, çok kaynaklı sorularda tüm gerekli bölümler, doğru sürüm, kaynak ID geçerliliği, beklenen durum, cevaplanabilir sorularda gereksiz ret, cevapsız sorularda uydurma. Tek bir başarı yüzdesi verilmez; metin eşitliği anlamsal doğruluk sayılmaz.
- İnsan inceleme sütunu `pending` başlar ve yalnızca gerçekten incelenen sorularda değişir. Hata kök nedeni: retrieval, versioning, generation, validation, infrastructure veya expected veri hatası.
- Anahtar/ağ/kota yoksa generation eval'ı `not_run`/`blocked` raporlanır. Bu kapsamda smoke + eval için toplam en fazla 25 generation çağrısı.

## 8. Kabul kontrol listesi

- [x] `data/knowledge/` tam 10 dosya, metadata doğrulaması geçiyor.
- [x] Sürüm seçimi sınır testleri (2026-06-30 / 2026-07-01 / 2026-10-04, taslak, withdrawn, gelecek sürüm, çakışma, bozuk supersedes) geçiyor.
- [x] Kapsam filtresi aramadan önce; DE isteğine TR fallback yok; eski belge daha yüksek skorlu olsa da kullanılmıyor (`retrieve` düzeyinde test edildi).
- [x] Stale indeks (metadata değişimi, silinen belge, model revision değişimi) servis edilmiyor.
- [x] Uydurma/istekte verilmemiş kaynak ID'si, kaynaksız claim ve tutarsız partial reddediliyor.
- [x] Alıntı modunda LLM hiç çağrılmıyor; generative istek anahtarsız 503 dönüyor.
- [x] .NET: istek doğrulama, giden JSON + request ID, 400/413/503/504/502 eşlemesi, timeout/iptal, readiness testleri geçiyor.
- [x] Python ve C# fixture round-trip testleri geçiyor.
- [ ] `pytest`, `ruff check`, `ruff format --check`, `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes` gerçekten çalıştırıldı.
- [ ] `docker compose up --build` ile anahtarsız alıntı modu çalışıyor.
- [ ] Eval .NET üzerinden gerçekten koşuldu; sonuçlar ve metadata kayıtlı; insan incelemesi `pending`.
- [ ] `.env`, anahtar, model ağırlığı, indeks ve build çıktısı Git'te yok.
- [ ] README komutları, ortam değişkenleri ve örnekler implementasyonla aynı; temiz kopyada denendi.
