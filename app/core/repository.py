from typing import List, Optional
from .database import get_conn
from ..models import Word, Example, Exercise


class WordRepository:
    def add_word(self, term_en: str, translation_tr: str, group_title: Optional[str] = None) -> int:
        with get_conn() as c:
            cur = c.execute(
                "INSERT INTO words(term_en, translation_tr, group_title) VALUES (?, ?, ?)",
                (term_en.strip(), translation_tr.strip(), (group_title or None)),
            )
            c.commit()
            return int(cur.lastrowid)

    def update_notes(self, word_id: int, notes: str) -> None:
        with get_conn() as c:
            c.execute("UPDATE words SET notes = ? WHERE id = ?", (notes, word_id))
            c.commit()

    def update_translation(self, word_id: int, new_translation_tr: str) -> None:
        with get_conn() as c:
            c.execute("UPDATE words SET translation_tr = ? WHERE id = ?", (new_translation_tr, word_id))
            c.commit()

    def update_group(self, word_id: int, group_title: Optional[str]) -> None:
        with get_conn() as c:
            c.execute("UPDATE words SET group_title = ? WHERE id = ?", (group_title, word_id))
            c.commit()

    def set_learned(self, word_id: int, learned: bool) -> None:
        with get_conn() as c:
            if learned:
                c.execute("UPDATE words SET is_learned = 1, learned_at = CURRENT_TIMESTAMP WHERE id = ?", (word_id,))
            else:
                c.execute("UPDATE words SET is_learned = 0, learned_at = NULL WHERE id = ?", (word_id,))
            c.commit()

    def get_word(self, word_id: int) -> Optional[Word]:
        with get_conn() as c:
            row = c.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
            if not row:
                return None
            return Word(
                id=row["id"], term_en=row["term_en"], translation_tr=row["translation_tr"],
                notes=row["notes"], group_title=row["group_title"], is_learned=row["is_learned"],
                learned_at=row["learned_at"], created_at=row["created_at"]
            )

    def find_by_term(self, term_en: str) -> Optional[Word]:
        with get_conn() as c:
            row = c.execute(
                "SELECT * FROM words WHERE lower(term_en) = lower(?)", (term_en.strip(),)
            ).fetchone()
            if not row:
                return None
            return Word(
                id=row["id"], term_en=row["term_en"], translation_tr=row["translation_tr"],
                notes=row["notes"], group_title=row["group_title"], is_learned=row["is_learned"],
                learned_at=row["learned_at"], created_at=row["created_at"]
            )

    def list_group_titles(self) -> List[str]:
        with get_conn() as c:
            rows = c.execute("SELECT DISTINCT group_title FROM words WHERE group_title IS NOT NULL ORDER BY group_title COLLATE NOCASE").fetchall()
            return [r[0] for r in rows if r[0]]

    def list_words(self, include_learned: bool = True) -> List[Word]:
        with get_conn() as c:
            if include_learned:
                rows = c.execute("SELECT * FROM words ORDER BY created_at DESC, id DESC").fetchall()
            else:
                rows = c.execute("SELECT * FROM words WHERE is_learned = 0 ORDER BY created_at DESC, id DESC").fetchall()
            return [
                Word(
                    id=r["id"], term_en=r["term_en"], translation_tr=r["translation_tr"],
                    notes=r["notes"], group_title=r["group_title"], is_learned=r["is_learned"],
                    learned_at=r["learned_at"], created_at=r["created_at"]
                ) for r in rows
            ]


class ExampleRepository:
    def add_example(self, word_id: int, text: str,
                    origin: str = "MANUAL",
                    direction: Optional[str] = None,
                    score: Optional[int] = None,
                    feedback: str = "",
                    exercise_id: Optional[int] = None) -> int:
        with get_conn() as c:
            cur = c.execute(
                """
                INSERT INTO examples(word_id, text, origin, direction, score, feedback, exercise_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (word_id, text.strip(), origin, direction, score, feedback, exercise_id)
            )
            c.commit()
            return int(cur.lastrowid)

    def list_examples(self, word_id: int) -> List[Example]:
        with get_conn() as c:
            rows = c.execute(
                "SELECT * FROM examples WHERE word_id = ? ORDER BY created_at DESC, id DESC",
                (word_id,),
            ).fetchall()
            result: List[Example] = []
            for r in rows:
                keys = r.keys()  # sqlite3.Row
                result.append(
                    Example(
                        id=r["id"], word_id=r["word_id"], text=r["text"],
                        origin=r["origin"] if "origin" in keys else "MANUAL",
                        direction=r["direction"] if "direction" in keys else None,
                        score=r["score"] if "score" in keys else None,
                        feedback=r["feedback"] if "feedback" in keys else "",
                        exercise_id=r["exercise_id"] if "exercise_id" in keys else None,
                        created_at=r["created_at"],
                    )
                )
            return result

    def avg_score(self, word_id: int) -> float:
        with get_conn() as c:
            row = c.execute(
                "SELECT AVG(score) FROM examples WHERE word_id = ? AND score IS NOT NULL",
                (word_id,)
            ).fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0


class ExerciseRepository:
    def add_exercise(self, word_id: int, direction: str, source_en: str, source_tr: str, sentence: str) -> int:
        with get_conn() as c:
            cur = c.execute(
                """
                INSERT INTO exercises(word_id, direction, source_en, source_tr, sentence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (word_id, direction, source_en, source_tr, sentence.strip()),
            )
            c.commit()
            return int(cur.lastrowid)

    def list_exercises(self, word_id: int) -> List[Exercise]:
        with get_conn() as c:
            rows = c.execute(
                "SELECT * FROM exercises WHERE word_id = ? ORDER BY created_at DESC, id DESC",
                (word_id,),
            ).fetchall()
            return [
                Exercise(
                    id=r["id"], word_id=r["word_id"], direction=r["direction"],
                    source_en=r["source_en"], source_tr=r["source_tr"], sentence=r["sentence"],
                    user_answer=r["user_answer"], score=r["score"], feedback=r["feedback"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    def get_exercise(self, ex_id: int) -> Optional[Exercise]:
        with get_conn() as c:
            r = c.execute("SELECT * FROM exercises WHERE id = ?", (ex_id,)).fetchone()
            if not r:
                return None
            return Exercise(
                id=r["id"], word_id=r["word_id"], direction=r["direction"],
                source_en=r["source_en"], source_tr=r["source_tr"], sentence=r["sentence"],
                user_answer=r["user_answer"], score=r["score"], feedback=r["feedback"],
                created_at=r["created_at"]
            )

    def update_answer_and_score(self, ex_id: int, user_answer: str, score: int, feedback: str) -> None:
        with get_conn() as c:
            c.execute(
                "UPDATE exercises SET user_answer = ?, score = ?, feedback = ? WHERE id = ?",
                (user_answer.strip(), score, feedback, ex_id),
            )
            c.commit()