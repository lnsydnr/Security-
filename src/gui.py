"""
GUI module for Security+ Study App.
Contains the MainWindow class and GUI wiring. Keeps UI code separate from core logic in app_core.py.
"""
import json
import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QTextOption, QColor, QBrush
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QTextEdit, QLineEdit, QFileDialog, QMessageBox,
    QTabWidget, QFormLayout, QSpinBox, QComboBox, QTableWidget, QTableWidgetItem,
    QInputDialog, QApplication, QScrollArea
)

from app_core import (
    get_conn, add_question, import_csv, import_json, convert_questions_to_import,
    list_domains, get_questions, record_attempt, stats_per_domain,
    schedule_update, due_flashcards, create_quiz, record_quiz_answer,
    update_quiz_score, get_quiz_history, get_quiz_details, consolidate_domains, clear_quiz_history, 
    consolidate_domains, assign_missing_domains, resolve_asset_path, delete_all_questions
)

# Optional: progress chart
try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


class MainWindow(QMainWindow):
    # Main window with tabs
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Security+ Study App")
        self.resize(1000, 700)
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowMinMaxButtonsHint | 
            Qt.WindowType.WindowCloseButtonHint
        )

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)

        # Create the scroll area container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Allows the inner widget to grow

        # Matplotlib requires a widget wrapper inside QScrollArea
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.addWidget(self.canvas) # Put your existing canvas here
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Set the content widget onto the scroll area
        self.scroll_area.setWidget(self.scroll_content)

        icon_path = resolve_asset_path("app_icon.png")
        if not icon_path:
            icon_path = resolve_asset_path("app_icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialize known cards tracking (will be loaded from file)
        self.easy_cards = []
        self.hard_cards = []
        self.easy_card_ids = set()
        self.hard_card_ids = set()
        self.flashcards_dir = Path(__file__).parent.parent / "flashcards"
        self.flashcards_dir.mkdir(exist_ok=True)
        self.known_cards_file = self.flashcards_dir / ".known_cards.json"
        self.load_known_cards()

        self.dashboard_tab()
        self.flashcards_tab()
        self.bank_tab()
        self.quiz_tab()
        self.history_tab()
        self.import_tab()
        self.settings_tab()

    # dashboard tab with stats
    def dashboard_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)

        h = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()
        h.addLayout(left, 2)
        h.addLayout(right, 1)

        left.addWidget(QLabel("<h2>Overview</h2>"))
        self.progress_table = QTableWidget(0, 3)
        self.progress_table.setHorizontalHeaderLabels(["Domain", "Attempts", "% Correct"])
        left.addWidget(self.progress_table)

        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(6, 2))
            self.canvas = FigureCanvas(self.fig)
            left.addWidget(self.canvas, 1)

        reload_btn = QPushButton("Refresh Stats")
        reload_btn.clicked.connect(self.load_stats)
        left.addWidget(reload_btn)

        right.addWidget(QLabel("<h3>Quick Actions</h3>"))
        right.addSpacing(0)
        btn_flash = QPushButton("Study Due Flashcards")
        btn_flash.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        right.addWidget(btn_flash)

        btn_quiz = QPushButton("Start Quick Quiz")
        btn_quiz.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        right.addWidget(btn_quiz)

        btn_import = QPushButton("Import Questions")
        btn_import.clicked.connect(lambda: self.tabs.setCurrentIndex(5))
        right.addWidget(btn_import)

        layout.addLayout(h)
        self.tabs.addTab(w, "Dashboard")
        self.load_stats()

    # Load and display stats
    def load_stats(self):
        stats = stats_per_domain()
        self.progress_table.setRowCount(len(stats))
    
        domains = []
        pct = []
    
        # Block table signals temporarily to speed up bulk row insertions
        self.progress_table.blockSignals(True)
    
        for i, s in enumerate(stats):
            self.progress_table.setItem(i, 0, QTableWidgetItem(s['domain']))
            self.progress_table.setItem(i, 1, QTableWidgetItem(str(s['attempts'])))
            self.progress_table.setItem(i, 2, QTableWidgetItem(f"{s['pct']:.1f}%"))
            domains.append(s['domain'])
            pct.append(s['pct'])
        self.progress_table.blockSignals(False)
        self.progress_table.resizeColumnsToContents()
        
        if MATPLOTLIB_AVAILABLE and domains:  # Added fallback check for empty data
            self.fig.clear()
        
            # Calculate dynamic width based on domain count
            width = max(8, len(domains) * 0.9)
            self.fig.set_size_inches(width, 5.5)
        
            ax = self.fig.add_subplot(111)
        
            # Create the bar chart
            bars = ax.barh(domains, pct, color='#3498db', edgecolor='black') # Added clean styling
        
            # Configure axes
            ax.set_xlabel("% Correct")
            ax.set_title("Accuracy by Domain", fontweight='bold', pad=15)
            ax.set_xlim(0, 100)
        
            # Crucial change: ha='right' aligns rotated text properly so it doesn't overlap lines
            ax.tick_params(axis='x', labelrotation=45)
            for label in ax.get_xticklabels():
                label.set_horizontalalignment('right')

            # Add value labels on top of each bar for easier reading
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

            # Recalculate margins cleanly to ensure rotated text fits on the screen
            self.fig.subplots_adjust(left=0.25) 
            self.fig.tight_layout()

            # CRUCIAL: Force the canvas widget to physically resize to match the new fig inches
            self.canvas.setMinimumWidth(int(width * self.fig.dpi))
            self.canvas.draw()

    # Flashcards tab with SRS
    def flashcards_tab(self):
        w = QWidget()
        layout = QHBoxLayout()
        w.setLayout(layout)

        left = QVBoxLayout()
        right = QVBoxLayout()
        layout.addLayout(left, 3)
        layout.addLayout(right, 2)

        left.addWidget(QLabel("<h2>Flashcards</h2>"))
        self.due_count_label = QLabel("Due cards: 0")
        left.addWidget(self.due_count_label)

        self.due_list = QListWidget()
        self.due_list.currentRowChanged.connect(self.show_flashcard)
        left.addWidget(self.due_list)

        left.addWidget(QLabel("<h3>Easy Flashcards</h3>"))
        self.easy_count_label = QLabel("Easy cards: 0")
        left.addWidget(self.easy_count_label)
        self.easy_list = QListWidget()
        self.easy_list.currentRowChanged.connect(self.show_easy_card)
        self.easy_list.setMaximumHeight(80)
        left.addWidget(self.easy_list)

        left.addWidget(QLabel("<h3>Hard Flashcards</h3>"))
        self.hard_count_label = QLabel("Hard cards: 0")
        left.addWidget(self.hard_count_label)
        self.hard_list = QListWidget()
        self.hard_list.currentRowChanged.connect(self.show_hard_card)
        self.hard_list.setMaximumHeight(80)
        left.addWidget(self.hard_list)

        right.addWidget(QLabel("<h3>Card</h3>"))
        self.card_status_label = QLabel("Select a due card or refresh due cards.")
        self.card_status_label.setWordWrap(True)
        right.addWidget(self.card_status_label)

        self.card_q = QTextEdit()
        self.card_q.setReadOnly(True)
        self.card_q.setLineWrapMode(QTextEdit.WidgetWidth)
        right.addWidget(self.card_q)

        self.card_a = QTextEdit()
        self.card_a.setReadOnly(True)
        self.card_a.setLineWrapMode(QTextEdit.WidgetWidth)
        self.card_a.hide()
        right.addWidget(self.card_a)

        self.show_ans_btn = QPushButton("Show Answer")
        def show_answer_and_disable():
            self.card_a.show()
            self.show_ans_btn.setDisabled(True)
        self.show_ans_btn.clicked.connect(show_answer_and_disable)
        right.addWidget(self.show_ans_btn)

        import functools
        grades_layout = QHBoxLayout()
        for label, score in [("Hard", 4), ("Easy", 5), ("Mastered", 6)]:
            btn = QPushButton(label)
            btn.clicked.connect(functools.partial(self.grade_card, score))
            grades_layout.addWidget(btn)
        right.addLayout(grades_layout)

        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.prev_flashcard)
        nav_layout.addWidget(prev_btn)
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.next_flashcard)
        nav_layout.addWidget(next_btn)
        right.addLayout(nav_layout)

        refresh = QPushButton("Refresh Due List")
        refresh.clicked.connect(self.load_due_flashcards)
        right.addWidget(refresh)

        self.flashcards_data = []
        self.current_card_index = -1
        self.load_due_flashcards()

        self.tabs.addTab(w, "Flashcards")

    # Helper to format question with options
    def format_question_with_options(self, card):
        """Format a question with its options from metadata."""
        question_text = card['question']
        
        # Parse metadata to get options (handle both dict and sqlite3.Row)
        try:
            metadata = card['metadata']
        except (KeyError, IndexError):
            metadata = None
        
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            options = metadata.get('options', []) if isinstance(metadata, dict) else []
            
            if options:
                # Format with options
                formatted = f"{question_text}\n\n"
                for i, option in enumerate(options, 1):
                    formatted += f"\n({chr(96 + i)}) {option}"
                return formatted
        
        return question_text

    # Load and display due flashcards
    def load_due_flashcards(self):
        self.flashcards_data = list(due_flashcards())
        self.due_list.clear()
        for r in self.flashcards_data:
            display = f"[{r['domain']}] {r['question'][:120]}"
            self.due_list.addItem(f"{r['id']}: {display}")
        self.due_count_label.setText(f"Due cards: {len(self.flashcards_data)}")
        
        # Rebuild easy_cards and hard_cards lists from IDs by querying database
        self.easy_cards = []
        self.hard_cards = []
        if self.easy_card_ids or self.hard_card_ids:
            all_questions = list(get_questions())
            for q in all_questions:
                if q['id'] in self.easy_card_ids:
                    self.easy_cards.append(q)
                elif q['id'] in self.hard_card_ids:
                    self.hard_cards.append(q)
        
        self.update_known_list()
        if self.flashcards_data:
            self.show_flashcard(0)
        else:
            self.current_card_index = -1
            self.card_status_label.setText("No due flashcards. Nice work!")
            self.card_q.clear()
            self.card_a.clear()
            self.show_ans_btn.setEnabled(False)

    # Display selected flashcard
    def show_flashcard(self, idx):
        if idx < 0 or idx >= len(self.flashcards_data):
            return
        if self.due_list.currentRow() != idx:
            self.due_list.setCurrentRow(idx)
        card = self.flashcards_data[idx]
        self.current_card_index = idx
        self.current_card_id = card['id']
        self.card_status_label.setText(f"Card {idx + 1} of {len(self.flashcards_data)}")
        self.card_q.setPlainText(self.format_question_with_options(card))
        self.card_a.setPlainText(card['answer'] or "<no answer provided>")
        self.card_a.hide()
        self.show_ans_btn.setEnabled(True)

    def show_easy_card(self, idx):
        if idx < 0 or idx >= len(self.easy_cards):
            return
        card = self.easy_cards[idx]
        self.card_status_label.setText(f"Easy Card - [{card['domain']}]")
        self.card_q.setPlainText(self.format_question_with_options(card))
        self.card_a.setPlainText(card['answer'] or "<no answer provided>")
        self.card_a.hide()
        self.show_ans_btn.setEnabled(True)

    def show_hard_card(self, idx):
        if idx < 0 or idx >= len(self.hard_cards):
            return
        card = self.hard_cards[idx]
        self.card_status_label.setText(f"Hard Card - [{card['domain']}]")
        self.card_q.setPlainText(self.format_question_with_options(card))
        self.card_a.setPlainText(card['answer'] or "<no answer provided>")
        self.card_a.hide()
        self.show_ans_btn.setEnabled(True)

    def prev_flashcard(self):
        if self.current_card_index > 0:
            self.show_flashcard(self.current_card_index - 1)

    def next_flashcard(self):
        if self.current_card_index + 1 < len(self.flashcards_data):
            self.show_flashcard(self.current_card_index + 1)

    def update_known_list(self):
        self.easy_list.clear()
        for r in self.easy_cards:
            display = f"[{r['domain']}] {r['question'][:80]}"
            self.easy_list.addItem(display)
        self.easy_count_label.setText(f"Easy cards: {len(self.easy_cards)}")
        
        self.hard_list.clear()
        for r in self.hard_cards:
            display = f"[{r['domain']}] {r['question'][:80]}"
            self.hard_list.addItem(display)
        self.hard_count_label.setText(f"Hard cards: {len(self.hard_cards)}")

    # Grade the card and update SRS
    def grade_card(self, quality):
        if not hasattr(self, "current_card_id") or self.current_card_index < 0:
            QMessageBox.warning(self, "No card", "Select a card first")
            return
        qid = self.current_card_id
        card = self.flashcards_data[self.current_card_index]
        schedule_update(qid, quality)
        record_attempt(qid, quality >= 4)
        
        # Add to easy or hard based on quality
        if quality == 5 and qid not in self.easy_card_ids:  # Easy
            self.easy_card_ids.add(qid)
            self.easy_cards.append(card)
        elif quality == 4 and qid not in self.hard_card_ids:  # Good (Hard)
            self.hard_card_ids.add(qid)
            self.hard_cards.append(card)
        
        self.update_known_list()
        QMessageBox.information(self, "Saved", "Your answer and scheduling updated.")
        
        # Remove the graded card from the current list and update UI
        if 0 <= self.current_card_index < len(self.flashcards_data):
            self.flashcards_data.pop(self.current_card_index)
            self.due_list.takeItem(self.current_card_index)
            self.due_count_label.setText(f"Due cards: {len(self.flashcards_data)}")
            
            # Show next card or previous if at end
            if self.current_card_index < len(self.flashcards_data):
                self.show_flashcard(self.current_card_index)
            elif self.current_card_index > 0:
                self.show_flashcard(self.current_card_index - 1)
            else:
                self.current_card_index = -1
                self.card_status_label.setText("No more due flashcards. Nice work!")
                self.card_q.clear()
                self.card_a.clear()
                self.show_ans_btn.setEnabled(False)
        
        # Save known cards to persist across sessions
        self.save_known_cards()

    def load_known_cards(self):
        """Load known cards from file."""
        if self.known_cards_file.exists():
            try:
                with open(self.known_cards_file, 'r') as f:
                    data = json.load(f)
                    self.easy_card_ids = set(data.get('easy_card_ids', []))
                    self.hard_card_ids = set(data.get('hard_card_ids', []))
            except Exception:
                pass

    def save_known_cards(self):
        """Save known cards to file for persistence."""
        try:
            with open(self.known_cards_file, 'w') as f:
                json.dump({
                    'easy_card_ids': list(self.easy_card_ids),
                    'hard_card_ids': list(self.hard_card_ids)
                }, f)
        except Exception:
            pass

    def closeEvent(self, event):
        """Save known cards when closing the app."""
        self.save_known_cards()
        super().closeEvent(event)

    # Question bank tab
    def bank_tab(self):
        w = QWidget()
        layout = QHBoxLayout()
        w.setLayout(layout)

        left = QVBoxLayout()
        right = QVBoxLayout()
        layout.addLayout(left, 3)
        layout.addLayout(right, 2)

        left.addWidget(QLabel("<h2>Question Bank</h2>"))
        self.domain_filter = QComboBox()
        self.domain_filter.addItem("All")
        self.domain_filter.addItems(list_domains())
        self.domain_filter.currentTextChanged.connect(self.load_bank)
        left.addWidget(self.domain_filter)

        self.bank_list = QListWidget()
        left.addWidget(self.bank_list)
        self.bank_list.currentRowChanged.connect(self.show_bank_question)

        right.addWidget(QLabel("<h3>Question</h3>"))
        self.bank_q = QTextEdit()
        self.bank_q.setReadOnly(True)
        self.bank_q.setLineWrapMode(QTextEdit.WidgetWidth)
        right.addWidget(self.bank_q)
        self.bank_a = QTextEdit()
        self.bank_a.setReadOnly(True)
        self.bank_a.setLineWrapMode(QTextEdit.WidgetWidth)
        right.addWidget(self.bank_a)

        del_btn = QPushButton("Delete Question")
        del_btn.clicked.connect(self.delete_question)
        right.addWidget(del_btn)

        refresh = QPushButton("Refresh Domains")
        refresh.clicked.connect(self.reload_domains)
        right.addWidget(refresh)

        self.tabs.addTab(w, "Question Bank")
        self.load_bank()

    # Reload domains and refresh bank list
    def reload_domains(self):
        self.domain_filter.clear()
        self.domain_filter.addItem("All")
        self.domain_filter.addItems(list_domains())
        self.load_bank()

    def load_bank(self):
        domain = self.domain_filter.currentText()
        self.bank_list.clear()
        for r in get_questions(domain if domain != "All" else None):
            self.bank_list.addItem(f"{r['id']}: [{r['domain']}] {r['question'][:80]}")

    def show_bank_question(self, idx):
        if idx < 0:
            return
        text = self.bank_list.item(idx).text()
        qid = int(text.split(":", 1)[0])
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM questions WHERE id=?", (qid,))
        r = c.fetchone()
        conn.close()
        if r:
            self.bank_q.setPlainText(r['question'])
            self.bank_a.setPlainText(r['answer'] or "")

    def delete_question(self):
        idx = self.bank_list.currentRow()
        if idx < 0:
            return
        text = self.bank_list.item(idx).text()
        qid = int(text.split(":", 1)[0])
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM questions WHERE id=?", (qid,))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Deleted", "Question removed")
        self.load_bank()

    def quiz_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)

        # Quiz config section
        self.quiz_config_widget = QWidget()
        config_layout = QFormLayout()
        self.quiz_config_widget.setLayout(config_layout)
        
        self.quiz_domain = QComboBox()
        self.quiz_domain.addItem("All")
        self.quiz_domain.addItems(list_domains())
        self.quiz_count = QSpinBox()
        self.quiz_count.setRange(1, 200)
        self.quiz_count.setValue(20)
        config_layout.addRow("Domain", self.quiz_domain)
        config_layout.addRow("Number of Questions", self.quiz_count)
        
        self.quiz_start_btn = QPushButton("Start Quiz")
        self.quiz_start_btn.clicked.connect(self.start_quiz)
        config_layout.addRow(self.quiz_start_btn)
        
        layout.addWidget(self.quiz_config_widget)

        # Quiz display section (initially hidden)
        self.quiz_display_widget = QWidget()
        quiz_display_layout = QVBoxLayout()
        quiz_display_layout.setSpacing(10)
        quiz_display_layout.setContentsMargins(10, 10, 10, 10)
        self.quiz_display_widget.setLayout(quiz_display_layout)
        
        # Progress label
        self.quiz_progress_label = QLabel()
        quiz_display_layout.addWidget(self.quiz_progress_label)
        
        # Question
        quiz_display_layout.addWidget(QLabel("<b>Question:</b>"))
        self.quiz_question = QTextEdit()
        self.quiz_question.setReadOnly(True)
        self.quiz_question.setLineWrapMode(QTextEdit.WidgetWidth)
        self.quiz_question.setMaximumHeight(100)
        quiz_display_layout.addWidget(self.quiz_question)
        
        # Answer options/input
        quiz_display_layout.addWidget(QLabel("<b>Your Answer:</b>"))
        self.quiz_options_widget = QWidget()
        self.quiz_options_layout = QVBoxLayout()
        self.quiz_options_layout.setSpacing(8)
        self.quiz_options_layout.setContentsMargins(0, 0, 0, 0)
        self.quiz_options_widget.setLayout(self.quiz_options_layout)
        self.quiz_options_widget.setMinimumHeight(250)
        quiz_display_layout.addWidget(self.quiz_options_widget)
        
        # Input field for free form
        self.quiz_answer_input = QLineEdit()
        self.quiz_answer_input.setPlaceholderText("Enter your answer")
        
        quiz_display_layout.addStretch()
        self.quiz_display_widget.hide()
        layout.addWidget(self.quiz_display_widget)

        # Results section (initially hidden)
        self.quiz_results_widget = QWidget()
        results_layout = QVBoxLayout()
        self.quiz_results_widget.setLayout(results_layout)
        
        self.results_summary = QLabel()
        results_layout.addWidget(self.results_summary)
        
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["#", "Correct", "Your Answer", "Explanation"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        
        back_btn = QPushButton("Back to Quiz Config")
        back_btn.clicked.connect(self.back_to_quiz_config)
        results_layout.addWidget(back_btn)
        
        self.quiz_results_widget.hide()
        layout.addWidget(self.quiz_results_widget)

        self.tabs.addTab(w, "Quiz")

    def start_quiz(self):
        domain = self.quiz_domain.currentText()
        count = self.quiz_count.value()
        qs = get_questions(domain if domain != "All" else None)
        if len(qs) == 0:
            QMessageBox.warning(self, "No questions", "No questions in chosen domain")
            return
        
        self.quiz_questions = random.sample(qs, min(count, len(qs)))
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_domain_name = domain if domain != "All" else "All Domains"
        self.quiz_id = create_quiz(self.quiz_domain_name, len(self.quiz_questions))
        self.quiz_answers = []  # Track answers for results
        self.quiz_selected_option = None
        self.quiz_option_buttons = []
        
        # Hide config, show quiz display
        self.quiz_config_widget.hide()
        self.quiz_results_widget.hide()
        self.quiz_display_widget.show()
        
        # Show first question
        self.show_quiz_question()

    def show_quiz_question(self):
        if self.quiz_index >= len(self.quiz_questions):
            self.show_quiz_results()
            return
        
        q = self.quiz_questions[self.quiz_index]
        self.current_quiz_question = q
        
        self.quiz_progress_label.setText(f"Question {self.quiz_index + 1} of {len(self.quiz_questions)}")
        self.quiz_question.setPlainText(q['question'])
        
        # Clear options layout
        while self.quiz_options_layout.count() > 0:
            item = self.quiz_options_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        qtype = q['qtype'] if 'qtype' in q.keys() else 'free'
        qtype = qtype or 'free'
        self.quiz_selected_option = None
        self.quiz_option_buttons = []
        
        if qtype == 'MCQ':
            metadata = {}
            raw_metadata = q['metadata'] if 'metadata' in q.keys() else None
            if raw_metadata:
                try:
                    metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
                except Exception:
                    pass
            
            options = metadata.get('options', [])
            if options:
                # Create buttons for each option
                for opt in options:
                    btn = QPushButton(opt)
                    btn.setCheckable(True)
                    btn.setMinimumHeight(60)
                    btn.setMaximumWidth(10000)
                    btn.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding: 10px;
                            border: 2px solid #ccc;
                            border-radius: 5px;
                            background-color: white;
                            color: black;
                            font-size: 13px;
                        }
                        QPushButton:hover {
                            background-color: #e8f4f8;
                            border: 2px solid #0078d4;
                        }
                        QPushButton:pressed {
                            background-color: #cce5ff;
                        }
                    """)
                    btn.clicked.connect(lambda checked, o=opt: self.select_option(o))
                    self.quiz_options_layout.addWidget(btn)
                    self.quiz_option_buttons.append(btn)
                
                # Add submit button
                self.quiz_options_layout.addSpacing(15)
                submit = QPushButton("Submit Answer")
                submit.setMinimumHeight(45)
                submit.setStyleSheet("""
                    QPushButton {
                        background-color: #0078d4;
                        color: white;
                        font-weight: bold;
                        border-radius: 5px;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #0063b1;
                    }
                """)
                submit.clicked.connect(self.submit_quiz_answer)
                self.quiz_options_layout.addWidget(submit)
            else:
                # No options, use text input
                self.quiz_options_layout.addWidget(self.quiz_answer_input)
                submit = QPushButton("Submit Answer")
                submit.setMinimumHeight(45)
                submit.setStyleSheet("""
                    QPushButton {
                        background-color: #0078d4;
                        color: white;
                        font-weight: bold;
                        border-radius: 5px;
                    }
                """)
                submit.clicked.connect(self.submit_quiz_answer)
                self.quiz_options_layout.addWidget(submit)
        else:
            # Free form question
            self.quiz_options_layout.addWidget(self.quiz_answer_input)
            submit = QPushButton("Submit Answer")
            submit.setMinimumHeight(45)
            submit.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    font-weight: bold;
                    border-radius: 5px;
                }
            """)
            submit.clicked.connect(self.submit_quiz_answer)
            self.quiz_options_layout.addWidget(submit)
        
        self.quiz_answer_input.clear()

    def select_option(self, option):
        """Handle MCQ option selection."""
        previous_selection = self.quiz_selected_option
        self.quiz_selected_option = option

        for btn in self.quiz_option_buttons:
            if btn.text() == option:
                btn.setChecked(True)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 10px;
                        border: 3px solid #107c10;
                        border-radius: 5px;
                        background-color: #d5f5d5;
                        font-size: 13px;
                        font-weight: bold;
                        color: #107c10;
                    }
                    QPushButton:hover {
                        background-color: #c8f0c8;
                    }
                """)
            elif previous_selection and btn.text() == previous_selection:
                btn.setChecked(False)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 10px;
                        border: 2px solid #ccc;
                        border-radius: 5px;
                        background-color: white;
                        color: black;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #e8f4f8;
                        border: 2px solid #0078d4;
                    }
                """)

    def submit_quiz_answer(self):
        """Submit the current answer and move to next question."""
        q = self.current_quiz_question
        qtype = q['qtype'] if 'qtype' in q.keys() else 'free'
        qtype = qtype or 'free'
        
        # Get user answer
        if qtype == 'MCQ' and self.quiz_selected_option:
            user_answer = self.quiz_selected_option
        else:
            user_answer = self.quiz_answer_input.text().strip()
        
        if not user_answer:
            QMessageBox.warning(self, "No Answer", "Please select or enter an answer")
            return
        
        # Check if correct
        correct = False
        answer = q['answer'] if 'answer' in q.keys() else None
        if answer:
            if qtype == 'MCQ':
                correct = user_answer == answer
            else:
                correct = user_answer.lower() == answer.lower()
        else:
            resp = QMessageBox.question(self, "Self Grade", f"Your answer: {user_answer}\n\nCorrect?", QMessageBox.Yes | QMessageBox.No)
            correct = (resp == QMessageBox.Yes)
        
        if correct:
            self.quiz_score += 1
        
        self.quiz_answers.append({
            'question': q['question'],
            'answer': answer or '',
            'user_answer': user_answer,
            'correct': correct,
            'metadata': q['metadata'] if 'metadata' in q.keys() else None
        })
        
        record_quiz_answer(self.quiz_id, q['id'], user_answer, correct)
        record_attempt(q['id'], correct)
        
        self.quiz_index += 1
        self.quiz_selected_option = None
        self.show_quiz_question()

    def show_quiz_results(self):
        """Display quiz results with all answers."""
        update_quiz_score(self.quiz_id, self.quiz_score)
        
        pct = (self.quiz_score / len(self.quiz_questions) * 100) if self.quiz_questions else 0
        self.results_summary.setText(f"<h3>Quiz Complete!</h3><p>Score: {self.quiz_score}/{len(self.quiz_questions)} ({pct:.1f}%)</p>")
        
        self.results_table.setRowCount(0)
        for i, ans in enumerate(self.quiz_answers):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self.results_table.setItem(row, 1, QTableWidgetItem(ans['answer']))
            self.results_table.setItem(row, 2, QTableWidgetItem(ans['user_answer']))
            
            expl = ""
            if ans.get('metadata'):
                try:
                    meta = json.loads(ans['metadata']) if isinstance(ans['metadata'], str) else ans['metadata']
                    expl = meta.get('explanation', '')
                except:
                    pass
            self.results_table.setItem(row, 3, QTableWidgetItem(expl))
            
            # Color code: green for correct, red for wrong
            color = QColor(0, 128, 0) if ans['correct'] else QColor(255, 0, 0)
            for col in range(4):
                item = self.results_table.item(row, col)
                item.setBackground(color)
                item.setForeground(Qt.white)
        
        self.quiz_display_widget.hide()
        self.quiz_results_widget.show()
        self.load_stats()

    def back_to_quiz_config(self):
        """Return to quiz configuration screen."""
        self.results_table.setRowCount(0)
        self.quiz_config_widget.show()
        self.quiz_results_widget.hide()
        self.quiz_display_widget.hide()

    def history_tab(self):
        """Tab for viewing previous quiz attempts."""
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)

        layout.addWidget(QLabel("<h2>Quiz History</h2>"))

        # History table
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Date & Time", "Domain", "Questions", "Score", "Action"])
        self.history_table.horizontalHeader().setStretchLastSection(False)
        self.history_table.itemSelectionChanged.connect(self.on_history_selection_changed)
        layout.addWidget(self.history_table)

        # Details section
        layout.addWidget(QLabel("<h3>Quiz Details</h3>"))
        
        self.history_details_table = QTableWidget(0, 4)
        self.history_details_table.setHorizontalHeaderLabels(["Question #", "Correct Answer", "Your Answer", "Explanation"])
        self.history_details_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_details_table)

        clear_history_btn = QPushButton("Clear Quiz History")
        clear_history_btn.clicked.connect(self.clear_quiz_history)
        layout.addWidget(clear_history_btn)

        refresh_btn = QPushButton("Refresh History")
        refresh_btn.clicked.connect(self.load_quiz_history)
        layout.addWidget(refresh_btn)

        self.tabs.addTab(w, "History")
        self.load_quiz_history()

    def load_quiz_history(self):
        """Load and display quiz history."""
        self.history_table.setRowCount(0)
        self.history_details_table.setRowCount(0)
        
        try:
            quizzes = get_quiz_history(50)
            if not quizzes:
                self.history_table.insertRow(0)
                self.history_table.setItem(0, 0, QTableWidgetItem("No quiz history yet"))
                return
                
            for quiz in quizzes:
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                
                # Parse timestamp
                try:
                    timestamp = quiz['timestamp']
                    # Format: "2024-01-15T14:30:45.123456"
                    formatted_time = timestamp[:16].replace('T', ' ')
                except Exception as e:
                    formatted_time = str(quiz['timestamp'])
                
                self.history_table.setItem(row, 0, QTableWidgetItem(formatted_time))
                self.history_table.setItem(row, 1, QTableWidgetItem(str(quiz['domain'] or '')))
                self.history_table.setItem(row, 2, QTableWidgetItem(str(quiz['total_questions'])))
                
                score_text = f"{quiz['score']}/{quiz['total_questions']}"
                if quiz['total_questions'] > 0:
                    percentage = (quiz['score'] / quiz['total_questions'] * 100)
                    score_text += f" ({percentage:.1f}%)"
                self.history_table.setItem(row, 3, QTableWidgetItem(score_text))
                
                # View button
                view_btn = QPushButton("View Details")
                view_btn.clicked.connect(lambda checked, qid=quiz['id']: self.view_quiz_details(qid))
                self.history_table.setCellWidget(row, 4, view_btn)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load quiz history: {e}")
            print(f"Error loading quiz history: {e}")

    def view_quiz_details(self, quiz_id):
        """Display details of a specific quiz."""
        try:
            self.history_details_table.setRowCount(0)
            
            quiz_answers = get_quiz_details(quiz_id)
            if not quiz_answers:
                row = self.history_details_table.rowCount()
                self.history_details_table.insertRow(row)
                self.history_details_table.setItem(row, 0, QTableWidgetItem("No answers recorded"))
                return
                
            for i, answer in enumerate(quiz_answers):
                row = self.history_details_table.rowCount()
                self.history_details_table.insertRow(row)
                
                self.history_details_table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
                self.history_details_table.setItem(row, 1, QTableWidgetItem(str(answer['answer'] or '')))
                self.history_details_table.setItem(row, 2, QTableWidgetItem(str(answer['user_answer'] or '')))
                
                # Extract explanation
                explanation = ""
                if answer['metadata']:
                    try:
                        metadata = json.loads(answer['metadata']) if isinstance(answer['metadata'], str) else answer['metadata']
                        explanation = metadata.get('explanation', '')
                    except Exception:
                        pass
                self.history_details_table.setItem(row, 3, QTableWidgetItem(explanation))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load quiz details: {e}")
            print(f"Error loading quiz details: {e}")

    def clear_quiz_history(self):
        """Clear all quiz history from the database."""
        reply = QMessageBox.question(
            self,
            "Clear history?",
            "This will remove all saved quiz history. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            clear_quiz_history()
            self.history_details_table.setRowCount(0)
            self.load_quiz_history()
            QMessageBox.information(self, "History cleared", "Quiz history has been cleared.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear quiz history: {e}")
            print(f"Error clearing quiz history: {e}")

    def on_history_selection_changed(self):
        """Handle selection change in history table (for potential future features)."""
        pass

    def import_tab(self):
        """Tab for importing questions from CSV or JSON files."""
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)

        layout.addWidget(QLabel("<h2>Import Questions</h2>"))

        btn_csv = QPushButton("Import CSV...")
        btn_csv.clicked.connect(self.on_import_csv)
        layout.addWidget(btn_csv)

        btn_json = QPushButton("Import JSON...")
        btn_json.clicked.connect(self.on_import_json)
        layout.addWidget(btn_json)

        btn_convert = QPushButton("Convert Questions File to Import Format...")
        btn_convert.clicked.connect(self.on_convert_questions)
        layout.addWidget(btn_convert)

        csv_format = QTextEdit()
        csv_format.setReadOnly(True)
        csv_format.setPlainText(
            "CSV format:\n"
            "domain,question,option a,option b,option c,option d,answer,explanation\n"
            "Domain 1,What is X?,Option A,Option B,Option C,Option D,Answer X,Explanation X"
        )
        csv_format.setMinimumHeight(80)
        layout.addWidget(csv_format)

        json_format = QTextEdit()
        json_format.setReadOnly(True)
        json_format.setPlainText(
            "JSON format:\n"
            "[{\"domain\": \"Domain 1\", \"question\": \"What is X?\", \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"], \"answer\": \"Answer X\", \"explanation\": \"Explanation X\"}]\n\n"
            "Required fields:\n"
            "- domain\n"
            "- question\n"
            "- options (for MCQs, optional for free form)\n"
            "- answer\n"
            "- explanation"
        )
        json_format.setMinimumHeight(140)
        layout.addWidget(json_format)
        self.tabs.addTab(w, "Import")

    def on_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", str(Path.home()), "CSV files (*.csv)")
        if not path:
            return
        added, duplicates = import_csv(path)
        message = f"Imported {added} question{'s' if added != 1 else ''}"
        if duplicates > 0:
            message += f"\nSkipped {duplicates} duplicate{'s' if duplicates != 1 else ''}"
        QMessageBox.information(self, "Imported", message)
        self.reload_domains()
        self.load_stats()
        # Refresh flashcards list in case imports created new flashcards
        try:
            self.load_due_flashcards()
        except Exception:
            pass

    def on_import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open JSON", str(Path.home()), "JSON files (*.json)")
        if not path:
            return
        added, duplicates = import_json(path)
        message = f"Imported {added} question{'s' if added != 1 else ''}"
        if duplicates > 0:
            message += f"\nSkipped {duplicates} duplicate{'s' if duplicates != 1 else ''}"
        consolidate_domains()  # Optional: consolidate domains after import
        QMessageBox.information(self, "Imported", message)
        self.reload_domains()
        self.load_stats()
        # Refresh flashcards list in case imports created new flashcards
        try:
            self.load_due_flashcards()
        except Exception:
            pass

    def on_convert_questions(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Questions File",
            str(Path.home()),
            "Question files (*.csv *.json);;CSV files (*.csv);;JSON files (*.json)"
        )
        if not source_path:
            return

        default_output = str(Path(source_path).with_name(f"{Path(source_path).stem}_import_ready.json"))
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Converted Questions",
            default_output,
            "JSON files (*.json)"
        )
        if not output_path:
            return

        try:
            converted_count, converted_file = convert_questions_to_import(source_path, output_path)
            QMessageBox.information(self, "Converted", f"Converted {converted_count} questions to {converted_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert questions: {e}")

    def settings_tab(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)

        layout.addWidget(QLabel("<h2>Settings & Export</h2>"))

        reassign_btn = QPushButton("Reassign Domains for All Questions")
        reassign_btn.clicked.connect(self.on_reassign_domains)
        layout.addWidget(reassign_btn)

        export_btn = QPushButton("Export Question Bank (JSON)")
        export_btn.clicked.connect(self.export_bank)
        layout.addWidget(export_btn)

        assign_domains_btn = QPushButton("Add Domains to Missing Questions")
        assign_domains_btn.clicked.connect(self.add_domains_to_questions)
        layout.addWidget(assign_domains_btn)

        delete_all_btn = QPushButton("Delete All Questions")
        delete_all_btn.clicked.connect(self.delete_all_questions)
        layout.addWidget(delete_all_btn)

        reset_btn = QPushButton("Reset Database (delete all)")
        reset_btn.clicked.connect(self.reset_db)
        layout.addWidget(reset_btn)

        self.tabs.addTab(w, "Settings")

    def add_domains_to_questions(self):
        try:
            summary = assign_missing_domains()
            self.reload_domains()
            self.load_stats()
            if summary['updated']:
                QMessageBox.information(
                    self,
                    "Domains updated",
                    f"Assigned domains to {summary['updated']} question(s). {summary['remaining']} still need review."
                )
            else:
                QMessageBox.information(
                    self,
                    "No domains updated",
                    "All questions already have domains assigned."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to assign domains: {e}")
            print(f"Error assigning domains: {e}")

    def on_reassign_domains(self):
        reply = QMessageBox.question(
            self,
            "Reassign domains?",
            "This will re-run domain classification on all questions, which may change existing domains. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                consolidate_domains()  # Optional: consolidate before reassigning
                assign_missing_domains()  # Reuse function to reassign all
                self.reload_domains()
                self.load_stats()
                QMessageBox.information(self, "Domains reassigned", "Domains have been reassigned for all questions.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reassign domains: {e}")
                print(f"Error reassigning domains: {e}")

    # Export question bank to JSON
    def export_bank(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", str(Path.home() / "questions_export.json"), "JSON files (*.json)")
        if not path:
            return
        qs = get_questions(None)
        out = []
        for q in qs:
            export_item = {
                "domain": q["domain"],
                "question": q["question"],
                "answer": q["answer"],
                "type": q["qtype"]
            }
            metadata = q['metadata']
            if metadata:
                try:
                    parsed_metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
                except (TypeError, json.JSONDecodeError):
                    parsed_metadata = {}
                if isinstance(parsed_metadata, dict):
                    if parsed_metadata.get('options'):
                        export_item['options'] = parsed_metadata['options']
                    if parsed_metadata.get('explanation'):
                        export_item['explanation'] = parsed_metadata['explanation']
            out.append(export_item)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Exported", f"Exported {len(out)} questions to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

    # reset database
    def reset_db(self):
        reply = QMessageBox.question(
            self,
            "Are you sure?",
            "This will delete ALL questions, flashcards, attempts, quiz history, and progress. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_quiz_history()
            conn = get_conn()
            c = conn.cursor()
            c.execute("DELETE FROM attempts")
            c.execute("DELETE FROM flashcards")
            c.execute("DELETE FROM questions")
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Reset", "Database reset")
            self.reload_domains()
            self.load_stats()
            self.load_quiz_history()
            try:
                self.load_due_flashcards()
            except Exception:
                pass

    def on_reassign_domains(self):
        from app_core import reassign_domains
        updated = reassign_domains()
        QMessageBox.information(self, "Domains reassigned", f"Reassigned domains for {updated} questions.")
        self.reload_domains()
        self.load_stats()

    def delete_all_questions(self):
        reply = QMessageBox.question(
            self,
            "Delete all questions?",
            "This will delete all questions from the bank. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_all_questions()
            QMessageBox.information(self, "Deleted", "All questions have been removed.")
            self.reload_domains()
            self.load_stats()
            self.load_quiz_history()
            try:
                self.load_due_flashcards()
            except Exception:
                pass