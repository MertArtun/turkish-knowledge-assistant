# ai-knowledge-assistant

Kurgu şirket **Yardım bende Destek Teknolojileri**'nin destek çalışanına, onaylı ve sürümlü bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur bir API. Cevapta kullanılan belge ve bölüm gösterilir, eski sürümün neden dışlandığı açıklanır; belge desteği yetersizse cevap uydurulmaz.

> Tamamen kurgu verilerle hazırlanmış değerlendirme demosudur. Üretim güvenliği veya KVKK/BDDK uyumu iddia edilmez.

**Durum:** geliştiriliyor. Alıntı modu (`evidence_only`) uçtan uca çalışıyor: .NET API → Python servisi → tarih/kapsam bazlı sürüm görünümü → arama → kaynak bölüm adayları. Üretken mod (kaynaklı LLM cevabı ve kaynak doğrulama) çalışıyor: sahte model/HTTP katmanıyla test edildi ve OpenRouter üzerinden birkaç gerçek smoke çağrısıyla denendi; değerlendirme koşusu henüz yapılmadı (bkz. [`docs/decisions.md`](docs/decisions.md), bilinen sınırlar). Docker Compose henüz yok.

Mimari akış: istek → .NET API → FastAPI RAG servisi → tarih/kapsam bazlı geçerli belge görünümü → bölüm araması → alıntı modu veya kaynaklı LLM cevabı → kaynak doğrulama → cevap.

## Yerelde çalıştırma (Docker olmadan)

Önkoşullar: [uv](https://docs.astral.sh/uv/) (Python 3.12'yi kendisi kurar), .NET SDK 10 (`global.json`: 10.0.102 ve sonraki yamalar), ilk çalıştırmada internet (model indirmesi).

1. Python RAG servisi, `src/rag_service` içinden:

   ```bash
   uv sync
   uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
   ```

   Servis korpusu doğrular, embedding modelini ve indeksi yükler, ancak ondan sonra bağlantı kabul eder. İlk çalıştırmada model indirmesi birkaç dakika sürebilir. Korpus, model veya indeks kullanılamazsa süreç hata vererek durur. Ayarlar ortam değişkenlerinden okunur (isimler ve varsayılanlar `.env.example`'da); servis `.env` dosyasını kendiliğinden okumaz. Varsayılanlarla alıntı modunda ve anahtarsız çalışır.

2. .NET API, ayrı bir terminalde repo kökünden:

   ```bash
   RAG_SERVICE_URL=http://127.0.0.1:8000 dotnet run --project src/SupportAssistant.Api
   ```

   API `http://127.0.0.1:8080` adresinde dinler. .NET de `.env` okumaz; `RAG_SERVICE_URL` verilmezse Compose'daki servis adı `http://rag:8000` kullanılır.

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

Açmak için Python servisini anahtarla başlatın (anahtar yoksa `generative` istek 503 `generation_not_configured` döner):

- `OPENAI_API_KEY`: sağlayıcı anahtarı. Değerlendirme kurulumunda bu bir OpenRouter anahtarıdır.
- `OPENAI_BASE_URL`: boşsa `https://api.openai.com/v1`; OpenRouter için `https://openrouter.ai/api/v1`. OpenRouter'da istek OpenAI'ın kendi uç noktasına sabitlenir, başka bir sağlayıcıya sessizce geçmez.
- `OPENAI_MODEL`: OpenAI'da `gpt-6-luna` (varsayılan), OpenRouter'da `openai/gpt-6-luna`.
- `APP_MODE=generative`, `mode` alanı verilmeyen istekleri de üretken moda alır.

```bash
# src/rag_service içinden; servis .env'i kendiliğinden okumaz, uv okutur
uv run --env-file ../../.env uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

OpenRouter ek bir aracıdır ve kendi veri politikası vardır. İstek `store=false` ile gönderilir, ancak bu OpenRouter'ın veya OpenAI'ın kendi saklama politikalarını ortadan kaldırmaz. Modele yalnızca soru, etkin tarih/kapsam ve seçilen bölümler gider; korpusun geri kalanı, eski sürümler, kimlik veya ortam bilgisi gitmez.

Her model çağrısı ücretlidir. Readiness modeli hiç çağırmaz; `generation_configured=true` yalnızca anahtarla bir istemci kurulduğunu gösterir.

## Yerel embedding modeli ve arama

- Model: `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3` (varsayılan; `EMBEDDING_REVISION` ile yalnızca tam commit hash'i verilebilir). Modelin kendi reposundaki ONNX dosyası ONNX Runtime ile CPU'da çalışır; GPU gerekmez.
- **İlk çalıştırma internet ister.** Model (yaklaşık 470 MB) ve tokenizer (yaklaşık 17 MB) `MODEL_CACHE_DIR` (varsayılan `var/models/`) altına iner. Önbellek dolduktan sonra model ağ olmadan yüklenir.
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
