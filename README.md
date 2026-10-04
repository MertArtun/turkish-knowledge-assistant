# ai-knowledge-assistant

Kurgu şirket **Yardım bende Destek Teknolojileri**'nin destek çalışanına, onaylı ve sürümlü bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur bir API. Cevapta kullanılan belge ve bölüm gösterilir, eski sürümün neden dışlandığı açıklanır; belge desteği yetersizse cevap uydurulmaz.

> Tamamen kurgu verilerle hazırlanmış değerlendirme demosudur. Üretim güvenliği veya KVKK/BDDK uyumu iddia edilmez.

**Durum:** geliştiriliyor. Alıntı modu (`evidence_only`) uçtan uca çalışıyor: .NET API → Python servisi → tarih/kapsam bazlı sürüm görünümü → arama → kaynak bölüm adayları. Üretken mod (kaynaklı LLM cevabı ve kaynak doğrulama) çalışıyor: sahte model/HTTP katmanıyla test edildi ve OpenRouter üzerinden birkaç gerçek smoke çağrısıyla denendi; değerlendirme koşusu henüz yapılmadı (bkz. [`docs/decisions.md`](docs/decisions.md), bilinen sınırlar). İki servis Docker Compose ile birlikte çalışıyor.

Mimari akış: istek → .NET API → FastAPI RAG servisi → tarih/kapsam bazlı geçerli belge görünümü → bölüm araması → alıntı modu veya kaynaklı LLM cevabı → kaynak doğrulama → cevap.

## Docker Compose ile çalıştırma

Önkoşullar: Docker Engine 25 veya üstü (sağlık kontrolündeki `start_interval` için) ve Docker Compose v2. Denenen ortam: Docker 29.1.3, Compose v2.40.3, macOS arm64. Python, uv veya .NET kurulu olması gerekmez.

**İlk başlangıç internet ister.** Embedding modeli (yaklaşık 490 MB) `rag-models` volume'üne iner, sonra indeks üretilir. Servis ancak bundan sonra hazır olur. Önbellek dolduktan sonraki başlangıçlar modeli ağsız yükler. Sıfırdan, internetsiz kurulum desteklenmez.

```bash
cp .env.example .env                  # isteğe bağlı; anahtarsız varsayılanlarla da çalışır
docker compose up --build -d --wait   # rag sağlıklı olana kadar bekler, sonra api başlar
curl -s http://127.0.0.1:8080/health/ready
curl -s http://127.0.0.1:8080/api/ask -H 'Content-Type: application/json' \
  -d '{"question": "İade kargosunu kim ödüyor?", "as_of": "2026-10-04"}'
docker compose logs rag api           # her satır bir JSON nesnesi
docker compose down                   # volume'ler (indeks ve model) korunur
```

- Host'a yalnızca .NET API açılır: `127.0.0.1:8080`. Python servisi (`rag:8000`) port yayımlamaz; yalnızca Compose ağından erişilir. Model indirmesi ve LLM sağlayıcısı için dış bağlantısı açıktır.
- `data/knowledge` salt okunur bağlanır. İndeks (`rag-index`) ve model önbelleği (`rag-models`) ayrı volume'lerdedir. İki konteyner de root olmayan kullanıcıyla çalışır.
- **Anahtarsız başlatma:** `.env` yoksa veya `OPENAI_API_KEY` boşsa servis alıntı modunda çalışır. `"mode": "generative"` isteği 503 `generation_not_configured` döner; alıntı moduna sessizce düşülmez.
- **Üretken moda geçmek:** `.env`'e `OPENAI_API_KEY` yazın, gerekirse `OPENAI_BASE_URL`, `OPENAI_MODEL` ve `APP_MODE=generative` ekleyin. Sonra `docker compose up -d --wait` çalıştırın; değişen ortam rag konteynerini yeniden oluşturur. Anahtar yalnızca rag konteynerine verilir. Değişkenlerin anlamı aşağıda, "Üretken mod" başlığında.
- `docker compose config` ve `docker inspect` çıktıları `.env`'deki anahtarı açık metin gösterir. Bu çıktıları paylaşmayın.

### Belgeler değişince yeniden indeksleme

- Belge veya metadata değişince `docker compose restart rag` yeterlidir. Servis açılışta fingerprint'i karşılaştırır, uyuşmazsa indeksi yeniden üretir ve ancak ondan sonra hazır olur. Logda `rebuilding index …` ve `built index …` görünür; değişiklik yoksa `reusing index …: fingerprint … matches`. Yeniden başlama süresince API 503 `upstream_unavailable` döner.
- İndeksi sıfırdan üretmek için: `docker compose down && docker volume rm ai-knowledge-assistant_rag-index && docker compose up -d --wait`.
- Docker olmadan, Python servisini yeniden başlatmak yeterlidir. `var/index.sqlite3` dosyasını silmek de güvenlidir.

