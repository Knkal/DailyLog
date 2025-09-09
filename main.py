# -*- coding: utf-8 -*-
"""
DailyLog Desktop - PySide6 (버튼 가시성/스타일 및 메뉴 토글 수정본)
- '📅 캘린더 보기'와 '📂 불러오기' 버튼을 '내보내기'와 동일한 success(초록) 스타일로 변경
- 보기 → 좌측 뷰 전환: 실제로 토글되도록 `toggled` 시그널 연결
"""

import sys, os, sqlite3
from datetime import datetime, date

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QGroupBox, QCheckBox,
    QDateEdit, QStyledItemDelegate, QAbstractItemView, QStyle, QStatusBar,
    QGraphicsDropShadowEffect, QCalendarWidget, QStackedWidget
)
from PySide6.QtCore import Qt, QDate, QRectF, QSize, QUrl
from PySide6.QtGui import QTextDocument, QIcon, QPixmap, QAction, QDesktopServices, QPalette, QColor, QTextCharFormat

# ===== Brand Settings =====
BRAND_PRIMARY = "#3B82F6"
BRAND_PRIMARY_DARK = "#2563EB"
FONT_FAMILY   = "Noto Sans KR"
FONT_SIZE_PT  = 10
FONT_FALLBACK = "'Segoe UI Emoji','Segoe UI Symbol','Apple Color Emoji'"
WEEKDAY_KR = ["월","화","수","목","금","토","일"]

# ===== Helpers =====
def normalize_date(input_str: str):
    if not input_str:
        d = date.today()
        iso = d.strftime("%Y-%m-%d")
        return iso, f"{iso} ({WEEKDAY_KR[d.weekday()]})"
    s = str(input_str).strip().split()[0].replace(".","-").replace("/","-")
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try: dt = datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception: dt = date.today()
    iso = dt.strftime("%Y-%m-%d")
    return iso, f"{iso} ({WEEKDAY_KR[dt.weekday()]})"

