# Teknik kararlar ve bilinen sınırlar

Her karar notu şu sırayı izler: **Seçim · Alternatif · Neden · Bedel · Ne zaman değişir.** Davranışın kendisi ve sözleşme `docs/project-spec.md` içindedir; burada tekrar edilmez.

## Karar notları

### K15 — Embedding: modelin kendi ONNX dosyası + ONNX Runtime (CPU)
- **Seçim:**
  - Model `intfloat/multilingual-e5-small`, Hugging Face commit'i `614241f622f53c4eeff9890bdc4f31cfecc418b3`'e sabit. Commit, Hugging Face API'sinden alındı.
  - Model reposundaki `onnx/model.onnx` ve `onnx/tokenizer.json` dosyaları `onnxruntime` ve `tokenizers` ile CPU'da çalışır.
  - Mean pooling ve L2 normalizasyonu `app/embeddings.py` içinde, birkaç satırlık kod.
  - Yeni bağımlılıklar: `onnxruntime`, `tokenizers`, `huggingface-hub` (indirme ve önbellek), `numpy`.
- **Alternatif:** `sentence-transformers` + PyTorch (CPU). Kod daha kısa olurdu, çünkü pooling ve normalizasyon kütüphanede hazır.
- **Neden:**
  - Linux imaj boyutu. PyPI'daki torch 2.14.1 Linux wheel'i 454 MB (aarch64) ve 555 MB (x86_64); x86_64'te ayrıca CUDA paketleri iner. CPU-only indeksteki wheel 159 / 196 MB'tır ve onu kullanmak için uv'de ayrı bir paket indeksi tanımlamak gerekir. `onnxruntime` 1.30.0 wheel'i 21–24 MB, `tokenizers` yaklaşık 3,5 MB. (Bunlar indirme boyutlarıdır; kurulu boyut daha büyüktür.)
  - Daha az dolaylı bağımlılık: transformers, scipy, scikit-learn ve Pillow gelmez.
  - ONNX dosyası modelin kendi reposunda ve aynı commit'te. Ayrı bir dönüştürme adımına veya başkasının yüklediği bir kopyaya gerek yok.
- **Doğrulama:**
  - Aynı commit'te `sentence-transformers` 6.1.0 + torch 2.14.1 ile üretilen vektörlerle karşılaştırıldı. Karşılaştırma ayrı, geçici bir ortamda yapıldı; bu paketler projeye eklenmedi.
  - 5 Türkçe sorgu ve bölüm girdisinde en büyük mutlak fark 1,5e-7, iki girdi arasındaki skor farkı en fazla 3,6e-7 çıktı.
  - Yüklenen model 384 boyutlu vektör üretiyor. Model dosyası 512 tokenlık girdiyi çalıştırıyor, 513 tokenda hata veriyor (`tests/test_embeddings_model.py`).
- **Bedel:**
  - Pooling ve normalizasyon bizim kodumuzda. Yanlış yazılırsa sessizce kötü vektör üretilebilir. Buna karşı birim testler (padding ortalamaya girmez; sıfır veya NaN vektör hatadır) ve gerçek model testleri (boyut, birim norm, basit bir sıralama kontrolü) var.
  - Başka bir model veya revision için ONNX dosyasının varlığı, boyut, token sınırı ve sıralama yeniden doğrulanmalıdır.
- **Ne zaman değişir:** ONNX dosyası olmayan bir modele geçilirse ya da pooling kodunun bakımı sorun olursa `sentence-transformers` + CPU torch kullanılır; imaj büyür. Revision değişirse `uv run pytest -m model` ve `uv run python measure_retrieval.py` yeniden çalıştırılır.

