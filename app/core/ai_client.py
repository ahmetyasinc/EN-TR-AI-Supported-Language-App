# app/core/ai_client.py
import os, json, re, time
from typing import Tuple
from openai import OpenAI, APITimeoutError, APIConnectionError, APIError, RateLimitError

def _to_int(s, default):
    try:
        return int(float(str(s)))
    except Exception:
        return default

class AIClient:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY tanımlı değil.")

        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")  # <-- chat'i öne aldık
        self.fallback_model = os.getenv("OPENROUTER_MODEL_FALLBACK", "deepseek/deepseek-r1:free")
        self.timeout = _to_int(os.getenv("OPENROUTER_TIMEOUT", "20"), 20)
        self.max_retries = _to_int(os.getenv("OPENROUTER_MAX_RETRIES", "2"), 2)

        self.client = OpenAI(api_key=api_key, base_url=self.base_url)

    # ---------- public ----------
    def generate_tr_sentence(self, term_en: str, tr_word: str) -> str:
        prompt = (
            "Sadece TEK bir Türkçe cümle üret. Açıklama yazma.\n"
            "Seviye: C2; 14-22 kelime; doğal, akıcı, ileri seviye sentaks; yan cümlecik/ortaç veya karşıtlık yapısı kullan.\n"
            "Basmakalıp ifadelerden kaçın. Özel isim kullanma. Tırnak ekleme.\n"
            f"İngilizce kelime: '{term_en}'. Türkçe karşılığı: '{tr_word}'.\n"
            f"Cümlede mutlaka '{tr_word}' geçsin ve anlamı korunmuş olsun."
        )
        return self._complete_compact(
            [{"role": "user", "content": prompt}],
            max_tokens=128, temperature=0.8
        )

    def generate_en_sentence(self, term_en: str, tr_word: str) -> str:
        prompt = (
            "Write EXACTLY ONE English sentence. No explanations.\n"
            "Level: C2; 14-22 words; natural, idiomatic, advanced syntax; use a subordinate clause or concessive structure.\n"
            "Avoid clichés and named entities. Do not use quotes.\n"
            f"Target English word: '{term_en}'. Its Turkish meaning: '{tr_word}'.\n"
            f"The sentence must include '{term_en}' and preserve its intended meaning."
        )
        return self._complete_compact(
            [{"role": "user", "content": prompt}],
            max_tokens=128, temperature=0.8
        )

    def score_translation(self, direction: str, original_sentence: str, user_translation: str) -> Tuple[int, str]:
        """
        direction == 'TR': original TR, user EN -> better önerisi İNGİLİZCE döner.
        direction == 'EN': original EN, user TR -> better önerisi TÜRKÇE döner.
        """
        if direction == 'TR':
            src_lang, tgt_lang = 'Turkish', 'English'
            better_hint = "Give 'better' in English."
            better_label = "Daha akıcı öneri (EN)"
        else:
            src_lang, tgt_lang = 'English', 'Turkish'
            better_hint = "Give 'better' in Turkish."
            better_label = "Daha akıcı öneri (TR)"

        system = {"role": "system", "content": "You are a precise bilingual grader. Return only JSON."}
        user = {"role": "user", "content": (
            "Evaluate the user's translation on adequacy (meaning preservation), fluency, and naturalness.\n"
            f"Source ({src_lang}): {original_sentence}\n"
            f"User translation ({tgt_lang}): {user_translation}\n\n"
            "Return ONLY strict JSON with fields:\n"
            "  'score': integer 0-10 (no text),\n"
            "  'feedback': a short Turkish sentence explaining the main issue(s),\n"
            "  'better': a more fluent/natural target-language version that preserves the meaning.\n"
            f"{better_hint}"
        )}
        raw = self._complete_compact([system, user], max_tokens=200, temperature=0.2)

        score, fb, better = self._parse_grade_json(raw)
        # 'feedback' + daha akıcı öneriyi tek metinde birleştiriyoruz (DB şemasını büyütmeden).
        combined = fb.strip()
        if better:
            combined = f"{combined}\n{better_label}: {better}"
        return score, combined

    def _parse_grade_json(self, text: str) -> Tuple[int, str, str]:
        """
        JSON beklenen alanlar: score, feedback, better
        Yoksa sayı yakalama ile düşer; better boş kalır.
        """
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                data = json.loads(m.group(0))
                s = int(data.get("score", 0))
                fb = str(data.get("feedback", "") or data.get("feedback_tr", ""))
                better = str(data.get("better", "") or data.get("suggested", "")).strip()
                s = max(0, min(10, s))
                return s, fb, better
            except Exception:
                pass
        # Düşme: "7/10" gibi bir sayı varsa al, feedback boş bırak.
        m2 = re.search(r"(\d{1,2})\s*/?\s*10", text)
        if m2:
            s = max(0, min(10, int(m2.group(1))))
            return s, "", ""
        return 0, "", ""

    # ---------- internals ----------
    def _complete_compact(self, messages, *, max_tokens=128, temperature=0.7) -> str:
        """Kısa prompt + timeout + retry + reasoning azaltma + fallback."""
        models_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_try.append(self.fallback_model)

        last_err = None
        for model_name in models_try:
            for attempt in range(self.max_retries + 1):
                try:
                    kwargs = dict(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=self.timeout,
                    )
                    # R1 gibi reasoning modelleri için düşünme eforunu azalt
                    if "r1" in model_name.lower() or "reason" in model_name.lower():
                        kwargs["reasoning"] = {"effort": "low"}  # içerik için yer kalsın

                    resp = self.client.chat.completions.create(**kwargs)
                    msg = resp.choices[0].message
                    content = (getattr(msg, "content", "") or "").strip()

                    # İçerik gelmediyse (sadece reasoning üretilmiş olabilir) -> bir kez daha, ama fallback ile
                    if not content and model_name == self.model and self.fallback_model:
                        # küçük bir bekleme + fallback denemesi
                        time.sleep(0.6)
                        break  # iç döngüden çıkar, fallback modeline geç

                    if not content:
                        raise APIError("Empty content from model.")

                    return content

                except (APITimeoutError, APIConnectionError, RateLimitError, APIError) as e:
                    last_err = e
                    time.sleep(1.2 * (attempt + 1))
                    continue

        raise RuntimeError(f"AI isteği başarısız: {last_err}")

    def _extract_score_json(self, text: str) -> Tuple[int, str]:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                data = json.loads(m.group(0))
                s = int(data.get("score", 0))
                fb = str(data.get("feedback", ""))
                s = max(0, min(10, s))
                return s, fb
            except Exception:
                pass
        m2 = re.search(r"(\d{1,2})\s*/?\s*10", text)
        if m2:
            s = max(0, min(10, int(m2.group(1))))
            return s, ""
        return 0, ""
