# 🇬🇧→🇹🇷 Vocabulary Desktop App (PySide6)

Kişisel İngilizce → Türkçe kelime çalışması için modern bir masaüstü uygulaması.
**DeepL** ile çeviri, **OpenRouter** (DeepSeek) ile cümle üretme & çeviri **skorlama**, örnek cümle arşivi ve “öğrenildi” takibi.


---

## ✨ Özellikler

* **EN→TR çeviri** (DeepL API).
* Her kelime için **yeni sekme**:
  **Sol**: Notlar, örnek cümleler (skorlu & skorsuz), anlık ortalama skor.
  **Sağ**: AI görevleri (TR/EN cümle üret, çevirini yaz, 10 üzerinden skor al).
* **Skor ortalaması > 7.0** olduğunda otomatik **“Öğrenildi”** işaretleme; manuel olarak da değiştirilebilir.
* **Skorsuz örnek** ekleme (AI kapalıyken de çalışabilme).
* Düzenli, modüler Python kod yapısı + **SQLite** veritabanı (yerel dosya).

---

## 📦 Proje Yapısı

```
vocab-app/
├─ README.md
├─ requirements.txt
└─ app/
   ├─ main.py                # Uygulama girişi
   ├─ models.py              # Word / Example / Exercise veri sınıfları
   ├─ core/
   │  ├─ database.py         # SQLite bağlantısı + şema
   │  └─ repository.py       # Word / Example / Exercise CRUD
   ├─ services/
   │  └─ word_service.py     # İş kuralları, AI akışı (OpenRouter + DeepL)
   └─ ui/
      ├─ main_window.py      # Kütüphane listesi, sekmeler
      └─ word_page.py        # Sol: Not+Örnekler, Sağ: AI görevleri (split layout)
```

---

## ⚙️ Kurulum

### 1) Sanal ortam & bağımlılıklar

```bash
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Ortam değişkenleri

Uygulama şu **ortam değişkenleri** ile çalışır:

* `DEEPL_API_KEY` — DeepL API anahtarın (Free/Pro).
* `OPENROUTER_API_KEY` — OpenRouter anahtarı (ücretsiz modellerle başlangıç).
* (Opsiyonel) `OPENROUTER_MODEL` — Varsayılan `deepseek/deepseek-chat`.
* (Opsiyonel) `OPENROUTER_MODEL_FALLBACK` — Örn. `deepseek/deepseek-r1:free`.
* (Opsiyonel) `OPENROUTER_TIMEOUT` (sn), `OPENROUTER_MAX_RETRIES`.

**Windows PowerShell**

```powershell
$env:DEEPL_API_KEY="YOUR-KEY"
$env:OPENROUTER_API_KEY="YOUR-KEY"
$env:OPENROUTER_MODEL="deepseek/deepseek-chat"
```

**macOS/Linux (bash/zsh)**

```bash
export DEEPL_API_KEY="YOUR-KEY"
export OPENROUTER_API_KEY="YOUR-KEY"
export OPENROUTER_MODEL="deepseek/deepseek-chat"
```

> API anahtarlarını **repoya koymayın**. `.env` kullanacaksanız `.gitignore` içinde tutun.

### 3) Çalıştırma

```bash
python -m app.main
```

İlk çalıştırmada `app/vocab.sqlite3` oluşturulur.

---

## 🧭 Kullanım

1. Ana ekrandan **kelime ekle** (EN terim, TR karşılık, grup başlığı opsiyonel).
2. Kütüphaneden kelimeyi çift tıkla → kelime **yeni sekmede** açılır.
3. **Sol panel**: Notlar + örnek cümleler.

   * Görev **seçili değilken** skorsuz örnek ekleyebilirsin (ortalama skora dahil olmaz).
4. **Sağ panel (AI)**:

   * **TR cümle üret (AI)**: Türkçe cümle üretir; sen **İngilizce** çevirini yazarsın.
   * **EN sentence (AI)**: İngilizce cümle üretir; sen **Türkçe** çevirini yazarsın.
   * **Değerlendir (AI)** butonu → çevirin **0–10** arası puanlanır, kısa geri bildirim gelir.
   * Cevabın **skorlu örnek** olarak arşivlenir; **ortalama** anında güncellenir.
   * Ortalama > 7.0 → kelime **otomatik** öğrenildi; istersen manuel olarak geri alabilirsin.

---

## 🧱 Veri Modeli (özet)

* **Word**: `term_en`, `translation_tr`, `notes`, `group_title`, `is_learned`, `learned_at`…
* **Exercise**: `direction ('TR'|'EN')`, `sentence`, `user_answer`, `score`, `feedback`…
* **Example**: Kullanıcı cümleleri (skorlu/skorsuz). Skorlu olanlar ortalamaya dahil edilir.

Veriler SQLite’da tutulur. DB dosyası varsayılan olarak `app/vocab.sqlite3` (git’e dahil **değil**).

## 🧰 Sorun Giderme

* **DeepL 403 / yetki hatası** → `DEEPL_API_KEY` geçerli mi? Free anahtarlar genellikle `:fx` ile biter.
* **DeepL kota** → Free hesap limitine takıldıysa çeviri hata verebilir.
* **OpenRouter 408 / timeout** → Internet/servis gecikmesi; tekrar deneyin, `OPENROUTER_TIMEOUT` değerini yükseltin, `OPENROUTER_MODEL_FALLBACK` tanımlayın.
* **Kalın satırlar** → `ui/word_page.py` içinde `font-size` ve `padding` değerleriyle satır yüksekliğini ince ayarlayabilirsiniz.
* **DB’yi sıfırla** → `app/vocab.sqlite3` dosyasını silip uygulamayı tekrar başlatın.

---

## 🛣️ Yol Haritası

* Kelime tekrar planlayıcı (SRS)
* Çoklu çeviri sağlayıcıları
* İçe/Dışa aktarma (CSV/JSON)

---

## 🤝 Katkı

PR ve issue’lar açık. UI mikro düzeltme önerilerine de açığız.
