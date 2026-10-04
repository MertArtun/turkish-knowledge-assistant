# ai-knowledge-assistant

Kurgu şirket **Yardım bende Destek Teknolojileri**'nin destek çalışanına, onaylı ve sürümlü bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur bir API. Cevapta kullanılan belge ve bölüm gösterilir, eski sürümün neden dışlandığı açıklanır; belge desteği yetersizse cevap uydurulmaz.

> Tamamen kurgu verilerle hazırlanmış değerlendirme demosudur. Üretim güvenliği veya KVKK/BDDK uyumu iddia edilmez.

**Durum:** İki mod da uçtan uca çalışıyor ve Docker Compose ile birlikte ayağa kalkıyor. Alıntı modu (`evidence_only`) anahtarsız çalışır ve model çağırmaz. Üretken mod (kaynaklı LLM cevabı ve sunucu tarafı kaynak doğrulaması) varsayılan testlerde sahte model/HTTP katmanıyla, canlı olarak da 18 soruluk değerlendirmenin bir üretken koşusuyla denendi. O koşuda 18 sorunun 14'ü beklenen durumu verdi; üç soruda (E15, E16, E18) beklenen bölüm arama sonucunun ilk 4'ünde değildi. Otomatik kontrollerin sonuçları: [`docs/decisions.md`](docs/decisions.md), "Değerlendirme bulguları". Kök neden analizi ve insan incelemesi henüz yapılmadı.

## Mimari akış

```text
istemci ──HTTP──▶ .NET API (127.0.0.1:8080)      istek doğrulama, request ID, timeout, hata eşleme
                     │ POST /internal/ask
                     ▼
                 Python RAG servisi (rag:8000, dışarı kapalı)
                     1. as_of ve kapsam → geçerli belge sürümleri (aramadan önce)
                     2. yerel embedding (E5, CPU) → yalnızca bu sürümlerde tam arama, ilk TOP_K (varsayılan 4)
                     3a. evidence_only: aday bölümler, cevap yok
                     3b. generative: getirilen TOP_K bölüm → LLM → kaynak doğrulama → sunucunun kurduğu cevap
```

Belgeler `data/knowledge/` altındaki 10 Markdown dosyasıdır (tek doğruluk kaynağı); embedding indeksi bunlardan türetilen bir SQLite dosyasıdır (`INDEX_PATH`). Embedding modeli `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3`'e sabittir (`EMBEDDING_REVISION`) ve ONNX Runtime ile CPU'da çalışır; GPU gerekmez. Kararların gerekçeleri: [`docs/decisions.md`](docs/decisions.md).

## Docker Compose ile çalıştırma (anahtarsız)

Önkoşullar: Docker Engine 25 veya üstü (sağlık kontrolündeki `start_interval` için) ve Docker Compose v2. Denenen ortam: Docker 29.1.3, Compose v2.40.3, macOS arm64. Python, uv veya .NET kurulu olması gerekmez.

**İlk başlangıç internet ister.** Embedding modeli ve tokenizer (toplam yaklaşık 490 MB) `rag-models` volume'üne iner, sonra indeks üretilir; servis ancak bundan sonra hazır olur (denenen makinede yarım dakikanın altında). Önbellek dolduktan sonraki başlangıçlar modeli ağsız yükler. Sıfırdan, internetsiz kurulum desteklenmez.

```bash
cp .env.example .env                  # isteğe bağlı; anahtarsız varsayılanlarla da çalışır
docker compose up --build -d --wait   # rag sağlıklı olana kadar bekler, sonra api başlar
curl -s http://127.0.0.1:8080/health/ready
curl -s http://127.0.0.1:8080/api/ask -H 'Content-Type: application/json' \
  -d '{"question": "İade kargosunu kim ödüyor?", "as_of": "2026-10-04"}'
docker compose logs rag api           # her satır bir JSON nesnesi
docker compose down                   # volume'ler (indeks ve model) korunur
```

Proje yolunda ASCII olmayan bir karakter varsa (ör. `ı`) derleme komutunu `COMPOSE_BAKE=false docker compose up --build -d --wait` olarak çalıştırın (Sorun giderme).