### K16 — Türetilmiş indeks: SQLite, fingerprint ve başlangıçta yeniden üretim
- **Seçim:**
  - Bölüm embedding'leri `INDEX_PATH` altındaki SQLite dosyasında little-endian float32 bayt olarak saklanır. Çalışırken bellekte tek bir NumPy matrisi olarak durur.
  - Fingerprint şunları kapsar: belge dosya adı, metadata, embedding girdisi (önek + başlık yolu + içerik), model adı ve revision, indeks biçim sürümü.
  - Kayıtlı indeks şu kontrollerden geçmezse kullanılmaz: fingerprint, bölüm listesi, vektör boyutu, NaN veya sonsuz değer, birim norm. O zaman uyarı loglanır ve indeks yeniden üretilir.
  - Yeniden üretim geçici bir dosyaya yazılır, aynı kontrollerle geri okunur ve `os.replace` ile yerine konur.
  - Yeni üretilen vektörler geçersizse servis başlamaz ve eski dosya olduğu gibi kalır.
- **Alternatif:** Her başlangıçta embedding'leri yeniden hesaplamak (kalıcı dosya yok); `.npy` veya pickle önbelleği; ayrı vektör veritabanı; bozuk indekste başlangıcı durdurmak.
- **Neden:**
  - Hangi korpus ve modelle üretildiği tek bir değerle (fingerprint) izlenebilir. Readiness ve değerlendirme koşusu bu değeri kaydedebilir.
  - Pickle keyfî kod çalıştırabilir. Float32 bayt ve boyut kontrolü yalnızca sayı okur.
  - İndeks Markdown'dan her zaman yeniden üretilebilir. Bu yüzden bozuk bir dosyada başlangıcı durdurmak yerine yeniden üretmek ve nedenini loglamak yeterli. Bozuk dosya sessizce kullanılmaz.
- **Bedel:**
  - Bu korpus için kalıcı indeks zorunlu değil. 32 bölümün embedding'i geliştirme makinesinde (Apple Silicon, CPU) 0,42 sn sürüyor; her başlangıçta yeniden hesaplamak da yeterli olurdu. Buna karşılık yaklaşık 150 satır kod ve testleri var.
  - `INDEX_FORMAT_VERSION` elle artırılmalıdır. Önek veya başlık yolu biçimi değişirse fingerprint bunu kendiliğinden yakalar, çünkü girdi metni fingerprint'e dâhil. Pooling kodu değişip sürüm artırılmazsa eski vektörler kullanılmaya devam eder.
  - Metadata fingerprint'e dâhil olduğu için yalnızca `valid_to` değişse bile tüm embedding'ler yeniden hesaplanır. 32 bölümde bu önemsizdir.
- **Ne zaman değişir:** Korpus binlerce bölüme büyürse, bölüm hash'ine göre artımlı güncelleme ve yaklaşık arama (ANN) düşünülür.

### K17 — Arama: önce sürüm ve kapsam görünümü, sonra tam dot product; skor eşiği kapalı
- **Seçim:**
  - `retrieve` yalnızca `select_versions`'ın seçtiği belgelerin bölümlerini puanlar.
  - Skor, normalize vektörlerde dot product'tır (yani cosine). Sıralama skora göre azalan; eşit skorda `chunk_id` artan. `top_k=4`.
  - `MIN_RETRIEVAL_SCORE` varsayılan olarak boş, yani eşik kapalı.
- **Alternatif:** Tüm korpusta top-k alıp sonra filtrelemek; BM25, hibrit arama veya reranker; sabit bir eşik (ör. 0,80).
- **Neden:**
  - Sonradan filtrelemede süresi dolmuş bir sürüm daha yüksek skor alırsa top-k'yı doldurur ve geçerli bölümü dışarı iter. Testte `top_k=1` iken D03 en yakın bölüm olsa da D04 dönüyor; sonradan filtreleme burada boş sonuç verirdi.
  - 32 bölümde tam tarama milisaniyenin altında sürer ve incelemesi kolaydır.
