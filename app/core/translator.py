from __future__ import annotations
import os

try:
    import deepl  # DeepL resmi SDK
    _DEEPL_OK = True
except Exception:
    _DEEPL_OK = False

class Translator:
    """
    EN→TR çeviri için **yalnızca DeepL** kullanır.

    Gerekli ortam değişkeni:
      - DEEPL_API_KEY: DeepL API anahtarın (Free veya Pro)
        * Free hesaplar için anahtar genelde "...:fx" ile biter.
    """

    def __init__(self, source: str = "en", target: str = "tr"):
        self.source = source
        self.target = target
        self.api_key = os.getenv("DEEPL_API_KEY")
        if not self.api_key:
            raise RuntimeError("DEEPL_API_KEY tanımlı değil. Lütfen ortam değişkenini ayarlayın.")
        if not _DEEPL_OK:
            raise RuntimeError("deepl paketi yüklü değil. 'pip install deepl' ile kurun.")
        self._client = deepl.Translator(self.api_key)

    def translate(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        try:
            result = self._client.translate_text(
                text,
                source_lang=self.source.upper(),
                target_lang=self.target.upper(),
            )
            return result.text
        except deepl.exceptions.AuthorizationException:
            return "Çeviri yapılamadı: DeepL yetkilendirme hatası (API anahtarı)."
        except deepl.exceptions.QuotaExceededException:
            return "Çeviri yapılamadı: DeepL kota sınırı aşıldı."
        except Exception as e:
            return f"Çeviri yapılamadı: {e}"