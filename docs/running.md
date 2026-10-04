# Yerel geliştirme ve işletim

Docker ile hızlı başlangıç için [README](../README.md).

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

## Belgeler değişince yeniden indeksleme

- Belge veya metadata değişince `docker compose restart rag` yeterlidir. Servis açılışta fingerprint'i karşılaştırır, uyuşmazsa indeksi yeniden üretir ve ancak ondan sonra hazır olur. Logda `rebuilding index …` ve `built index …` görünür; değişiklik yoksa `reusing index …: fingerprint … matches`. Yeniden başlama süresince API 503 `upstream_unavailable` döner. Yeni fingerprint `/health/ready` → `run_metadata.corpus_fingerprint`'te görünür.
- Korpus geçersizse (ör. çakışan iki onaylı sürüm) rag başlamaz; neden `docker compose logs rag`'de `CorpusError` olarak yazar.
- **Yeni sürüm eklemek** (ör. iade prosedürünün v3'ü): önceki sürümün `valid_to` değerini yeni sürümün `valid_from` tarihine çekin, yeni dosyayı `NN-slug.md` adıyla ekleyin (`supersedes` önceki belge), sonra `docker compose restart rag`. O tarihten önceki `as_of` değerleri eski sürümü, sonrakiler yenisini seçer. Kural: [`docs/project-spec.md`](project-spec.md) §4.
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