### Sorun giderme

| Belirti | Neden / çözüm |
|---|---|
| `docker compose build`: `header key "x-docker-expose-session-sharedkey" contains value with non-printable ASCII characters` | Proje yolunda ASCII olmayan bir karakter var (ör. `ı`), Compose'un bake derlemesi bunu kabul etmiyor. `COMPOSE_BAKE=false docker compose up --build -d --wait` kullanın veya repoyu ASCII bir yola kopyalayın. |
| `--wait` uzun sürüyor, rag `health: starting` | İlk başlangıçta model iniyor: `docker compose logs -f rag`. Sağlık kontrolü ilk 10 dakikadaki başarısızlıkları saymaz; sonra üç başarısız denemede konteyner `unhealthy` olur ve `--wait` hata verir. İlk başlangıç internetsiz başarısız olur. |
| rag konteyneri duruyor (`exited`) | `docker compose logs rag`: yapılandırma veya korpus hatası (`ConfigError`, `CorpusError`) düz metin Python traceback'i olarak görünür; mesaj değişkeni veya dosyayı söyler, anahtarın değerini yazmaz. Örnek: `APP_MODE=generative` ama anahtar boş. |
| `/health/ready` → 503 `upstream_unavailable` | Python servisi henüz dinlemiyor: yükleniyor, yeniden başlıyor veya durmuş. |
| Üretken istek → 503 `provider_unavailable` / 504 `generation_timeout` | Sağlayıcı hatası; "belgede bilgi yok" değildir. Aynı `request_id` ile rag logundaki `generation` satırının `detail` alanına bakın: HTTP durumu, sağlayıcı kodu, OpenRouter yönlendirme nedeni. |
| `127.0.0.1:8080` başka bir süreçte | `lsof -nP -iTCP:8080 -sTCP:LISTEN` ile bulun ve durdurun. Docker olmadan çalışan `dotnet run` da aynı portu kullanır. |
| Logda JSON olmayan `Warning: You are sending unauthenticated requests to the HF Hub` | Hugging Face kütüphanesi bu uyarıyı kendi handler'ıyla bir kez daha düz metin olarak yazar. Yalnızca model indirilirken görülür, zararsızdır. |

## Yerelde çalıştırma (Docker olmadan)

