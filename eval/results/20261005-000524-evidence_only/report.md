# Değerlendirme raporu: `20261005-000524-evidence_only`

Bu dosyayı `eval/run_eval.py` üretti. Otomatik kontroller durumları, bölüm kimliklerini, sürüm kararlarını, alıntıları ve claim metinlerinde birkaç düzenli ifadeyi karşılaştırır; anlamsal doğruluğu ölçmez. Her sorunun insan incelemesi `pending` başlar.

## Koşu bilgileri

| Alan | Değer |
|---|---|
| Gerçek çalıştırma zamanı | 2026-10-05T00:05:24+03:00 → 2026-10-05T00:05:24+03:00 |
| Mod | `evidence_only` |
| API | `http://127.0.0.1:8080/api/ask`, istek başına 60 sn timeout |
| Commit | `c192230f13312109b0091bae1b414eaf749428b6`; koşu girdileri commit'ten farklı (dirty): hayır |
| Soru sayısı | 18 |
| Corpus fingerprint | `245685196f8082b298d0d0816de4fb8a48090210a7018a96469a9b843c377b54` |
| Embedding | `intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| LLM modeli (yapılandırılan) | `openai/gpt-6-luna`; generation_configured=true |
| Prompt | `answer-v5`, SHA-256 `42d1275e6cae26d7e48c1638ad8c570361e4130d2021fdf940a73027a59453bb` |
| top_k / skor eşiği | 4 / kapalı |
| Readiness koşu sonunda aynı | evet |

İsteklerdeki as_of değerlendirilen iş tarihidir (E16 dışında 2026-10-04, E16'da 2026-06-01); gerçek çalıştırma zamanıyla aynı kavram değildir.

## Otomatik ölçümler

Payda, kontrolün o soru ve modda uygulandığı sorulardır (tanımlar `docs/project-spec.md` §7). Değerlendirilemeyen: kontrol uygulanıyor ama API kullanılabilir bir cevap dönmedi.

| Ölçüm | Geçen / uygulanan | Başarısız | Değerlendirilemeyen |
|---|---|---|---|
| HTTP 200 ve istekle aynı request_id | 18 / 18 | — | — |
| Beklenen iş durumu | 15 / 15 | — | — |
| Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 15 / 15 | — | — |
| Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 0 / 0 | — | — |
| Doğru sürüm kararı (`version_decisions`) | 6 / 6 | — | — |
| Kaynak/aday geçerli: bölüm korpusta var, alıntı o bölümün birebir metni, belge/sürüm bilgisi bölüm kaydıyla aynı, getirilen bölüm, seçili sürüm, claim atıfları = `sources` (kaynak/aday yoksa uygulanmaz) | 18 / 18 | — | — |
| Cevaplanabilir soruda `insufficient_evidence` dönmedi (üretken mod) | 0 / 0 | — | — |
| Cevapsız soruda claim üretilmedi (üretken mod; claim'in anlamsal yanlışlığını ölçmez) | 0 / 0 | — | — |
| Gerekli bilgi kalıpları claim'lerde var (sınırlı; anlamsal değil) | 0 / 0 | — | — |
| Yasak bilgi kalıpları claim'lerde yok (sınırlı; anlamsal değil) | 0 / 0 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 1 / 1 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 0 / 0 | — | — |

## Soru bazında özet

| ID | Kategori | Beklenen durum | Gerçek | Beklenen bölüm | İlk k | Kaynak / aday | Başarısız kontroller | İnsan incelemesi |
|---|---|---|---|---|---|---|---|---|
| E01 | normal | evidence_only | evidence_only | D01#baglanti | D01#kullanim, D01#baglanti, D02#ses-yok, D01#tamamlama | D01#kullanim, D01#baglanti, D02#ses-yok, D01#tamamlama | — | pending |
| E02 | normal | evidence_only | evidence_only | D02#ses-yok | D02#ses-yok, D02#sinir, D02#kullanim, D01#tamamlama | D02#ses-yok, D02#sinir, D02#kullanim, D01#tamamlama | — | pending |
| E03 | version_conflict | evidence_only | evidence_only | D04#sure | D04#sure, D05#bedel, D05#kullanim, D01#kullanim | D04#sure, D05#bedel, D05#kullanim, D01#kullanim | — | pending |
| E04 | version_conflict | evidence_only | evidence_only | D04#kargo | D05#bedel, D04#kargo, D05#kullanim, D04#sure | D05#bedel, D04#kargo, D05#kullanim, D04#sure | — | pending |
| E05 | normal | evidence_only | evidence_only | D05#bedel | D05#bedel, D04#sure, D05#kullanim, D04#kargo | D05#bedel, D04#sure, D05#kullanim, D04#kargo | — | pending |
| E06 | normal | evidence_only | evidence_only | D06#alanlar | D06#alanlar, D06#kullanim, D10#kullanim, D10#paylasim | D06#alanlar, D06#kullanim, D10#kullanim, D10#paylasim | — | pending |
| E07 | normal | evidence_only | evidence_only | D07#p1 | D07#p1, D07#iletisim, D02#ses-yok, D07#kullanim | D07#p1, D07#iletisim, D02#ses-yok, D07#kullanim | — | pending |
| E08 | normal | evidence_only | evidence_only | D08#saatler | D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim | D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim | — | pending |
| E09 | normal | evidence_only | evidence_only | D09#sifre | D09#sifre, D10#paylasim, D09#kullanim, D10#musteri-istegi | D09#sifre, D10#paylasim, D09#kullanim, D10#musteri-istegi | — | pending |
| E10 | normal | evidence_only | evidence_only | D10#paylasim | D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk | D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk | — | pending |
| E11 | unanswerable | — | evidence_only | — | D04#uygulama, D02#kullanim, D04#sure, D01#tamamlama | D04#uygulama, D02#kullanim, D04#sure, D01#tamamlama | — | pending |
| E12 | unanswerable | — | evidence_only | — | D04#sure, D05#bedel, D05#kullanim, D04#kargo | D04#sure, D05#bedel, D05#kullanim, D04#kargo | — | pending |
| E13 | unanswerable | — | evidence_only | — | D06#alanlar, D02#ses-yok, D06#kullanim, D10#paylasim | D06#alanlar, D02#ses-yok, D06#kullanim, D10#paylasim | — | pending |
| E14 | paraphrase | evidence_only | evidence_only | D04#sure | D04#sure, D06#dogruluk, D05#bedel, D09#kullanim | D04#sure, D06#dogruluk, D05#bedel, D09#kullanim | — | pending |
| E15 | partial | evidence_only | evidence_only | D04#sure | D04#sure, D04#uygulama, D05#kullanim, D01#kullanim | D04#sure, D04#uygulama, D05#kullanim, D01#kullanim | — | pending |
| E16 | historical_version | evidence_only | evidence_only | D03#sure | D03#uygulama, D05#bedel, D03#sure, D05#kullanim | D03#uygulama, D05#bedel, D03#sure, D05#kullanim | — | pending |
| E17 | false_premise | evidence_only | evidence_only | D07#p1 | D07#p1, D07#iletisim, D07#kullanim, D10#paylasim | D07#p1, D07#iletisim, D07#kullanim, D10#paylasim | — | pending |
| E18 | multi_source | evidence_only | evidence_only | D04#sure, D05#bedel | D05#bedel, D04#sure, D05#kullanim, D04#uygulama | D05#bedel, D04#sure, D05#kullanim, D04#uygulama | — | pending |

## Ayrıntılar

### E01 · normal

- Soru: MH-10'u destek panelinde nasıl kullanmaya başlarım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D01#baglanti. Rubrik: USB bağlantısı ve panelde hem giriş hem çıkış aygıtı seçimi söylenmeli; belgede olmayan adım eklenmemeli.
  - Gerekli: MH-10 bilgisayarın USB bağlantı noktasına takılır.
  - Gerekli: Destek panelinin ses ayarlarında MH-10 giriş aygıtı (mikrofon) olarak seçilir.
  - Gerekli: MH-10 çıkış aygıtı (hoparlör) olarak da seçilir.
  - Yasak: Belgede olmayan bir kurulum adımı (ör. sürücü kurmak, işletim sisteminin ses ayarını değiştirmek).
- Gerçek: HTTP 200, `evidence_only`, 53 ms
  - İlk k: D01#kullanim, D01#baglanti, D02#ses-yok, D01#tamamlama; kaynak/aday: D01#kullanim, D01#baglanti, D02#ses-yok, D01#tamamlama
  - reason_code: —
  - Sürüm kararları: mh10-setup → D01; audio-troubleshooting → D02
- İnsan incelemesi: pending

### E02 · normal

- Soru: Kulaklıktan ses gelmiyor, ne kontrol etmeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D02#ses-yok. Rubrik: Belgedeki kontrol sırası (USB, aygıt seçimi, test çağrısı, ticket) verilmeli; rastgele teknik tavsiye eklenmemeli.
  - Gerekli: USB kablosunun takılı olduğu kontrol edilir.
  - Gerekli: Panelde MH-10'un giriş ve çıkış aygıtı olarak seçili olduğu doğrulanır.
  - Gerekli: Panelden test çağrısı yapılır.
  - Gerekli: Sorun sürerse destek talebi (ticket) açılır.
  - Yasak: Belgede olmayan teknik tavsiye (sürücü veya işletim sistemi ayarı değiştirmek gibi).
- Gerçek: HTTP 200, `evidence_only`, 30 ms
  - İlk k: D02#ses-yok, D02#sinir, D02#kullanim, D01#tamamlama; kaynak/aday: D02#ses-yok, D02#sinir, D02#kullanim, D01#tamamlama
  - reason_code: —
  - Sürüm kararları: audio-troubleshooting → D02; mh10-setup → D01
- İnsan incelemesi: pending

### E03 · version_conflict

- Soru: Kulaklığı kaç gün içinde iade edebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: 30 takvim günü, teslimden itibaren; 14 gün denmemeli. D04 seçili, D03 expired görünmeli.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: Süre teslim tarihinden itibaren sayılır.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `evidence_only`, 25 ms
  - İlk k: D04#sure, D05#bedel, D05#kullanim, D01#kullanim; kaynak/aday: D04#sure, D05#bedel, D05#kullanim, D01#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; mh10-setup → D01
- İnsan incelemesi: pending

### E04 · version_conflict

- Soru: İade kargosunu kim ödüyor?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#kargo. Rubrik: Şirketin sağladığı etiket ve etiketli gönderimin bedeli şirkette; müşteri öder denmemeli. D03 expired.
  - Gerekli: Şirket iade etiketi sağlar.
  - Gerekli: Etiketle yapılan gönderimin kargo bedelini şirket karşılar.
  - Yasak: İade kargosunu müşteri öder (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `evidence_only`, 21 ms
  - İlk k: D05#bedel, D04#kargo, D05#kullanim, D04#sure; kaynak/aday: D05#bedel, D04#kargo, D05#kullanim, D04#sure
  - reason_code: —
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

### E05 · normal

- Soru: Para iadesi süresi kargoya verdiğim gün mü başlıyor?
- Soru sürümü: 2 (önceki sürümler `revisions` alanında)
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D05#bedel. Rubrik: Yanlış ön kabul düzeltilmeli: süre kargodan değil kabulden sonra başlar ve 5 iş günüdür.
  - Gerekli: Hayır; süre ürünün kargoya verildiği tarihten başlamaz.
  - Gerekli: İade bedeli iadenin kabulünden sonra ödenir.
  - Gerekli: Ödeme süresi 5 iş günüdür.
  - Yasak: Sürenin kargoya verme tarihinden başladığı.
  - Yasak: Sürenin takvim günü olduğu.
- Gerçek: HTTP 200, `evidence_only`, 37 ms
  - İlk k: D05#bedel, D04#sure, D05#kullanim, D04#kargo; kaynak/aday: D05#bedel, D04#sure, D05#kullanim, D04#kargo
  - reason_code: —
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

### E06 · normal

- Soru: Destek talebinde hangi bilgileri vermeliyim?
- Soru sürümü: 2 (önceki sürümler `revisions` alanında)
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar. Rubrik: Üç alan eksiksiz: seri numarası, varsa hata kodu, yeniden üretme adımları.
  - Gerekli: MH-10'un seri numarası.
  - Gerekli: Görüntülendiyse hata kodu.
  - Gerekli: Sorunu yeniden üretme adımları.
  - Yasak: Belgede olmayan bir alan (ör. parola, OTP, fatura bilgisi) istemek.
- Gerçek: HTTP 200, `evidence_only`, 20 ms
  - İlk k: D06#alanlar, D06#kullanim, D10#kullanim, D10#paylasim; kaynak/aday: D06#alanlar, D06#kullanim, D10#kullanim, D10#paylasim
  - reason_code: —
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### E07 · normal

- Soru: Tüm temsilciler çalışamıyorsa ilk yanıt ne zaman gelir?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D07#p1. Rubrik: P1 ve 2 çalışma saatlik ilk yanıt hedefi; çözüm süresi garantisine dönüştürülmemeli.
  - Gerekli: Tüm temsilcilerin çalışmasını durduran olay P1'dir.
  - Gerekli: P1 için ilk yanıt hedefi 2 çalışma saatidir.
  - Gerekli: Bu hedef çözüm süresi garantisi değildir.
  - Yasak: Sorunun 2 saat içinde çözüleceği / çözüm garantisi.
- Gerçek: HTTP 200, `evidence_only`, 33 ms
  - İlk k: D07#p1, D07#iletisim, D02#ses-yok, D07#kullanim; kaynak/aday: D07#p1, D07#iletisim, D02#ses-yok, D07#kullanim
  - reason_code: —
  - Sürüm kararları: priority-sla → D07; audio-troubleshooting → D02
- İnsan incelemesi: pending

### E08 · normal

- Soru: Destek ekibine hangi saatlerde ulaşabilirim?
- Soru sürümü: 2 (önceki sürümler `revisions` alanında)
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D08#saatler. Rubrik: Hafta içi 09.00–18.00, Türkiye saati (Europe/Istanbul).
  - Gerekli: Hafta içi ulaşılabilir.
  - Gerekli: Saatler 09.00–18.00.
  - Gerekli: Saatler Türkiye saatine (Europe/Istanbul) göredir.
  - Yasak: Hafta sonu veya 7/24 destek.
- Gerçek: HTTP 200, `evidence_only`, 33 ms
  - İlk k: D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim; kaynak/aday: D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim
  - reason_code: —
  - Sürüm kararları: support-hours → D08; support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### E09 · normal

- Soru: Parolamı unuttum, ne yapmalıyım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre. Rubrik: Kayıtlı e-posta adresine gönderilen parola sıfırlama bağlantısı.
  - Gerekli: Giriş ekranından parola sıfırlama istenir.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir.
  - Yasak: Bağlantının görüşmede söylenen başka bir adrese gönderilebileceği.
- Gerçek: HTTP 200, `evidence_only`, 21 ms
  - İlk k: D09#sifre, D10#paylasim, D09#kullanim, D10#musteri-istegi; kaynak/aday: D09#sifre, D10#paylasim, D09#kullanim, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: pending

### E10 · normal

- Soru: Destek personeline OTP kodumu göndereyim mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D10#paylasim. Rubrik: Hayır: parola ve OTP paylaşılmaz; destek personeli de istemez.
  - Gerekli: Hayır; OTP destek personeliyle paylaşılmaz.
  - Yasak: OTP'nin gönderilebileceği.
- Gerçek: HTTP 200, `evidence_only`, 22 ms
  - İlk k: D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk; kaynak/aday: D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk
  - reason_code: —
  - Sürüm kararları: safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: pending

### E11 · unanswerable

- Soru: MH-10'un garantisi kaç ay?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: garanti süresi belgelerde yok; süre uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Herhangi bir garanti süresi.
- Gerçek: HTTP 200, `evidence_only`, 26 ms
  - İlk k: D04#uygulama, D02#kullanim, D04#sure, D01#tamamlama; kaynak/aday: D04#uygulama, D02#kullanim, D04#sure, D01#tamamlama
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); audio-troubleshooting → D02; mh10-setup → D01
- İnsan incelemesi: pending

### E12 · unanswerable

- Soru: Almanya'daki müşteriler de 30 günde iade edebilir mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: İstek kapsamı TR/B2B/MH-10, soru Almanya'yı soruyor: insufficient_evidence; Türkiye kuralı Almanya'ya genellenmemeli.
  - Yasak: Türkiye/B2B kapsamındaki 30 günlük kuralın Almanya'ya uygulanması.
- Gerçek: HTTP 200, `evidence_only`, 32 ms
  - İlk k: D04#sure, D05#bedel, D05#kullanim, D04#kargo; kaynak/aday: D04#sure, D05#bedel, D05#kullanim, D04#kargo
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: pending

### E13 · unanswerable

- Soru: 4711 numaralı ticket'ım çözüldü mü?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: canlı ticket sistemine erişim yok; durum uydurulmamalı.
  - Yasak: Ticket'ın çözüldüğü, kapandığı veya bir durumunun bilindiği.
- Gerçek: HTTP 200, `evidence_only`, 18 ms
  - İlk k: D06#alanlar, D02#ses-yok, D06#kullanim, D10#paylasim; kaynak/aday: D06#alanlar, D02#ses-yok, D06#kullanim, D10#paylasim
  - reason_code: —
  - Sürüm kararları: support-ticket → D06; audio-troubleshooting → D02; safe-support-sharing → D10
- İnsan incelemesi: pending

### E14 · paraphrase

- Soru: Ürünü geri yollamak için ne kadar vaktim var?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: E03'ün farklı ifadesi: Türkiye/B2B kapsamında 30 takvim günü.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü).
- Gerçek: HTTP 200, `evidence_only`, 14 ms
  - İlk k: D04#sure, D06#dogruluk, D05#bedel, D09#kullanim; kaynak/aday: D04#sure, D06#dogruluk, D05#bedel, D09#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); support-ticket → D06; refund-payment → D05; account-access → D09
- İnsan incelemesi: pending

### E15 · partial

- Soru: Türkiye'de MH-10'u iade etmek için teslimden itibaren kaç günüm var? Almanya'da da aynı süre geçerli mi?
- Soru sürümü: 2 (önceki sürümler `revisions` alanında)
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `partial`; bölümler D04#sure. Rubrik: partial: Türkiye için 30 takvim günü kaynaklı; Almanya eksik konu olarak ayrılmalı.
  - Gerekli: Türkiye/B2B için iade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Yasak: Almanya için bir süre veya Türkiye kuralının Almanya'ya uygulanması.
- Gerçek: HTTP 200, `evidence_only`, 38 ms
  - İlk k: D04#sure, D04#uygulama, D05#kullanim, D01#kullanim; kaynak/aday: D04#sure, D04#uygulama, D05#kullanim, D01#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; mh10-setup → D01
- İnsan incelemesi: pending

### E16 · historical_version

- Soru: 1 Haziran 2026'da iade süresi neydi?
- İstek: as_of `2026-06-01`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D03#sure. Rubrik: İstek as_of=2026-06-01: 14 takvim günü (D03); D04 future_effective görünmeli.
  - Gerekli: 1.0 sürümünde iade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü).
- Gerçek: HTTP 200, `evidence_only`, 26 ms
  - İlk k: D03#uygulama, D05#bedel, D03#sure, D05#kullanim; kaynak/aday: D03#uygulama, D05#bedel, D03#sure, D05#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: pending

### E17 · false_premise

- Soru: P1 sorunları kesin iki saatte çözülüyor, doğru mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D07#p1. Rubrik: Yanlış ön kabul düzeltilmeli: 2 çalışma saati ilk yanıt hedefidir, çözüm garantisi değildir.
  - Gerekli: 2 çalışma saati çözüm değil ilk yanıt hedefidir.
  - Gerekli: Bu hedef çözüm süresi garantisi değildir.
  - Yasak: P1 sorunlarının iki saatte çözüldüğünü onaylamak.
- Gerçek: HTTP 200, `evidence_only`, 17 ms
  - İlk k: D07#p1, D07#iletisim, D07#kullanim, D10#paylasim; kaynak/aday: D07#p1, D07#iletisim, D07#kullanim, D10#paylasim
  - reason_code: —
  - Sürüm kararları: priority-sla → D07; safe-support-sharing → D10
- İnsan incelemesi: pending

### E18 · multi_source

- Soru: İade için kaç günüm var, kabulden sonra param ne zaman döner?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#sure, D05#bedel. Rubrik: İki kaynak birlikte: 30 takvim günü (D04#sure) ve kabulden sonra 5 iş günü (D05#bedel).
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: İade bedeli kabulden sonra 5 iş günü içinde ödenir.
  - Yasak: 14 takvim günü (süresi dolmuş sürüm).
- Gerçek: HTTP 200, `evidence_only`, 29 ms
  - İlk k: D05#bedel, D04#sure, D05#kullanim, D04#uygulama; kaynak/aday: D05#bedel, D04#sure, D05#kullanim, D04#uygulama
  - reason_code: —
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

