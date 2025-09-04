from typing import Optional, List, Tuple
from ..core.repository import WordRepository, ExampleRepository, ExerciseRepository
from ..models import Word, Exercise
from ..core.ai_client import AIClient

AUTO_LEARN_MIN_AVG = 7.0  # ortalama > 7 ise otomatik öğrenildi

class WordService:
    def __init__(self, repo: Optional[WordRepository] = None,
                 exrepo: Optional[ExampleRepository] = None,
                 exerrepo: Optional[ExerciseRepository] = None,
                 ai: Optional[AIClient] = None):
        self.repo = repo or WordRepository()
        self.exrepo = exrepo or ExampleRepository()
        self.exerrepo = exerrepo or ExerciseRepository()
        self.ai = ai or AIClient()

    # ---- words ----
    def add_or_get(self, term_en: str, translation_tr: str, group_title: Optional[str] = None) -> Word:
        existing = self.repo.find_by_term(term_en)
        if existing:
            if translation_tr and translation_tr != existing.translation_tr:
                self.repo.update_translation(existing.id, translation_tr)
            if group_title and group_title != (existing.group_title or None):
                self.repo.update_group(existing.id, group_title)
            return self.repo.get_word(existing.id)
        _id = self.repo.add_word(term_en, translation_tr, group_title)
        return self.repo.get_word(_id)

    def set_learned(self, word_id: int, learned: bool) -> None:
        self.repo.set_learned(word_id, learned)

    def list_group_titles(self) -> List[str]:
        return self.repo.list_group_titles()

    def list_words(self, include_learned: bool = True) -> List[Word]:
        return self.repo.list_words(include_learned=include_learned)

    # ---- examples ----
    def add_example_manual(self, word_id: int, text: str) -> int:
        # Skorsuz örnek; ortalamayı etkilemez
        return self.exrepo.add_example(word_id, text, origin="MANUAL")

    def list_examples(self, word_id: int):
        return self.exrepo.list_examples(word_id)

    def get_avg_score(self, word_id: int) -> float:
        return self.exrepo.avg_score(word_id)

    def _auto_mark_learned_by_avg(self, word_id: int):
        avg = self.get_avg_score(word_id)
        w = self.repo.get_word(word_id)
        if w and not w.is_learned and avg > AUTO_LEARN_MIN_AVG:
            self.repo.set_learned(word_id, True)

    # ---- exercises (AI) ----
    def create_exercise_tr(self, word_id: int) -> int:
        w = self.repo.get_word(word_id)
        if not w:
            raise ValueError("word not found")
        sentence = self.ai.generate_tr_sentence(w.term_en, w.translation_tr)
        return self.exerrepo.add_exercise(w.id, "TR", w.term_en, w.translation_tr, sentence)

    def create_exercise_en(self, word_id: int) -> int:
        w = self.repo.get_word(word_id)
        if not w:
            raise ValueError("word not found")
        sentence = self.ai.generate_en_sentence(w.term_en, w.translation_tr)
        return self.exerrepo.add_exercise(w.id, "EN", w.term_en, w.translation_tr, sentence)

    def list_exercises(self, word_id: int) -> List[Exercise]:
        return self.exerrepo.list_exercises(word_id)

    def evaluate_exercise(self, ex_id: int, user_answer: str) -> Tuple[int, str]:
        ex = self.exerrepo.get_exercise(ex_id)
        if not ex:
            raise ValueError("exercise not found")
        score, feedback = self.ai.score_translation(ex.direction, ex.sentence, user_answer)
        # egzersizi güncelle
        self.exerrepo.update_answer_and_score(ex_id, user_answer, score, feedback)
        # skorlu örnek olarak kaydet
        self.exrepo.add_example(
            word_id=ex.word_id,
            text=user_answer,
            origin="AI",
            direction=ex.direction,
            score=score,
            feedback=feedback,
            exercise_id=ex.id,
        )
        # ortalama → otomatik öğrenildi
        self._auto_mark_learned_by_avg(ex.word_id)
        return score, feedback