Önkoşullar: [uv](https://docs.astral.sh/uv/) (Python 3.12'yi kendisi kurar), .NET SDK 10 (`global.json`: 10.0.102 ve sonraki yamalar), ilk çalıştırmada internet (model indirmesi).

1. Python RAG servisi, `src/rag_service` içinden:

   ```bash
   uv sync
   uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --log-config log_config.json
   ```

   Servis korpusu doğrular, embedding modelini ve indeksi yükler, ancak ondan sonra bağlantı kabul eder. İlk çalıştırmada model indirmesi birkaç dakika sürebilir. Korpus, model veya indeks kullanılamazsa süreç hata vererek durur. Ayarlar ortam değişkenlerinden okunur (isimler ve varsayılanlar `.env.example`'da); servis `.env` dosyasını kendiliğinden okumaz. Varsayılanlarla alıntı modunda ve anahtarsız çalışır. `--log-config log_config.json`, uygulamanın satırları dâhil bütün logu JSON olarak yazar. Bu seçenek verilmezse uvicorn'un varsayılan ayarı `app.*` satırlarını göstermez.

2. .NET API, ayrı bir terminalde repo kökünden:

   ```bash
   RAG_SERVICE_URL=http://127.0.0.1:8000 dotnet run --project src/SupportAssistant.Api
   ```

   API `http://127.0.0.1:8080` adresinde dinler ve JSON log yazar. .NET de `.env` okumaz; `RAG_SERVICE_URL` verilmezse Compose'daki servis adı `http://rag:8000` kullanılır.

3. İstek:

   ```bash
   curl -s http://127.0.0.1:8080/health/ready
   curl -s http://127.0.0.1:8080/api/ask -H 'Content-Type: application/json' \
     -d '{"question": "İade kargosunu kim ödüyor?", "as_of": "2026-10-04"}'
   ```

   Diğer örnekler (tarihsel `as_of`, desteklenmeyen kapsam, hatalar): [`examples/requests.http`](examples/requests.http).

Alıntı modunda cevap `status: "evidence_only"` ile döner: `evidence` sürüm görünümünden getirilen aday bölümlerdir (birebir alıntı, belge, sürüm, geçerlilik tarihleri), `answer` `null`'dır. Adaylar sorunun cevabı olduğu iddiasını taşımaz. Desteklenmeyen kapsam veya geçerli sürüm olmayan tarih `insufficient_evidence` ve `reason_code` ile döner. `version_decisions` hangi sürümün seçildiğini ve hangisinin neden dışlandığını gösterir. Tüm alanlar, durumlar ve hata kodları: [`docs/project-spec.md`](docs/project-spec.md) §5.

## Üretken mod (LLM ile kaynaklı cevap)

`"mode": "generative"` isteğinde sürüm görünümünden gelen en fazla 4 bölüm, soru, etkin tarih ve kapsamla birlikte dil modeline gider. Model yalnızca kısa iddialar (claim) ve her biri için bölüm ID'leri döndürür. Sunucu her ID'nin bu istekte verilen bölümlerden biri olduğunu ve durumun iddialarla tutarlı olduğunu denetler, cevabı ve birebir alıntıları kendisi kurar. Kurallara uymayan çıktı düzeltilmez, 502 `invalid_generation_output` olur. Sağlayıcı hataları 503 `provider_unavailable` veya 504 `generation_timeout` döner; hiçbiri "belgede bilgi yok" sayılmaz ve alıntı moduna düşülmez. Kurallar: [`docs/project-spec.md`](docs/project-spec.md) §5 "Üretim".

Açmak için Python servisini anahtarla başlatın; Docker'da bu değişkenler `.env`'den okunur (yukarıda). Anahtar yoksa `generative` istek 503 `generation_not_configured` döner:

- `OPENAI_API_KEY`: sağlayıcı anahtarı. Değerlendirme kurulumunda bu bir OpenRouter anahtarıdır.
- `OPENAI_BASE_URL`: boşsa `https://api.openai.com/v1`; OpenRouter için `https://openrouter.ai/api/v1`. OpenRouter'da istek OpenAI'ın kendi uç noktasına sabitlenir, başka bir sağlayıcıya sessizce geçmez.
- `OPENAI_MODEL`: OpenAI'da `gpt-6-luna` (varsayılan), OpenRouter'da `openai/gpt-6-luna`.
- `APP_MODE=generative`, `mode` alanı verilmeyen istekleri de üretken moda alır.

```bash
# src/rag_service içinden; servis .env'i kendiliğinden okumaz, uv okutur
uv run --env-file ../../.env uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --log-config log_config.json
```

OpenRouter ek bir aracıdır ve kendi veri politikası vardır. İstek `store=false` ile gönderilir, ancak bu OpenRouter'ın veya OpenAI'ın kendi saklama politikalarını ortadan kaldırmaz. Modele yalnızca soru, etkin tarih/kapsam ve seçilen bölümler gider; korpusun geri kalanı, eski sürümler, kimlik veya ortam bilgisi gitmez.

Her model çağrısı ücretlidir. Readiness modeli hiç çağırmaz; `generation_configured=true` yalnızca anahtarla bir istemci kurulduğunu gösterir.

## Yerel embedding modeli ve arama

- Model: `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3` (varsayılan; `EMBEDDING_REVISION` ile yalnızca tam commit hash'i verilebilir). Modelin kendi reposundaki ONNX dosyası ONNX Runtime ile CPU'da çalışır; GPU gerekmez.
- **İlk çalıştırma internet ister.** Model (yaklaşık 470 MB) ve tokenizer (yaklaşık 17 MB) `MODEL_CACHE_DIR` altına iner: yerelde varsayılan `var/models/`, Docker'da `rag-models` volume'ü. Önbellek dolduktan sonra model ağ olmadan yüklenir.
- İndeks (`INDEX_PATH`, varsayılan `var/index.sqlite3`) Markdown belgelerden türetilmiş veridir. Belge, metadata veya model değiştiyse indeks yüklenirken kendiliğinden yeniden üretilir; bozuk dosya kullanılmaz, yeniden üretilir. Dosyayı silmek de güvenlidir.

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

## Belgeler

- [`docs/project-spec.md`](docs/project-spec.md) — gereksinimler, korpus, sürüm kuralları, indeks ve arama, API ve hata sözleşmesi, kabul listesi.
- [`docs/decisions.md`](docs/decisions.md) — teknik kararlar ve bilinen sınırlar.
