# ai-knowledge-assistant

Kurgu şirket **Yardım bende Destek Teknolojileri**'nin destek çalışanına, onaylı ve sürümlü bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur bir API. Cevapta kullanılan belge ve bölüm gösterilir, eski sürümün neden dışlandığı açıklanır; belge desteği yetersizse cevap uydurulmaz.

> Tamamen kurgu verilerle hazırlanmış değerlendirme demosudur. Üretim güvenliği veya KVKK/BDDK uyumu iddia edilmez.

**Durum:** geliştiriliyor. Servis iskeletleri ve sağlık uçları çalışıyor. Kurgu korpus (`data/knowledge/`, 10 belge), korpus doğrulaması, tarih/kapsam bazlı sürüm seçimi, yerel embedding, SQLite indeks ve sürüm görünümü içinde arama Python kodu olarak hazır ve testli, ancak henüz API'ye bağlı değil. Kurulum, çalıştırma ve değerlendirme adımları tamamlandıkça buraya eklenecek.

Mimari akış: istek → .NET API → FastAPI RAG servisi → tarih/kapsam bazlı geçerli belge görünümü → bölüm araması → alıntı modu veya kaynaklı LLM cevabı → kaynak doğrulama → cevap.

## Yerel embedding modeli ve arama

- Model: `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3` (`src/rag_service/app/settings.py` içinde sabit). Modelin kendi reposundaki ONNX dosyası ONNX Runtime ile CPU'da çalışır; GPU gerekmez.
- **İlk çalıştırma internet ister.** Model (yaklaşık 470 MB) ve tokenizer (yaklaşık 17 MB) `MODEL_CACHE_DIR` (varsayılan `var/models/`) altına iner. Önbellek dolduktan sonra model ağ olmadan yüklenir.
- İndeks (`INDEX_PATH`, varsayılan `var/index.sqlite3`) Markdown belgelerden türetilmiş veridir. Belge, metadata veya model değiştiyse indeks yüklenirken kendiliğinden yeniden üretilir; bozuk dosya kullanılmaz, yeniden üretilir. Dosyayı silmek de güvenlidir.

Komutlar (`src/rag_service` içinden):

```bash
uv sync
uv run pytest                          # ağsız; sahte embedding ile birim testleri
uv run pytest -m model                 # gerçek model testleri (ilk seferde modeli indirir)
uv run python measure_retrieval.py     # geliştirme sorularının sıralaması ve ham skorları
```

## Belgeler

- [`docs/project-spec.md`](docs/project-spec.md) — gereksinimler, korpus, sürüm kuralları, indeks ve arama, API ve hata sözleşmesi, kabul listesi.
- [`docs/decisions.md`](docs/decisions.md) — teknik kararlar ve bilinen sınırlar.
