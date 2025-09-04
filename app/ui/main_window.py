from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QLabel, QSplitter, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from ..core.translator import Translator
from ..core.repository import WordRepository
from ..services.word_service import WordService
from .word_page import WordPage
from datetime import datetime

class TranslateWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, translator: Translator, term: str):
        super().__init__()
        self.translator = translator
        self.term = term

    def run(self):
        try:
            out = self.translator.translate(self.term)
            if out:
                self.finished.emit(out)
            else:
                self.failed.emit("Boş yanıt")
        except Exception as e:
            self.failed.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EN→TR Vocabulary")
        self.resize(1200, 760)

        self.repo = WordRepository()
        self.service = WordService(self.repo)
        self.translator = Translator(source="en", target="tr")
        self._worker: TranslateWorker | None = None

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Horizontal)

        # Left pane
        left = QWidget(self)
        left_layout = QVBoxLayout(left)

        # Row 1: Term input + Translate
        row1 = QHBoxLayout()
        self.txtTerm = QLineEdit(self)
        self.txtTerm.setPlaceholderText("Enter English word…")
        self.btnTranslate = QPushButton("Translate")
        self.btnTranslate.clicked.connect(self.on_translate)
        row1.addWidget(self.txtTerm)
        row1.addWidget(self.btnTranslate)
        left_layout.addLayout(row1)

        # Row 2: Editable translation + Add
        row2 = QHBoxLayout()
        self.txtTranslation = QLineEdit(self)
        self.txtTranslation.setPlaceholderText("Türkçe çeviriyi düzenleyebilirsin…")
        self.btnAdd = QPushButton("Add to Library")
        self.btnAdd.clicked.connect(self.on_add)
        row2.addWidget(self.txtTranslation)
        row2.addWidget(self.btnAdd)
        left_layout.addLayout(row2)

        # Row 3: Group select + filter learned
        row3 = QHBoxLayout()
        self.cmbGroup = QComboBox(self)
        self.cmbGroup.setEditable(True)  # yazıp Enter ile yeni başlık oluşturabil
        self.chkShowLearned = QCheckBox("Show learned")
        self.chkShowLearned.setChecked(True)
        self.chkShowLearned.stateChanged.connect(lambda _: self.load_library())
        row3.addWidget(QLabel("Group:"))
        row3.addWidget(self.cmbGroup, 1)
        row3.addWidget(self.chkShowLearned)
        left_layout.addLayout(row3)

        # Info label
        self.lblResult = QLabel("")
        self.lblResult.setWordWrap(True)
        left_layout.addWidget(self.lblResult)

        # Tree library: Group -> Date -> Words
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._tree_item_double_clicked)
        left_layout.addWidget(self.tree, 1)

        # Right pane (tabs)
        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)
        right_layout.addWidget(self.tabs)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        container = QWidget(self)
        root_layout = QVBoxLayout(container)
        root_layout.addWidget(splitter)
        self.setCentralWidget(container)

        self._refresh_groups()
        self.load_library()

    # ---- helpers ----
    def _set_busy(self, busy: bool):
        self.btnTranslate.setEnabled(not busy)
        self.btnAdd.setEnabled(not busy)
        if busy:
            self.lblResult.setText("Translating…")

    def _start_worker(self, term: str, on_done):
        if self._worker and self._worker.isRunning():
            return
        self._worker = TranslateWorker(self.translator, term)
        self._worker.finished.connect(lambda res: (self._set_busy(False), on_done(res)))
        self._worker.failed.connect(lambda err: (self._set_busy(False), self._on_translate_failed(err)))
        self._set_busy(True)
        self._worker.start()

    def _refresh_groups(self):
        self.cmbGroup.clear()
        titles = self.service.list_group_titles()
        if titles:
            self.cmbGroup.addItems(titles)

    def _group_key(self, w) -> str:
        return w.group_title or "(General)"

    def _date_key(self, w) -> str:
        # YYYY-MM-DD
        try:
            d = datetime.fromisoformat(str(w.created_at))
            return d.strftime("%Y-%m-%d")
        except Exception:
            return str(w.created_at)[:10]

    def load_library(self):
        self.tree.clear()
        words = self.service.list_words(include_learned=self.chkShowLearned.isChecked())
        # group -> date -> [words]
        gmap = {}
        for w in words:
            g = self._group_key(w)
            d = self._date_key(w)
            gmap.setdefault(g, {}).setdefault(d, []).append(w)
        for g, dates in sorted(gmap.items(), key=lambda x: x[0].lower()):
            g_item = QTreeWidgetItem([g])
            g_font = QFont()
            g_font.setBold(True)
            g_item.setFont(0, g_font)
            self.tree.addTopLevelItem(g_item)
            for d, lst in sorted(dates.items(), key=lambda x: x[0], reverse=True):
                d_item = QTreeWidgetItem([d])
                d_color = QColor("#64748b")  # slate-500
                d_item.setForeground(0, d_color)
                g_item.addChild(d_item)
                for w in sorted(lst, key=lambda w: w.term_en.lower()):
                    label = f"{w.term_en} → {w.translation_tr}"
                    w_item = QTreeWidgetItem([label])
                    if w.is_learned:
                        w_item.setForeground(0, QColor("#16a34a"))  # green-600
                        w_font = QFont()
                        w_font.setBold(True)
                        w_item.setFont(0, w_font)
                    w_item.setToolTip(0, f"Group: {self._group_key(w)} Date: {self._date_key(w)}")
                    w_item.setData(0, Qt.UserRole, w.id)
                    d_item.addChild(w_item)
            g_item.setExpanded(True)

    def on_translate(self):
        term = (self.txtTerm.text() or "").strip()
        if not term:
            self.lblResult.setText("Please enter a word.")
            return
        def _done(translated: str):
            self.txtTranslation.setText(translated)  # 🔧 Sonucu kullanıcı düzenleyebilir
            self.lblResult.setText(f"<b>Translation:</b> {translated}")
        self._start_worker(term, _done)

    def _on_translate_failed(self, err: str):
        self.lblResult.setText(f"Çeviri yapılamadı (DeepL): {err}")

    def on_add(self):
        term = (self.txtTerm.text() or "").strip()
        translation = (self.txtTranslation.text() or "").strip()  # 🔧 kullanıcı düzenlemesi
        if not term:
            self.lblResult.setText("Please enter a word.")
            return
        if not translation:
            # Çeviri boşsa önce çevir, sonra kullanıcı düzenlemek isterse düzenler
            return self.on_translate()
        group_title = (self.cmbGroup.currentText() or None)
        w = self.service.add_or_get(term, translation, group_title)
        # Yeni grup girilmişse listeye ekle
        if group_title and group_title not in [self.cmbGroup.itemText(i) for i in range(self.cmbGroup.count())]:
            self.cmbGroup.addItem(group_title)
        self.lblResult.setText(f"Added to library: <b>{w.term_en}</b> → {w.translation_tr}")
        self.load_library()

    def _tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        word_id = item.data(0, Qt.UserRole)
        if not word_id:
            # Grup veya tarih düğümü
            item.setExpanded(not item.isExpanded())
            return
        w = self.repo.get_word(int(word_id))
        if not w:
            return
        # Zaten açık mı kontrol et
        for i in range(self.tabs.count()):
            page = self.tabs.widget(i)
            if getattr(page, "word", None) and page.word.id == w.id:
                self.tabs.setCurrentIndex(i)
                return
        page = WordPage(w, examples_provider=self.service)
        page.notesChanged.connect(self._on_notes_changed)
        page.markLearned.connect(self._on_mark_learned)
        idx = self.tabs.addTab(page, w.term_en)
        self.tabs.setCurrentIndex(idx)

    def _on_notes_changed(self, word_id: int, notes: str):
        self.repo.update_notes(word_id, notes)

    def _on_mark_learned(self, word_id: int, learned: bool):
        self.service.set_learned(word_id, learned)
        self.load_library()