class DailyLogDB:
    def __init__(self, db_path="daily_log.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries(
                date_iso TEXT PRIMARY KEY,
                date_label TEXT,
                daily_log TEXT DEFAULT '',
                trades TEXT DEFAULT '',
                holdings TEXT DEFAULT '',
                considerations TEXT DEFAULT '',
                interests TEXT DEFAULT '',
                updated_at TEXT
            );
            """
        ); self.conn.commit()

    def close(self): self.conn.close()

    def get_all(self, search_text: str = ""):
        cur = self.conn.cursor()
        if search_text:
            like = f"%{search_text.lower()}%"
            cur.execute(
                """
                SELECT date_iso, date_label, daily_log, trades, holdings, considerations, interests
                FROM entries
                WHERE lower(date_label) LIKE ?
                   OR lower(daily_log) LIKE ?
                   OR lower(trades) LIKE ?
                   OR lower(holdings) LIKE ?
                   OR lower(considerations) LIKE ?
                   OR lower(interests) LIKE ?
                ORDER BY date_iso DESC;
                """,(like,like,like,like,like,like))
        else:
            cur.execute(
                """
                SELECT date_iso, date_label, daily_log, trades, holdings, considerations, interests
                FROM entries ORDER BY date_iso DESC;
                """
            )
        return cur.fetchall()

    def get_by_date(self, date_iso: str):
        cur = self.conn.cursor()
        cur.execute("SELECT date_label, daily_log, trades, holdings, considerations, interests FROM entries WHERE date_iso=?", (date_iso,))
        return cur.fetchone()

    def get_all_dates(self):
        cur = self.conn.cursor()
        cur.execute("SELECT date_iso FROM entries")
        return [r[0] for r in cur.fetchall()]

    def upsert_merge(self, date_iso, date_label, vals):
        cur = self.conn.cursor()
        cur.execute("SELECT daily_log,trades,holdings,considerations,interests FROM entries WHERE date_iso=?", (date_iso,))
        row = cur.fetchone()
        cols = ["daily_log","trades","holdings","considerations","interests"]
        if row:
            merged={}
            for i,c in enumerate(cols):
                old=row[i] or ""; new=vals.get(c,"") or ""
                merged[c] = (old.strip()+"\n"+new.strip()) if (old and new) else (old or new).strip()
            cur.execute(
                """
                UPDATE entries
                SET date_label=?, daily_log=?, trades=?, holdings=?, considerations=?, interests=?, updated_at=datetime('now','localtime')
                WHERE date_iso=?""",
                (date_label, merged["daily_log"], merged["trades"], merged["holdings"],
                 merged["considerations"], merged["interests"], date_iso))
        else:
            cur.execute(
                """
                INSERT INTO entries(date_iso,date_label,daily_log,trades,holdings,considerations,interests,updated_at)
                VALUES(?,?,?,?,?,?,?,datetime('now','localtime'))""",
                (date_iso,date_label,vals.get("daily_log",""),vals.get("trades",""),
                 vals.get("holdings",""),vals.get("considerations",""),vals.get("interests","")))
        self.conn.commit()

    def overwrite(self, date_iso, date_label, vals):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM entries WHERE date_iso=?", (date_iso,))
        if cur.fetchone():
            cur.execute(
                """
                UPDATE entries
                SET date_label=?, daily_log=?, trades=?, holdings=?, considerations=?, interests=?, updated_at=datetime('now','localtime')
                WHERE date_iso=?""",
                (date_label, vals.get("daily_log",""), vals.get("trades",""), vals.get("holdings",""),
                 vals.get("considerations",""), vals.get("interests",""), date_iso))
        else:
            cur.execute(
                """
                INSERT INTO entries(date_iso,date_label,daily_log,trades,holdings,considerations,interests,updated_at)
                VALUES(?,?,?,?,?,?,?,datetime('now','localtime'))""",
                (date_iso,date_label,vals.get("daily_log",""),vals.get("trades",""),
                 vals.get("holdings",""),vals.get("considerations",""),vals.get("interests","")))
        self.conn.commit()

    def delete(self, date_iso):
        self.conn.execute("DELETE FROM entries WHERE date_iso=?", (date_iso,))
        self.conn.commit()

    def wipe_all(self):
        self.conn.execute("DELETE FROM entries;")
        self.conn.commit()

class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query = ""
        self.dark_mode = False

    def setQuery(self, q: str):
        self.query = (q or "").strip()

    def setDarkMode(self, dark_mode: bool):
        self.dark_mode = dark_mode

    def paint(self, painter, option, index):
        text = index.data() or ""
        selected_flag = getattr(QStyle.StateFlag, 'State_Selected', getattr(QStyle, 'State_Selected', 0))
        if selected_flag and (option.state & selected_flag):
            painter.fillRect(option.rect, option.palette.highlight())

        import html, re as _re
        safe = html.escape(str(text)).replace("\n", "<br>")
        if self.query:
            pat = _re.compile(_re.escape(self.query), _re.IGNORECASE)
            safe = pat.sub(lambda m: f"<span style='background-color:#fde68a'>{html.escape(m.group(0))}</span>", safe)

        if selected_flag and (option.state & selected_flag):
            text_color = "#FFFFFF" if self.dark_mode else "#111827"
        else:
            text_color = "#111827" if not self.dark_mode else "#FFFFFF"

        doc = QTextDocument()
        doc.setHtml(f"<span style='color:{text_color}'>{safe}</span>")
        doc.setTextWidth(option.rect.width() - 10)

        painter.save()
        painter.translate(option.rect.x() + 5, option.rect.y() + 5)
        doc.drawContents(painter, QRectF(0, 0, option.rect.width() - 10, option.rect.height() - 10))
        painter.restore()

    def sizeHint(self, option, index):
        import html
        text = index.data() or ""
        doc = QTextDocument()
        doc.setHtml(html.escape(str(text)).replace("\n", "<br>"))
        width = option.widget.columnWidth(index.column()) - 10 if option.widget else 400
        doc.setTextWidth(width)
        h = int(doc.size().height()) + 10
        return QSize(width, h)

def gb(title, widget):
    box = QGroupBox(title)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(12, 10, 12, 12)
    lay.setSpacing(8)
    lay.addWidget(widget)
    box.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=16, xOffset=0, yOffset=2))
    return box

class MainWindow(QMainWindow):
    VIEW_LIST = 0
    VIEW_CAL  = 1

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HelloJJ")
        self.resize(1700, 650)
        self.setStatusBar(QStatusBar())
        self.dark_mode = False  # 라이트 모드 기본
        self.left_view_mode = self.VIEW_LIST

        # App icon
        icon_path = "logo.png" if os.path.exists("logo.png") else ("app.ico" if os.path.exists("app.ico") else ("app.icns" if os.path.exists("app.icns") else None))
        if icon_path: self.setWindowIcon(QIcon(icon_path))

        # DB
        self.db_path = os.path.join(os.getcwd(), "daily_log.db")
        self.db = DailyLogDB(self.db_path)

        # ===== Top Bar =====
        self.topbar = QWidget(); self.topbar.setObjectName("TopBar")
        tb_layout = QHBoxLayout(self.topbar); tb_layout.setContentsMargins(16, 10, 16, 10); tb_layout.setSpacing(8)

        self.lbl_title = QLabel(); self.lbl_title.setObjectName("AppTitle")
        _banner = "logo.png"
        if os.path.exists(_banner):
            _pm = QPixmap(_banner)
            self.lbl_title.setPixmap(_pm.scaledToHeight(40, Qt.SmoothTransformation))
            self.lbl_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.lbl_title.setStyleSheet("background: transparent;")
        else:
            self.lbl_title.setText("Daily Log")
        tb_layout.addWidget(self.lbl_title)

        if os.path.exists(_banner):
            self.lbl_subtitle = QLabel("Daily Log"); self.lbl_subtitle.setObjectName("AppSubtitle")
            self.lbl_subtitle.setStyleSheet(
                "background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);"
                f"padding: 4px 8px; border-radius: 4px; color: #FFFFFF; font-family: '{FONT_FAMILY}';"
                f"font-size: {FONT_SIZE_PT+2}pt; font-weight: bold; margin-left: 8px;"
            )
            tb_layout.addWidget(self.lbl_subtitle)

        tb_layout.addStretch(1)

        # 검색
        self.search_edit = QLineEdit(); self.search_edit.setObjectName("search_edit")
        self.search_edit.setPlaceholderText("검색 (모든 컬럼)"); self.search_edit.setMinimumWidth(300)
        self.search_edit.textChanged.connect(self.refresh_table)

        # --- Buttons (변경 포인트) ---
        # 좌측 뷰 전환 버튼: "내보내기"처럼 success(초록) 채움 + 토글
        self.btn_toggle_view = QPushButton("📅 캘린더 보기")
        self.btn_toggle_view.setObjectName("viewToggle")
        self.btn_toggle_view.setProperty("role", "success")  # 초록색 채움
        self.btn_toggle_view.setCheckable(True)
        self.btn_toggle_view.setChecked(False)  # 기본: 리스트 보기
        self.btn_toggle_view.setFixedHeight(28)
        self.btn_toggle_view.setCursor(Qt.PointingHandCursor)
        # 클릭뿐 아니라 토글에도 반응 (메뉴 액션에서 상태만 바꿔도 동작)
        self.btn_toggle_view.toggled.connect(self.on_view_toggle)

        # 불러오기 / 내보내기: 둘 다 success(초록)로 통일 (가시성 향상)
        self.btn_import = QPushButton("📂 불러오기")
        self.btn_export = QPushButton("📤 내보내기")
        for b in (self.btn_import, self.btn_export):
            b.setFixedHeight(28); b.setCursor(Qt.PointingHandCursor)
            b.setProperty("role", "success")  # 모두 초록
        self.btn_import.setToolTip("선택한 엑셀 파일로 전체 리스트를 '완전 대체'합니다.")
        self.btn_import.clicked.connect(self.on_import_excel)
        self.btn_export.clicked.connect(self.on_export_excel)

        tb_layout.addWidget(self.search_edit, 0)
        tb_layout.addWidget(self.btn_toggle_view, 0)
        tb_layout.addWidget(self.btn_import, 0)
        tb_layout.addWidget(self.btn_export, 0)

        # ===== Central =====
        central = QWidget(); central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(16, 12, 16, 16); central_layout.setSpacing(12)
        self.splitter = QSplitter(Qt.Horizontal)

        # Left stack (list <-> calendar)
        self.left_stack = QStackedWidget()

        # 1) List(Table)
        list_wrap = QWidget(); left_layout = QVBoxLayout(list_wrap); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(10)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["날짜", "Daily Log", "주식 거래내역", "남은 주식 수(증권사별)", "주식 고려사항", "관심 주"])
        self.table.setWordWrap(True)
        try: self.table.setTextElideMode(Qt.ElideNone)
        except Exception: pass
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.Stretch); hh.setMinimumSectionSize(120)
        try: self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        except Exception: pass
        try: self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        except Exception: pass
        try: self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        except Exception: pass
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self.on_row_clicked)
        self.hl_delegate = HighlightDelegate(self.table)
        self.table.setItemDelegate(self.hl_delegate)
        left_layout.addWidget(self.table)
        self.left_stack.addWidget(list_wrap)

        # 2) Calendar
        cal_wrap = QWidget(); cal_layout = QVBoxLayout(cal_wrap); cal_layout.setContentsMargins(0,0,0,0); cal_layout.setSpacing(10)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.selectionChanged.connect(self.on_calendar_changed)
        cal_layout.addWidget(self.calendar)
        self.left_stack.addWidget(cal_wrap)

        # Right form
        right = QWidget(); form = QVBoxLayout(right); form.setContentsMargins(0,0,0,0); form.setSpacing(8)
        date_row = QHBoxLayout(); date_row.setSpacing(6)
        lbl_date = QLabel("날짜"); lbl_date.setObjectName("FieldLabel")
        self.date_edit = QDateEdit(); self.date_edit.setDisplayFormat("yyyy-MM-dd"); self.date_edit.setCalendarPopup(True); self.date_edit.setDate(QDate.currentDate())
        self.overwrite_chk = QCheckBox("덮어쓰기 (기존 텍스트 대체)")
        self.overwrite_chk.setToolTip("체크하면 저장 시 기존 데이터를 폼 내용으로 완전 대체합니다.")
        self.overwrite_chk.toggled.connect(self._update_save_mode)
        date_row.addWidget(lbl_date); date_row.addWidget(self.date_edit, 1); date_row.addWidget(self.overwrite_chk, 0)
        form.addLayout(date_row)

        self.daily_log_edit = QTextEdit(); self.daily_log_edit.setPlaceholderText("🍲 점심: ..., 🚶 점심운동: ..., 👟 운동: ..., 🌳 산책: ..., 📖 독서: ...")
        self.trades_edit = QTextEdit(); self.trades_edit.setPlaceholderText("📈 매수: ... / 📉 매도: ...")
        self.holdings_edit = QTextEdit(); self.holdings_edit.setPlaceholderText("🏦 대신증권: ... | 🏦 키움증권: ... | 🏦 키움 ISA: ...")
        self.consider_edit = QTextEdit(); self.consider_edit.setPlaceholderText("🔎 메모: ...")
        self.interest_edit = QTextEdit(); self.interest_edit.setPlaceholderText("✅ 관심주 ...  ⭐ 강조 ...")

        form.addWidget(gb("Daily Log", self.daily_log_edit))
        self._add_chip_toolbar(form.itemAt(form.count()-1).widget().layout(), [
            ("🍲 점심", self.daily_log_edit, "🍲 점심: "),
            ("🚶 점심운동", self.daily_log_edit, "🚶 점심운동: "),
            ("👟 운동", self.daily_log_edit, "👟 운동: "),
            ("🌳 산책", self.daily_log_edit, "🌳 산책: "),
            ("📖 독서", self.daily_log_edit, "📖 독서: "),
        ])
        form.addWidget(gb("주식 거래내역", self.trades_edit))
        self._add_chip_toolbar(form.itemAt(form.count()-1).widget().layout(), [
            ("📈 매수", self.trades_edit, "📈 매수: "),
            ("📉 매도", self.trades_edit, "📉 매도: "),
        ])
        form.addWidget(gb("남은 주식 수(증권사별)", self.holdings_edit))
        self._add_chip_toolbar(form.itemAt(form.count()-1).widget().layout(), [
            ("🏦 대신증권", self.holdings_edit, "🏦 대신증권: "),
            ("🏦 키움증권", self.holdings_edit, "🏦 키움증권: "),
            ("🏦 키움 ISA", self.holdings_edit, "🏦 키움 ISA: "),
        ])
        form.addWidget(gb("주식 고려사항", self.consider_edit))
        self._add_chip_toolbar(form.itemAt(form.count()-1).widget().layout(), [
            ("🔎 메모", self.consider_edit, "🔎 메모: "),
            ("• 항목", self.consider_edit, "- "),
        ])
        form.addWidget(gb("관심 주", self.interest_edit))
        self._add_chip_toolbar(form.itemAt(form.count()-1).widget().layout(), [
            ("✅ 체크", self.interest_edit, "✅ "),
            ("⭐ 강조", self.interest_edit, "⭐ "),
        ])

        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self.btn_save = QPushButton(" 저장"); btn_delete = QPushButton(" 선택 날짜 삭제"); btn_clear = QPushButton(" 폼 지우기")
        self.btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        btn_clear.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.btn_save.setProperty("role", "accent"); btn_delete.setProperty("role", "danger")
        for b in (self.btn_save, btn_delete, btn_clear): b.setFixedHeight(28); b.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.on_save); btn_delete.clicked.connect(self.on_delete); btn_clear.clicked.connect(self.on_clear_form)
        btn_row.addWidget(self.btn_save); btn_row.addWidget(btn_delete); btn_row.addStretch(1); btn_row.addWidget(btn_clear)
        form.addLayout(btn_row)

        # split
        self.splitter.addWidget(self.left_stack)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 85); self.splitter.setStretchFactor(1, 15)
        central_layout.addWidget(self.splitter)

        # central attach
        container = QWidget(); container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0,0,0,0); container_layout.setSpacing(0)
        container_layout.addWidget(self.topbar); container_layout.addWidget(central)
        self.setCentralWidget(container)

        self._build_menubar()
        self.apply_theme(light_mode=not self.dark_mode)
        self.refresh_table()
        self.refresh_calendar_marks()
        self._update_save_mode(self.overwrite_chk.isChecked())
        self._show_db_path()

    # ===== Left view handling =====
    def on_view_toggle(self, checked: bool):
        # checked=True → 캘린더 보기, False → 리스트 보기
        self.left_view_mode = self.VIEW_CAL if checked else self.VIEW_LIST
        self.left_stack.setCurrentIndex(self.left_view_mode)
        self.btn_toggle_view.setText("📋 리스트 보기" if checked else "📅 캘린더 보기")
        if checked:
            self.refresh_calendar_marks()
        self._show_db_path()

    def toggle_left_view(self):
        # 메뉴/단축키 → 상태 토글 (toggled 시그널이 on_view_toggle을 호출)
        self.btn_toggle_view.setChecked(not self.btn_toggle_view.isChecked())

    def on_calendar_changed(self):
        qd: QDate = self.calendar.selectedDate()
        iso, label = normalize_date(qd.toString("yyyy-MM-dd"))
        self.date_edit.setDate(qd)
        row = self.db.get_by_date(iso)
        if row:
            self.daily_log_edit.setPlainText(row[1] or "")
            self.trades_edit.setPlainText(row[2] or "")
            self.holdings_edit.setPlainText(row[3] or "")
            self.consider_edit.setPlainText(row[4] or "")
            self.interest_edit.setPlainText(row[5] or "")
        else:
            for w in (self.daily_log_edit, self.trades_edit, self.holdings_edit, self.consider_edit, self.interest_edit):
                w.clear()
        self.statusBar().showMessage(f"캘린더 선택: {label}", 2000)

    def refresh_calendar_marks(self):
        self.calendar.setWeekdayTextFormat(Qt.Monday, QTextCharFormat())
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#DCFCE7"))
        fmt.setForeground(QColor("#065F46"))
        for iso in self.db.get_all_dates():
            try:
                y,m,d = map(int, iso.split("-"))
                qd = QDate(y,m,d)
                self.calendar.setDateTextFormat(qd, fmt)
            except Exception:
                continue

    # ===== Table/List =====
    def refresh_table(self):
        q = self.search_edit.text().strip()
        self.hl_delegate.setQuery(q)
        self.hl_delegate.setDarkMode(self.dark_mode)
        rows = self.db.get_all(q)
        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount(); self.table.insertRow(row)
            for c, val in enumerate([r[1], r[2], r[3], r[4], r[5], r[6]]):
                item = QTableWidgetItem(str(val or ""))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                item.setForeground(QColor("#FFFFFF" if self.dark_mode else "#111827"))
                self.table.setItem(row, c, item)
        try: self.table.resizeRowsToContents()
        except Exception: pass

    def _add_chip_toolbar(self, parent_layout, pairs):
        row = QHBoxLayout(); row.setSpacing(4)
        for label, target, snippet in pairs:
            btn = QPushButton(label); btn.setProperty("variant", "chip"); btn.setFixedHeight(22)
            btn.clicked.connect(lambda _, e=target, s=snippet: self._insert_snippet(e, s))
            row.addWidget(btn)
        row.addStretch(1)
        parent_layout.addLayout(row)

    def _insert_snippet(self, edit_widget, snippet: str):
        if not snippet: return
        cursor = edit_widget.textCursor(); text = edit_widget.toPlainText()
        if text and not text.endswith("\n"): cursor.insertText("\n")
        cursor.insertText(snippet); edit_widget.setFocus()

    # ===== Title bar colors (Windows) =====
    def _set_win_titlebar_colors(self, fg_rgb=None, bg_rgb=None, dark_mode=None):
        if sys.platform != "win32": return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            if dark_mode is not None:
                val = ctypes.c_int(1 if dark_mode else 0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), ctypes.c_uint(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(val), ctypes.sizeof(val))
            if bg_rgb is not None:
                bgr = (bg_rgb[2] << 16) | (bg_rgb[1] << 8) | bg_rgb[0]
                val = ctypes.c_int(bgr)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), ctypes.c_uint(DWMWA_CAPTION_COLOR), ctypes.byref(val), ctypes.sizeof(val))
            if fg_rgb is not None:
                bgr = (fg_rgb[2] << 16) | (fg_rgb[1] << 8) | fg_rgb[0]
                val = ctypes.c_int(bgr)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), ctypes.c_uint(DWMWA_TEXT_COLOR), ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            return

    # ===== Menus =====
    def _build_menubar(self):
        mb = self.menuBar()
        # 파일
        m_file = mb.addMenu("파일(&F)")
        act_import = QAction("불러오기(엎기)", self); act_export = QAction("내보내기", self); act_exit = QAction("종료(Exit)", self)
        act_import.triggered.connect(self.on_import_excel); act_export.triggered.connect(self.on_export_excel); act_exit.triggered.connect(self.close)
        m_file.addAction(act_import); m_file.addAction(act_export); m_file.addSeparator(); m_file.addAction(act_exit)
        # 편집
        m_edit = mb.addMenu("편집(&E)")
        act_clear = QAction("폼 지우기(Clear Form)", self); act_delete = QAction("선택 삭제(Delete Entry)", self)
        act_clear.triggered.connect(self.on_clear_form); act_delete.triggered.connect(self.on_delete)
        m_edit.addAction(act_clear); m_edit.addAction(act_delete)
        # 보기
        m_view = mb.addMenu("보기(&V)")
        self.act_theme = QAction("테마 전환 (라이트/다크)", self, checkable=True); self.act_theme.setChecked(self.dark_mode); self.act_theme.toggled.connect(self.toggle_theme)
        m_view.addAction(self.act_theme)
        self.act_toggle_left = QAction("좌측 뷰 전환 (리스트/캘린더)", self)
        self.act_toggle_left.triggered.connect(self.toggle_left_view)
        m_view.addAction(self.act_toggle_left)
        # 도움말
        m_help = mb.addMenu("도움말(&H)")
        act_readme = QAction("README 열기", self); act_about = QAction("버전 정보(About)", self)
        act_readme.triggered.connect(self.open_readme); act_about.triggered.connect(self.show_about)
        m_help.addAction(act_readme); m_help.addAction(act_about)

    def open_readme(self):
        for fname in ("README.txt", "README.md"):
            fpath = os.path.join(os.getcwd(), fname)
            if os.path.exists(fpath):
                QDesktopServices.openUrl(QUrl.fromLocalFile(fpath))
                self.statusBar().showMessage(f"열기: {fname}", 1500)
                return
        QMessageBox.information(self, "README", "README 파일을 찾을 수 없습니다.")

    def show_about(self):
        QMessageBox.about(self, "About DailyLog", "DailyLog Desktop\n\n© 2025 JJ. All rights reserved.")

    def _update_save_mode(self, checked: bool):
        if not hasattr(self, "btn_save") or self.btn_save is None: return
        if checked:
            self.btn_save.setText(" 덮어쓰기 저장")
            self.btn_save.setToolTip("지정 날짜의 기존 데이터를 폼 내용으로 완전 대체합니다. (빈 칸은 빈 값)")
        else:
            self.btn_save.setText(" 추가/병합 저장")
            self.btn_save.setToolTip("기존이 있으면 줄바꿈 병합, 없으면 새로 저장")

    def toggle_theme(self, on: bool):
        self.dark_mode = bool(on)
        self.apply_theme(light_mode=not self.dark_mode)
        self.hl_delegate.setDarkMode(self.dark_mode)
        self.refresh_table(); self.refresh_calendar_marks()
        self.table.viewport().update()
        self._show_db_path()

    def _show_db_path(self):
        self.statusBar().showMessage(
            f"DB: {self.db_path}   |   Theme: {'Dark' if self.dark_mode else 'Light'}   |   View: {'Calendar' if self.left_view_mode==self.VIEW_CAL else 'List'}",
            2500
        )

    def on_row_clicked(self, row, col):
        date_label = self.table.item(row, 0).text(); iso = date_label[:10]
        self.date_edit.setDate(QDate.fromString(iso, "yyyy-MM-dd"))
        self.daily_log_edit.setPlainText(self.table.item(row, 1).text())
        self.trades_edit.setPlainText(self.table.item(row, 2).text())
        self.holdings_edit.setPlainText(self.table.item(row, 3).text())
        self.consider_edit.setPlainText(self.table.item(row, 4).text())
        self.interest_edit.setPlainText(self.table.item(row, 5).text())

    def _collect_form_vals(self):
        return {
            "daily_log": self.daily_log_edit.toPlainText(),
            "trades": self.trades_edit.toPlainText(),
            "holdings": self.holdings_edit.toPlainText(),
            "considerations": self.consider_edit.toPlainText(),
            "interests": self.interest_edit.toPlainText(),
        }

    def on_save(self):
        iso, label = normalize_date(self.date_edit.date().toString("yyyy-MM-dd"))
        vals = self._collect_form_vals()
        if self.overwrite_chk.isChecked():
            if QMessageBox.question(self, "덮어쓰기 확인", f"{label} 항목을 현재 폼 내용으로 완전히 대체할까요?\n(빈 칸은 빈 값으로 저장)", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                self.statusBar().showMessage("덮어쓰기 취소됨", 1500)
                return
            self.db.overwrite(iso, label, vals)
            self.statusBar().showMessage(f"{label} 덮어쓰기 완료", 2000)
        else:
            vals = {k: v.strip() for k, v in vals.items()}
            self.db.upsert_merge(iso, label, vals)
            self.statusBar().showMessage(f"{label} 저장(병합) 완료", 2000)
        self.refresh_table(); self.refresh_calendar_marks()

    def on_delete(self):
        iso, label = normalize_date(self.date_edit.date().toString("yyyy-MM-dd"))
        if QMessageBox.question(self, "삭제 확인", f"{label} 항목을 삭제할까요?") == QMessageBox.Yes:
            self.db.delete(iso)
            self.refresh_table(); self.refresh_calendar_marks()
            self.statusBar().showMessage(f"{label} 삭제 완료", 2000)

    def on_clear_form(self):
        self.date_edit.setDate(QDate.currentDate())
        for w in (self.daily_log_edit, self.trades_edit, self.holdings_edit, self.consider_edit, self.interest_edit):
            w.clear()
        self.statusBar().showMessage("폼을 초기화했습니다", 1500)

    # ===== Excel Import/Export =====
    def on_import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "엑셀 파일 선택 (DB '완전 대체')", "", "Excel Files (*.xlsx *.xls)")
        if not path: return
        if QMessageBox.question(
            self, "전체 대체(엎기) 확인",
            "선택한 엑셀 파일의 내용으로 전체 리스트를 '완전 대체'합니다.\n현재 DB의 모든 데이터는 삭제됩니다.\n진행할까요?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            self.statusBar().showMessage("불러오기 취소됨", 1500)
            return
        try:
            import pandas as pd
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(os.path.dirname(path) or os.getcwd(), f"Daily_Log_backup_{ts}.xlsx")
            data = self._to_dataframe()
            df = pd.DataFrame(data, columns=["날짜", "Daily Log", "주식 거래내역", "남은 주식 수(증권사별)", "주식 고려사항", "관심 주"])
            with pd.ExcelWriter(backup_path, engine="openpyxl") as w:
                df.to_excel(w, sheet_name="Daily Log-From July 21", index=False)
        except Exception as e:
            QMessageBox.warning(self, "백업 경고", f"백업 실패, 계속 진행합니다.\n\n세부: {e}")
        try:
            self.db.wipe_all()
            self._import_excel_to_db(path, sheet_name="Daily Log-From July 21")
            self.refresh_table(); self.refresh_calendar_marks()
            QMessageBox.information(self, "완료", "엑셀 파일 내용으로 전체 리스트를 완전히 대체했습니다.")
            self.statusBar().showMessage("엑셀 불러오기(전체 대체) 완료", 2000)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"불러오기 중 오류: {e}")

    def _import_excel_to_db(self, xlsx_path, sheet_name="Daily Log-From July 21"):
        import pandas as pd
        if not os.path.exists(xlsx_path): raise FileNotFoundError(xlsx_path)
        def canon(s: str) -> str:
            if s is None: return ""
            s = str(s).replace("（", "(").replace("）", ")").replace("\u00a0", " ").strip().lower().replace(" ", "")
            return s.replace(" (", "(").replace("( ", "(").replace(" )", ")").replace(") ", ")")
        expected = {
            canon("날짜"): "날짜",
            canon("Daily Log"): "Daily Log",
            canon("주식 거래내역"): "주식 거래내역",
            canon("남은 주식 수(증권사별)"): "남은 주식 수(증권사별)",
            canon("주식 고려사항"): "주식 고려사항",
            canon("관심 주"): "관심 주"
        }
        def rename_columns(df):
            m = {}
            for c in df.columns:
                k = canon(c)
                if k in expected: m[c] = expected[k]
                elif k == canon("주식거래내역"): m[c] = "주식 거래내역"
                elif k == canon("관심주"): m[c] = "관심 주"
            return df.rename(columns=m)

        try:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name, dtype=str, engine="openpyxl").fillna("")
            df = rename_columns(df)
            have = set(df.columns)
            if not {"날짜", "Daily Log"}.issubset(have): raise ValueError("header0_missing")
        except Exception:
            raw = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl").fillna("")
            header_row, best = -1, -1
            for i in range(min(15, len(raw))):
                vals = [canon(v) for v in raw.iloc[i].tolist()]
                hits = sum(1 for v in vals if v in expected)
                if canon("날짜") in vals and hits > best: best = hits; header_row = i
            if header_row < 0:
                raise ValueError("엑셀 시트에서 헤더 행을 찾을 수 없습니다. '날짜'가 포함된 행이 필요합니다.")
            header_vals = raw.iloc[header_row].tolist()
            data = raw.iloc[header_row + 1:].copy(); data.columns = header_vals
            df = rename_columns(data).fillna("")
        for name in ["날짜", "Daily Log", "주식 거래내역", "남은 주식 수(증권사별)", "주식 고려사항", "관심 주"]:
            if name not in df.columns: df[name] = ""
        for _, row in df.iterrows():
            iso, label = normalize_date(row["날짜"])
            vals = {
                "daily_log": row.get("Daily Log", ""),
                "trades": row.get("주식 거래내역", ""),
                "holdings": row.get("남은 주식 수(증권사별)", ""),
                "considerations": row.get("주식 고려사항", ""),
                "interests": row.get("관심 주", "")
            }
            self.db.overwrite(iso, label, vals)

    def on_export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "엑셀로 내보내기", "Daily_Log_updated.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        try:
            import pandas as pd
            df = pd.DataFrame(self._to_dataframe(),
                              columns=["날짜", "Daily Log", "주식 거래내역", "남은 주식 수(증권사별)", "주식 고려사항", "관심 주"])
            with pd.ExcelWriter(path, engine="openpyxl") as w:
                df.to_excel(w, sheet_name="Daily Log-From July 21", index=False)
            QMessageBox.information(self, "내보내기 완료", f"저장됨: {path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 중 오류: {e}")

    def _to_dataframe(self):
        rows = self.db.get_all()
        data = []
        for r in rows:
            data.append({
                "날짜": r[1], "Daily Log": r[2], "주식 거래내역": r[3],
                "남은 주식 수(증권사별)": r[4], "주식 고려사항": r[5], "관심 주": r[6]
            })
        return data

    # ===== Theming =====
    def apply_theme(self, light_mode=True):
        if light_mode:
            primary = BRAND_PRIMARY
            topbar_bg = BRAND_PRIMARY
            topbar_text = "#FFFFFF"
            base_bg = "#F5F7FA"
            text_col = "#111827"
            card_bg = "#FFFFFF"
            alt_bg = "#FAFAFB"
            header_bg = "#F9FAFB"
            header_text = "#111827"
            border_col = "#E5E7EB"
            table_sel = f"{primary}22"
            btn_border = "#E5E7EB"
            chip_bg = "#F9FAFB"
            chip_hover = "#EFF6FF"
            selection_color = "#111827"
        else:
            primary = "#60A5FA"
            topbar_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB)"
            topbar_text = "#FFFFFF"
            base_bg = "#0B1220"
            text_col = "#FFFFFF"
            card_bg = "#111827"
            alt_bg = "#1E293B"
            header_bg = "#0F172A"          # darker header/menu background
            header_text = "#E5E7EB"        # light gray text for headers/menus
            border_col = "#334155"
            table_sel = "#1D4ED833"
            btn_border = "#2D3748"
            chip_bg = alt_bg
            chip_hover = "#334155"
            selection_color = "#FFFFFF"

        qss = f"""
        QWidget {{ background:{base_bg}; font-family:'{FONT_FAMILY}', {FONT_FALLBACK}; font-size:{FONT_SIZE_PT}pt; color:{text_col}; }}
        QWidget#TopBar {{ background: {topbar_bg}; border-bottom: 1px solid {border_col}; }}
        QWidget#TopBar QLabel#AppTitle {{ color:{topbar_text}; font-family:'{FONT_FAMILY}'; font-size:{FONT_SIZE_PT+5}pt; font-weight:800; }}
        QWidget#TopBar QLabel#AppSubtitle {{ background-color: {topbar_bg}; padding: 4px 8px; border-radius: 4px; color: #FFFFFF; font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE_PT+2}pt; font-weight: bold; margin-left: 8px; letter-spacing: 0.5px; }}

        QTableWidget {{ background:{card_bg}; border:1px solid {border_col}; border-radius:12px; gridline-color:{border_col};
                        alternate-background-color:{alt_bg}; selection-background-color:{table_sel}; selection-color:{selection_color}; padding:8px; }}
        QTableWidget::item {{ padding:6px; }}

        /* Calendar */
        QCalendarWidget QWidget {{ alternate-background-color:{alt_bg}; background:{card_bg}; color:{text_col}; }}
        QCalendarWidget QAbstractItemView:enabled {{ selection-background-color:{table_sel}; selection-color:{selection_color}; background:{card_bg}; color:{text_col}; }}
        QCalendarWidget QToolButton {{ color:{text_col}; background: transparent; border: none; padding:4px 8px; }}
        QCalendarWidget QToolButton:hover {{ background:{chip_hover}; border-radius:6px; }}
        QCalendarWidget QMenu {{ background:{header_bg}; color:{header_text}; border:1px solid {border_col}; }}

        /* Inputs */
        QLineEdit, QTextEdit, QDateEdit {{ background:{card_bg}; border:1px solid {btn_border}; border-radius:7px; padding:4px 6px; color:{text_col}; }}
        QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {{ border-color:{primary}; }}
        QDateEdit::drop-down {{ width:18px; }}
        QDateEdit::down-arrow {{ width:10px; height:10px; }}
        QLineEdit#search_edit {{ min-width: 300px; padding: 6px 12px; }}

        QCheckBox {{ spacing:6px; color:{text_col}; }}

        /* Buttons */
        QPushButton {{ font-size:{FONT_SIZE_PT}pt; padding:5px 10px; border:1px solid {btn_border}; border-radius:7px; background:{card_bg}; color:{text_col}; }}
        QPushButton:hover {{ background:{chip_hover}; }}
        QPushButton[role="accent"] {{ background:{primary}; color:#FFFFFF; border-color:{primary}; }}
        QPushButton[role="success"] {{ background:#16A34A; color:#FFFFFF; border-color:#16A34A; }}
        QPushButton[role="danger"] {{ background:#DC2626; color:#FFFFFF; border-color:#DC2626; }}
        QPushButton[variant="chip"] {{ font-size:{max(FONT_SIZE_PT-1,8)}pt; padding:2px 8px; border:1px solid {btn_border}; border-radius:12px; background:{chip_bg}; color:{text_col}; }}

        /* View toggle checked */
        QPushButton#viewToggle:checked {{ background:#15803D; color:#FFFFFF; border-color:#15803D; }}

        /* === Titles (Table Header) === */
        QHeaderView::section {{ background:{header_bg}; color:{header_text}; border:0px; border-bottom:1px solid {border_col}; padding:6px; font-weight:600; }}

        /* === Menus === */
        QMenuBar {{ background:{header_bg}; color:{header_text}; }}
        QMenuBar::item {{ background:transparent; padding:4px 8px; }}
        QMenuBar::item:selected {{ background:{chip_hover}; color:{header_text}; border-radius:6px; }}
        QMenu {{ background:{header_bg}; color:{header_text}; border:1px solid {border_col}; }}
        QMenu::item:selected {{ background:{chip_hover}; color:{header_text}; }}

        QScrollBar:vertical, QScrollBar:horizontal {{ background:transparent; border:none; margin:0; }}
        QScrollBar::handle {{ background:#64748B; border-radius:6px; }}
        QScrollBar::handle:hover {{ background:#94A3B8; }}

        *:focus {{ outline:2px solid {primary}33; outline-offset:1px; }}
        """
        self.setStyleSheet(qss)

        pal = self.palette()
        if light_mode:
            pal.setColor(QPalette.Window, QColor("#F5F7FA"))
            pal.setColor(QPalette.WindowText, QColor("#111827"))
            pal.setColor(QPalette.Base, QColor("#FFFFFF"))
            pal.setColor(QPalette.Text, QColor("#111827"))
            pal.setColor(QPalette.Button, QColor("#FFFFFF"))
            pal.setColor(QPalette.ButtonText, QColor("#111827"))
            pal.setColor(QPalette.Highlight, QColor(BRAND_PRIMARY))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        else:
            pal.setColor(QPalette.Window, QColor("#0B1220"))
            pal.setColor(QPalette.WindowText, QColor("#FFFFFF"))
            pal.setColor(QPalette.Base, QColor("#0B1220"))
            pal.setColor(QPalette.Text, QColor("#FFFFFF"))
            pal.setColor(QPalette.Button, QColor("#111827"))
            pal.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
            pal.setColor(QPalette.Highlight, QColor("#60A5FA"))
            pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(pal)

# --- main entry point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
