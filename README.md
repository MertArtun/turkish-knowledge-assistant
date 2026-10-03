# ai-knowledge-assistant

Kurgu şirket **Yardım bende Destek Teknolojileri**'nin destek çalışanına, onaylı ve sürümlü bilgi belgelerine dayanarak Türkçe cevap veren tek turlu, salt okunur bir API. Cevapta kullanılan belge ve bölüm gösterilir, eski sürümün neden dışlandığı açıklanır; belge desteği yetersizse cevap uydurulmaz.

> Tamamen kurgu verilerle hazırlanmış değerlendirme demosudur. Üretim güvenliği veya KVKK/BDDK uyumu iddia edilmez.

**Durum:** geliştiriliyor. Servis iskeletleri ve sağlık uçları çalışıyor. Kurgu korpus (`data/knowledge/`, 10 belge), korpus doğrulaması ve tarih/kapsam bazlı sürüm seçimi Python kodu olarak hazır ve testli, ancak henüz API'ye bağlı değil. Kurulum, çalıştırma ve değerlendirme adımları ilgili aşamalar tamamlandıkça buraya eklenecek.

Mimari akış: istek → .NET API → FastAPI RAG servisi → tarih/kapsam bazlı geçerli belge görünümü → bölüm araması → alıntı modu veya kaynaklı LLM cevabı → kaynak doğrulama → cevap.

## Belgeler

- [`docs/project-spec.md`](docs/project-spec.md) — gereksinimler, korpus, sürüm kuralları, API ve hata sözleşmesi, kabul listesi.
- [`docs/progress.md`](docs/progress.md) — plan ve ilerleme.
- [`docs/judgment.md`](docs/judgment.md) — kararlar, bilinen sınırlar, inceleme akışı.
