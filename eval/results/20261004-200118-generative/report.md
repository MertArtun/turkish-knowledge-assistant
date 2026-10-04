# Değerlendirme raporu: `20261004-200118-generative`

Bu dosyayı `eval/run_eval.py` üretti. Otomatik kontroller durumları, bölüm kimliklerini, sürüm kararlarını, alıntıları ve claim metinlerinde birkaç düzenli ifadeyi karşılaştırır; anlamsal doğruluğu ölçmez. Her sorunun insan incelemesi `pending` başlar.

## Koşu bilgileri

| Alan | Değer |
|---|---|
| Gerçek çalıştırma zamanı | 2026-10-04T20:01:18+03:00 → 2026-10-04T20:01:53+03:00 |
| Mod | `generative` |
| API | `http://127.0.0.1:8080/api/ask`, istek başına 60 sn timeout |
| Commit | `50518bc4fb57f220d78b67eb22fa68da4dff04b4`; koşu girdileri commit'ten farklı (dirty): hayır |
| Soru sayısı | 18 |
| Corpus fingerprint | `fabd5f021008b2ddecfa6c3cced27735cd8d65391453fabc8f77a61ac5bf5e2f` |
| Embedding | `intfloat/multilingual-e5-small@614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| LLM modeli (yapılandırılan) | `openai/gpt-6-luna`; generation_configured=true |
| Prompt | `answer-v1`, SHA-256 `e24d9ade7581b15623beca2eac3ca38c17b787aa41fd76921e266762525ea6b0` |
| top_k / skor eşiği | 4 / kapalı |
| Readiness koşu sonunda aynı | evet |

İsteklerdeki as_of değerlendirilen iş tarihidir (E16 dışında 2026-10-04, E16'da 2026-06-01); gerçek çalıştırma zamanıyla aynı kavram değildir.

## Otomatik ölçümler

Payda, kontrolün o soru ve modda uygulandığı sorulardır (tanımlar `docs/project-spec.md` §7). Değerlendirilemeyen: kontrol uygulanıyor ama API kullanılabilir bir cevap dönmedi.

| Ölçüm | Geçen / uygulanan | Başarısız | Değerlendirilemeyen |
|---|---|---|---|
| HTTP 200 ve istekle aynı request_id | 18 / 18 | — | — |
| Beklenen iş durumu | 14 / 18 | E12, E15, E16, E18 | — |
| Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 12 / 15 | E15, E16, E18 | — |
| Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 12 / 15 | E15, E16, E18 | — |
| Doğru sürüm kararı (`version_decisions`) | 6 / 6 | — | — |
| Kaynak/aday kimliği geçerli: getirilen bölüm, seçili sürüm, birebir alıntı, claim atıfları = `sources` | 18 / 18 | — | — |
| Cevaplanabilir soruda gereksiz ret yok | 14 / 15 | E15 | — |
| Cevapsız soruda iddia (yanlış cevap) yok | 2 / 3 | E12 | — |
| Gerekli bilgi kalıpları claim'lerde var (sınırlı; anlamsal değil) | 12 / 15 | E15, E16, E18 | — |
| Yasak bilgi kalıpları claim'lerde yok (sınırlı; anlamsal değil) | 10 / 10 | — | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı ilk k sonuçta (`retrieved_chunk_ids`) | 0 / 1 | E18 | — |
| Çok kaynaklı sorular: Beklenen bölümlerin tamamı kaynak gösterildi (`sources`) | 0 / 1 | E18 | — |

## Soru bazında özet

| ID | Kategori | Beklenen durum | Gerçek | Beklenen bölüm | İlk k | Kaynak / aday | Başarısız kontroller | İnsan incelemesi |
|---|---|---|---|---|---|---|---|---|
| E01 | normal | answered | answered | D01#baglanti | D01#baglanti, D01#tamamlama, D06#alanlar, D01#kullanim | D01#baglanti, D01#tamamlama | — | pending |
| E02 | normal | answered | answered | D02#ses-yok | D02#ses-yok, D02#kullanim, D02#sinir, D01#tamamlama | D02#ses-yok, D02#kullanim, D02#sinir | — | pending |
| E03 | version_conflict | answered | answered | D04#sure | D05#kullanim, D05#bedel, D04#uygulama, D04#sure | D04#sure | — | pending |
| E04 | version_conflict | answered | answered | D04#kargo | D04#kargo, D05#kullanim, D05#bedel, D04#tarihler | D04#kargo | — | pending |
| E05 | normal | answered | answered | D05#bedel | D05#bedel, D05#kullanim, D04#tarihler, D04#kargo | D05#bedel | — | pending |
| E06 | normal | answered | answered | D06#alanlar | D06#alanlar, D06#kullanim, D10#kullanim, D10#musteri-istegi | D06#alanlar, D10#musteri-istegi | — | pending |
| E07 | normal | answered | answered | D07#p1 | D07#p1, D07#iletisim, D07#kullanim, D01#kullanim | D07#p1, D07#iletisim | — | pending |
| E08 | normal | answered | answered | D08#saatler | D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim | D08#saatler | — | pending |
| E09 | normal | answered | answered | D09#sifre | D09#sifre, D09#kullanim, D10#paylasim, D10#musteri-istegi | D09#sifre, D10#paylasim | — | pending |
| E10 | normal | answered | answered | D10#paylasim | D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk | D10#paylasim | — | pending |
| E11 | unanswerable | insufficient_evidence | insufficient_evidence | — | D04#sure, D01#tamamlama, D02#kullanim, D06#alanlar | — | — | pending |
| E12 | unanswerable | insufficient_evidence | partial | — | D04#sure, D05#kullanim, D04#tarihler, D05#bedel | D04#sure | status, no_wrong_answer | pending |
| E13 | unanswerable | insufficient_evidence | insufficient_evidence | — | D02#ses-yok, D06#kullanim, D10#musteri-istegi, D10#paylasim | — | — | pending |
| E14 | paraphrase | answered | answered | D04#sure | D04#sure, D04#tarihler, D06#dogruluk, D07#iletisim | D04#sure, D04#tarihler | — | pending |
| E15 | partial | partial | insufficient_evidence | D04#sure | D08#saat-dilimi, D05#is-gunu, D08#saatler, D04#tarihler | — | status, retrieval, citation, no_unnecessary_refusal, required_facts | pending |
| E16 | historical_version | answered | partial | D03#sure | D03#uygulama, D05#bedel, D05#kullanim, D03#tarihler | D03#tarihler | status, retrieval, citation, required_facts | pending |
| E17 | false_premise | answered | answered | D07#p1 | D07#p1, D07#iletisim, D07#kullanim, D02#ses-yok | D07#p1, D07#iletisim | — | pending |
| E18 | multi_source | answered | partial | D04#sure, D05#bedel | D05#bedel, D05#kullanim, D04#tarihler, D05#is-gunu | D05#bedel | status, retrieval, citation, required_facts | pending |

## Ayrıntılar

### E01 · normal

- Soru: MH-10'u destek panelinde nasıl kullanmaya başlarım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D01#baglanti. Rubrik: USB bağlantısı ve panelde hem giriş hem çıkış aygıtı seçimi söylenmeli; belgede olmayan adım eklenmemeli.
  - Gerekli: MH-10 bilgisayarın USB bağlantı noktasına takılır.
  - Gerekli: Destek panelinin ses ayarlarında MH-10 giriş aygıtı (mikrofon) olarak seçilir.
  - Gerekli: MH-10 çıkış aygıtı (hoparlör) olarak da seçilir.
  - Yasak: Belgede olmayan bir kurulum adımı (ör. sürücü kurmak, işletim sisteminin ses ayarını değiştirmek).
- Gerçek: HTTP 200, `answered`, 2555 ms
  - İlk k: D01#baglanti, D01#tamamlama, D06#alanlar, D01#kullanim; kaynak/aday: D01#baglanti, D01#tamamlama
  - reason_code: —
  - Claim: MH-10'u bilgisayarın USB bağlantı noktasına takın, ardından destek panelinin ses ayarlarında hem giriş aygıtı (mikrofon) hem de çıkış aygıtı (hoparlör) olarak seçin. [D01#baglanti]
  - Claim: MH-10 her iki aygıt olarak seçildiğinde kurulum tamamlanır ve kulaklık destek paneli üzerinden yapılan görüşmelerde kullanılabilir. [D01#tamamlama]
  - Cevap: MH-10'u bilgisayarın USB bağlantı noktasına takın, ardından destek panelinin ses ayarlarında hem giriş aygıtı (mikrofon) hem de çıkış aygıtı (hoparlör) olarak seçin. MH-10 her iki aygıt olarak seçildiğinde kurulum tamamlanır ve kulaklık destek paneli üzerinden yapılan görüşmelerde kullanılabilir.
  - Sürüm kararları: mh10-setup → D01; support-ticket → D06
- İnsan incelemesi: pending

### E02 · normal

- Soru: Kulaklıktan ses gelmiyor, ne kontrol etmeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D02#ses-yok. Rubrik: Belgedeki kontrol sırası (USB, aygıt seçimi, test çağrısı, ticket) verilmeli; rastgele teknik tavsiye eklenmemeli.
  - Gerekli: USB kablosunun takılı olduğu kontrol edilir.
  - Gerekli: Panelde MH-10'un giriş ve çıkış aygıtı olarak seçili olduğu doğrulanır.
  - Gerekli: Panelden test çağrısı yapılır.
  - Gerekli: Sorun sürerse destek talebi (ticket) açılır.
  - Yasak: Belgede olmayan teknik tavsiye (sürücü veya işletim sistemi ayarı değiştirmek gibi).
- Gerçek: HTTP 200, `answered`, 2580 ms
  - İlk k: D02#ses-yok, D02#kullanim, D02#sinir, D01#tamamlama; kaynak/aday: D02#ses-yok, D02#kullanim, D02#sinir
  - reason_code: —
  - Claim: MH-10'un USB kablosunun bilgisayara tam takılı olduğunu kontrol edin; gerekirse çıkarıp yeniden takın. [D02#ses-yok]
  - Claim: Destek panelinin ses ayarlarında MH-10'un hem giriş hem de çıkış aygıtı olarak seçili olduğunu doğrulayın. [D02#ses-yok]
  - Claim: Panelden test çağrısı yaparak sesin iki yönde de iletildiğini kontrol edin. [D02#ses-yok]
  - Claim: Kontrolleri sırayla yapın; bir adım sorunu çözerse sonraki adıma geçmeniz gerekmez. [D02#kullanim]
  - Claim: Sorun bu kontrollerden sonra da devam ederse destek talebi açın; sürücü veya işletim sistemi ayarlarını değiştirmeyin. [D02#ses-yok, D02#sinir]
  - Cevap: MH-10'un USB kablosunun bilgisayara tam takılı olduğunu kontrol edin; gerekirse çıkarıp yeniden takın. Destek panelinin ses ayarlarında MH-10'un hem giriş hem de çıkış aygıtı olarak seçili olduğunu doğrulayın. Panelden test çağrısı yaparak sesin iki yönde de iletildiğini kontrol edin. Kontrolleri sırayla yapın; bir adım sorunu çözerse sonraki adıma geçmeniz gerekmez. Sorun bu kontrollerden sonra da devam ederse destek talebi açın; sürücü veya işletim sistemi ayarlarını değiştirmeyin.
  - Sürüm kararları: audio-troubleshooting → D02; mh10-setup → D01
- İnsan incelemesi: pending

### E03 · version_conflict

- Soru: Kulaklığı kaç gün içinde iade edebilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: 30 takvim günü, teslimden itibaren; 14 gün denmemeli. D04 seçili, D03 expired görünmeli.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: Süre teslim tarihinden itibaren sayılır.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `answered`, 1361 ms
  - İlk k: D05#kullanim, D05#bedel, D04#uygulama, D04#sure; kaynak/aday: D04#sure
  - reason_code: —
  - Claim: İade talebi, ürünün tesliminden itibaren 30 takvim günü içinde açılabilir. [D04#sure]
  - Cevap: İade talebi, ürünün tesliminden itibaren 30 takvim günü içinde açılabilir.
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

### E04 · version_conflict

- Soru: İade kargosunu kim ödüyor?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#kargo. Rubrik: Şirketin sağladığı etiket ve etiketli gönderimin bedeli şirkette; müşteri öder denmemeli. D03 expired.
  - Gerekli: Şirket iade etiketi sağlar.
  - Gerekli: Etiketle yapılan gönderimin kargo bedelini şirket karşılar.
  - Yasak: İade kargosunu müşteri öder (süresi dolmuş 1.0 sürümü, D03).
- Gerçek: HTTP 200, `answered`, 1353 ms
  - İlk k: D04#kargo, D05#kullanim, D05#bedel, D04#tarihler; kaynak/aday: D04#kargo
  - reason_code: —
  - Claim: Şirket, iade talebi onaylanan müşteriye iade etiketi sağlar ve bu etiketle yapılan gönderimin kargo bedelini karşılar. [D04#kargo]
  - Cevap: Şirket, iade talebi onaylanan müşteriye iade etiketi sağlar ve bu etiketle yapılan gönderimin kargo bedelini karşılar.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- İnsan incelemesi: pending

### E05 · normal

- Soru: Para iadesi süresi kargoya verdiğim gün mü başlıyor?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D05#bedel. Rubrik: Yanlış ön kabul düzeltilmeli: süre kargodan değil kabulden sonra başlar ve 5 iş günüdür.
  - Gerekli: Hayır; süre ürünün kargoya verildiği tarihten başlamaz.
  - Gerekli: İade bedeli iadenin kabulünden sonra ödenir.
  - Gerekli: Ödeme süresi 5 iş günüdür.
  - Yasak: Sürenin kargoya verme tarihinden başladığı.
  - Yasak: Sürenin takvim günü olduğu.
- Gerçek: HTTP 200, `answered`, 1365 ms
  - İlk k: D05#bedel, D05#kullanim, D04#tarihler, D04#kargo; kaynak/aday: D05#bedel
  - reason_code: —
  - Claim: Hayır. İade bedeli, iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir; bu süre ürünün kargoya verildiği tarihten başlamaz. [D05#bedel]
  - Cevap: Hayır. İade bedeli, iadenin kabul edilmesinden sonra 5 iş günü içinde ödenir; bu süre ürünün kargoya verildiği tarihten başlamaz.
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- İnsan incelemesi: pending

### E06 · normal

- Soru: Destek talebinde hangi bilgileri vermeliyim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D06#alanlar. Rubrik: Üç alan eksiksiz: seri numarası, varsa hata kodu, yeniden üretme adımları.
  - Gerekli: MH-10'un seri numarası.
  - Gerekli: Görüntülendiyse hata kodu.
  - Gerekli: Sorunu yeniden üretme adımları.
  - Yasak: Belgede olmayan bir alan (ör. parola, OTP, fatura bilgisi) istemek.
- Gerçek: HTTP 200, `answered`, 2116 ms
  - İlk k: D06#alanlar, D06#kullanim, D10#kullanim, D10#musteri-istegi; kaynak/aday: D06#alanlar, D10#musteri-istegi
  - reason_code: —
  - Claim: Destek talebinde MH-10’un seri numarasını belirtin. [D06#alanlar]
  - Claim: Ekranda hata kodu görüntülendiyse talebe bu kodu ekleyin; hata kodu yoksa bu alanı boş bırakabilirsiniz. [D06#alanlar]
  - Claim: Sorunu yeniden üretmek için sorun ortaya çıkana kadar yaptığınız işlemleri hangi sırayla gerçekleştirdiğinizi yazın. [D06#alanlar]
  - Claim: Parolanızı veya OTP kodunuzu destek talebinde paylaşmayın; kişisel bilgileri gizlenmemiş bir görsel göndermeden önce bu bilgileri gizleyin. [D10#musteri-istegi]
  - Cevap: Destek talebinde MH-10’un seri numarasını belirtin. Ekranda hata kodu görüntülendiyse talebe bu kodu ekleyin; hata kodu yoksa bu alanı boş bırakabilirsiniz. Sorunu yeniden üretmek için sorun ortaya çıkana kadar yaptığınız işlemleri hangi sırayla gerçekleştirdiğinizi yazın. Parolanızı veya OTP kodunuzu destek talebinde paylaşmayın; kişisel bilgileri gizlenmemiş bir görsel göndermeden önce bu bilgileri gizleyin.
  - Sürüm kararları: support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### E07 · normal

- Soru: Tüm temsilciler çalışamıyorsa ilk yanıt ne zaman gelir?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D07#p1. Rubrik: P1 ve 2 çalışma saatlik ilk yanıt hedefi; çözüm süresi garantisine dönüştürülmemeli.
  - Gerekli: Tüm temsilcilerin çalışmasını durduran olay P1'dir.
  - Gerekli: P1 için ilk yanıt hedefi 2 çalışma saatidir.
  - Gerekli: Bu hedef çözüm süresi garantisi değildir.
  - Yasak: Sorunun 2 saat içinde çözüleceği / çözüm garantisi.
- Gerçek: HTTP 200, `answered`, 1547 ms
  - İlk k: D07#p1, D07#iletisim, D07#kullanim, D01#kullanim; kaynak/aday: D07#p1, D07#iletisim
  - reason_code: —
  - Claim: Tüm temsilcilerin çalışmasını durduran bir olay P1 olarak sınıflandırılır ve P1 olaylarda ilk yanıt hedefi 2 çalışma saatidir. [D07#p1]
  - Claim: Bu süre ilk yanıt hedefidir; sorunun 2 çalışma saati içinde çözüleceği anlamına gelmez. [D07#p1, D07#iletisim]
  - Cevap: Tüm temsilcilerin çalışmasını durduran bir olay P1 olarak sınıflandırılır ve P1 olaylarda ilk yanıt hedefi 2 çalışma saatidir. Bu süre ilk yanıt hedefidir; sorunun 2 çalışma saati içinde çözüleceği anlamına gelmez.
  - Sürüm kararları: priority-sla → D07; mh10-setup → D01
- İnsan incelemesi: pending

### E08 · normal

- Soru: Destek ekibine hangi saatlerde ulaşabilirim?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D08#saatler. Rubrik: Hafta içi 09.00–18.00, Türkiye saati (Europe/Istanbul).
  - Gerekli: Hafta içi ulaşılabilir.
  - Gerekli: Saatler 09.00–18.00.
  - Gerekli: Saatler Türkiye saatine (Europe/Istanbul) göredir.
  - Yasak: Hafta sonu veya 7/24 destek.
- Gerçek: HTTP 200, `answered`, 1529 ms
  - İlk k: D08#kullanim, D08#saatler, D06#kullanim, D10#kullanim; kaynak/aday: D08#saatler
  - reason_code: —
  - Claim: Destek ekibine hafta içi (pazartesi-cuma) Türkiye saatiyle 09.00–18.00 arasında ulaşabilirsiniz. [D08#saatler]
  - Cevap: Destek ekibine hafta içi (pazartesi-cuma) Türkiye saatiyle 09.00–18.00 arasında ulaşabilirsiniz.
  - Sürüm kararları: support-hours → D08; support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### E09 · normal

- Soru: Parolamı unuttum, ne yapmalıyım?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D09#sifre. Rubrik: Kayıtlı e-posta adresine gönderilen parola sıfırlama bağlantısı.
  - Gerekli: Giriş ekranından parola sıfırlama istenir.
  - Gerekli: Sıfırlama bağlantısı hesapta kayıtlı e-posta adresine gönderilir.
  - Yasak: Bağlantının görüşmede söylenen başka bir adrese gönderilebileceği.
- Gerçek: HTTP 200, `answered`, 2124 ms
  - İlk k: D09#sifre, D09#kullanim, D10#paylasim, D10#musteri-istegi; kaynak/aday: D09#sifre, D10#paylasim
  - reason_code: —
  - Claim: Destek panelinin giriş ekranından parola sıfırlama isteğinde bulunun; bağlantı hesapta kayıtlı e-posta adresine gönderilir ve bu bağlantıyla yeni parolanızı belirleyebilirsiniz. [D09#sifre]
  - Claim: Parolanızı destek personeliyle veya başka biriyle paylaşmayın; destek personeli de parolanızı istemez. [D10#paylasim]
  - Cevap: Destek panelinin giriş ekranından parola sıfırlama isteğinde bulunun; bağlantı hesapta kayıtlı e-posta adresine gönderilir ve bu bağlantıyla yeni parolanızı belirleyebilirsiniz. Parolanızı destek personeliyle veya başka biriyle paylaşmayın; destek personeli de parolanızı istemez.
  - Sürüm kararları: account-access → D09; safe-support-sharing → D10
- İnsan incelemesi: pending

### E10 · normal

- Soru: Destek personeline OTP kodumu göndereyim mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D10#paylasim. Rubrik: Hayır: parola ve OTP paylaşılmaz; destek personeli de istemez.
  - Gerekli: Hayır; OTP destek personeliyle paylaşılmaz.
  - Yasak: OTP'nin gönderilebileceği.
- Gerçek: HTTP 200, `answered`, 1449 ms
  - İlk k: D10#musteri-istegi, D10#paylasim, D06#alanlar, D06#dogruluk; kaynak/aday: D10#paylasim
  - reason_code: —
  - Claim: OTP kodunuzu destek personeliyle paylaşmayın; destek personeli de bu kodu istemez. [D10#paylasim]
  - Cevap: OTP kodunuzu destek personeliyle paylaşmayın; destek personeli de bu kodu istemez.
  - Sürüm kararları: safe-support-sharing → D10; support-ticket → D06
- İnsan incelemesi: pending

### E11 · unanswerable

- Soru: MH-10'un garantisi kaç ay?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: garanti süresi belgelerde yok; süre uydurulmamalı, kaynak gösterilmemeli.
  - Yasak: Herhangi bir garanti süresi.
- Gerçek: HTTP 200, `insufficient_evidence`, 1813 ms
  - İlk k: D04#sure, D01#tamamlama, D02#kullanim, D06#alanlar; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: MH-10 garantisinin kaç ay olduğu verilen bölümlerde belirtilmiyor.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: MH-10 garantisinin kaç ay olduğu verilen bölümlerde belirtilmiyor.
  - Sürüm kararları: returns → D04 (D03 expired); mh10-setup → D01; audio-troubleshooting → D02; support-ticket → D06
- İnsan incelemesi: pending

### E12 · unanswerable

- Soru: Almanya'daki müşteriler de 30 günde iade edebilir mi?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: İstek kapsamı TR/B2B/MH-10, soru Almanya'yı soruyor: insufficient_evidence; Türkiye kuralı Almanya'ya genellenmemeli.
  - Yasak: Türkiye/B2B kapsamındaki 30 günlük kuralın Almanya'ya uygulanması.
- Gerçek: HTTP 200, `partial`, 1515 ms
  - İlk k: D04#sure, D05#kullanim, D04#tarihler, D05#bedel; kaynak/aday: D04#sure
  - reason_code: unsupported_scope
  - Claim: MH-10 için iade talebi, ürünün tesliminden itibaren 30 takvim günü içinde açılabilir. [D04#sure]
  - Eksik konu: Bu 30 günlük iade süresinin Almanya'daki müşteriler için geçerli olup olmadığı, verilen belgelerde belirtilmiyor.
  - Cevap: MH-10 için iade talebi, ürünün tesliminden itibaren 30 takvim günü içinde açılabilir. Bu istekteki belgelerle yanıtlanamayan konular: Bu 30 günlük iade süresinin Almanya'daki müşteriler için geçerli olup olmadığı, verilen belgelerde belirtilmiyor.
  - Sürüm kararları: returns → D04 (D03 expired); refund-payment → D05
- Kontrol sorunu: status: partial, beklenen insufficient_evidence
- Kontrol sorunu: no_wrong_answer: 1 iddia üretildi
- İnsan incelemesi: pending

### E13 · unanswerable

- Soru: 4711 numaralı ticket'ım çözüldü mü?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `insufficient_evidence`; bölümler —. Rubrik: insufficient_evidence: canlı ticket sistemine erişim yok; durum uydurulmamalı.
  - Yasak: Ticket'ın çözüldüğü, kapandığı veya bir durumunun bilindiği.
- Gerçek: HTTP 200, `insufficient_evidence`, 1968 ms
  - İlk k: D02#ses-yok, D06#kullanim, D10#musteri-istegi, D10#paylasim; kaynak/aday: —
  - reason_code: not_in_documents
  - Eksik konu: 4711 numaralı ticket'ın çözülüp çözülmediğini doğrulayacak canlı ticket bilgisi bu bölümlerde yer almıyor; canlı sisteme erişimim yok.
  - Cevap: Onaylı belgelerde bu soruyu yanıtlayacak bilgi bulunamadı. Bu istekteki belgelerle yanıtlanamayan konular: 4711 numaralı ticket'ın çözülüp çözülmediğini doğrulayacak canlı ticket bilgisi bu bölümlerde yer almıyor; canlı sisteme erişimim yok.
  - Sürüm kararları: audio-troubleshooting → D02; support-ticket → D06; safe-support-sharing → D10
- İnsan incelemesi: pending

### E14 · paraphrase

- Soru: Ürünü geri yollamak için ne kadar vaktim var?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#sure. Rubrik: E03'ün farklı ifadesi: Türkiye/B2B kapsamında 30 takvim günü.
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Yasak: 14 takvim günü (süresi dolmuş 1.0 sürümü).
- Gerçek: HTTP 200, `answered`, 1386 ms
  - İlk k: D04#sure, D04#tarihler, D06#dogruluk, D07#iletisim; kaynak/aday: D04#sure, D04#tarihler
  - reason_code: —
  - Claim: İade talebini ürünün tesliminden itibaren 30 takvim günü içinde açabilirsiniz; takvim günü hesabına hafta sonları da dâhildir. [D04#sure, D04#tarihler]
  - Cevap: İade talebini ürünün tesliminden itibaren 30 takvim günü içinde açabilirsiniz; takvim günü hesabına hafta sonları da dâhildir.
  - Sürüm kararları: returns → D04 (D03 expired); support-ticket → D06; priority-sla → D07
- İnsan incelemesi: pending

### E15 · partial

- Soru: Türkiye'de kaç günüm var; Almanya'da da aynı mı?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `partial`; bölümler D04#sure. Rubrik: partial: Türkiye için 30 takvim günü kaynaklı; Almanya eksik konu olarak ayrılmalı.
  - Gerekli: Türkiye/B2B için iade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Yasak: Almanya için bir süre veya Türkiye kuralının Almanya'ya uygulanması.
- Gerçek: HTTP 200, `insufficient_evidence`, 2789 ms
  - İlk k: D08#saat-dilimi, D05#is-gunu, D08#saatler, D04#tarihler; kaynak/aday: —
  - reason_code: unsupported_scope
  - Eksik konu: Türkiye için kaç gün olduğu; verilen bölümlerde iade süresinin uzunluğu belirtilmiyor.
  - Eksik konu: Almanya’da sürenin aynı olup olmadığı; Almanya bu isteğin kapsamı dışında.
  - Cevap: Belgeler yalnızca isteğin kapsamı için geçerlidir; soruda geçen başka bir kapsama uygulanamaz. Bu istekteki belgelerle yanıtlanamayan konular: Türkiye için kaç gün olduğu; verilen bölümlerde iade süresinin uzunluğu belirtilmiyor; Almanya’da sürenin aynı olup olmadığı; Almanya bu isteğin kapsamı dışında.
  - Sürüm kararları: support-hours → D08; refund-payment → D05; returns → D04 (D03 expired)
- Kontrol sorunu: status: insufficient_evidence, beklenen partial
- Kontrol sorunu: retrieval: D04#sure ilk k'da yok
- Kontrol sorunu: citation: D04#sure kaynak gösterilmedi
- Kontrol sorunu: no_unnecessary_refusal: insufficient_evidence döndü
- Kontrol sorunu: required_facts: bulunamadı: Türkiye/B2B için iade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
- İnsan incelemesi: pending

### E16 · historical_version

- Soru: 1 Haziran 2026'da iade süresi neydi?
- İstek: as_of `2026-06-01`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D03#sure. Rubrik: İstek as_of=2026-06-01: 14 takvim günü (D03); D04 future_effective görünmeli.
  - Gerekli: 1.0 sürümünde iade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
  - Yasak: 30 takvim günü (henüz yürürlükte olmayan 2.0 sürümü).
- Gerçek: HTTP 200, `partial`, 2602 ms
  - İlk k: D03#uygulama, D05#bedel, D05#kullanim, D03#tarihler; kaynak/aday: D03#tarihler
  - reason_code: not_in_documents
  - Claim: İade süresi ürünün teslim tarihinden itibaren sayılır; iade talebinin açıldığı tarih süreyi başlatmaz. [D03#tarihler]
  - Eksik konu: 1 Haziran 2026'da geçerli iade süresinin kaç gün olduğu belirtilmiyor.
  - Cevap: İade süresi ürünün teslim tarihinden itibaren sayılır; iade talebinin açıldığı tarih süreyi başlatmaz. Bu istekteki belgelerle yanıtlanamayan konular: 1 Haziran 2026'da geçerli iade süresinin kaç gün olduğu belirtilmiyor.
  - Sürüm kararları: returns → D03 (D04 future_effective); refund-payment → D05
- Kontrol sorunu: status: partial, beklenen answered
- Kontrol sorunu: retrieval: D03#sure ilk k'da yok
- Kontrol sorunu: citation: D03#sure kaynak gösterilmedi
- Kontrol sorunu: required_facts: bulunamadı: 1.0 sürümünde iade talebi teslimden itibaren 14 takvim günü içinde açılabilir.
- İnsan incelemesi: pending

### E17 · false_premise

- Soru: P1 sorunları kesin iki saatte çözülüyor, doğru mu?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D07#p1. Rubrik: Yanlış ön kabul düzeltilmeli: 2 çalışma saati ilk yanıt hedefidir, çözüm garantisi değildir.
  - Gerekli: 2 çalışma saati çözüm değil ilk yanıt hedefidir.
  - Gerekli: Bu hedef çözüm süresi garantisi değildir.
  - Yasak: P1 sorunlarının iki saatte çözüldüğünü onaylamak.
- Gerçek: HTTP 200, `answered`, 1877 ms
  - İlk k: D07#p1, D07#iletisim, D07#kullanim, D02#ses-yok; kaynak/aday: D07#p1, D07#iletisim
  - reason_code: —
  - Claim: P1 olaylarda iki çalışma saati, destek ekibinin ilk yanıtı için belirlenen hedeftir; sorunun iki saatte çözüleceği garanti edilmez. [D07#p1, D07#iletisim]
  - Cevap: P1 olaylarda iki çalışma saati, destek ekibinin ilk yanıtı için belirlenen hedeftir; sorunun iki saatte çözüleceği garanti edilmez.
  - Sürüm kararları: priority-sla → D07; audio-troubleshooting → D02
- İnsan incelemesi: pending

### E18 · multi_source

- Soru: İade için kaç günüm var, kabulden sonra param ne zaman döner?
- İstek: as_of `2026-10-04`, kapsam `TR/B2B/MH-10`, mod `generative`
- Beklenen (üretken mod): `answered`; bölümler D04#sure, D05#bedel. Rubrik: İki kaynak birlikte: 30 takvim günü (D04#sure) ve kabulden sonra 5 iş günü (D05#bedel).
  - Gerekli: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
  - Gerekli: İade bedeli kabulden sonra 5 iş günü içinde ödenir.
  - Yasak: 14 takvim günü (süresi dolmuş sürüm).
- Gerçek: HTTP 200, `partial`, 2391 ms
  - İlk k: D05#bedel, D05#kullanim, D04#tarihler, D05#is-gunu; kaynak/aday: D05#bedel
  - reason_code: not_in_documents
  - Claim: İade bedeli, iade kabul edildikten sonra 5 iş günü içinde ödenir; bu süre ürünün kargoya verildiği tarihten başlamaz. [D05#bedel]
  - Eksik konu: İade talebinin açılabileceği süre belgelerde belirtilmiyor.
  - Cevap: İade bedeli, iade kabul edildikten sonra 5 iş günü içinde ödenir; bu süre ürünün kargoya verildiği tarihten başlamaz. Bu istekteki belgelerle yanıtlanamayan konular: İade talebinin açılabileceği süre belgelerde belirtilmiyor.
  - Sürüm kararları: refund-payment → D05; returns → D04 (D03 expired)
- Kontrol sorunu: status: partial, beklenen answered
- Kontrol sorunu: retrieval: D04#sure ilk k'da yok
- Kontrol sorunu: citation: D04#sure kaynak gösterilmedi
- Kontrol sorunu: required_facts: bulunamadı: İade talebi teslimden itibaren 30 takvim günü içinde açılabilir.
- İnsan incelemesi: pending

