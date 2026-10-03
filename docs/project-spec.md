# Proje spesifikasyonu

Kurgu bir şirketin destek çalışanına, onaylı bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur API. Genel amaçlı chatbot, işlem platformu veya üretime hazır sistem değildir. Kararların gerekçeleri `docs/judgment.md` içindedir; burada yalnızca davranış ve sözleşme yer alır.

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
| R10 | Teknik tercihler, gerekçeler, bilinen sınırlar | `docs/judgment.md` |
| R11 | API anahtarının kodda ve Git geçmişinde olmaması | `.gitignore`, `.env.example` boş anahtar, commit öncesi tarama |

İşveren .NET ve FastAPI'yi **önermiştir**; ikisi de zorunlu değildir. Arayüz ve çok ajanlı yapı istenmemiştir.

**Bizim tercihlerimiz (zorunlu değil):** .NET + FastAPI iki servis; 18 soruluk eval ve 4 geliştirme sorusu; alıntı modu (`evidence_only`); readiness/loglama/timeout gibi işletim ayrıntıları; Docker Compose; `retrieved_chunk_ids` ile dış API üzerinden retrieval ölçümü.

## 2. Korpus

Şirket: **Yardım bende Destek Teknolojileri** (tamamen hayalî). Tüm süreler ve koşullar demo kurgusudur. Her belgenin kapsamı `country=TR`, `customer_type=B2B`, `product=MH-10`. Belge başına yaklaşık 120–250 kelime.

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