- **Eşik ölçümü:**
  - 4 geliştirme sorusu kullanıldı (`eval/dev_questions.jsonl`); 18 değerlendirme sorusu bu karar için kullanılmadı.
  - Komut: `uv run python measure_retrieval.py` (`src/rag_service` içinden). Model `intfloat/multilingual-e5-small@614241f…`, `top_k=4`.

  | Soru | Tür | Beklenen bölüm (sıra, skor) | 1. sonuç (skor) | 4. sonuç (skor) |
  |---|---|---|---|---|
  | DEV01 hata görseli paylaşımı | normal | `D10#paylasim` (3, 0,8686) | `D10#musteri-istegi` (0,8817) | `D10#kullanim` (0,8660) |
  | DEV02 sıfırlama bağlantısının adresi | normal | `D09#eposta` (1, 0,9130) | `D09#eposta` (0,9130) | `D10#musteri-istegi` (0,8654) |
  | DEV03 Şubat'ta açılan iadede kargo bedeli (`as_of=2026-02-16`) | sürüm | `D03#kargo` (2, 0,8593) | `D05#kullanim` (0,8657) | `D03#tarihler` (0,8228) |
  | DEV04 şarj süresi | cevapsız | — | `D01#kullanim` (0,8610) | `D02#kullanim` (0,8395) |

  - Beklenen üç bölümün üçü de ilk 4 içinde.
  - Cevapsız sorunun en yüksek skoru (0,8610), cevaplanabilir bir sorunun beklenen bölümünün skorundan (DEV03: 0,8593) daha yüksek. İlk 4'teki tüm skorlar 0,82–0,91 arasında sıkışık.
  - DEV04'ü eleyecek bir eşik, DEV03'ün doğru bölümünü de eler. Bu nedenle eşik kapalı kalır.
- **Bedel:**
  - Eşik kapalı olduğu için arama cevapsız sorularda da 4 aday döndürür. Konuya yakın ama cevapsız soruların reddi, üretim aşamasındaki kanıt yeterliliği kontrolüne dayanır. Alıntı modunda bu adaylar cevap olarak değil, aday olarak sunulur.
  - Açıklayıcı bölümler (`kullanim`, `musteri-istegi`) zorunlu bölümlerle aynı ilk 4'ü paylaşıyor. DEV01'de beklenen bölüm 3. sırada. DEV03'te 1. sırada `D05#kullanim` var; bu bölüm iade kargosunun kendi konusu olmadığını söylüyor.
- **Ne zaman değişir:**
  - Geliştirme veya değerlendirme ölçümü beklenen bölümün ilk k dışında kaldığını gösterirse önce bölümleme ve girdi düzeltilir (ör. açıklayıcı bölümü zorunlu bölümle birleştirmek). Ölçüm ve değişiklik kaydedilir.
  - Eşik ancak cevaplanabilir ve cevapsız soruları ayıran, ölçülmüş bir değer bulunursa açılır.

## Bilinen sınırlar

- **İlk indirme.** İlk başlangıç internet ister: model yaklaşık 470 MB, tokenizer yaklaşık 17 MB olarak `MODEL_CACHE_DIR` altına iner. Önbellek dolduktan sonra sabit commit sayesinde ağ isteği yapılmaz. Sıfırdan internetsiz kurulum desteklenmez.
- **Revision kodda sabit.** Embedding revision'ı `app/settings.py` içinde tam commit hash'i olarak sabittir; ortam değişkeniyle değiştirilemez. `EMBEDDING_MODEL` değiştirilirse aynı commit o repoda bulunmaz ve başlangıç hata verir.
- **Soru uzunluğu.** Sorgu da 512 token sınırına tabidir. Sınırı aşan soru kesilmez, `EmbeddingError` verir. 2.000 karakterlik soru sınırı, sorunun 512 tokenın altında kalacağını garanti etmez.
- **Skorların taşınabilirliği.** Skorlar farklı CPU mimarilerinde son basamaklarda (yaklaşık 1e-6) farklı çıkabilir. Eşit skorda `chunk_id` sıralaması yalnızca birebir eşit skorlar için devreye girer.
- **Küçük ölçüm.** Eşik kararı 4 geliştirme sorusuna dayanır; genellenebilir bir sonuç iddia edilmez.
