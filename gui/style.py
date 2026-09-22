from pathlib import Path

_CHEVRON = Path(__file__).resolve().with_name("chevron.png").as_posix()

STYLE_SHEET = """
QMainWindow, QDialog, QWidget#page, QWidget#scrollBody {
    background-color: #fafafa;
    color: #09090b;
}

QWidget {
    font-family: "PingFang SC", "SF Pro Text", ".AppleSystemUIFont", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
    color: #09090b;
}

QLabel {
    background: transparent;
    padding: 0;
    color: #09090b;
}

QLabel#muted, QLabel#linkLabel {
    color: #71717a;
    font-size: 12px;
}

QLabel#cardTitle {
    font-size: 14px;
    font-weight: 600;
    color: #09090b;
}

QLabel#metricValue {
    font-size: 18px;
    font-weight: 600;
    color: #09090b;
}

QLabel#fieldLabel {
    font-size: 13px;
    font-weight: 500;
    color: #09090b;
}

QLabel#badgeOk, QLabel#badgeMuted, QLabel#badgeDanger {
    border-radius: 6px;
    padding: 1px 8px;
    font-size: 12px;
    font-weight: 500;
    min-height: 20px;
    max-height: 22px;
}

QLabel#badgeOk {
    color: #166534;
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
}

QLabel#badgeMuted {
    color: #3f3f46;
    background-color: #f4f4f5;
    border: 1px solid #e4e4e7;
}

QLabel#badgeDanger {
    color: #991b1b;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
}

QLabel#probeOk {
    color: #166534;
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    padding: 10px 12px;
}

QLabel#probeBad {
    color: #991b1b;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    padding: 10px 12px;
}

QLabel#probeIdle {
    color: #71717a;
    background: transparent;
    padding: 2px 0;
}

QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 12px;
}

QFrame#separator {
    background-color: #e4e4e7;
    border: none;
    max-height: 1px;
    min-height: 1px;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #09090b;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #18181b;
    selection-color: #fafafa;
    min-height: 20px;
}

QLineEdit:hover, QTextEdit:hover {
    border-color: #d4d4d8;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #18181b;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #f4f4f5;
    color: #a1a1aa;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 8px 12px;
    padding-right: 28px;
    min-height: 20px;
    color: #09090b;
}

QComboBox:hover {
    border-color: #d4d4d8;
}

QComboBox:focus, QComboBox:on {
    border: 1px solid #18181b;
}

QComboBox::drop-down {
    border: none;
    background: transparent;
    width: 28px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}

QComboBox::down-arrow {
    image: url(CHEVRON_ICON);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #09090b;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 4px;
    outline: 0;
    selection-background-color: #f4f4f5;
    selection-color: #09090b;
}

QComboBox QAbstractItemView::item {
    border: none;
    outline: none;
    border-radius: 6px;
    padding: 8px 10px;
    min-height: 22px;
    color: #09090b;
    background: transparent;
}

QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {
    background-color: #f4f4f5;
    color: #09090b;
    border: none;
}

QPushButton {
    background-color: #ffffff;
    color: #18181b;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 20px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #f4f4f5;
}

QPushButton:pressed {
    background-color: #e4e4e7;
}

QPushButton:disabled {
    background-color: #fafafa;
    color: #a1a1aa;
    border-color: #e4e4e7;
}

QPushButton#primaryButton {
    background-color: #18181b;
    color: #fafafa;
    border: 1px solid #18181b;
}

QPushButton#primaryButton:hover {
    background-color: #27272a;
    border-color: #27272a;
}

QPushButton#primaryButton:pressed {
    background-color: #09090b;
}

QPushButton#primaryButton:disabled {
    background-color: #e4e4e7;
    color: #a1a1aa;
    border-color: #e4e4e7;
}

QPushButton#dangerButton {
    background-color: #ffffff;
    color: #dc2626;
    border: 1px solid #fecaca;
}

QPushButton#dangerButton:hover {
    background-color: #fef2f2;
}

QPushButton#dangerButton:pressed {
    background-color: #fee2e2;
}

QPushButton#dangerButton:disabled {
    color: #fca5a5;
    border-color: #fee2e2;
    background-color: #ffffff;
}

QTabWidget {
    background: #ffffff;
}

QTabWidget::pane {
    border: none;
    border-top: 1px solid #e4e4e7;
    background: #fafafa;
    top: 0px;
}

QTabWidget::tab-bar {
    left: 8px;
}

QTabBar {
    background: #ffffff;
    border: none;
}

QTabBar::tab {
    background: #ffffff;
    color: #71717a;
    border: none;
    border-bottom: 3px solid transparent;
    padding: 12px 12px;
    margin: 2px 2px 0 0;
    font-size: 14px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #09090b;
    background: #ffffff;
    border: none;
    border-bottom: 3px solid #18181b;
}

QTabBar::tab:!selected:hover {
    color: #18181b;
    background: #f4f4f5;
}

QTextEdit#log_text {
    background-color: #09090b;
    color: #fafafa;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 12px;
    font-family: "Menlo";
    font-size: 12px;
}

QFrame#alert {
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 12px;
}

QLabel#alertBody {
    color: #3f3f46;
    font-size: 13px;
}

QPushButton#ghostButton {
    background: transparent;
    border: none;
    color: #71717a;
    padding: 4px 8px;
    min-height: 0px;
}

QPushButton#ghostButton:hover {
    background-color: #f4f4f5;
    color: #18181b;
}

QStackedWidget, QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background: #d4d4d8;
    border-radius: 4px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #a1a1aa;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background: #d4d4d8;
    border-radius: 4px;
    min-width: 28px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0px;
}

QWidget#toastHost {
    background: transparent;
}

QFrame#toast {
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 10px;
}

QCheckBox {
    spacing: 8px;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #d4d4d8;
    border-radius: 4px;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #18181b;
    border-color: #18181b;
}

QFrame#toastDot {
    background-color: #16a34a;
    border: none;
    border-radius: 4px;
}

QLabel#toastText {
    color: #09090b;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}

QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #09090b;
}

QToolTip {
    background-color: #18181b;
    color: #fafafa;
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
}
""".replace("CHEVRON_ICON", _CHEVRON)
