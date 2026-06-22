from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect

class Theme:
    BG_PRIMARY = "#080C1A"
    BG_SECONDARY = "#0E1328"
    BG_CARD = "#151B35"
    BG_CARD_GLASS = "rgba(21, 27, 53, 0.75)"
    BG_SIDEBAR = "#0B0F20"
    GLASS_BORDER = "rgba(108, 140, 255, 0.12)"
    ACCENT = "#6C8CFF"
    ACCENT_DIM = "rgba(108, 140, 255, 0.15)"
    ACCENT_DEEP = "#4A6FD4"
    STAR_GOLD = "#FFD700"
    STAR_WARM = "#FFB347"
    STAR_COOL = "#A8C8FF"
    STAR_RED = "#FF6B6B"
    TEXT_PRIMARY = "#E8EAF0"
    TEXT_SECONDARY = "#8B8FA8"
    TEXT_MUTED = "#555A78"
    SUCCESS = "#4CAF50"
    WARNING = "#FFA726"
    DANGER = "#EF5350"
    DIVIDER = "#1E2545"
    SURFACE_GLOW = "rgba(108, 140, 255, 0.05)"
    RA_DEC_LINE = "rgba(108, 140, 255, 0.15)"

    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_MONO = "Consolas"

    CORNER_RADIUS_SM = 6
    CORNER_RADIUS_MD = 12
    CORNER_RADIUS_LG = 16

    @classmethod
    def font(cls, size=10, bold=False, mono=False):
        return QFont(cls.FONT_FAMILY_MONO if mono else cls.FONT_FAMILY, size, QFont.Weight.Bold if bold else QFont.Weight.Normal)

    @classmethod
    def h1(cls):
        return cls.font(22, bold=True)

    @classmethod
    def h2(cls):
        return cls.font(16, bold=True)

    @classmethod
    def h3(cls):
        return cls.font(14, bold=True)

    @classmethod
    def body(cls):
        return cls.font(12)

    @classmethod
    def caption(cls):
        return cls.font(9)

    @classmethod
    def shadow(cls, radius=12, color=QColor(0, 0, 0, 80)):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(radius)
        shadow.setColor(color)
        shadow.setOffset(0, 2)
        return shadow

    @classmethod
    def glass_style(cls, radius=CORNER_RADIUS_MD):
        return f"""
            QFrame#glass {{
                background: {cls.BG_CARD_GLASS};
                border: 1px solid {cls.GLASS_BORDER};
                border-radius: {radius}px;
            }}
        """

    @classmethod
    def card_style(cls):
        return f"""
            QFrame#card {{
                background-color: {cls.BG_CARD};
                border: 1px solid {cls.DIVIDER};
                border-radius: {cls.CORNER_RADIUS_MD}px;
            }}
            QFrame#card:hover {{
                border: 1px solid {cls.ACCENT};
            }}
        """

    @classmethod
    def nav_button_style(cls, active=False):
        bg = cls.ACCENT if active else "transparent"
        txt = "white" if active else cls.TEXT_SECONDARY
        return f"""
            QPushButton#navBtn {{
                background: {bg};
                color: {txt};
                border: none;
                border-radius: {cls.CORNER_RADIUS_SM}px;
                padding: 10px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: {'bold' if active else 'normal'};
            }}
            QPushButton#navBtn:hover {{
                background: {cls.ACCENT if active else cls.ACCENT_DIM};
                color: {'white' if active else cls.TEXT_PRIMARY};
            }}
        """

    @classmethod
    def combo_style(cls):
        return f"""
            QComboBox {{
                background: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.DIVIDER};
                border-radius: {cls.CORNER_RADIUS_SM}px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border: 1px solid {cls.ACCENT}; }}
            QComboBox::drop-down {{ border: none; padding-right: 8px; }}
            QComboBox QAbstractItemView {{
                background: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.DIVIDER};
                selection-background-color: {cls.ACCENT};
                selection-color: white;
            }}
        """

    @classmethod
    def line_edit_style(cls):
        return f"""
            QLineEdit {{
                background: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.DIVIDER};
                border-radius: {cls.CORNER_RADIUS_SM}px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {cls.ACCENT}; }}
        """

    @classmethod
    def scroll_style(cls):
        return f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {cls.BG_PRIMARY};
                width: 6px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.BG_CARD};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cls.ACCENT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ height: 0; }}
        """

    @classmethod
    def apply_dark_palette(cls, app):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(cls.BG_PRIMARY))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(cls.BG_SECONDARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(cls.BG_CARD))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Text, QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(cls.ACCENT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Qt.GlobalColor.white))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(cls.BG_CARD))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(cls.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Link, QColor(cls.ACCENT))
        app.setPalette(palette)
