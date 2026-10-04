# Değerlendirme raporu: `20261005-005746-evidence_only-holdout`

Bu dosyayı `eval/run_eval.py` üretti. Otomatik kontroller durumları, bölüm kimliklerini, sürüm kararlarını, alıntıları ve claim metinlerinde birkaç düzenli ifadeyi karşılaştırır; anlamsal doğruluğu ölçmez. Her sorunun insan incelemesi `pending` başlar.

## Koşu bilgileri

| Alan | Değer |
|---|---|
| Gerçek çalıştırma zamanı | 2026-10-05T00:57:46+03:00 → 2026-10-05T00:57:47+03:00 |
| Mod | `evidence_only` |
| API | `http://127.0.0.1:8080/api/ask`, istek başına 60 sn timeout |
| Commit | `151b8032e05a07b16053925746ea5333e82357a8`; koşu girdileri commit'ten farklı (dirty): hayır |
| Soru dosyası | `eval/holdout_questions.jsonl`, 26 soru, SHA-256 `3ecb65b4fd130b02fa34f5ca52f45012dc5fd913305c01a4b121812195d59cac` |
| Corpus fingerprint | `245685196f8082b298d0d0816de4fb8a48090210a7018a96469a9b843c377b54` |
| Embedding | `intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| LLM modeli (yapılandırılan) | `openai/gpt-6-luna`; generation_configured=true |
| Prompt | `answer-v5`, SHA-256 `42d1275e6cae26d7e48c1638ad8c570361e4130d2021fdf940a73027a59453bb` |
| top_k / skor eşiği | 4 / kapalı |
| Readiness koşu sonunda aynı | evet |

İsteklerdeki as_of değerlendirilen iş tarihidir (2026-10-04 (23 soru), 2026-04-10 (H11), 2026-06-30 (H12), 2026-02-09 (H13)); gerçek çalıştırma zamanıyla aynı kavram değildir.

## Otomatik ölçümler

Payda, kontrolün o soru ve modda uygulandığı sorulardır (tanımlar `docs/project-spec.md` §7). Değerlendirilemeyen: kontrol uygulanıyor ama API kullanılabilir bir cevap dönmedi.

| Ölçüm | Geçen / uygulanan | Başarısız | Değerlendirilemeyen |
|---|---|---|---|
| HTTP 200 ve istekle aynı request_id | 26 / 26 | — | — |
| Beklenen iş durumu | 22 / 22 | — | — |
| Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 22 / 22 | — | — |
| Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 0 / 0 | — | — |
| Doğru sürüm kararı (`version_decisions`) | 6 / 6 | — | — |
| Kaynak/aday geçerli: bölüm korpusta var, alıntı o bölümün birebir metni, belge/sürüm bilgisi bölüm kaydıyla aynı, getirilen bölüm, seçili sürüm, claim atıfları = `sources` (kaynak/aday yoksa uygulanmaz) | 26 / 26 | — | — |
| Cevaplanabilir soruda `insufficient_evidence` dönmedi (üretken mod) | 0 / 0 | — | — |
| Cevapsız soruda claim üretilmedi (üretken mod; claim'in anlamsal yanlışlığını ölçmez) | 0 / 0 | — | — |
| Gerekli bilgi kalıpları claim'lerde var (sınırlı; anlamsal değil) | 0 / 0 | — | — |
| Yasak bilgi kalıpları claim'lerde yok (sınırlı; anlamsal değil) | 0 / 0 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 4 / 4 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 0 / 0 | — | — |

## Soru bazında özet

| ID | Kategori | Beklenen durum | Gerçek | Beklenen bölüm | İlk k | Kaynak / aday | Başarısız kontroller | İnsan incelemesi |
|---|---|---|---|---|---|---|---|---|
| H01 | normal | evidence_only | evidence_only | D01#tamamlama | D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok | D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok | — | pending |
| H02 | normal | evidence_only | evidence_only | D02#sinir | D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi | D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi | — | pending |
| H03 | normal | evidence_only | evidence_only | D06#dogruluk | D10#musteri-istegi, D06#dogruluk, D01#kullanim, D06#alanlar | D10#musteri-istegi, D06#dogruluk, D01#kullanim, D06#alanlar | — | pending |
| H04 | normal | evidence_only | evidence_only | D07#iletisim | D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi | D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi | — | pending |
| H05 | normal | evidence_only | evidence_only | D08#saat-dilimi | D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim | D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim | — | pending |
| H06 | normal | evidence_only | evidence_only | D09#eposta | D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta | D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta | — | pending |
| H07 | normal | evidence_only | evidence_only | D10#musteri-istegi | D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim | D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim | — | pending |
| H08 | normal | evidence_only | evidence_only | D05#kullanim, D05#bedel | D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi | D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi | — | pending |
| H09 | version_conflict | evidence_only | evidence_only | D04#sure | D04#sure, D04#uygulama, D05#kullanim, D01#kullanim | D04#sure, D04#uygulama, D05#kullanim, D01#kullanim | — | pending |
| H10 | version_conflict | evidence_only | evidence_only | D04#kargo | D04#kargo, D05#bedel, D05#kullanim, D04#sure | D04#kargo, D05#bedel, D05#kullanim, D04#sure | — | pending |
| H11 | historical_version | evidence_only | evidence_only | D03#kargo | D03#kargo, D05#bedel, D03#sure, D05#kullanim | D03#kargo, D05#bedel, D03#sure, D05#kullanim | — | pending |
| H12 | historical_version | evidence_only | evidence_only | D03#uygulama, D03#sure | D03#sure, D03#uygulama, D05#bedel, D03#kargo | D03#sure, D03#uygulama, D05#bedel, D03#kargo | — | pending |
| H13 | historical_version | evidence_only | evidence_only | D03#sure | D03#sure, D05#bedel, D05#kullanim, D03#uygulama | D03#sure, D05#bedel, D05#kullanim, D03#uygulama | — | pending |
| H14 | unanswerable | — | evidence_only | — | D04#uygulama, D05#kullanim, D04#sure, D02#sinir | D04#uygulama, D05#kullanim, D04#sure, D02#sinir | — | pending |
| H15 | unanswerable | — | evidence_only | — | D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi | D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi | — | pending |
| H16 | unanswerable | — | evidence_only | — | D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir | D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir | — | pending |
| H17 | unanswerable | — | evidence_only | — | D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk | D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk | — | pending |
| H18 | partial | evidence_only | evidence_only | D08#saatler | D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim | D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim | — | pending |
| H19 | partial | evidence_only | evidence_only | D05#bedel | D05#kullanim, D05#bedel, D04#sure, D04#kargo | D05#kullanim, D05#bedel, D04#sure, D04#kargo | — | pending |
| H20 | partial | evidence_only | evidence_only | D06#alanlar | D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim | D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim | — | pending |
| H21 | false_premise | evidence_only | evidence_only | D04#sure | D04#sure, D05#bedel, D05#kullanim, D04#uygulama | D04#sure, D05#bedel, D05#kullanim, D04#uygulama | — | pending |
| H22 | false_premise | evidence_only | evidence_only | D06#alanlar | D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi | D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi | — | pending |
| H23 | false_premise | evidence_only | evidence_only | D01#baglanti | D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir | D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir | — | pending |
| H24 | multi_source | evidence_only | evidence_only | D06#alanlar, D10#paylasim | D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi | D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi | — | pending |
| H25 | multi_source | evidence_only | evidence_only | D09#sifre, D10#paylasim | D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim | D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim | — | pending |
| H26 | paraphrase | evidence_only | evidence_only | D09#sifre | D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta | D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta | — | pending |

## Ayrıntılar

### H01 · normal

- Soru: Panelde kulaklık kurulumunu kontrol ediyorum; hangi koşul sağlandığında MH-10 kurulumu tamamlanmış sayılır?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D01#tamamlama. Rubrik: Kurulum, MH-10 destek panelinde hem giriş hem çıkış aygıtı olarak seçildiğinde tamamlanır ve kulaklık panel görüşmelerinde kullanılabilir; belgede olmayan ek adım eklenmemeli.
  - Gerekli: MH-10 giriş aygıtı (mikrofon) olarak seçilmiş olmalıdır.
  - Gerekli: MH-10 çıkış aygıtı (hoparlör) olarak da seçilmiş olmalıdır.
  - Gerekli: İkisi de seçildiğinde kurulum tamamlanır ve kulaklık panel üzerinden yapılan görüşmelerde kullanılabilir.
  - Yasak: Kurulumun tamamlanması için belgede olmayan ek bir adım (ör. sürücü kurmak, test çağrısı yapmak, diğer uygulamaların ses ayarlarını değiştirmek) gerektiği.
- Gerçek: HTTP 200, `evidence_only`, 174 ms
  - İlk k: D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok; kaynak/aday: D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok
  - reason_code: —
  - Sürüm kararları: mh10-setup → D01; returns → D04 (D03 expired); audio-troubleshooting → D02
- İnsan incelemesi: pending

### H02 · normal

- Soru: Ses sorunu yaşayan müşteriye ses kartı sürücüsünü güncellemesini tavsiye edebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D02#sinir. Rubrik: Hayır: ses sorunu belgesi yalnızca kendi kontrollerini içerir; sürücü veya işletim sistemi değişikliği müşteriye önerilmez, sorun sürerse destek talebiyle ilerlenir.
  - Gerekli: Hayır; sürücü veya işletim sistemi ayarı gibi belgede yer almayan teknik işlemler müşteriye önerilmez.
  - Gerekli: Sorun sürüyorsa destek talebiyle (ticket) ilerlenir.
  - Yasak: Müşteriye sürücü güncelleme veya işletim sistemi ayarı değiştirme adımı tarif etmek.
- Gerçek: HTTP 200, `evidence_only`, 37 ms
  - İlk k: D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi; kaynak/aday: D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: audio-troubleshooting → D02; safe-support-sharing → D10
- İnsan incelemesi: pending

### H03 · normal

- Soru: Destek talebinde sorunu anlatmak için sadece 'kulaklık çalışmıyor' yazsam yeterli olur mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D06#dogruluk. Rubrik: Hayır: 'çalışmıyor' gibi genel ifade yerine adımlar yapıldıkları sırayla, her adımdan sonra ekranda görüleni belirterek ve destek ekibinin sorunu aynı adımlarla görebileceği açıklıkta yazılmalı.
  - Gerekli: Hayır; 'çalışmıyor' gibi genel bir ifade yeterli değildir.
  - Gerekli: Adımlar yapıldıkları sırayla yazılır.
  - Gerekli: Her adımdan sonra ekranda ne görüldüğü belirtilir.
  - Gerekli: Adımlar, destek ekibinin aynı adımları izleyerek sorunu görebileceği açıklıkta olmalıdır.
  - Yasak: Genel bir ifadenin yeterli olduğu.
- Gerçek: HTTP 200, `evidence_only`, 26 ms
  - İlk k: D10#musteri-istegi, D06#dogruluk, D01#kullanim, D06#alanlar; kaynak/aday: D10#musteri-istegi, D06#dogruluk, D01#kullanim, D06#alanlar
  - reason_code: —
  - Sürüm kararları: safe-support-sharing → D10; support-ticket → D06; mh10-setup → D01
- İnsan incelemesi: pending

### H04 · normal

- Soru: Müşteri, P1 olayındaki ilk yanıt hedefini sorunun çözüleceği süre sanıyor. Ona farkı nasıl açıklamalıyım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D07#iletisim. Rubrik: İlk yanıt, destek ekibinin olaya verdiği ilk dönüştür; çözüm süresi belgede tanımlı değildir ve olayın niteliğine göre değişebilir; hedef çözüm süresi gibi sunulmamalı.
  - Gerekli: İlk yanıt, destek ekibinin olaya verdiği ilk dönüştür.
  - Gerekli: Çözümün ne kadar süreceği tanımlanmamıştır; olayın niteliğine göre değişebilir.
  - Gerekli: İlk yanıt hedefi çözüm süresi gibi sunulmaz; 'ilk yanıt' ifadesi kullanılır.
  - Yasak: Sorunun ilk yanıt hedefi içinde (ör. 2 çalışma saatinde) çözüleceği veya bir çözüm süresi garantisi verilmesi.
- Gerçek: HTTP 200, `evidence_only`, 34 ms
  - İlk k: D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi; kaynak/aday: D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: priority-sla → D07; safe-support-sharing → D10
- İnsan incelemesi: pending

### H05 · normal

- Soru: Müşteriye destek saatlerini bildirirken sadece 'mesai saatleri içinde ulaşabilirsiniz' demem yeterli mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D08#saat-dilimi. Rubrik: Hayır: yalnızca 'mesai saatleri' demek yetmez; başlangıç ve bitiş saati birlikte ve saat dilimiyle, başka dilime çevrilmeden Türkiye saati olarak verilmeli.
  - Gerekli: Hayır; başlangıç ve bitiş saati birlikte verilir.
  - Gerekli: Saat dilimi de yazılır: saatler başka bir saat dilimine çevrilmeden Türkiye saati (Europe/Istanbul) olarak ifade edilir.
  - Yasak: Yalnızca 'mesai saatleri' demenin yeterli olduğu.
  - Yasak: Saatlerin müşterinin kendi saat dilimine çevrilmesi gerektiği.
- Gerçek: HTTP 200, `evidence_only`, 41 ms
  - İlk k: D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim; kaynak/aday: D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim
  - reason_code: —
  - Sürüm kararları: support-hours → D08; support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### H06 · normal

- Soru: Kullanıcı parola sıfırlama bağlantısını telefonuna SMS olarak almak istiyor. Bağlantıyı ona SMS ile gönderebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D09#eposta. Rubrik: Hayır: sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir; temsilci bağlantıyı başka bir adrese veya kanala göndermeyi teklif etmez.
  - Gerekli: Hayır; sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir.
  - Gerekli: Destek temsilcisi bağlantıyı başka bir adrese göndermeyi teklif etmez.
  - Yasak: Bağlantının SMS ile gönderilebileceği.
  - Yasak: Bağlantının başka bir kanal veya adres üzerinden gönderilebileceği.
- Gerçek: HTTP 200, `evidence_only`, 42 ms
  - İlk k: D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta; kaynak/aday: D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta
  - reason_code: —
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: pending

### H07 · normal

- Soru: Müşteri sorunu anlatırken parolasını destek talebinin açıklamasına yazmak istiyor. Ona nasıl karşılık vermeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D10#musteri-istegi. Rubrik: Müşteriye parolasını paylaşmaması gerektiği nazikçe söylenmeli; parola destek talebinde paylaşılmaz.
  - Gerekli: Müşteriye parolasını paylaşmaması gerektiği söylenir.
  - Gerekli: Bu nazikçe söylenir.
  - Yasak: Parolanın talebe yazılabileceği veya temsilcinin parolayı isteyebileceği.
- Gerçek: HTTP 200, `evidence_only`, 23 ms
  - İlk k: D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim; kaynak/aday: D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim
  - reason_code: —
  - Sürüm kararları: safe-support-sharing → D10; priority-sla → D07; account-access → D09
- İnsan incelemesi: pending

### H08 · normal

- Soru: Müşteri iade bedeli için ona belirli bir ödeme günü söylememi istiyor. Belirli bir gün taahhüt edebilir miyim, yoksa ona ne söylemeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D05#kullanim, D05#bedel. Rubrik: Hayır: belgede yazmayan bir ödeme tarihi taahhüt edilmez; müşteriye yalnızca bedelin iadenin kabulünden sonra 5 iş günü içinde ödendiği söylenebilir.
  - Gerekli: Hayır; belgede yazmayan bir ödeme tarihi müşteriye taahhüt edilmez.
  - Gerekli: İade bedeli iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir.
  - Yasak: Belirli bir takvim tarihi (gün/ay) taahhüt etmek.
  - Yasak: Sürenin takvim günüyle sayıldığı (ör. 5 takvim günü).
  - Yasak: Sürenin kargoya verildiği günden başladığı.
- Gerçek: HTTP 200, `evidence_only`, 22 ms
  - İlk k: D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi; kaynak/aday: D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired); safe-support-sharing → D10
- İnsan incelemesi: pending

### H09 · version_conflict

- Soru: Müşteri MH-10'u 10 Eylül 2026'da teslim aldı ve bugün (4 Ekim 2026) iade talebi açmak istiyor. Hâlâ iade süresi içinde mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: Evet: as_of=2026-10-04 için 2.0 sürümünde iade talebi teslimden itibaren 30 takvim günü içinde açılabilir; 10 Eylül'den 4 Ekim'e 24 gün geçtiği için süre dolmamıştır. 14 gün kuralı uygulanmamalı; D04 seçili, D03 expired.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: Süre teslim tarihinden sayılır.
  - Gerekli: Evet; 4 Ekim, 10 Eylül'deki teslimden sonraki 30 takvim günü içindedir, talep süresi içindedir.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
  - Yasak: Sürenin dolduğu veya talebin süre dışında kaldığı.
- Gerçek: HTTP 200, `evidence_only`, 28 ms
  - İlk k: D04#sure, D04#uygulama, D05#kullanim, D01#kullanim; kaynak/aday: D04#sure, D04#uygulama, D05#kullanim, D01#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; mh10-setup → D01
- İnsan incelemesi: pending

### H10 · version_conflict

- Soru: Müşteri iade talebi açarken ona iade kargosunun ücretini kendisinin ödeyeceğini söylemeli miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#kargo. Rubrik: Hayır: güncel 2.0 sürümünde şirket, talebi onaylanan müşteriye iade etiketi sağlar ve etiketli gönderimin kargo bedelini karşılar; müşterinin ödediği söylenmemeli. D04 seçili, D03 expired.
  - Gerekli: Hayır; şirket, iade talebi onaylanan müşteriye bir iade etiketi sağlar.
  - Gerekli: Bu etiketle yapılan gönderimin kargo bedelini şirket karşılar.
  - Yasak: Kargo bedelini müşterinin ödediği (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `evidence_only`, 27 ms
  - İlk k: D04#kargo, D05#bedel, D05#kullanim, D04#sure; kaynak/aday: D04#kargo, D05#bedel, D05#kullanim, D04#sure
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: pending

### H11 · historical_version

- Soru: Bugün açılan bir iade talebinde müşteriyi iade kargosu konusunda ne zaman ve neyle ilgili bilgilendirmeliyim?
- İstek: as_of `2026-04-10`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D03#kargo. Rubrik: as_of=2026-04-10 için 1.0 sürümü: iade kargosunun bedelini müşteri öder ve bu bilgi müşteriye iade talebi açılırken verilir; etiket veya şirketin ödediği söylenmemeli. D03 seçili, D04 future_effective.
  - Gerekli: İade kargosunun bedelini müşteri öder; ürün geri gönderilirken oluşan kargo ücreti müşteriye aittir.
  - Gerekli: Bu bilgi iade talebi açılırken verilir; müşteri ürünü göndermeden önce bunu bilir.
  - Yasak: Şirketin iade etiketi sağladığı (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Kargo bedelini şirketin karşıladığı (2.0 sürümü).
- Gerçek: HTTP 200, `evidence_only`, 33 ms
  - İlk k: D03#kargo, D05#bedel, D03#sure, D05#kullanim; kaynak/aday: D03#kargo, D05#bedel, D03#sure, D05#kullanim
  - reason_code: —
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: pending

### H12 · historical_version

- Soru: Bugün açılan bir iade talebi hangi prosedür sürümüne göre değerlendirilir ve müşterinin teslimden itibaren kaç günü vardır?
- İstek: as_of `2026-06-30`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D03#uygulama, D03#sure. Rubrik: as_of=2026-06-30 (1.0 sürümünün son geçerli günü): talep 1.0 sürümüne göre değerlendirilir ve müşteri iade talebini teslimden itibaren 14 takvim günü içinde açabilir; 2.0 veya 30 gün denmemeli. D03 seçili, D04 future_effective.
  - Gerekli: Talep 1.0 sürümüne göre değerlendirilir (1 Temmuz 2026'dan önce açılan talepler).
  - Gerekli: İade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Talebin 2.0 sürümüne göre değerlendirileceği.
- Gerçek: HTTP 200, `evidence_only`, 27 ms
  - İlk k: D03#sure, D03#uygulama, D05#bedel, D03#kargo; kaynak/aday: D03#sure, D03#uygulama, D05#bedel, D03#kargo
  - reason_code: —
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: pending

### H13 · historical_version

- Soru: Bugün iade talebi açmak isteyen bir müşterinin süresi hesaplanırken cumartesi ve pazar günleri de sayılıyor mu? Teslimden itibaren toplam kaç günü var?
- İstek: as_of `2026-02-09`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D03#sure. Rubrik: as_of=2026-02-09 için 1.0 sürümü: süre teslimden itibaren 14 takvim günüdür ve hafta sonları dâhildir; iş günü veya 30 gün denmemeli. D03 seçili, D04 future_effective.
  - Gerekli: İade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Gerekli: Takvim günü hesabına hafta sonları (cumartesi ve pazar) da dâhildir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Sürenin iş günüyle sayıldığı veya hafta sonlarının sayılmadığı.
- Gerçek: HTTP 200, `evidence_only`, 24 ms
  - İlk k: D03#sure, D05#bedel, D05#kullanim, D03#uygulama; kaynak/aday: D03#sure, D05#bedel, D05#kullanim, D03#uygulama
  - reason_code: —
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: pending

### H14 · unanswerable

- Soru: Elli adet MH-10 alırsak toplu alım indirimi uygulanıyor mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: fiyat ve toplu alım indirimi belgelerde yok; oran veya fiyat uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Herhangi bir indirim oranı veya fiyat.
  - Yasak: İndirim uygulandığı veya uygulanmadığı yönünde bir taahhüt.
- Gerçek: HTTP 200, `evidence_only`, 38 ms
  - İlk k: D04#uygulama, D05#kullanim, D04#sure, D02#sinir; kaynak/aday: D04#uygulama, D05#kullanim, D04#sure, D02#sinir
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; audio-troubleshooting → D02
- İnsan incelemesi: pending

### H15 · unanswerable

- Soru: Destek panelinde iki aşamalı doğrulamayı (2FA) kendi hesabım için nasıl açarım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: iki aşamalı doğrulamanın nasıl açılacağı belgelerde yok; OTP paylaşım kuralı veya parola sıfırlama bu sorunun cevabı gibi sunulmamalı.
  - Yasak: Belgelerde olmayan bir 2FA etkinleştirme adımı (ör. ayarlar menüsünden açmak).
  - Yasak: OTP paylaşım kuralını veya parola sıfırlama adımlarını 2FA'yı açma yöntemi gibi sunmak.
- Gerçek: HTTP 200, `evidence_only`, 26 ms
  - İlk k: D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi; kaynak/aday: D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: pending

### H16 · unanswerable

- Soru: MH-10'un kulak süngerleri yıprandı; yedek süngeri nereden sipariş edebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: yedek parça ve sipariş kanalı belgelerde yok; kanal veya fiyat uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Yedek parça için bir sipariş kanalı, fiyat, adres veya bağlantı uydurmak.
- Gerçek: HTTP 200, `evidence_only`, 29 ms
  - İlk k: D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir; kaynak/aday: D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir
  - reason_code: —
  - Sürüm kararları: audio-troubleshooting → D02; returns → D04 (D03 expired); mh10-setup → D01
- İnsan incelemesi: pending

### H17 · unanswerable

- Soru: Yeni işe başlayan bir temsilci için destek panelinde kullanıcı hesabını nasıl oluştururum?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: destek panelinde kullanıcı hesabı oluşturma belgelerde yok; yeni temsilci için kulaklık kurulum adımları hesap açma yöntemi gibi sunulmamalı.
  - Yasak: MH-10 kurulum adımlarını veya parola sıfırlamayı kullanıcı hesabı oluşturma yöntemi gibi sunmak.
  - Yasak: Belgelerde olmayan bir hesap açma adımı uydurmak.
- Gerçek: HTTP 200, `evidence_only`, 16 ms
  - İlk k: D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk; kaynak/aday: D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk
  - reason_code: —
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: pending

### H18 · partial

- Soru: Cuma günü Türkiye saatiyle 19.00'da destek ekibine ulaşabilir miyim? Ulaşabileceğim telefon numarası nedir?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `partial`; bölümler D08#saatler. Rubrik: partial: destek ekibine hafta içi 09.00–18.00 (Türkiye saati) arasında ulaşılabildiği için cuma 19.00'da ulaşılamaz (kaynaklı); telefon numarası belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: Hayır; destek ekibine hafta içi 09.00–18.00 arasında ulaşılabilir, 19.00 bu saatlerin dışındadır.
  - Gerekli: Telefon numarası eksik konu olarak ayrılır.
  - Yasak: Bir telefon numarası uydurmak.
  - Yasak: Cuma 19.00'da destek ekibine ulaşılabileceği.
- Gerçek: HTTP 200, `evidence_only`, 25 ms
  - İlk k: D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim; kaynak/aday: D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim
  - reason_code: —
  - Sürüm kararları: support-hours → D08; support-ticket → D06
- İnsan incelemesi: pending

### H19 · partial

- Soru: İadesi kabul edilen MH-10'un bedeli kaç iş gününde ödenir? Ödeme kredi kartına mı yapılır, banka hesabına mı?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `partial`; bölümler D05#bedel. Rubrik: partial: bedel iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir (kaynaklı); ödemenin kredi kartına mı banka hesabına mı yapılacağı belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: İade bedeli iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir.
  - Gerekli: Ödeme yöntemi (kredi kartı / banka hesabı) eksik konu olarak ayrılır.
  - Yasak: Ödemenin belirli bir yönteme (kredi kartı veya banka hesabı) yapıldığı.
  - Yasak: Sürenin takvim günüyle sayıldığı (ör. 5 takvim günü).
  - Yasak: Sürenin kargoya verildiği günden başladığı.
- Gerçek: HTTP 200, `evidence_only`, 31 ms
  - İlk k: D05#kullanim, D05#bedel, D04#sure, D04#kargo; kaynak/aday: D05#kullanim, D05#bedel, D04#sure, D04#kargo
  - reason_code: —
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

### H20 · partial

- Soru: Destek talebine MH-10'un seri numarasını yazmam gerekiyor mu? Talebe en fazla kaç dosya ekleyebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `partial`; bölümler D06#alanlar. Rubrik: partial: seri numarası talebe yazılması gereken bilgilerdendir (kaynaklı); eklenebilecek dosya sayısı belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: Evet; seri numarası talepte bulunması gereken bilgilerdendir.
  - Gerekli: Dosya sayısı sınırı eksik konu olarak ayrılır.
  - Yasak: Talebe eklenebilecek dosya sayısı veya boyutu için bir sınır uydurmak.
  - Yasak: Seri numarasının gerekmediği.
- Gerçek: HTTP 200, `evidence_only`, 27 ms
  - İlk k: D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim; kaynak/aday: D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim
  - reason_code: —
  - Sürüm kararları: support-ticket → D06; audio-troubleshooting → D02
- İnsan incelemesi: pending

### H21 · false_premise

- Soru: Müşteriye iade süresinin, iade talebini açtığı günden itibaren işlemeye başladığını söyledim. Bu doğru mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: Yanlış ön kabul düzeltilmeli: iade süresi teslim tarihinden sayılır; talebin açıldığı tarih süreyi başlatmaz, yalnızca uygulanacak sürümü belirler. Süre söylenirse 2.0'a göre 30 takvim günüdür; D04 seçili, D03 expired.
  - Gerekli: Hayır; süre ürünün teslim tarihinden sayılır.
  - Gerekli: İade talebinin açıldığı tarih süreyi başlatmaz; yalnızca hangi prosedür sürümünün uygulanacağını belirler.
  - Gerekli: Süre belirtilirse: teslimden itibaren 30 takvim günü.
  - Yasak: Sürenin iade talebinin açıldığı günden başladığını onaylamak.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `evidence_only`, 41 ms
  - İlk k: D04#sure, D05#bedel, D05#kullanim, D04#uygulama; kaynak/aday: D04#sure, D05#bedel, D05#kullanim, D04#uygulama
  - reason_code: —
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: pending

### H22 · false_premise

- Soru: Ekranda hata kodu çıkmadığı için destek talebi açamıyoruz, değil mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar. Rubrik: Yanlış ön kabul düzeltilmeli: hata kodu görüntülenmediyse bu alan boş bırakılabilir; talep seri numarası ve yeniden üretme adımlarıyla açılır.
  - Gerekli: Hayır; hata kodu görüntülenmediyse bu bilgi boş bırakılabilir.
  - Gerekli: Talep seri numarası ve sorunu yeniden üretme adımlarıyla açılır.
  - Yasak: Hata kodu olmadan destek talebi açılamayacağı.
- Gerçek: HTTP 200, `evidence_only`, 20 ms
  - İlk k: D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi; kaynak/aday: D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### H23 · false_premise

- Soru: MH-10'u panelde yalnızca hoparlör (çıkış aygıtı) olarak seçmem yeterli, mikrofonu ayrıca seçmeme gerek yok, değil mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D01#baglanti. Rubrik: Yanlış ön kabul düzeltilmeli: yalnızca birini seçmek yetmez; MH-10 hem giriş hem çıkış aygıtı olarak seçilmeli, giriş aygıtı seçilmezse müşteri temsilciyi duyamaz.
  - Gerekli: Hayır; MH-10 hem giriş (mikrofon) hem çıkış (hoparlör) aygıtı olarak seçilmelidir.
  - Gerekli: Giriş aygıtı seçilmezse müşteri temsilciyi duyamaz.
  - Yasak: Yalnızca çıkış aygıtı seçmenin yeterli olduğu.
- Gerçek: HTTP 200, `evidence_only`, 39 ms
  - İlk k: D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir; kaynak/aday: D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir
  - reason_code: —
  - Sürüm kararları: mh10-setup → D01; audio-troubleshooting → D02
- İnsan incelemesi: pending

### H24 · multi_source

- Soru: Panelde aldığımız hata için ekran görüntüsüyle birlikte ticket açacağız. Ticket'a neler yazılmalı ve görüntüyü yüklemeden önce üzerindeki hangi bilgileri kapatmalıyız?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar, D10#paylasim. Rubrik: İki kaynak birlikte: talebe seri numarası, görüntülendiyse hata kodu ve yeniden üretme adımları yazılır (D06#alanlar); görüntüdeki ad, telefon numarası ve e-posta adresi gibi kişisel bilgiler paylaşmadan önce gizlenir (D10#paylasim).
  - Gerekli: MH-10'un seri numarası.
  - Gerekli: Ekranda görüntülendiyse hata kodu.
  - Gerekli: Sorunu yeniden üretme adımları.
  - Gerekli: Görüntü paylaşılmadan önce görseldeki kişisel bilgiler gizlenir.
  - Gerekli: Gizlenecek kişisel bilgilere örnek: ad, telefon numarası, e-posta adresi.
  - Yasak: Görselin kişisel bilgiler gizlenmeden paylaşılabileceği.
  - Yasak: Talebe parola veya OTP yazılması.
- Gerçek: HTTP 200, `evidence_only`, 43 ms
  - İlk k: D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi; kaynak/aday: D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi
  - reason_code: —
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### H25 · multi_source

- Soru: Parolasını unutan bir kullanıcı panele yeniden nasıl girer? Bu sırada ondan telefonuna gelen doğrulama kodunu (OTP) isteyebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre, D10#paylasim. Rubrik: İki kaynak birlikte: kullanıcı giriş ekranından sıfırlama ister, bağlantı kayıtlı e-posta adresine gelir ve yeni parola belirlenir (D09#sifre); OTP paylaşılmaz ve destek personeli istemez (D10#paylasim).
  - Gerekli: Kullanıcı giriş ekranından parola sıfırlama isteğinde bulunur.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir; kullanıcı bağlantıyla yeni parolasını belirler.
  - Gerekli: Hayır; OTP destek personeliyle paylaşılmaz, destek personeli de istemez.
  - Yasak: Temsilcinin OTP veya parola isteyebileceği.
- Gerçek: HTTP 200, `evidence_only`, 21 ms
  - İlk k: D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim; kaynak/aday: D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim
  - reason_code: —
  - Sürüm kararları: safe-support-sharing → D10; account-access → D09
- İnsan incelemesi: pending

### H26 · paraphrase

- Soru: Şifremi hatırlamıyorum, panele bir türlü giriş yapamıyorum. Hesabıma tekrar nasıl girerim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `evidence_only`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre. Rubrik: 'Şifre' kelimesiyle sorulan parola sıfırlama: giriş ekranından sıfırlama istenir, bağlantı hesapta kayıtlı e-posta adresine gelir, kullanıcı yeni parolasını belirleyip onunla giriş yapar.
  - Gerekli: Giriş ekranından parola sıfırlama isteğinde bulunulur.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir.
  - Gerekli: Bağlantı açılarak yeni parola belirlenir ve yeni parolayla giriş yapılır.
  - Yasak: Bağlantının görüşmede söylenen başka bir adrese gönderilebileceği veya temsilcinin parolayı söyleyeceği.
- Gerçek: HTTP 200, `evidence_only`, 27 ms
  - İlk k: D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta; kaynak/aday: D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta
  - reason_code: —
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: pending

