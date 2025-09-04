from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QSplitter
)
from PySide6.QtCore import Signal, Qt, QThread
from PySide6.QtGui import QGuiApplication


class _AiGenWorker(QThread):
    finished = Signal(int)   # new exercise id
    failed = Signal(str)

    def __init__(self, service, word_id: int, direction: str):
        super().__init__()
        self.service = service
        self.word_id = word_id
        self.direction = direction

    def run(self):
        try:
            if self.direction == 'TR':
                ex_id = self.service.create_exercise_tr(self.word_id)
            else:
                ex_id = self.service.create_exercise_en(self.word_id)
            self.finished.emit(ex_id)
        except Exception as e:
            self.failed.emit(str(e))


class _AiScoreWorker(QThread):
    finished = Signal(int, str)  # score, feedback
    failed = Signal(str)

    def __init__(self, service, exercise_id: int, answer: str):
        super().__init__()
        self.service = service
        self.exercise_id = exercise_id
        self.answer = answer

    def run(self):
        try:
            score, feedback = self.service.evaluate_exercise(self.exercise_id, self.answer)
            self.finished.emit(score, feedback)
        except Exception as e:
            self.failed.emit(str(e))


class WordPage(QWidget):
    notesChanged = Signal(int, str)  # word_id, notes
    markLearned = Signal(int, bool)  # word_id, learned

    def __init__(self, word, examples_provider, parent=None):
        super().__init__(parent)
        self.word = word
        self.service = examples_provider  # WordService
        self._gen_worker = None
        self._score_worker = None
        self._selected_exercise_id = None

        # Root: split left (notes+examples) | right (AI tasks)
        root = QVBoxLayout(self)

        header = QLabel(f"<h2 style='margin:4px 0'>{word.term_en} → {word.translation_tr}</h2>")
        root.addWidget(header)

        top = QHBoxLayout()
        self.lblLearned = QLabel("Öğrenildi: Evet" if word.is_learned else "Öğrenildi: Hayır")
        self._apply_learned_badge()
        self.btnToggleLearned = QPushButton("Öğrenildi olarak işaretle" if not word.is_learned else "Öğrenilmediye geri al")
        self.btnToggleLearned.clicked.connect(self._toggle_learned)
        top.addWidget(self.lblLearned)
        top.addWidget(self.btnToggleLearned)
        top.addStretch(1)
        root.addLayout(top)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # ========== LEFT COLUMN: Notes + Avg + Examples + Manual (compact) ==========
        left = QWidget(self)
        l = QVBoxLayout(left)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)

        l.addWidget(QLabel("Notlar"))
        self.txtNotes = QTextEdit(self)
        self.txtNotes.setPlaceholderText("Bu kelimeyle ilgili açıklamalar, ipuçları...")
        self.txtNotes.setText(word.notes or "")
        self.txtNotes.textChanged.connect(self._emit_notes)
        self.txtNotes.setMaximumHeight(90)  # daha küçük alan
        l.addWidget(self.txtNotes)

        self.lblAvg = QLabel("Ortalama: -")
        l.addWidget(self.lblAvg)

        l.addWidget(QLabel("Örnek Cümleler"))
        self.examplesList = QListWidget(self)
        self.examplesList.setSpacing(0)
        self.examplesList.setStyleSheet(
            "QListWidget::item{ margin:0px; }"
        )
        l.addWidget(self.examplesList, 1)

        row_manual = QHBoxLayout()
        self.exampleInput = QLineEdit(self)
        self.exampleInput.setPlaceholderText("Skorsuz örnek cümle yaz (görev seçili değilken aktif)…")
        self.btnAddExample = QPushButton("Skorsuz Ekle")
        self.btnAddExample.clicked.connect(self._add_example_manual)
        row_manual.addWidget(self.exampleInput)
        row_manual.addWidget(self.btnAddExample)
        l.addLayout(row_manual)

        splitter.addWidget(left)

        # ========== RIGHT COLUMN: AI Tasks (compact list) ==========
        right = QWidget(self)
        r = QVBoxLayout(right)
        r.setContentsMargins(0, 0, 0, 0)
        r.setSpacing(6)

        r.addWidget(QLabel("AI Görevleri"))
        row_ai = QHBoxLayout()
        self.btnGenTR = QPushButton("TR cümle üret (AI)")
        self.btnGenEN = QPushButton("EN sentence (AI)")
        self.btnGenTR.clicked.connect(lambda: self._start_gen('TR'))
        self.btnGenEN.clicked.connect(lambda: self._start_gen('EN'))
        row_ai.addWidget(self.btnGenTR)
        row_ai.addWidget(self.btnGenEN)
        r.addLayout(row_ai)

        self.exList = QListWidget(self)
        self.exList.setSpacing(0)
        self.exList.setStyleSheet("QListWidget::item{ margin:0px; }")
        self.exList.itemSelectionChanged.connect(self._on_exercise_selected)
        r.addWidget(self.exList, 1)

        self.answerInput = QTextEdit(self)
        self.answerInput.setPlaceholderText("Seçili görev için çevirini yaz ve değerlendir…")
        self.answerInput.setMaximumHeight(110)  # daha kompakt
        self.btnScore = QPushButton("Değerlendir (AI)")
        self.btnScore.clicked.connect(self._start_score)
        r.addWidget(self.answerInput)
        r.addWidget(self.btnScore)

        self.lblScore = QLabel("")
        r.addWidget(self.lblScore)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # İlk yükleme
        self.refresh_examples()
        self.refresh_exercises()
        self.exampleInput.setEnabled(True)
        self.btnAddExample.setEnabled(True)

    # ---------- helpers ----------
    def _apply_learned_badge(self):
        if self.word.is_learned:
            self.lblLearned.setObjectName("badgeSuccess")
        else:
            self.lblLearned.setObjectName("badgeMuted")
        self.lblLearned.style().unpolish(self.lblLearned)
        self.lblLearned.style().polish(self.lblLearned)
        self.lblLearned.update()

    def _emit_notes(self):
        self.notesChanged.emit(self.word.id, self.txtNotes.toPlainText())

    def _toggle_learned(self):
        new_state = 0 if self.word.is_learned else 1
        self.markLearned.emit(self.word.id, bool(new_state))
        self.word.is_learned = new_state
        self.lblLearned.setText("Öğrenildi: Evet" if self.word.is_learned else "Öğrenildi: Hayır")
        self.btnToggleLearned.setText("Öğrenildi olarak işaretle" if not self.word.is_learned else "Öğrenilmediye geri al")
        self._apply_learned_badge()

    # ---- compact row builders ----
    def _compact_label(self, text: str, left_color: str = "#2e2e2e") -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Çok ince satır + alt çizgi + sol çizgi + ufak font
        lbl.setStyleSheet(
            f"font-size:12px; padding: 1px 6px; border-left: 2px solid {left_color}; border-bottom: 1px solid #2a2a2a;"
        )
        return lbl

    def _make_example_item(self, ex) -> QWidget:
        # Sadece skor (varsa başta) + kullanıcı cümlesi
        if getattr(ex, "origin", "MANUAL") == "AI" and getattr(ex, "score", None) is not None:
            head = f"{ex.score}/10  •  "
            color = "#3b82f6"  # mavi sol çizgi
        else:
            head = ""
            color = "#444444"  # skorsuz gri
        w = QWidget(self)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        lbl = self._compact_label(f"{head}{ex.text}", left_color=color)
        h.addWidget(lbl)
        return w

    def refresh_examples(self):
        self.examplesList.clear()
        examples = self.service.list_examples(self.word.id)
        for ex in examples:
            widget = self._make_example_item(ex)
            item = QListWidgetItem(self.examplesList)
            item.setSizeHint(widget.sizeHint())
            self.examplesList.addItem(item)
            self.examplesList.setItemWidget(item, widget)
        avg = self.service.get_avg_score(self.word.id)
        self.lblAvg.setText(f"Ortalama: {avg:.2f}/10" if avg > 0 else "Ortalama: -")

    def _make_exercise_item(self, ex) -> QWidget:
        tag = "[TR]" if ex.direction == "TR" else "[EN]"
        score_head = f"{ex.score}/10  •  " if ex.score is not None else ""
        text = f"{tag}  {score_head}{ex.sentence}"
        w = QWidget(self)
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        lbl = self._compact_label(text, left_color="#94a3b8")  # nötr sol çizgi
        h.addWidget(lbl)
        return w

    # ---- exercises ----
    def refresh_exercises(self):
        self.exList.clear()
        for ex in self.service.list_exercises(self.word.id):
            widget = self._make_exercise_item(ex)
            item = QListWidgetItem(self.exList)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, ex.id)  # seçim için id
            self.exList.addItem(item)
            self.exList.setItemWidget(item, widget)

    def _on_exercise_selected(self):
        items = self.exList.selectedItems()
        if not items:
            self._selected_exercise_id = None
            self.answerInput.clear()
            self.lblScore.setText("")
            self.exampleInput.setEnabled(True)
            self.btnAddExample.setEnabled(True)
            return
        it = items[0]
        self._selected_exercise_id = it.data(Qt.UserRole)
        ex_id = int(self._selected_exercise_id)
        for ex in self.service.list_exercises(self.word.id):
            if ex.id == ex_id:
                self.answerInput.setText(ex.user_answer or "")
                self.lblScore.setText(f"Skor: {ex.score}/10 — {ex.feedback}" if ex.score is not None else "")
                break
        self.exampleInput.setEnabled(False)
        self.btnAddExample.setEnabled(False)

    def _set_busy(self, busy: bool):
        self.btnGenTR.setEnabled(not busy)
        self.btnGenEN.setEnabled(not busy)
        self.btnScore.setEnabled(not busy)
        self.exampleInput.setEnabled((not busy) and (self._selected_exercise_id is None))
        self.btnAddExample.setEnabled((not busy) and (self._selected_exercise_id is None))

    def _start_gen(self, direction: str):
        self._set_busy(True)
        self._gen_worker = _AiGenWorker(self.service, self.word.id, direction)
        self._gen_worker.finished.connect(lambda exid: (self._set_busy(False), self.refresh_exercises()))
        self._gen_worker.failed.connect(lambda err: (self._set_busy(False), QMessageBox.warning(self, "AI", f"Görev oluşturulamadı: {err}")))
        self._gen_worker.start()

    def _start_score(self):
        if not self._selected_exercise_id:
            QMessageBox.information(self, "AI", "Lütfen bir görev seçin.")
            return
        ans = (self.answerInput.toPlainText() or "").strip()
        if not ans:
            QMessageBox.information(self, "AI", "Lütfen çevirinizi yazın.")
            return
        self._set_busy(True)
        self._score_worker = _AiScoreWorker(self.service, int(self._selected_exercise_id), ans)
        self._score_worker.finished.connect(self._on_scored)
        self._score_worker.failed.connect(lambda err: (self._set_busy(False), QMessageBox.warning(self, "AI", f"Değerlendirilemedi: {err}")))
        self._score_worker.start()

    def _on_scored(self, score: int, feedback: str):
        self._set_busy(False)
        self.lblScore.setText(f"Skor: {score}/10 — {feedback}")
        self.refresh_exercises()
        self.refresh_examples()
        w = self.service.repo.get_word(self.word.id)
        if w:
            self.word.is_learned = w.is_learned
            self.lblLearned.setText("Öğrenildi: Evet" if w.is_learned else "Öğrenildi: Hayır")
            self.btnToggleLearned.setText("Öğrenildi olarak işaretle" if not w.is_learned else "Öğrenilmediye geri al")
            self._apply_learned_badge()

    def _add_example_manual(self):
        text = (self.exampleInput.text() or "").strip()
        if not text:
            return
        if self._selected_exercise_id:
            QMessageBox.information(self, "Örnek", "Görev seçiliyken skorsuz örnek ekleyemezsiniz.")
            return
        self.service.add_example_manual(self.word.id, text)
        self.exampleInput.clear()
        self.refresh_examples()