- Frontmatter (YAML, güvenli parser): `doc_id`, `procedure_id`, `title`, `version` (string), `valid_from`, `valid_to` (null olabilir), `status` (`approved` | `draft` | `withdrawn`), `scope` (`country`, `customer_type`, `product`), `supersedes` (null veya doc_id).
- Bölüm ID'si başlıkta açıkça yazılır: `## İade süresi {#sure}`. ID `[a-z0-9-]+`; başlıktan otomatik transliterasyon yapılmaz. Kesin sözdizimi aşama 2'de loader testleriyle sabitlenir.
- Bölüm alanları: `chunk_id` (`D04#sure` biçiminde, belge + bölüm ID'si), `doc_id`, `section_id`, `heading_path` (belge başlığı → bölüm başlığı), `content`, `content_hash`.
- Bir kuralın koşulu/istisnası ayrı bölüme bölünmez. Başlık yolu embedding girdisine ve kaynak gösterimine taşınır. Tokenizer sınırını (önek ve özel tokenlar dâhil) aşan bölüm sessizce kesilmez; açıklayıcı yükleme hatası verir.
- Yalnızca `data/knowledge/` altındaki beklenen `.md` dosyaları okunur; dizin dışına çıkan yol veya symlink reddedilir.
- Yüklemede reddedilenler: eksik/zıt metadata, duplicate belge veya bölüm ID'si, boş içerik, geçersiz tarih aralığı, bilinmeyen status, var olmayan ya da farklı prosedür/kapsama işaret eden `supersedes`, döngüsel supersedes zinciri, onaylı sürümlerde tarih çakışması.
- Markdown tek doğruluk kaynağıdır; SQLite indeks türetilmiştir. Fingerprint: belge içeriği + metadata + bölümleme sürümü + embedding model/revision + ön işleme ayarları. Uyuşmazlıkta servis hazır olmadan indeksi atomik olarak yeniden üretir; yarım indeks servis edilmez. Embedding'ler pickle olmadan saklanır; boyut uyuşmazlığı, sıfır norm ve NaN reddedilir.

## 4. Sürüm seçimi

1. İstek kapsamı ve etkin `as_of` bir kez çözülür (`as_of` yoksa Europe/Istanbul'a göre bugün; saat enjekte edilebilir).
2. Yalnızca kapsama tam uyan belgeler; kapsamlar arası fallback yok.
3. `approved` olmayanlar elenir.
4. `valid_from <= as_of` ve (`valid_to` null veya `as_of < valid_to`). Başlangıç dâhil, bitiş hariç.
5. Her `(procedure_id, scope)` için en fazla bir geçerli sürüm; birden fazlası korpus hatasıdır (dosya sırası, sürüm numarası veya LLM ile çözülmez).
6. Arama yalnızca bu geçerli belge kümesinde yapılır.

Beklenen sınırlar: 2026-06-30 → D03; 2026-07-01 ve 2026-10-04 → D04. Geçerli sürüm olmayan tarihte başka tarihli belge seçilmez. Yeni onaylı v3 eklenirken önceki sürümün `valid_to` değeri v3'ün `valid_from` değerine çekilmelidir; açık uçlu önceki sürümle örtüşen v3 reddedilir. `supersedes` açıklayıcıdır, geçerlilik kurallarını geçersiz kılmaz.

Dışlama nedenleri: `expired`, `future_effective`, `not_approved`, `scope_mismatch`. Serbest metinden tarih çıkarılmaz; soru başka bir tarihi soruyor ama istek o tarihe ayarlı değilse cevap `as_of_required` ile bunu belirtir.

## 5. API sözleşmesi

### Uçlar

| Servis | Uç | Açıklama |
|---|---|---|
| .NET (dış, `127.0.0.1:8080`) | `POST /api/ask` | Soru sorma |
| .NET | `GET /health/live` | Süreç çalışıyor mu: `{"status":"live"}` |
| .NET | `GET /health/ready` | Python readiness'ının kısa timeout ile alınan tipli kopyası (ham gövde aktarılmaz) |
| Python (iç, `rag:8000`, host'a port açılmaz) | `POST /internal/ask`, `GET /health/live`, `GET /health/ready` | Aynı gövde şekilleri |

JSON alanları snake_case; tarihler `YYYY-MM-DD`; boş değerler `null` veya `[]` olarak her zaman yazılır (alan atlanmaz).

### İstek

| Alan | Kural |
|---|---|
| `question` | Zorunlu. Trim sonrası boş olamaz, en fazla 2000 karakter. |
| `as_of` | Opsiyonel, yalnızca `YYYY-MM-DD`. Boşsa Europe/Istanbul'a göre bugün. |
| `scope` | Opsiyonel; verilirse `country`, `customer_type`, `product` üçü de zorunlu. Varsayılan `TR` / `B2B` / `MH-10`. Desteklenmeyen kapsam 400 değil, `insufficient_evidence` + `unsupported_scope` üretir. Scope filtresi yetkilendirme değildir. |
| `mode` | Opsiyonel: `generative` veya `evidence_only`; boşsa `APP_MODE`. |

Tanınmayan alan veya enum değeri 400 ile reddedilir. HTTP gövde sınırı 16 KiB (aşılırsa 413). Request ID `X-Request-ID` başlığıyla gelir; `^[A-Za-z0-9._-]{1,64}$` değilse veya yoksa .NET yenisini üretir ve Python'a aynı başlıkla taşır.

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
| `answered` | ≥1 kaynaklı claim, `answer` dolu, `missing_topics` boş |
| `partial` | ≥1 kaynaklı claim, `answer` dolu, `missing_topics` dolu |
| `insufficient_evidence` | claim/sources boş, `answer` Türkçe açıklama, `reason_code` dolu |
| `evidence_only` | yalnızca `mode=evidence_only`; claim/sources boş, `answer=null`, `evidence` dolu (aday yoksa `insufficient_evidence`) |

`mode=evidence_only` hiçbir zaman claim üretmez. Model durum/claim çelişkisi üretirse sunucu bunu düzeltip başarıya çevirmez; `invalid_generation_output` döner.

### Hata cevabı

`{"request_id": "...", "error": {"code": "...", "message": "..."}}`. `message` güvenli Türkçe metindir; ham exception, anahtar, dosya yolu veya kullanıcı sorusu içermez. .NET, Python'un hata gövdesini aktarmaz; bilinen kodu kendi mesajıyla eşler, bilinmeyen kodu `upstream_invalid_response` sayar.

| `error.code` | Üreten | HTTP | Ne zaman |
|---|---|---|---|
| `invalid_request` | .NET, Python | 400 | Şema/doğrulama hatası (Python'da FastAPI'nin varsayılan 422'si de 400'e çevrilir) |
| `payload_too_large` | .NET | 413 | Gövde 16 KiB'den büyük |
| `service_not_ready` | Python | 503 | İndeks veya embedding modeli hazır değil |
| `generation_not_configured` | Python | 503 | `generative` istendi ama anahtar/yapılandırma yok (mock cevap yok, sessiz fallback yok) |
| `provider_unavailable` | Python | 503 | Sağlayıcı isteği reddetti: kimlik doğrulama, kota, hız sınırı, model erişimi, ağ |
| `generation_timeout` | Python | 504 | LLM çağrısı `LLM_TIMEOUT_SECONDS` içinde bitmedi |
| `upstream_timeout` | .NET | 504 | Python `RAG_TIMEOUT_SECONDS` içinde cevap vermedi |
| `upstream_unavailable` | .NET | 503 | Python'a bağlanılamadı |
| `invalid_generation_output` | Python | 502 | Model çıktısı şemaya/değişmezlere uymuyor, uydurma veya istekte verilmemiş kaynak ID'si, kaynaksız claim, model reddi (refusal) |
| `upstream_invalid_response` | .NET | 502 | Python cevabı sözleşmeye uymuyor |
| `internal_error` | .NET, Python | 500 | Beklenmeyen hata (ayrıntı yalnızca logda) |

### Readiness

`GET /health/ready` → hazırsa 200, değilse 503; gövde her iki durumda aynı şekilde:
`status` (`ready`|`not_ready`), `checks` (`corpus_index`, `embedding_model`), `run_metadata` (`app_mode`, `generation_configured`, `llm_model`, `embedding_model`, `embedding_revision`, `corpus_fingerprint`, `prompt_hash`, `top_k`, `min_retrieval_score`). Readiness hiçbir zaman ücretli LLM çağrısı yapmaz; `generation_configured=true` yalnızca anahtarın tanımlı olduğunu söyler, kotanın kullanılabilir olduğunu kanıtlamaz.

### Cevapta olmayan, logda olan

Skorlar, arama/üretim/toplam süreleri, prompt hash'i, model revision'ı ve corpus fingerprint'i her cevaba eklenmez; `request_id` ile JSON loglarında bulunur. Çalışma bazındaki sabit metadata readiness'tan alınır. Loglarda ham soru, cevap, belge gövdesi, auth başlığı ve anahtar yer almaz.

### Fixture'lar

`tests/contracts/` altındaki dosyalar **sözleşme örnekleridir, gerçek değerlendirme çıktısı değildir.** Alıntı metinleri örnektir ve listeler okunabilirlik için kısaltılmıştır. Python (`app/contracts.py`) ve C# testleri her fixture'ı kayıpsız okuyup aynı JSON'a geri yazabilmelidir.

| Dosya | Model |
|---|---|
| `ask-request.json` | İstek |
| `ask-response-answered.json`, `-partial.json`, `-insufficient-evidence.json`, `-evidence-only.json` | Başarılı cevap (her durum için bir örnek) |
| `error-response.json` | Hata cevabı |
| `readiness-not-ready.json` | Readiness |

## 6. Yapılandırma

İsimler `.env.example`, kod ve README'de birebir aynıdır. Python: `APP_MODE` (`evidence_only` varsayılan | `generative`), `OPENAI_API_KEY`, `OPENAI_MODEL`, `EMBEDDING_MODEL`, embedding revision (aşama 3'te doğrulanmış gerçek değerle eklenecek), `KNOWLEDGE_DIR`, `INDEX_PATH`, `MODEL_CACHE_DIR`, `TOP_K` (1–20, varsayılan 4), `MIN_RETRIEVAL_SCORE` (boş = kapalı; −1..1), `LLM_TIMEOUT_SECONDS` (0–120, varsayılan 25). .NET: `RAG_SERVICE_URL`, `RAG_TIMEOUT_SECONDS` (varsayılan 45). Geçersiz değer veya `APP_MODE=generative` + boş anahtar başlangıçta açık hata verir; hata mesajı değişken adını söyler, değerini asla yazmaz.

## 7. Değerlendirme beklentileri

- `eval/questions.jsonl`: 18 soru (E01–E18); her kayıtta `id`, `category`, `request`, `expected_status`, `required_facts`, `forbidden_facts`, `expected_source_ids`, `rubric`. Varsayılan kapsam TR/B2B/MH-10, `as_of=2026-10-04` (E16: `2026-06-01`). Ayrıca 4 geliştirme sorusu; eşik/bölümleme kararları önce onlarda denenir.
- Runner dış .NET API'sini HTTP ile çağırır (timeout'lu); hatalı HTTP cevapları da gerçek çıktı olarak kaydedilir.
- Çıktı: `eval/results/<run_id>/actual.jsonl`, makinece okunur kontroller, Markdown karşılaştırma raporu. Run metadata: gerçek çalıştırma zamanı, commit SHA + dirty bayrağı, readiness'tan alınan `run_metadata`, soru sayısı.
- Ölçümler payda ve sayılarla: beklenen bölüm top-k'da mı, çok kaynaklı sorularda tüm gerekli bölümler, doğru sürüm, kaynak ID geçerliliği, beklenen durum, cevaplanabilir sorularda gereksiz ret, cevapsız sorularda uydurma. Tek bir başarı yüzdesi verilmez; metin eşitliği anlamsal doğruluk sayılmaz.
- İnsan inceleme sütunu `pending` başlar ve yalnızca gerçekten incelenen sorularda değişir. Hata kök nedeni: retrieval, versioning, generation, validation, infrastructure veya expected veri hatası.
- Anahtar/ağ/kota yoksa generation eval'ı `not_run`/`blocked` raporlanır. Bu kapsamda smoke + eval için toplam en fazla 25 generation çağrısı.

## 8. Kabul kontrol listesi

- [ ] `data/knowledge/` tam 10 dosya, metadata doğrulaması geçiyor.
- [ ] Sürüm seçimi sınır testleri (2026-06-30 / 2026-07-01 / 2026-10-04, taslak, withdrawn, gelecek sürüm, çakışma, bozuk supersedes) geçiyor.
- [ ] Kapsam filtresi aramadan önce; DE isteğine TR fallback yok; eski belge daha yüksek skorlu olsa da kullanılmıyor.
- [ ] Stale indeks (metadata değişimi, silinen belge, model revision değişimi) servis edilmiyor.
- [ ] Uydurma/istekte verilmemiş kaynak ID'si, kaynaksız claim ve tutarsız partial reddediliyor.
- [ ] Alıntı modunda LLM hiç çağrılmıyor; generative istek anahtarsız 503 dönüyor.
- [ ] .NET: istek doğrulama, giden JSON + request ID, 400/413/503/504/502 eşlemesi, timeout/iptal, readiness testleri geçiyor.
- [ ] Python ve C# fixture round-trip testleri geçiyor.
- [ ] `pytest`, `ruff check`, `ruff format --check`, `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes` gerçekten çalıştırıldı.
- [ ] `docker compose up --build` ile anahtarsız alıntı modu çalışıyor.
- [ ] Eval .NET üzerinden gerçekten koşuldu; sonuçlar ve metadata kayıtlı; insan incelemesi `pending`.
- [ ] `.env`, anahtar, model ağırlığı, indeks ve build çıktısı Git'te yok.
- [ ] README komutları, ortam değişkenleri ve örnekler implementasyonla aynı; temiz kopyada denendi.
