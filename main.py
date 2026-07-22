#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

# 高分屏清晰渲染（必须在 QApplication 创建前设置）
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)

from app.main_window import MainWindow
from app.theme import Theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("星迹 StarTrail")
    app.setApplicationVersion("1.1.0")
    app.setStyle("Fusion")

    Theme.apply_dark_palette(app)

    app.setStyleSheet(f"""
        QToolTip {{
            background: {Theme.BG_CARD};
            color: {Theme.TEXT_PRIMARY};
            border: 1px solid {Theme.DIVIDER};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        QLabel {{ background: transparent; }}
        QFrame {{ background: transparent; }}
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
