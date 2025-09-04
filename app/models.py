from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Word:
    id: Optional[int]
    term_en: str
    translation_tr: str
    notes: str = ""
    group_title: Optional[str] = None  # Örn: "Book: Atomic Habits"
    is_learned: int = 0               # 0/1
    learned_at: Optional[datetime] = None
    created_at: datetime = datetime.utcnow()

@dataclass
class Example:
    id: Optional[int]
    word_id: int
    text: str
    origin: str = "MANUAL"          # 'AI' | 'MANUAL'
    direction: Optional[str] = None # 'TR' | 'EN' | None
    score: Optional[int] = None
    feedback: str = ""
    exercise_id: Optional[int] = None
    created_at: datetime = datetime.utcnow()

@dataclass
class Exercise:
    id: Optional[int]
    word_id: int
    direction: str             # 'TR' (TR cümle; kullanıcı EN çeviri) veya 'EN'
    source_en: str
    source_tr: str
    sentence: str              # Üretilen cümle (TR/EN)
    user_answer: str = ""
    score: Optional[int] = None
    feedback: str = ""
    created_at: datetime = datetime.utcnow()