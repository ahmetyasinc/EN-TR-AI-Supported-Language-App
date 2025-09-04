import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "vocab.sqlite3"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_en TEXT NOT NULL,
    translation_tr TEXT NOT NULL,
    notes TEXT DEFAULT '',
    group_title TEXT DEFAULT NULL,
    is_learned INTEGER DEFAULT 0,
    learned_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    origin TEXT DEFAULT 'MANUAL' CHECK(origin IN ('AI','MANUAL')),
    direction TEXT DEFAULT NULL CHECK(direction IN ('TR','EN') OR direction IS NULL),
    score INTEGER DEFAULT NULL,
    feedback TEXT DEFAULT '',
    exercise_id INTEGER DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_examples_word_id ON examples(word_id);
CREATE INDEX IF NOT EXISTS idx_examples_score ON examples(word_id, score);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('TR','EN')),
    source_en TEXT NOT NULL,
    source_tr TEXT NOT NULL,
    sentence TEXT NOT NULL,
    user_answer TEXT DEFAULT '',
    score INTEGER DEFAULT NULL,
    feedback TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_exercises_word_id ON exercises(word_id);
"""

def _add_col(conn, table, col, decl):
    if not any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})")):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _table_exists(conn, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return bool(row)


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    try:
        return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))
    except Exception:
        return False


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if not _table_exists(conn, "exercises"):
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    else:
        try:
            _add_col(conn, "examples", "origin", "TEXT DEFAULT 'MANUAL'")
            _add_col(conn, "examples", "direction", "TEXT DEFAULT NULL")
            _add_col(conn, "examples", "score", "INTEGER DEFAULT NULL")
            _add_col(conn, "examples", "feedback", "TEXT DEFAULT ''")
            _add_col(conn, "examples", "exercise_id", "INTEGER DEFAULT NULL")
            cols = {r[1] for r in conn.execute("PRAGMA table_info(words)")}
            if "term_tr" in cols and "translation_en" in cols and "term_en" not in cols and "translation_tr" not in cols:
                try:
                    conn.execute("ALTER TABLE words RENAME COLUMN term_tr TO term_en")
                    conn.execute("ALTER TABLE words RENAME COLUMN translation_en TO translation_tr")
                    conn.commit()
                except Exception:
                    conn.executescript(
                        """
                        BEGIN;
                        CREATE TABLE IF NOT EXISTS words_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            term_en TEXT NOT NULL,
                            translation_tr TEXT NOT NULL,
                            notes TEXT DEFAULT '',
                            group_title TEXT DEFAULT NULL,
                            is_learned INTEGER DEFAULT 0,
                            learned_at DATETIME DEFAULT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        );
                        INSERT INTO words_new (id, term_en, translation_tr, notes, created_at)
                            SELECT id, term_tr, translation_en, notes, created_at FROM words;
                        DROP TABLE words;
                        ALTER TABLE words_new RENAME TO words;
                        COMMIT;
                        """
                    )
            if not _column_exists(conn, "words", "group_title"):
                conn.execute("ALTER TABLE words ADD COLUMN group_title TEXT DEFAULT NULL")
            if not _column_exists(conn, "words", "is_learned"):
                conn.execute("ALTER TABLE words ADD COLUMN is_learned INTEGER DEFAULT 0")
            if not _column_exists(conn, "words", "learned_at"):
                conn.execute("ALTER TABLE words ADD COLUMN learned_at DATETIME DEFAULT NULL")
            conn.commit()
        except Exception:
            pass
    return conn