- Host'a yalnızca .NET API açılır: `127.0.0.1:8080`. Python servisi (`rag:8000`) port yayımlamaz; yalnızca Compose ağından erişilir. Model indirmesi ve LLM sağlayıcısı için dış bağlantısı açıktır.
- `data/knowledge` salt okunur bağlanır. İndeks (`rag-index`) ve model önbelleği (`rag-models`) ayrı volume'lerdedir. İki konteyner de root olmayan kullanıcıyla çalışır.
- **Anahtarsız başlatma:** `.env` yoksa veya `OPENAI_API_KEY` boşsa servis alıntı modunda çalışır. `"mode": "generative"` isteği 503 `generation_not_configured` döner; alıntı moduna sessizce düşülmez.
- `docker compose config` ve `docker inspect` çıktıları `.env`'deki anahtarı açık metin gösterir. Bu çıktıları paylaşmayın.

## Üretken mod (LLM ile kaynaklı cevap)

`"mode": "generative"` isteğinde sürüm görünümünden getirilen `TOP_K` bölüm (varsayılan 4, en fazla 8), soru, etkin tarih ve kapsamla birlikte dil modeline gider. Model yalnızca kısa iddialar (claim) ve her biri için bölüm ID'leri döndürür. Sunucu her ID'nin bu istekte verilen bölümlerden biri olduğunu ve durumun iddialarla tutarlı olduğunu denetler, cevabı ve birebir alıntıları kendisi kurar. Kurallara uymayan çıktı düzeltilmez, 502 `invalid_generation_output` olur. Sağlayıcı hataları 503 `provider_unavailable` veya 504 `generation_timeout` döner; hiçbiri "belgede bilgi yok" sayılmaz ve alıntı moduna düşülmez. Kurallar: [`docs/project-spec.md`](docs/project-spec.md) §5 "Üretim".

Açmak için `.env`'e anahtarı yazın ve stack'i yeniden başlatın (`docker compose up -d --wait`; değişen ortam rag konteynerini yeniden oluşturur). Anahtar yalnızca rag konteynerine verilir.

