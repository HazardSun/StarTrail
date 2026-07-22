from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect


class Theme:
    # ════════════════════════════════════════
    #  背景 — 深空紫蓝渐变基底
    # ════════════════════════════════════════
    BG_PRIMARY = "#070B14"                          # 最底层深空黑
    BG_SECONDARY = "#0D1224"                        # 次级 / 输入框底
    BG_CARD = "rgba(16, 23, 48, 0.72)"            # 半透明卡片底
    BG_CARD_GLASS = "rgba(19, 27, 56, 0.66)"      # 玻璃态面板
    BG_SIDEBAR = "#0A0E1C"                         # 侧栏
    BG_SURFACE = "rgba(255, 255, 255, 0.022)"     # 分区表面
    BG_ELEVATED = "rgba(255, 255, 255, 0.042)"    # 浮起层 / hover
    BG_GRADIENT = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:1,"
        " stop:0 #070B14, stop:0.5 #0B1022, stop:1 #100E26)"
    )
    BG_GRADIENT_RADIAL = (
        "qradialgradient(cx:0.5, cy:0.3, radius:0.8,"
        " stop:0 #111830, stop:1 #070B14)"
    )

    # ════════════════════════════════════════
    #  边框 — 微妙发光
    # ════════════════════════════════════════
    DIVIDER = "rgba(255, 255, 255, 0.055)"
    GLASS_BORDER = "rgba(120, 150, 255, 0.09)"
    CARD_BORDER = "rgba(255, 255, 255, 0.065)"
    CARD_BORDER_HOVER = "rgba(120, 150, 255, 0.18)"
    INPUT_BORDER = "rgba(255, 255, 255, 0.08)"
    INPUT_BORDER_FOCUS = "rgba(107, 142, 255, 0.5)"

    # ════════════════════════════════════════
    #  强调色 — 亮蓝紫系
    # ════════════════════════════════════════
    ACCENT = "#6B8EFF"                              # 主强调蓝
    ACCENT_DIM = "rgba(107, 142, 255, 0.11)"       # 弱强调填充
    ACCENT_GLOW = "rgba(107, 142, 255, 0.16)"      # 发光晕
    ACCENT_DEEP = "#5070D8"                         # 深强调 / 按下态
    ACCENT_PURPLE = "#9B7CF7"                       # 紫辅助强调
    ACCENT_CYAN = "#38BDF8"                         # 青辅助

    # ════════════════════════════════════════
    #  文字 — 提亮 + 层级分明
    # ════════════════════════════════════════
    TEXT_PRIMARY = "#EEF0F4"                        # 主文字
    TEXT_SECONDARY = "#B4BCD0"                      # 次要
    TEXT_MUTED = "#6E7790"                          # 弱化
    TEXT_HEADING = "#FFFFFF"                        # 标题纯白
    TEXT_ON_ACCENT = "#FFFFFF"                      # 强调色上的文字
    TEXT_LINK = "#6B8EFF"                           # 链接

    # ════════════════════════════════════════
    #  功能色
    # ════════════════════════════════════════
    SUCCESS = "#34D399"                             # 成功 / 优秀
    WARNING = "#FBBF24"                             # 警告 / 一般
    DANGER = "#F87171"                              # 危险 / 差
    INFO = "#60A5FA"                                # 信息 / 良好

    # ════════════════════════════════════════
    #  观星指数分级色（新增）
    # ════════════════════════════════════════
    SG_EXCELLENT = "#22C55E"                        # 优秀 — 绿
    SG_GOOD = "#84CC16"                              # 良好 — 黄绿
    SG_FAIR = "#F59E0B"                              # 一般 — 橙
    SG_POOR = "#EF4444"                              # 差 — 红

    @classmethod
    def sg_color(cls, level):
        """根据等级 0-3 返回观星索引颜色。"""
        return [cls.SG_POOR, cls.SG_FAIR, cls.SG_GOOD, cls.SG_EXCELLENT][max(0, min(3, level))]

    @classmethod
    def sg_color_qcolor(cls, level):
        return QColor(cls.sg_color(level))

    @staticmethod
    def qcolor(value, alpha=None):
        """安全地把主题色值转为 QColor。

        - 支持 hex（"#6B8EFF"）与函数式 rgba()/rgb() 字符串
          （QColor 本身无法解析 "rgba(...)"，会返回 invalid 黑，故需手动解析）
        - alpha 可覆盖或补充透明度（0-255）
        """
        s = str(value).strip()
        a = alpha
        if s.startswith("rgba("):
            parts = s[5:-1].split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            if a is None:
                a = int(float(parts[3]) * 255)
            return QColor(r, g, b, max(0, min(255, int(a))))
        if s.startswith("rgb("):
            parts = s[4:-1].split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            return QColor(r, g, b, a if a is not None else 255)
        c = QColor(s)
        if a is not None:
            c.setAlpha(max(0, min(255, int(a))))
        return c

    # ════════════════════════════════════════
    #  恒星颜色（保留）
    # ════════════════════════════════════════
    STAR_GOLD = "#FFD700"
    STAR_WARM = "#FFB347"
    STAR_COOL = "#A8C8FF"
    STAR_RED = "#FF6B6B"

    # ════════════════════════════════════════
    #  发光效果
    # ════════════════════════════════════════
    SURFACE_GLOW = "rgba(107, 142, 255, 0.05)"
    RA_DEC_LINE = "rgba(107, 142, 255, 0.11)"

    # ════════════════════════════════════════
    #  圆角（加大）
    # ════════════════════════════════════════
    CORNER_RADIUS_SM = 8                            # 按钮 / 输入框
    CORNER_RADIUS_MD = 14                           # 卡片
    CORNER_RADIUS_LG = 20                           # 大面板

    # ════════════════════════════════════════
    #  字体
    # ════════════════════════════════════════
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_FAMILY_MONO = "Consolas"

    # ── 字体工厂 ──────────────────────────────

    @classmethod
    def font(cls, size=10, bold=False, mono=False):
        return QFont(
            cls.FONT_FAMILY_MONO if mono else cls.FONT_FAMILY,
            size,
            QFont.Weight.Bold if bold else QFont.Weight.Normal,
        )

    @classmethod
    def h1(cls):       return cls.font(24, bold=True)     # 页面大标题
    @classmethod
    def h2(cls):       return cls.font(17, bold=True)     # 卡片标题
    @classmethod
    def h3(cls):       return cls.font(14, bold=True)     # 小标题
    @classmethod
    def body(cls):     return cls.font(13)                 # 正文
    @classmethod
    def caption(cls):  return cls.font(11)                 # 标签 / 注释
    @classmethod
    def tiny(cls):     return cls.font(9)                  # 微注

    @classmethod
    def big_number(cls):  return cls.font(32, bold=True)   # 数据大数字
    @classmethod
    def metric(cls):     return cls.font(24, bold=True)   # 指标值

    # ── 阴影 ──────────────────────────────────

    @classmethod
    def shadow(cls, radius=16, color=None):
        if color is None:
            color = QColor(0, 0, 0, 70)
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(radius)
        s.setColor(color)
        s.setOffset(0, 3)
        return s

    @classmethod
    def glow_shadow(cls, color_str=ACCENT, radius=20):
        c = QColor(color_str)
        c.setAlpha(40)
        return cls.shadow(radius, c)

    # ════════════════════════════════════════
    #  全局样式表
    # ════════════════════════════════════════

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
        r = cls.CORNER_RADIUS_MD
        return f"""
            QFrame#card {{
                background-color: {cls.BG_CARD};
                border: 1px solid {cls.CARD_BORDER};
                border-radius: {r}px;
            }}
            QFrame#card:hover {{
                border: 1px solid {cls.CARD_BORDER_HOVER};
                background-color: {cls.BG_ELEVATED};
            }}
        """

    @classmethod
    def nav_button_style(cls, active=False):
        bg = cls.ACCENT if active else "transparent"
        txt = "#FFFFFF" if active else cls.TEXT_SECONDARY
        active_bg_hover = cls.ACCENT_DEEP
        inactive_bg_hover = cls.ACCENT_DIM
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
                background: {active_bg_hover if active else inactive_bg_hover};
                color: {'white' if active else cls.TEXT_PRIMARY};
            }}
        """

    @classmethod
    def combo_style(cls):
        r = cls.CORNER_RADIUS_SM
        return f"""
            QComboBox {{
                background: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {r}px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border: 1px solid {cls.CARD_BORDER_HOVER}; }}
            QComboBox:focus {{ border: 1px solid {cls.INPUT_BORDER_FOCUS}; }}
            QComboBox::drop-down {{ border: none; padding-right: 8px; }}
            QComboBox QAbstractItemView {{
                background: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.CARD_BORDER};
                selection-background-color: {cls.ACCENT_DIM};
                selection-color: {cls.TEXT_PRIMARY};
                border-radius: {r}px;
            }}
        """

    @classmethod
    def line_edit_style(cls):
        r = cls.CORNER_RADIUS_SM
        return f"""
            QLineEdit {{
                background: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {r}px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {cls.INPUT_BORDER_FOCUS}; }}
        """

    @classmethod
    def button_primary_style(cls):
        r = cls.CORNER_RADIUS_SM
        return f"""
            QPushButton[primary="true"] {{
                background: {cls.ACCENT};
                color: white;
                border: none;
                border-radius: {r}px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton[primary="true"]:hover {{
                background: {cls.ACCENT_DEEP};
            }}
            QPushButton[primary="true"]:pressed {{
                background: #4060C0;
            }}
        """

    @classmethod
    def button_ghost_style(cls):
        r = cls.CORNER_RADIUS_SM
        return f"""
            QPushButton[ghost="true"] {{
                background: transparent;
                color: {cls.ACCENT};
                border: 1px solid {cls.ACCENT_DIM};
                border-radius: {r}px;
                padding: 8px 18px;
                font-size: 13px;
            }}
            QPushButton[ghost="true"]:hover {{
                background: {cls.ACCENT_DIM};
                border-color: {cls.ACCENT};
            }}
        """

    @classmethod
    def scroll_style(cls):
        return f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                border: none;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(107, 142, 255, 0.18);
                border-radius: 4px;
                min-height: 36px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(107, 142, 255, 0.35);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ height: 0; }}

            /* Horizontal scrollbar */
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                border: none;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(107, 142, 255, 0.18);
                border-radius: 4px;
                min-width: 36px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(107, 142, 255, 0.35);
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{ width: 0; }}
        """

    @classmethod
    def tooltip_style(cls):
        return f"""
            QToolTip {{
                background: {cls.BG_CARD_GLASS};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.GLASS_BORDER};
                border-radius: {cls.CORNER_RADIUS_SM}px;
                padding: 6px 10px;
                font-size: 12px;
            }}
        """

    # ════════════════════════════════════════
    #  Palette
    # ════════════════════════════════════════

    @classmethod
    def apply_dark_palette(cls, app):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(cls.BG_PRIMARY))
        p.setColor(QPalette.ColorRole.WindowText, QColor(cls.TEXT_PRIMARY))
        p.setColor(QPalette.ColorRole.Base, QColor(cls.BG_SECONDARY))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor("#0E1528"))
        p.setColor(QPalette.ColorRole.Button, QColor(cls.BG_CARD))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(cls.TEXT_PRIMARY))
        p.setColor(QPalette.ColorRole.Text, QColor(cls.TEXT_PRIMARY))
        p.setColor(QPalette.ColorRole.Highlight, QColor(cls.ACCENT))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(Qt.GlobalColor.white))
        p.setColor(QPalette.ColorRole.ToolTipBase, QColor(19, 27, 56, 220))
        p.setColor(QPalette.ColorRole.ToolTipText, QColor(cls.TEXT_PRIMARY))
        p.setColor(QPalette.ColorRole.Link, QColor(cls.ACCENT))
        app.setPalette(p)
