# Değerlendirme raporu: `20261005-005747-generative-holdout`

Bu dosyayı `eval/run_eval.py` üretti. Otomatik kontroller durumları, bölüm kimliklerini, sürüm kararlarını, alıntıları ve claim metinlerinde birkaç düzenli ifadeyi karşılaştırır; anlamsal doğruluğu ölçmez. Her sorunun insan incelemesi `pending` başlar.

## Koşu bilgileri

| Alan | Değer |
|---|---|
| Gerçek çalıştırma zamanı | 2026-10-05T00:57:47+03:00 → 2026-10-05T00:58:36+03:00 |
| Mod | `generative` |
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
| HTTP 200 ve istekle aynı request_id | 25 / 26 | H03 | — |
| Beklenen iş durumu | 23 / 26 | H05, H09 | H03 |
| Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 21 / 22 | — | H03 |
| Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 21 / 22 | — | H03 |
| Doğru sürüm kararı (`version_decisions`) | 6 / 6 | — | — |
| Kaynak/aday geçerli: bölüm korpusta var, alıntı o bölümün birebir metni, belge/sürüm bilgisi bölüm kaydıyla aynı, getirilen bölüm, seçili sürüm, claim atıfları = `sources` (kaynak/aday yoksa uygulanmaz) | 21 / 22 | — | H03 |
| Cevaplanabilir soruda `insufficient_evidence` dönmedi (üretken mod) | 21 / 22 | — | H03 |
| Cevapsız soruda claim üretilmedi (üretken mod; claim'in anlamsal yanlışlığını ölçmez) | 4 / 4 | — | — |
| Gerekli bilgi kalıpları claim'lerde var (sınırlı; anlamsal değil) | 19 / 22 | H02, H23 | H03 |
| Yasak bilgi kalıpları claim'lerde yok (sınırlı; anlamsal değil) | 12 / 12 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 4 / 4 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 4 / 4 | — | — |

## Soru bazında özet

| ID | Kategori | Beklenen durum | Gerçek | Beklenen bölüm | İlk k | Kaynak / aday | Başarısız kontroller | İnsan incelemesi |
|---|---|---|---|---|---|---|---|---|
| H01 | normal | answered | answered | D01#tamamlama | D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok | D01#tamamlama | — | doğru |
| H02 | normal | answered | answered | D02#sinir | D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi | D02#sinir | required_facts | kabul edilebilir: 'sorun sürerse destek talebi' söylenmedi (generation) |
| H03 | normal | answered | error:invalid_generation_output | D06#dogruluk | — | — | http | yanlış: model partial dedi ama eksik konu yazmadı; sunucu 502 ile reddetti (validation) |
| H04 | normal | answered | answered | D07#iletisim | D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi | D07#p1, D07#iletisim | — | doğru |
| H05 | normal | answered | partial | D08#saat-dilimi | D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim | D08#saat-dilimi | status | kabul edilebilir: cevap doğru; D08#saatler ilk 4'te olmadığı için saatleri eksik konu olarak ekledi (retrieval) |
| H06 | normal | answered | answered | D09#eposta | D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta | D09#sifre, D09#eposta | — | doğru |
| H07 | normal | answered | answered | D10#musteri-istegi | D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim | D10#musteri-istegi, D10#paylasim | — | doğru |
| H08 | normal | answered | answered | D05#kullanim, D05#bedel | D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi | D05#bedel, D05#kullanim | — | doğru |
| H09 | version_conflict | answered | partial | D04#sure | D04#sure, D04#uygulama, D05#kullanim, D01#kullanim | D04#sure | status | kabul edilebilir: 30 takvim günü kuralı doğru; iki tarih arasını bilerek hesaplamıyor (generation, tasarım tercihi) |
| H10 | version_conflict | answered | answered | D04#kargo | D04#kargo, D05#bedel, D05#kullanim, D04#sure | D04#kargo | — | doğru |
| H11 | historical_version | answered | answered | D03#kargo | D03#kargo, D05#bedel, D03#sure, D05#kullanim | D03#kargo | — | doğru |
| H12 | historical_version | answered | answered | D03#uygulama, D03#sure | D03#sure, D03#uygulama, D05#bedel, D03#kargo | D03#uygulama, D03#sure | — | doğru |
| H13 | historical_version | answered | answered | D03#sure | D03#sure, D05#bedel, D05#kullanim, D03#uygulama | D03#sure | — | doğru |
| H14 | unanswerable | insufficient_evidence | insufficient_evidence | — | D04#uygulama, D05#kullanim, D04#sure, D02#sinir | — | — | doğru |
| H15 | unanswerable | insufficient_evidence | insufficient_evidence | — | D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi | — | — | doğru |
| H16 | unanswerable | insufficient_evidence | insufficient_evidence | — | D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir | — | — | doğru |
| H17 | unanswerable | insufficient_evidence | insufficient_evidence | — | D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk | — | — | doğru |
| H18 | partial | partial | partial | D08#saatler | D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim | D08#saatler | — | doğru |
| H19 | partial | partial | partial | D05#bedel | D05#kullanim, D05#bedel, D04#sure, D04#kargo | D05#kullanim, D05#bedel | — | doğru |
| H20 | partial | partial | partial | D06#alanlar | D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim | D06#alanlar | — | doğru |
| H21 | false_premise | answered | answered | D04#sure | D04#sure, D05#bedel, D05#kullanim, D04#uygulama | D04#sure, D04#uygulama | — | doğru |
| H22 | false_premise | answered | answered | D06#alanlar | D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi | D06#alanlar | — | doğru |
| H23 | false_premise | answered | answered | D01#baglanti | D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir | D01#baglanti | required_facts | kabul edilebilir: ön kabul düzeltildi; 'giriş seçilmezse müşteri temsilciyi duyamaz' söylenmedi (generation) |
| H24 | multi_source | answered | answered | D06#alanlar, D10#paylasim | D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi | D06#alanlar, D06#kullanim, D10#paylasim | — | doğru |
| H25 | multi_source | answered | answered | D09#sifre, D10#paylasim | D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim | D09#sifre, D09#kullanim, D10#paylasim | — | doğru |
| H26 | paraphrase | answered | answered | D09#sifre | D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta | D09#sifre | — | doğru |

## Ayrıntılar

### H01 · normal

- Soru: Panelde kulaklık kurulumunu kontrol ediyorum; hangi koşul sağlandığında MH-10 kurulumu tamamlanmış sayılır?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D01#tamamlama. Rubrik: Kurulum, MH-10 destek panelinde hem giriş hem çıkış aygıtı olarak seçildiğinde tamamlanır ve kulaklık panel görüşmelerinde kullanılabilir; belgede olmayan ek adım eklenmemeli.
  - Gerekli: MH-10 giriş aygıtı (mikrofon) olarak seçilmiş olmalıdır.
  - Gerekli: MH-10 çıkış aygıtı (hoparlör) olarak da seçilmiş olmalıdır.
  - Gerekli: İkisi de seçildiğinde kurulum tamamlanır ve kulaklık panel üzerinden yapılan görüşmelerde kullanılabilir.
  - Yasak: Kurulumun tamamlanması için belgede olmayan ek bir adım (ör. sürücü kurmak, test çağrısı yapmak, diğer uygulamaların ses ayarlarını değiştirmek) gerektiği.
- Gerçek: HTTP 200, `answered`, 1894 ms
  - İlk k: D01#tamamlama, D01#kullanim, D04#sure, D02#ses-yok; kaynak/aday: D01#tamamlama
  - reason_code: —
  - Claim: MH-10 hem giriş hem de çıkış aygıtı olarak seçildiğinde destek panelindeki kurulum tamamlanmış sayılır. [D01#tamamlama]
  - Cevap: MH-10 hem giriş hem de çıkış aygıtı olarak seçildiğinde destek panelindeki kurulum tamamlanmış sayılır.
  - Sürüm kararları: mh10-setup → D01; returns → D04 (D03 expired); audio-troubleshooting → D02
- İnsan incelemesi: doğru

### H02 · normal

- Soru: Ses sorunu yaşayan müşteriye ses kartı sürücüsünü güncellemesini tavsiye edebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D02#sinir. Rubrik: Hayır: ses sorunu belgesi yalnızca kendi kontrollerini içerir; sürücü veya işletim sistemi değişikliği müşteriye önerilmez, sorun sürerse destek talebiyle ilerlenir.
  - Gerekli: Hayır; sürücü veya işletim sistemi ayarı gibi belgede yer almayan teknik işlemler müşteriye önerilmez.
  - Gerekli: Sorun sürüyorsa destek talebiyle (ticket) ilerlenir.
  - Yasak: Müşteriye sürücü güncelleme veya işletim sistemi ayarı değiştirme adımı tarif etmek.
- Gerçek: HTTP 200, `answered`, 1571 ms
  - İlk k: D02#sinir, D02#ses-yok, D02#kullanim, D10#musteri-istegi; kaynak/aday: D02#sinir
  - reason_code: —
  - Claim: MH-10 ile yaşanan ses sorunlarında ses kartı sürücüsünü güncellemeyi müşteriye önermeyin; belgede yer almayan sürücü değişiklikleri önerilmemelidir. [D02#sinir]
  - Cevap: MH-10 ile yaşanan ses sorunlarında ses kartı sürücüsünü güncellemeyi müşteriye önermeyin; belgede yer almayan sürücü değişiklikleri önerilmemelidir.
  - Sürüm kararları: audio-troubleshooting → D02; safe-support-sharing → D10
- Kontrol sorunu: required_facts: bulunamadı: Sorun sürüyorsa destek talebiyle (ticket) ilerlenir.
- İnsan incelemesi: kabul edilebilir: 'sorun sürerse destek talebi' söylenmedi (generation)

### H03 · normal

- Soru: Destek talebinde sorunu anlatmak için sadece 'kulaklık çalışmıyor' yazsam yeterli olur mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D06#dogruluk. Rubrik: Hayır: 'çalışmıyor' gibi genel ifade yerine adımlar yapıldıkları sırayla, her adımdan sonra ekranda görüleni belirterek ve destek ekibinin sorunu aynı adımlarla görebileceği açıklıkta yazılmalı.
  - Gerekli: Hayır; 'çalışmıyor' gibi genel bir ifade yeterli değildir.
  - Gerekli: Adımlar yapıldıkları sırayla yazılır.
  - Gerekli: Her adımdan sonra ekranda ne görüldüğü belirtilir.
  - Gerekli: Adımlar, destek ekibinin aynı adımları izleyerek sorunu görebileceği açıklıkta olmalıdır.
  - Yasak: Genel bir ifadenin yeterli olduğu.
- Gerçek: HTTP 502, `error:invalid_generation_output`, 2312 ms
  - Gövde: `{"request_id": "eval.20261005-005747-generative-holdout.H03", "error": {"code": "invalid_generation_output", "message": "Dil modelinin cevabı kaynak doğrulamasından geçmedi; güvenilir bir cevap üretilemedi."}}`
- Kontrol sorunu: http: HTTP 502 error:invalid_generation_output
- İnsan incelemesi: yanlış: model partial dedi ama eksik konu yazmadı; sunucu 502 ile reddetti (validation)

### H04 · normal

- Soru: Müşteri, P1 olayındaki ilk yanıt hedefini sorunun çözüleceği süre sanıyor. Ona farkı nasıl açıklamalıyım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D07#iletisim. Rubrik: İlk yanıt, destek ekibinin olaya verdiği ilk dönüştür; çözüm süresi belgede tanımlı değildir ve olayın niteliğine göre değişebilir; hedef çözüm süresi gibi sunulmamalı.
  - Gerekli: İlk yanıt, destek ekibinin olaya verdiği ilk dönüştür.
  - Gerekli: Çözümün ne kadar süreceği tanımlanmamıştır; olayın niteliğine göre değişebilir.
  - Gerekli: İlk yanıt hedefi çözüm süresi gibi sunulmaz; 'ilk yanıt' ifadesi kullanılır.
  - Yasak: Sorunun ilk yanıt hedefi içinde (ör. 2 çalışma saatinde) çözüleceği veya bir çözüm süresi garantisi verilmesi.
- Gerçek: HTTP 200, `answered`, 1832 ms
  - İlk k: D07#iletisim, D07#p1, D07#kullanim, D10#musteri-istegi; kaynak/aday: D07#p1, D07#iletisim
  - reason_code: —
  - Claim: P1 olaylarında ilk yanıt hedefi 2 çalışma saatidir; bu, destek ekibinin ilk yanıtı ne zaman vereceğini belirtir, olayın bu süre içinde çözüleceği anlamına gelmez ve çözüm süresi garantisi değildir. [D07#p1]
  - Claim: Müşteriye ilk yanıtın destek ekibinin olaya verdiği ilk yanıt olduğunu açıklayın; çözümün ne kadar süreceği bu belgede tanımlanmamıştır ve olayın niteliğine göre değişebilir. [D07#iletisim]
  - Cevap: P1 olaylarında ilk yanıt hedefi 2 çalışma saatidir; bu, destek ekibinin ilk yanıtı ne zaman vereceğini belirtir, olayın bu süre içinde çözüleceği anlamına gelmez ve çözüm süresi garantisi değildir. Müşteriye ilk yanıtın destek ekibinin olaya verdiği ilk yanıt olduğunu açıklayın; çözümün ne kadar süreceği bu belgede tanımlanmamıştır ve olayın niteliğine göre değişebilir.
  - Sürüm kararları: priority-sla → D07; safe-support-sharing → D10
- İnsan incelemesi: doğru

### H05 · normal

- Soru: Müşteriye destek saatlerini bildirirken sadece 'mesai saatleri içinde ulaşabilirsiniz' demem yeterli mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D08#saat-dilimi. Rubrik: Hayır: yalnızca 'mesai saatleri' demek yetmez; başlangıç ve bitiş saati birlikte ve saat dilimiyle, başka dilime çevrilmeden Türkiye saati olarak verilmeli.
  - Gerekli: Hayır; başlangıç ve bitiş saati birlikte verilir.
  - Gerekli: Saat dilimi de yazılır: saatler başka bir saat dilimine çevrilmeden Türkiye saati (Europe/Istanbul) olarak ifade edilir.
  - Yasak: Yalnızca 'mesai saatleri' demenin yeterli olduğu.
  - Yasak: Saatlerin müşterinin kendi saat dilimine çevrilmesi gerektiği.
- Gerçek: HTTP 200, `partial`, 1631 ms
  - İlk k: D08#kullanim, D08#saat-dilimi, D06#dogruluk, D10#kullanim; kaynak/aday: D08#saat-dilimi
  - reason_code: not_in_documents
  - Claim: Türkiye’deki B2B müşterilere destek saatlerini bildirirken yalnızca “mesai saatleri” demek yeterli değildir; başlangıç ve bitiş saatlerini Türkiye saati olarak birlikte belirtin. [D08#saat-dilimi]
  - Eksik konu: Destek saatlerinin başlangıç ve bitiş saatleri belirtilmemiştir.
  - Cevap: Türkiye’deki B2B müşterilere destek saatlerini bildirirken yalnızca “mesai saatleri” demek yeterli değildir; başlangıç ve bitiş saatlerini Türkiye saati olarak birlikte belirtin. Bu istekteki belgelerle yanıtlanamayan konular: Destek saatlerinin başlangıç ve bitiş saatleri belirtilmemiştir.
  - Sürüm kararları: support-hours → D08; support-ticket → D06; safe-support-sharing → D10
- Kontrol sorunu: status: partial, beklenen answered
- İnsan incelemesi: kabul edilebilir: cevap doğru; D08#saatler ilk 4'te olmadığı için saatleri eksik konu olarak ekledi (retrieval)

### H06 · normal

- Soru: Kullanıcı parola sıfırlama bağlantısını telefonuna SMS olarak almak istiyor. Bağlantıyı ona SMS ile gönderebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D09#eposta. Rubrik: Hayır: sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir; temsilci bağlantıyı başka bir adrese veya kanala göndermeyi teklif etmez.
  - Gerekli: Hayır; sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir.
  - Gerekli: Destek temsilcisi bağlantıyı başka bir adrese göndermeyi teklif etmez.
  - Yasak: Bağlantının SMS ile gönderilebileceği.
  - Yasak: Bağlantının başka bir kanal veya adres üzerinden gönderilebileceği.
- Gerçek: HTTP 200, `answered`, 1634 ms
  - İlk k: D09#sifre, D10#musteri-istegi, D09#kullanim, D09#eposta; kaynak/aday: D09#sifre, D09#eposta
  - reason_code: —
  - Claim: Türkiye’deki B2B MH-10 kullanıcıları için parola sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir; SMS ile gönderilmez. [D09#sifre, D09#eposta]
  - Cevap: Türkiye’deki B2B MH-10 kullanıcıları için parola sıfırlama bağlantısı yalnızca hesapta kayıtlı e-posta adresine gönderilir; SMS ile gönderilmez.
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: doğru

### H07 · normal

- Soru: Müşteri sorunu anlatırken parolasını destek talebinin açıklamasına yazmak istiyor. Ona nasıl karşılık vermeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D10#musteri-istegi. Rubrik: Müşteriye parolasını paylaşmaması gerektiği nazikçe söylenmeli; parola destek talebinde paylaşılmaz.
  - Gerekli: Müşteriye parolasını paylaşmaması gerektiği söylenir.
  - Gerekli: Bu nazikçe söylenir.
  - Yasak: Parolanın talebe yazılabileceği veya temsilcinin parolayı isteyebileceği.
- Gerçek: HTTP 200, `answered`, 1397 ms
  - İlk k: D10#musteri-istegi, D07#iletisim, D10#paylasim, D09#kullanim; kaynak/aday: D10#musteri-istegi, D10#paylasim
  - reason_code: —
  - Claim: Parolanızı destek talebinin açıklamasına yazmamanız gerektiğini nazikçe söyleyin; destek personeli parolanızı istemez ve parolalar destek talebinde paylaşılmaz. [D10#musteri-istegi, D10#paylasim]
  - Cevap: Parolanızı destek talebinin açıklamasına yazmamanız gerektiğini nazikçe söyleyin; destek personeli parolanızı istemez ve parolalar destek talebinde paylaşılmaz.
  - Sürüm kararları: safe-support-sharing → D10; priority-sla → D07; account-access → D09
- İnsan incelemesi: doğru

### H08 · normal

- Soru: Müşteri iade bedeli için ona belirli bir ödeme günü söylememi istiyor. Belirli bir gün taahhüt edebilir miyim, yoksa ona ne söylemeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D05#kullanim, D05#bedel. Rubrik: Hayır: belgede yazmayan bir ödeme tarihi taahhüt edilmez; müşteriye yalnızca bedelin iadenin kabulünden sonra 5 iş günü içinde ödendiği söylenebilir.
  - Gerekli: Hayır; belgede yazmayan bir ödeme tarihi müşteriye taahhüt edilmez.
  - Gerekli: İade bedeli iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir.
  - Yasak: Belirli bir takvim tarihi (gün/ay) taahhüt etmek.
  - Yasak: Sürenin takvim günüyle sayıldığı (ör. 5 takvim günü).
  - Yasak: Sürenin kargoya verildiği günden başladığı.
- Gerçek: HTTP 200, `answered`, 2029 ms
  - İlk k: D05#bedel, D05#kullanim, D04#sure, D10#musteri-istegi; kaynak/aday: D05#bedel, D05#kullanim
  - reason_code: —
  - Claim: Türkiye’deki kurumsal (B2B) MH-10 müşterisine, iade bedelinin iade kabul edildikten sonra 5 iş günü içinde ödeneceğini söyleyin; süre ürünün kargoya verildiği tarihten başlamaz. [D05#bedel, D05#kullanim]
  - Claim: Belgelerde yazmayan belirli bir ödeme tarihini müşteriye taahhüt etmeyin. [D05#kullanim]
  - Cevap: Türkiye’deki kurumsal (B2B) MH-10 müşterisine, iade bedelinin iade kabul edildikten sonra 5 iş günü içinde ödeneceğini söyleyin; süre ürünün kargoya verildiği tarihten başlamaz. Belgelerde yazmayan belirli bir ödeme tarihini müşteriye taahhüt etmeyin.
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired); safe-support-sharing → D10
- İnsan incelemesi: doğru

### H09 · version_conflict

- Soru: Müşteri MH-10'u 10 Eylül 2026'da teslim aldı ve bugün (4 Ekim 2026) iade talebi açmak istiyor. Hâlâ iade süresi içinde mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: Evet: as_of=2026-10-04 için 2.0 sürümünde iade talebi teslimden itibaren 30 takvim günü içinde açılabilir; 10 Eylül'den 4 Ekim'e 24 gün geçtiği için süre dolmamıştır. 14 gün kuralı uygulanmamalı; D04 seçili, D03 expired.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: Süre teslim tarihinden sayılır.
  - Gerekli: Evet; 4 Ekim, 10 Eylül'deki teslimden sonraki 30 takvim günü içindedir, talep süresi içindedir.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
  - Yasak: Sürenin dolduğu veya talebin süre dışında kaldığı.
- Gerçek: HTTP 200, `partial`, 3016 ms
  - İlk k: D04#sure, D04#uygulama, D05#kullanim, D01#kullanim; kaynak/aday: D04#sure
  - reason_code: not_in_documents
  - Claim: Türkiye'deki B2B müşteriler, MH-10 için teslim tarihinden itibaren 30 takvim günü içinde iade talebi açabilir; hafta sonları da bu süreye dâhildir. [D04#sure]
  - Eksik konu: 10 Eylül 2026 teslim tarihine göre 4 Ekim 2026'nın 30 takvim günlük süre içinde olup olmadığı, bölümlerde belirtilmiyor.
  - Cevap: Türkiye'deki B2B müşteriler, MH-10 için teslim tarihinden itibaren 30 takvim günü içinde iade talebi açabilir; hafta sonları da bu süreye dâhildir. Bu istekteki belgelerle yanıtlanamayan konular: 10 Eylül 2026 teslim tarihine göre 4 Ekim 2026'nın 30 takvim günlük süre içinde olup olmadığı, bölümlerde belirtilmiyor.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; mh10-setup → D01
- Kontrol sorunu: status: partial, beklenen answered
- İnsan incelemesi: kabul edilebilir: 30 takvim günü kuralı doğru; iki tarih arasını bilerek hesaplamıyor (generation, tasarım tercihi)

### H10 · version_conflict

- Soru: Müşteri iade talebi açarken ona iade kargosunun ücretini kendisinin ödeyeceğini söylemeli miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#kargo. Rubrik: Hayır: güncel 2.0 sürümünde şirket, talebi onaylanan müşteriye iade etiketi sağlar ve etiketli gönderimin kargo bedelini karşılar; müşterinin ödediği söylenmemeli. D04 seçili, D03 expired.
  - Gerekli: Hayır; şirket, iade talebi onaylanan müşteriye bir iade etiketi sağlar.
  - Gerekli: Bu etiketle yapılan gönderimin kargo bedelini şirket karşılar.
  - Yasak: Kargo bedelini müşterinin ödediği (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `answered`, 2180 ms
  - İlk k: D04#kargo, D05#bedel, D05#kullanim, D04#sure; kaynak/aday: D04#kargo
  - reason_code: —
  - Claim: Türkiye'deki kurumsal (B2B) müşterilerin MH-10 için onaylanan iade taleplerinde, şirket iade etiketi sağlar ve bu etiketle yapılan gönderimin kargo bedelini karşılar. [D04#kargo]
  - Cevap: Türkiye'deki kurumsal (B2B) müşterilerin MH-10 için onaylanan iade taleplerinde, şirket iade etiketi sağlar ve bu etiketle yapılan gönderimin kargo bedelini karşılar.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: doğru

### H11 · historical_version

- Soru: Bugün açılan bir iade talebinde müşteriyi iade kargosu konusunda ne zaman ve neyle ilgili bilgilendirmeliyim?
- İstek: as_of `2026-04-10`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D03#kargo. Rubrik: as_of=2026-04-10 için 1.0 sürümü: iade kargosunun bedelini müşteri öder ve bu bilgi müşteriye iade talebi açılırken verilir; etiket veya şirketin ödediği söylenmemeli. D03 seçili, D04 future_effective.
  - Gerekli: İade kargosunun bedelini müşteri öder; ürün geri gönderilirken oluşan kargo ücreti müşteriye aittir.
  - Gerekli: Bu bilgi iade talebi açılırken verilir; müşteri ürünü göndermeden önce bunu bilir.
  - Yasak: Şirketin iade etiketi sağladığı (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Kargo bedelini şirketin karşıladığı (2.0 sürümü).
- Gerçek: HTTP 200, `answered`, 2574 ms
  - İlk k: D03#kargo, D05#bedel, D03#sure, D05#kullanim; kaynak/aday: D03#kargo
  - reason_code: —
  - Claim: Türkiye'deki kurumsal (B2B) MH-10 müşterisine, iade talebi açılırken ürünü şirkete geri gönderme kargo ücretinin müşteriye ait olduğunu bildirin. [D03#kargo]
  - Cevap: Türkiye'deki kurumsal (B2B) MH-10 müşterisine, iade talebi açılırken ürünü şirkete geri gönderme kargo ücretinin müşteriye ait olduğunu bildirin.
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: doğru

### H12 · historical_version

- Soru: Bugün açılan bir iade talebi hangi prosedür sürümüne göre değerlendirilir ve müşterinin teslimden itibaren kaç günü vardır?
- İstek: as_of `2026-06-30`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D03#uygulama, D03#sure. Rubrik: as_of=2026-06-30 (1.0 sürümünün son geçerli günü): talep 1.0 sürümüne göre değerlendirilir ve müşteri iade talebini teslimden itibaren 14 takvim günü içinde açabilir; 2.0 veya 30 gün denmemeli. D03 seçili, D04 future_effective.
  - Gerekli: Talep 1.0 sürümüne göre değerlendirilir (1 Temmuz 2026'dan önce açılan talepler).
  - Gerekli: İade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Talebin 2.0 sürümüne göre değerlendirileceği.
- Gerçek: HTTP 200, `answered`, 1957 ms
  - İlk k: D03#sure, D03#uygulama, D05#bedel, D03#kargo; kaynak/aday: D03#uygulama, D03#sure
  - reason_code: —
  - Claim: Türkiye’deki B2B müşterilerin MH-10 için açtığı iade taleplerinde, bugün yani 2026-06-30’da açılan talebe 1.0 sürümü uygulanır. [D03#uygulama]
  - Claim: Türkiye’deki B2B müşteriler, MH-10 ürününün tesliminden itibaren 14 takvim günü içinde iade talebi açabilir; hafta sonları da bu süreye dâhildir. [D03#sure]
  - Cevap: Türkiye’deki B2B müşterilerin MH-10 için açtığı iade taleplerinde, bugün yani 2026-06-30’da açılan talebe 1.0 sürümü uygulanır. Türkiye’deki B2B müşteriler, MH-10 ürününün tesliminden itibaren 14 takvim günü içinde iade talebi açabilir; hafta sonları da bu süreye dâhildir.
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: doğru

### H13 · historical_version

- Soru: Bugün iade talebi açmak isteyen bir müşterinin süresi hesaplanırken cumartesi ve pazar günleri de sayılıyor mu? Teslimden itibaren toplam kaç günü var?
- İstek: as_of `2026-02-09`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D03#sure. Rubrik: as_of=2026-02-09 için 1.0 sürümü: süre teslimden itibaren 14 takvim günüdür ve hafta sonları dâhildir; iş günü veya 30 gün denmemeli. D03 seçili, D04 future_effective.
  - Gerekli: İade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Gerekli: Takvim günü hesabına hafta sonları (cumartesi ve pazar) da dâhildir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü, D04).
  - Yasak: Sürenin iş günüyle sayıldığı veya hafta sonlarının sayılmadığı.
- Gerçek: HTTP 200, `answered`, 1503 ms
  - İlk k: D03#sure, D05#bedel, D05#kullanim, D03#uygulama; kaynak/aday: D03#sure
  - reason_code: —
  - Claim: Türkiye’deki B2B müşteriler, MH-10 ürünü için iade talebini teslim tarihinden itibaren 14 takvim günü içinde açabilir; takvim günü hesabına cumartesi ve pazar da dâhildir. [D03#sure]
  - Cevap: Türkiye’deki B2B müşteriler, MH-10 ürünü için iade talebini teslim tarihinden itibaren 14 takvim günü içinde açabilir; takvim günü hesabına cumartesi ve pazar da dâhildir.
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- İnsan incelemesi: doğru

### H14 · unanswerable

- Soru: Elli adet MH-10 alırsak toplu alım indirimi uygulanıyor mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: fiyat ve toplu alım indirimi belgelerde yok; oran veya fiyat uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Herhangi bir indirim oranı veya fiyat.
  - Yasak: İndirim uygulandığı veya uygulanmadığı yönünde bir taahhüt.
- Gerçek: HTTP 200, `insufficient_evidence`, 1330 ms
  - İlk k: D04#uygulama, D05#kullanim, D04#sure, D02#sinir; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: Elli adet MH-10 alımında toplu alım indirimi uygulanıp uygulanmadığı verilen belgelerde belirtilmiyor.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: Elli adet MH-10 alımında toplu alım indirimi uygulanıp uygulanmadığı verilen belgelerde belirtilmiyor.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05; audio-troubleshooting → D02
- İnsan incelemesi: doğru

### H15 · unanswerable

- Soru: Destek panelinde iki aşamalı doğrulamayı (2FA) kendi hesabım için nasıl açarım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: iki aşamalı doğrulamanın nasıl açılacağı belgelerde yok; OTP paylaşım kuralı veya parola sıfırlama bu sorunun cevabı gibi sunulmamalı.
  - Yasak: Belgelerde olmayan bir 2FA etkinleştirme adımı (ör. ayarlar menüsünden açmak).
  - Yasak: OTP paylaşım kuralını veya parola sıfırlama adımlarını 2FA'yı açma yöntemi gibi sunmak.
- Gerçek: HTTP 200, `insufficient_evidence`, 1261 ms
  - İlk k: D09#kullanim, D10#paylasim, D06#dogruluk, D10#musteri-istegi; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: Destek panelinde iki aşamalı doğrulamayı kendi hesabınız için nasıl açacağınız verilen belgelerde açıklanmıyor.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: Destek panelinde iki aşamalı doğrulamayı kendi hesabınız için nasıl açacağınız verilen belgelerde açıklanmıyor.
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: doğru

### H16 · unanswerable

- Soru: MH-10'un kulak süngerleri yıprandı; yedek süngeri nereden sipariş edebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: yedek parça ve sipariş kanalı belgelerde yok; kanal veya fiyat uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Yedek parça için bir sipariş kanalı, fiyat, adres veya bağlantı uydurmak.
- Gerçek: HTTP 200, `insufficient_evidence`, 1704 ms
  - İlk k: D02#ses-yok, D04#sure, D01#tamamlama, D02#sinir; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: Yedek kulak süngerlerinin nereden sipariş edilebileceği verilen bölümlerde belirtilmiyor.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: Yedek kulak süngerlerinin nereden sipariş edilebileceği verilen bölümlerde belirtilmiyor.
  - Sürüm kararları: audio-troubleshooting → D02; returns → D04 (D03 expired); mh10-setup → D01
- İnsan incelemesi: doğru

### H17 · unanswerable

- Soru: Yeni işe başlayan bir temsilci için destek panelinde kullanıcı hesabını nasıl oluştururum?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: destek panelinde kullanıcı hesabı oluşturma belgelerde yok; yeni temsilci için kulaklık kurulum adımları hesap açma yöntemi gibi sunulmamalı.
  - Yasak: MH-10 kurulum adımlarını veya parola sıfırlamayı kullanıcı hesabı oluşturma yöntemi gibi sunmak.
  - Yasak: Belgelerde olmayan bir hesap açma adımı uydurmak.
- Gerçek: HTTP 200, `insufficient_evidence`, 1713 ms
  - İlk k: D09#kullanim, D10#musteri-istegi, D06#kullanim, D06#dogruluk; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: Yeni işe başlayan bir temsilci için destek panelinde kullanıcı hesabı oluşturma adımları verilen bölümlerde açıklanmıyor.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: Yeni işe başlayan bir temsilci için destek panelinde kullanıcı hesabı oluşturma adımları verilen bölümlerde açıklanmıyor.
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: doğru

### H18 · partial

- Soru: Cuma günü Türkiye saatiyle 19.00'da destek ekibine ulaşabilir miyim? Ulaşabileceğim telefon numarası nedir?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `partial`; bölümler D08#saatler. Rubrik: partial: destek ekibine hafta içi 09.00–18.00 (Türkiye saati) arasında ulaşılabildiği için cuma 19.00'da ulaşılamaz (kaynaklı); telefon numarası belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: Hayır; destek ekibine hafta içi 09.00–18.00 arasında ulaşılabilir, 19.00 bu saatlerin dışındadır.
  - Gerekli: Telefon numarası eksik konu olarak ayrılır.
  - Yasak: Bir telefon numarası uydurmak.
  - Yasak: Cuma 19.00'da destek ekibine ulaşılabileceği.
- Gerçek: HTTP 200, `partial`, 3238 ms
  - İlk k: D08#saatler, D08#kullanim, D06#alanlar, D06#kullanim; kaynak/aday: D08#saatler
  - reason_code: not_in_documents
  - Claim: Türkiye’deki B2B müşteriler destek ekibine hafta içi, pazartesiden cumaya, Türkiye saatiyle 09.00–18.00 arasında ulaşabilir; bu nedenle cuma günü saat 19.00’da destek ekibi ulaşılamaz. [D08#saatler]
  - Eksik konu: Destek ekibinin telefon numarası verilen bölümlerde belirtilmiyor.
  - Cevap: Türkiye’deki B2B müşteriler destek ekibine hafta içi, pazartesiden cumaya, Türkiye saatiyle 09.00–18.00 arasında ulaşabilir; bu nedenle cuma günü saat 19.00’da destek ekibi ulaşılamaz. Bu istekteki belgelerle yanıtlanamayan konular: Destek ekibinin telefon numarası verilen bölümlerde belirtilmiyor.
  - Sürüm kararları: support-hours → D08; support-ticket → D06
- İnsan incelemesi: doğru

### H19 · partial

- Soru: İadesi kabul edilen MH-10'un bedeli kaç iş gününde ödenir? Ödeme kredi kartına mı yapılır, banka hesabına mı?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `partial`; bölümler D05#bedel. Rubrik: partial: bedel iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir (kaynaklı); ödemenin kredi kartına mı banka hesabına mı yapılacağı belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: İade bedeli iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir.
  - Gerekli: Ödeme yöntemi (kredi kartı / banka hesabı) eksik konu olarak ayrılır.
  - Yasak: Ödemenin belirli bir yönteme (kredi kartı veya banka hesabı) yapıldığı.
  - Yasak: Sürenin takvim günüyle sayıldığı (ör. 5 takvim günü).
  - Yasak: Sürenin kargoya verildiği günden başladığı.
- Gerçek: HTTP 200, `partial`, 1749 ms
  - İlk k: D05#kullanim, D05#bedel, D04#sure, D04#kargo; kaynak/aday: D05#kullanim, D05#bedel
  - reason_code: not_in_documents
  - Claim: Türkiye’deki kurumsal (B2B) müşterilerin iadesi kabul edilen MH-10 kulaklıklarının bedeli, iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir; süre ürünün kargoya verildiği tarihten başlamaz. [D05#kullanim, D05#bedel]
  - Eksik konu: İade bedelinin kredi kartına mı yoksa banka hesabına mı yatırıldığı verilen bölümlerde belirtilmiyor.
  - Cevap: Türkiye’deki kurumsal (B2B) müşterilerin iadesi kabul edilen MH-10 kulaklıklarının bedeli, iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir; süre ürünün kargoya verildiği tarihten başlamaz. Bu istekteki belgelerle yanıtlanamayan konular: İade bedelinin kredi kartına mı yoksa banka hesabına mı yatırıldığı verilen bölümlerde belirtilmiyor.
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: doğru

### H20 · partial

- Soru: Destek talebine MH-10'un seri numarasını yazmam gerekiyor mu? Talebe en fazla kaç dosya ekleyebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `partial`; bölümler D06#alanlar. Rubrik: partial: seri numarası talebe yazılması gereken bilgilerdendir (kaynaklı); eklenebilecek dosya sayısı belgelerde yok, eksik konu olarak ayrılmalı.
  - Gerekli: Evet; seri numarası talepte bulunması gereken bilgilerdendir.
  - Gerekli: Dosya sayısı sınırı eksik konu olarak ayrılır.
  - Yasak: Talebe eklenebilecek dosya sayısı veya boyutu için bir sınır uydurmak.
  - Yasak: Seri numarasının gerekmediği.
- Gerçek: HTTP 200, `partial`, 1554 ms
  - İlk k: D06#alanlar, D02#ses-yok, D02#sinir, D06#kullanim; kaynak/aday: D06#alanlar
  - reason_code: not_in_documents
  - Claim: Türkiye’deki B2B müşteriler için MH-10 destek talebine MH-10’un seri numarası yazılmalıdır. [D06#alanlar]
  - Eksik konu: Destek talebine eklenebilecek en fazla dosya sayısı verilen bölümlerde belirtilmiyor.
  - Cevap: Türkiye’deki B2B müşteriler için MH-10 destek talebine MH-10’un seri numarası yazılmalıdır. Bu istekteki belgelerle yanıtlanamayan konular: Destek talebine eklenebilecek en fazla dosya sayısı verilen bölümlerde belirtilmiyor.
  - Sürüm kararları: support-ticket → D06; audio-troubleshooting → D02
- İnsan incelemesi: doğru

### H21 · false_premise

- Soru: Müşteriye iade süresinin, iade talebini açtığı günden itibaren işlemeye başladığını söyledim. Bu doğru mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: Yanlış ön kabul düzeltilmeli: iade süresi teslim tarihinden sayılır; talebin açıldığı tarih süreyi başlatmaz, yalnızca uygulanacak sürümü belirler. Süre söylenirse 2.0'a göre 30 takvim günüdür; D04 seçili, D03 expired.
  - Gerekli: Hayır; süre ürünün teslim tarihinden sayılır.
  - Gerekli: İade talebinin açıldığı tarih süreyi başlatmaz; yalnızca hangi prosedür sürümünün uygulanacağını belirler.
  - Gerekli: Süre belirtilirse: teslimden itibaren 30 takvim günü.
  - Yasak: Sürenin iade talebinin açıldığı günden başladığını onaylamak.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `answered`, 1575 ms
  - İlk k: D04#sure, D05#bedel, D05#kullanim, D04#uygulama; kaynak/aday: D04#sure, D04#uygulama
  - reason_code: —
  - Claim: Türkiye'deki B2B müşteriler, MH-10 temsilci kulaklıkları için iade talebini ürünün tesliminden itibaren 30 takvim günü içinde açabilir; süre teslim tarihinden başlar, talebin açıldığı tarihten değil. [D04#sure]
  - Claim: İade talebinin açıldığı tarih, uygulanacak prosedür sürümünü belirler. [D04#sure, D04#uygulama]
  - Cevap: Türkiye'deki B2B müşteriler, MH-10 temsilci kulaklıkları için iade talebini ürünün tesliminden itibaren 30 takvim günü içinde açabilir; süre teslim tarihinden başlar, talebin açıldığı tarihten değil. İade talebinin açıldığı tarih, uygulanacak prosedür sürümünü belirler.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: doğru

### H22 · false_premise

- Soru: Ekranda hata kodu çıkmadığı için destek talebi açamıyoruz, değil mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar. Rubrik: Yanlış ön kabul düzeltilmeli: hata kodu görüntülenmediyse bu alan boş bırakılabilir; talep seri numarası ve yeniden üretme adımlarıyla açılır.
  - Gerekli: Hayır; hata kodu görüntülenmediyse bu bilgi boş bırakılabilir.
  - Gerekli: Talep seri numarası ve sorunu yeniden üretme adımlarıyla açılır.
  - Yasak: Hata kodu olmadan destek talebi açılamayacağı.
- Gerçek: HTTP 200, `answered`, 1968 ms
  - İlk k: D06#alanlar, D06#dogruluk, D10#paylasim, D10#musteri-istegi; kaynak/aday: D06#alanlar
  - reason_code: —
  - Claim: Türkiye’deki B2B müşteriler MH-10 için ekranda hata kodu görüntülenmediyse, talepte hata kodu bilgisini boş bırakabilir; bu nedenle hata kodu olmaması destek talebi açmaya engel değildir. [D06#alanlar]
  - Cevap: Türkiye’deki B2B müşteriler MH-10 için ekranda hata kodu görüntülenmediyse, talepte hata kodu bilgisini boş bırakabilir; bu nedenle hata kodu olmaması destek talebi açmaya engel değildir.
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: doğru

### H23 · false_premise

- Soru: MH-10'u panelde yalnızca hoparlör (çıkış aygıtı) olarak seçmem yeterli, mikrofonu ayrıca seçmeme gerek yok, değil mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D01#baglanti. Rubrik: Yanlış ön kabul düzeltilmeli: yalnızca birini seçmek yetmez; MH-10 hem giriş hem çıkış aygıtı olarak seçilmeli, giriş aygıtı seçilmezse müşteri temsilciyi duyamaz.
  - Gerekli: Hayır; MH-10 hem giriş (mikrofon) hem çıkış (hoparlör) aygıtı olarak seçilmelidir.
  - Gerekli: Giriş aygıtı seçilmezse müşteri temsilciyi duyamaz.
  - Yasak: Yalnızca çıkış aygıtı seçmenin yeterli olduğu.
- Gerçek: HTTP 200, `answered`, 1640 ms
  - İlk k: D01#baglanti, D01#tamamlama, D02#ses-yok, D02#sinir; kaynak/aday: D01#baglanti
  - reason_code: —
  - Claim: MH-10 için destek panelinde hem giriş aygıtı (mikrofon) hem de çıkış aygıtı (hoparlör) seçilmelidir; yalnızca hoparlörü seçmek yeterli değildir. [D01#baglanti]
  - Cevap: MH-10 için destek panelinde hem giriş aygıtı (mikrofon) hem de çıkış aygıtı (hoparlör) seçilmelidir; yalnızca hoparlörü seçmek yeterli değildir.
  - Sürüm kararları: mh10-setup → D01; audio-troubleshooting → D02
- Kontrol sorunu: required_facts: bulunamadı: Giriş aygıtı seçilmezse müşteri temsilciyi duyamaz.
- İnsan incelemesi: kabul edilebilir: ön kabul düzeltildi; 'giriş seçilmezse müşteri temsilciyi duyamaz' söylenmedi (generation)

### H24 · multi_source

- Soru: Panelde aldığımız hata için ekran görüntüsüyle birlikte ticket açacağız. Ticket'a neler yazılmalı ve görüntüyü yüklemeden önce üzerindeki hangi bilgileri kapatmalıyız?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar, D10#paylasim. Rubrik: İki kaynak birlikte: talebe seri numarası, görüntülendiyse hata kodu ve yeniden üretme adımları yazılır (D06#alanlar); görüntüdeki ad, telefon numarası ve e-posta adresi gibi kişisel bilgiler paylaşmadan önce gizlenir (D10#paylasim).
  - Gerekli: MH-10'un seri numarası.
  - Gerekli: Ekranda görüntülendiyse hata kodu.
  - Gerekli: Sorunu yeniden üretme adımları.
  - Gerekli: Görüntü paylaşılmadan önce görseldeki kişisel bilgiler gizlenir.
  - Gerekli: Gizlenecek kişisel bilgilere örnek: ad, telefon numarası, e-posta adresi.
  - Yasak: Görselin kişisel bilgiler gizlenmeden paylaşılabileceği.
  - Yasak: Talebe parola veya OTP yazılması.
- Gerçek: HTTP 200, `answered`, 2187 ms
  - İlk k: D06#alanlar, D06#kullanim, D10#paylasim, D10#musteri-istegi; kaynak/aday: D06#alanlar, D06#kullanim, D10#paylasim
  - reason_code: —
  - Claim: Türkiye’deki B2B müşteriler, MH-10 veya destek paneliyle ilgili bir sorun için ticket’a MH-10’un seri numarasını, ekranda görüntülendiyse hata kodunu ve sorun ortaya çıkana kadar yapılan işlemlerin sırasını yazmalıdır; hata kodu görüntülenmediyse bu bilgi boş bırakılabilir. [D06#alanlar, D06#kullanim]
  - Claim: Ekran görüntüsünü paylaşmadan önce üzerindeki kişisel bilgileri, örneğin ad, telefon numarası ve e-posta adresini gizlemeli; parola ve tek kullanımlık doğrulama kodunu destek talebinde paylaşmamalısınız. [D10#paylasim]
  - Cevap: Türkiye’deki B2B müşteriler, MH-10 veya destek paneliyle ilgili bir sorun için ticket’a MH-10’un seri numarasını, ekranda görüntülendiyse hata kodunu ve sorun ortaya çıkana kadar yapılan işlemlerin sırasını yazmalıdır; hata kodu görüntülenmediyse bu bilgi boş bırakılabilir. Ekran görüntüsünü paylaşmadan önce üzerindeki kişisel bilgileri, örneğin ad, telefon numarası ve e-posta adresini gizlemeli; parola ve tek kullanımlık doğrulama kodunu destek talebinde paylaşmamalısınız.
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: doğru

### H25 · multi_source

- Soru: Parolasını unutan bir kullanıcı panele yeniden nasıl girer? Bu sırada ondan telefonuna gelen doğrulama kodunu (OTP) isteyebilir miyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre, D10#paylasim. Rubrik: İki kaynak birlikte: kullanıcı giriş ekranından sıfırlama ister, bağlantı kayıtlı e-posta adresine gelir ve yeni parola belirlenir (D09#sifre); OTP paylaşılmaz ve destek personeli istemez (D10#paylasim).
  - Gerekli: Kullanıcı giriş ekranından parola sıfırlama isteğinde bulunur.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir; kullanıcı bağlantıyla yeni parolasını belirler.
  - Gerekli: Hayır; OTP destek personeliyle paylaşılmaz, destek personeli de istemez.
  - Yasak: Temsilcinin OTP veya parola isteyebileceği.
- Gerçek: HTTP 200, `answered`, 2039 ms
  - İlk k: D10#paylasim, D10#musteri-istegi, D09#sifre, D09#kullanim; kaynak/aday: D09#sifre, D09#kullanim, D10#paylasim
  - reason_code: —
  - Claim: Türkiye’deki B2B müşterilerinin MH-10 destek panelinde parolasını unutan kullanıcı, giriş ekranından parola sıfırlama isteği gönderir; sıfırlama bağlantısı kayıtlı e-posta adresine gönderilir ve kullanıcı bağlantıyı açıp yeni parolasını belirledikten sonra panele giriş yapar. [D09#sifre, D09#kullanim]
  - Claim: Türkiye’deki B2B müşterilerinin MH-10 destek paneli için destek personeli kullanıcıdan parolasını veya tek kullanımlık doğrulama kodunu (OTP) istemez; bu bilgiler destek görüşmesinde ya da destek talebinde paylaşılmaz. [D10#paylasim]
  - Cevap: Türkiye’deki B2B müşterilerinin MH-10 destek panelinde parolasını unutan kullanıcı, giriş ekranından parola sıfırlama isteği gönderir; sıfırlama bağlantısı kayıtlı e-posta adresine gönderilir ve kullanıcı bağlantıyı açıp yeni parolasını belirledikten sonra panele giriş yapar. Türkiye’deki B2B müşterilerinin MH-10 destek paneli için destek personeli kullanıcıdan parolasını veya tek kullanımlık doğrulama kodunu (OTP) istemez; bu bilgiler destek görüşmesinde ya da destek talebinde paylaşılmaz.
  - Sürüm kararları: safe-support-sharing → D10; account-access → D09
- İnsan incelemesi: doğru

### H26 · paraphrase

- Soru: Şifremi hatırlamıyorum, panele bir türlü giriş yapamıyorum. Hesabıma tekrar nasıl girerim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre. Rubrik: 'Şifre' kelimesiyle sorulan parola sıfırlama: giriş ekranından sıfırlama istenir, bağlantı hesapta kayıtlı e-posta adresine gelir, kullanıcı yeni parolasını belirleyip onunla giriş yapar.
  - Gerekli: Giriş ekranından parola sıfırlama isteğinde bulunulur.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir.
  - Gerekli: Bağlantı açılarak yeni parola belirlenir ve yeni parolayla giriş yapılır.
  - Yasak: Bağlantının görüşmede söylenen başka bir adrese gönderilebileceği veya temsilcinin parolayı söyleyeceği.
- Gerçek: HTTP 200, `answered`, 1805 ms
  - İlk k: D09#kullanim, D09#sifre, D10#musteri-istegi, D09#eposta; kaynak/aday: D09#sifre
  - reason_code: —
  - Claim: Türkiye’deki B2B müşteriler MH-10 destek paneline giriş ekranından parola sıfırlama isteği göndererek hesaplarına yeniden erişebilir; sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir. [D09#sifre]
  - Claim: Kullanıcı sıfırlama bağlantısını açarak yeni parolasını belirler ve destek paneline yeni parolasıyla giriş yapar. [D09#sifre]
  - Cevap: Türkiye’deki B2B müşteriler MH-10 destek paneline giriş ekranından parola sıfırlama isteği göndererek hesaplarına yeniden erişebilir; sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir. Kullanıcı sıfırlama bağlantısını açarak yeni parolasını belirler ve destek paneline yeni parolasıyla giriş yapar.
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: doğru