- `OPENAI_API_KEY`: sağlayıcı anahtarı. Değerlendirme kurulumunda bu bir OpenRouter anahtarıdır.
- `OPENAI_BASE_URL`: boşsa `https://api.openai.com/v1`; OpenRouter için `https://openrouter.ai/api/v1` (`.env.example`'daki değer). OpenRouter'da istek OpenAI'ın kendi uç noktasına sabitlenir, başka bir sağlayıcıya sessizce geçmez.
- `OPENAI_MODEL`: OpenAI'da `gpt-6-luna` (kod varsayılanı), OpenRouter'da `openai/gpt-6-luna` (`.env.example`'daki değer).
- `APP_MODE=generative`, `mode` alanı verilmeyen istekleri de üretken moda alır; bu durumda anahtar zorunludur, yoksa servis başlamaz.

OpenRouter ek bir aracıdır ve kendi veri politikası vardır. İstek `store=false` ile gönderilir, ancak bu OpenRouter'ın veya OpenAI'ın kendi saklama politikalarını ortadan kaldırmaz. Modele yalnızca soru, etkin tarih/kapsam ve seçilen bölümler gider; korpusun geri kalanı, eski sürümler, kimlik veya ortam bilgisi gitmez.

Her model çağrısı ücretlidir. Readiness modeli hiç çağırmaz; `generation_configured=true` yalnızca anahtarla bir istemci kurulduğunu gösterir, anahtarın veya kotanın çalıştığını kanıtlamaz.

## İstekler ve cevap durumları

İstek alanları: `question` (zorunlu, en fazla 2000 karakter), `as_of` (`YYYY-MM-DD`; boşsa Europe/Istanbul'a göre bugün), `scope` (boşsa `TR`/`B2B`/`MH-10`), `mode` (`generative` | `evidence_only`; boşsa `APP_MODE`). Bilinmeyen alan veya enum değeri 400'dür. `X-Request-ID` başlığı isteğe bağlıdır; verilmezse API üretir, cevapta ve iki servisin logunda aynı değer görünür.

Örnekler (güncel sürüm, tarihsel `as_of`, varsayılanlar, desteklenmeyen kapsam, üretken mod, geçersiz enum): [`examples/requests.http`](examples/requests.http). Tarihsel sorgu örneği:

```bash
curl -s http://127.0.0.1:8080/api/ask -H 'Content-Type: application/json' \
  -d '{"question": "1 Haziran 2026'"'"'da iade süresi neydi?", "as_of": "2026-06-01"}'
# version_decisions: returns → D03 seçildi, D04 "future_effective"
```

| `status` (HTTP 200) | Anlamı |
|---|---|
| `answered` | Her iddia en az bir kaynağa dayanıyor; eksik konu yok. |
| `partial` | Kaynaklı iddialar var, ayrıca `missing_topics` belgelerle yanıtlanamayan kısmı söylüyor. |
| `insufficient_evidence` | İddia ve kaynak yok; `answer` nedeni açıklar, `reason_code` makinece verir (`not_in_documents`, `unsupported_scope`, `no_valid_version`, `as_of_required`). |
| `evidence_only` | Alıntı modu: `evidence` aday bölümlerdir (birebir alıntı, belge, sürüm, geçerlilik tarihleri), `answer` `null`'dır. Adaylar sorunun cevabı olduğu iddiasını taşımaz; eşik kapalı olduğu için cevapsız sorularda da aday döner. |

Her başarılı cevapta `version_decisions` hangi sürümün seçildiğini ve hangisinin neden dışlandığını, `retrieved_chunk_ids` sıralı ilk `TOP_K` (varsayılan 4) bölümü gösterir (skor yok; skorlar logda). Hatalar `{"request_id", "error": {"code", "message"}}` biçimindedir: 400 `invalid_request`, 413 `payload_too_large` (16 KiB), 503 `generation_not_configured` / `provider_unavailable` / `upstream_unavailable`, 504 `generation_timeout` / `upstream_timeout`, 502 `invalid_generation_output` / `upstream_invalid_response`, 500 `internal_error`. Tam sözleşme: [`docs/project-spec.md`](docs/project-spec.md) §5.

## Yerelde çalıştırma (Docker olmadan)

Önkoşullar: [uv](https://docs.astral.sh/uv/) (Python 3.12'yi kendisi kurar), .NET SDK 10 (`global.json`: 10.0.102 ve sonraki yamalar), ilk çalıştırmada internet (model indirmesi `var/models/` altına).

1. Python RAG servisi, `src/rag_service` içinden:

   ```bash
   uv sync
   uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --log-config log_config.json
   ```

   Servis korpusu doğrular, embedding modelini ve indeksi yükler, ancak ondan sonra bağlantı kabul eder. Korpus, model veya indeks kullanılamazsa süreç hata vererek durur. Ayarlar ortam değişkenlerinden okunur (isimler ve varsayılanlar `.env.example`'da); servis `.env` dosyasını kendiliğinden okumaz. Varsayılanlarla alıntı modunda ve anahtarsız çalışır. `--log-config log_config.json` bütün logu JSON olarak yazar; verilmezse uvicorn'un varsayılan ayarı uygulamanın `app.*` satırlarını göstermez. Üretken mod için anahtarı uv'ye okutun: `uv run --env-file ../../.env uvicorn …` (aynı seçeneklerle).

2. .NET API, ayrı bir terminalde repo kökünden:

   ```bash
   RAG_SERVICE_URL=http://127.0.0.1:8000 dotnet run --project src/SupportAssistant.Api
   ```

   API `http://127.0.0.1:8080` adresinde dinler ve JSON log yazar. .NET de `.env` okumaz; `RAG_SERVICE_URL` verilmezse Compose'daki servis adı `http://rag:8000` kullanılır.

3. İstekler yukarıdaki `curl` komutlarıyla veya `examples/requests.http` ile gönderilir.

## Testler

Python (`src/rag_service` içinden):

```bash
uv run pytest                          # ağsız; sahte embedding ve sahte model ile birim ve API testleri
uv run pytest -m model                 # gerçek model testleri (ilk seferde modeli indirir)
uv run python measure_retrieval.py     # geliştirme sorularının sıralaması ve ham skorları
uv run ruff check . && uv run ruff format --check .
```

Canlı üretim smoke testi; varsayılan testlerin parçası değildir, anahtar ister ve tam iki ücretli model çağrısı yapar (iki geliştirme sorusu):

```bash
uv run --env-file ../../.env python smoke_generation.py
```

.NET (repo kökünden):

```bash
dotnet build
dotnet test                            # Python servisi gerekmez; sahte HTTP handler kullanılır
dotnet format --verify-no-changes
```

## Değerlendirme

18 soruluk küçük, görülebilir bir regresyon setidir (`eval/questions.jsonl`): normal, sürüm çelişkisi, cevapsız, kısmi, tarihsel sürüm, yanlış ön kabul ve çok kaynaklı sorular. Genellenebilir bir benchmark değildir. Runner (`eval/run_eval.py`) dış .NET API'sini HTTP ile çağırır ve yalnızca Python standart kütüphanesini kullanır (Python 3.12 ve 3.14 ile denendi). Kontrollerin tanımı: [`docs/project-spec.md`](docs/project-spec.md) §7.

Repo kökünden, stack çalışırken (yukarıdaki `docker compose up --build -d --wait`):

```bash
python3 -m unittest discover -s eval -v                  # runner'ın kendi testleri; stack gerekmez
python3 eval/run_eval.py --mode evidence_only            # model çağrısı yok
python3 eval/run_eval.py --mode generative               # anahtar gerekir; soru başına bir ücretli model çağrısı
# İsteğe bağlı: koşunun servis log satırları (skorlar, süreler, token sayıları)
docker compose logs --no-log-prefix rag | grep '"eval\.<run_id>\.' > eval/results/<run_id>/rag-log.jsonl
```

Her koşu `eval/results/<run_id>/` altına `actual.jsonl` (her HTTP cevabı, hatalar dâhil), `checks.json` (koşu bilgileri ve kontroller) ve `report.md` (beklenen ve gerçek karşılaştırması) yazar. `generative` koşu, stack'te anahtar yoksa hiç istek göndermeden durur. `docker compose logs` yalnızca çalışan konteynerlerin logunu gösterir; log satırları konteyner yeniden oluşturulmadan önce alınmalıdır.

Commit edilen koşular: alıntı modu ve üretken mod, her biri bir kez ([`docs/decisions.md`](docs/decisions.md), "Değerlendirme bulguları"; her sorunun beklenen ve gerçek çıktısı ilgili `report.md`'de). Üretken koşu canlı modelle bir kez yapıldı; tekrarlanmadı.

## Belgeler değişince yeniden indeksleme

- Belge veya metadata değişince `docker compose restart rag` yeterlidir. Servis açılışta fingerprint'i karşılaştırır, uyuşmazsa indeksi yeniden üretir ve ancak ondan sonra hazır olur. Logda `rebuilding index …` ve `built index …` görünür; değişiklik yoksa `reusing index …: fingerprint … matches`. Yeniden başlama süresince API 503 `upstream_unavailable` döner. Yeni fingerprint `/health/ready` → `run_metadata.corpus_fingerprint`'te görünür.
- Korpus geçersizse (ör. çakışan iki onaylı sürüm) rag başlamaz; neden `docker compose logs rag`'de `CorpusError` olarak yazar.
- **Yeni sürüm eklemek** (ör. iade prosedürünün v3'ü): önceki sürümün `valid_to` değerini yeni sürümün `valid_from` tarihine çekin, yeni dosyayı `NN-slug.md` adıyla ekleyin (`supersedes` önceki belge), sonra `docker compose restart rag`. O tarihten önceki `as_of` değerleri eski sürümü, sonrakiler yenisini seçer. Kural: [`docs/project-spec.md`](docs/project-spec.md) §4.
- İndeksi sıfırdan üretmek için: `docker compose down && docker volume rm ai-knowledge-assistant_rag-index && docker compose up -d --wait`.
- Docker olmadan, Python servisini yeniden başlatmak yeterlidir. `var/index.sqlite3` dosyasını silmek de güvenlidir.

## Sorun giderme

| Belirti | Neden / çözüm |
|---|---|
| `docker compose build`: `header key "x-docker-expose-session-sharedkey" contains value with non-printable ASCII characters` | Proje yolunda ASCII olmayan bir karakter var (ör. `ı`), Compose'un bake derlemesi bunu kabul etmiyor. `COMPOSE_BAKE=false docker compose up --build -d --wait` kullanın veya repoyu ASCII bir yola kopyalayın. |
| `--wait` uzun sürüyor, rag `health: starting` | İlk başlangıçta model iniyor: `docker compose logs -f rag`. Sağlık kontrolü ilk 10 dakikadaki başarısızlıkları saymaz; sonra üç başarısız denemede konteyner `unhealthy` olur ve `--wait` hata verir. İlk başlangıç internetsiz başarısız olur. |
| rag konteyneri duruyor (`exited`) | `docker compose logs rag`: yapılandırma veya korpus hatası (`ConfigError`, `CorpusError`) düz metin Python traceback'i olarak görünür; mesaj değişkeni veya dosyayı söyler, anahtarın değerini yazmaz. Örnek: `APP_MODE=generative` ama anahtar boş. |
| `/health/ready` → 503 `upstream_unavailable` | Python servisi dinlemiyor: yükleniyor, yeniden başlıyor veya durmuş. rag durduktan hemen sonraki ilk çağrı ad çözümlemesi yüzünden 504 `upstream_timeout` da dönebilir; `docker compose ps` ile bakın. |
| Üretken istek → 503 `provider_unavailable` / 504 `generation_timeout` | Sağlayıcı hatası; "belgede bilgi yok" değildir. Aynı `request_id` ile rag logundaki `generation` satırının `detail` alanına bakın: HTTP durumu, sağlayıcı kodu, OpenRouter yönlendirme nedeni. |
| Gövdesiz `400 Bad Request` | Kestrel HTTP isteğini uygulamaya ulaşmadan reddetti; örneğin bir başlık değeri ASCII olmayan karakter içeriyor (`X-Request-ID` yalnızca `A-Z a-z 0-9 . _ -` kabul eder). |
| `127.0.0.1:8080` başka bir süreçte | `lsof -nP -iTCP:8080 -sTCP:LISTEN` ile bulun ve durdurun. Docker olmadan çalışan `dotnet run` da aynı portu kullanır. |
| Logda JSON olmayan `Warning: You are sending unauthenticated requests to the HF Hub` | Hugging Face kütüphanesi bu uyarıyı kendi handler'ıyla bir kez daha düz metin olarak yazar. Yalnızca model indirilirken görülür, zararsızdır. |

## Sınırlar

- Kaynak doğrulaması anlamsal değildir: doğru bölüme atıf yapan yanlış bir sayı geçebilir. Bunu yalnızca değerlendirme ve insan incelemesi yakalar.
- Skor eşiği kapalıdır. Değerlendirmede üç soruda (E15, E16, E18) beklenen bölüm ilk 4'te değildi; nedeni henüz incelenmedi.
- Tarihsel cevap için `as_of` istekte verilmelidir; sorudaki tarih okunmaz.
- Kimlik doğrulama, belge bazlı yetkilendirme, TLS, saklama politikası ve yük testi yoktur; kapsam filtresi yetkilendirme değildir.
- Canlı üretim tek bir koşuyla ölçüldü ve sonuçlar insan tarafından incelenmedi.

Tam liste ve gerekçeler: [`docs/decisions.md`](docs/decisions.md), "Bilinen sınırlar".

## Belgeler

- [`docs/project-spec.md`](docs/project-spec.md) — gereksinimler, korpus, sürüm kuralları, indeks ve arama, API ve hata sözleşmesi, değerlendirme, kabul listesi.
- [`docs/decisions.md`](docs/decisions.md) — beş ana karar, ayrıntılı karar notları, değerlendirme bulguları ve bilinen sınırlar.
