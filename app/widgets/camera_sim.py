import math

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFrame, QSpinBox, QSlider, QPushButton, QDoubleSpinBox)
from PySide6.QtCore import Qt, Signal

from app.theme import Theme


class CameraPanel(QFrame):
    params_changed = Signal(dict)

    FULL_FRAME = (36.0, 24.0)
    APS_C = (23.5, 15.6)
    M4_3 = (17.3, 13.0)
    ONE_INCH = (13.2, 8.8)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(Theme.card_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel("📷 摄影器材模拟")
        title.setFont(Theme.font(13, bold=True))
        title.setStyleSheet(f"color: {Theme.STAR_GOLD};")
        layout.addWidget(title)

        presets = QHBoxLayout()
        presets.setSpacing(4)
        for label, sw, sh in [("全画幅", 36, 24), ("APS-C", 23.5, 15.6), ("M4/3", 17.3, 13), ("1英寸", 13.2, 8.8)]:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                    border: 1px solid {Theme.DIVIDER}; border-radius: 4px;
                    padding: 2px 8px; font-size: 10px;
                }}
                QPushButton:hover {{ border: 1px solid {Theme.STAR_GOLD}; color: {Theme.STAR_GOLD}; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, w=sw, h=sh: self._set_sensor(w, h))
            presets.addWidget(btn)
        layout.addLayout(presets)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        sw_lbl = QLabel("传感器宽")
        sw_lbl.setFont(Theme.caption())
        sw_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        row1.addWidget(sw_lbl)

        self.sensor_w = QDoubleSpinBox()
        self.sensor_w.setRange(1, 100)
        self.sensor_w.setValue(36.0)
        self.sensor_w.setSuffix(" mm")
        self.sensor_w.setStyleSheet(self._spin_style())
        row1.addWidget(self.sensor_w)

        sh_lbl = QLabel("高")
        sh_lbl.setFont(Theme.caption())
        sh_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        row1.addWidget(sh_lbl)

        self.sensor_h = QDoubleSpinBox()
        self.sensor_h.setRange(1, 100)
        self.sensor_h.setValue(24.0)
        self.sensor_h.setSuffix(" mm")
        self.sensor_h.setStyleSheet(self._spin_style())
        row1.addWidget(self.sensor_h)

        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        fl_lbl = QLabel("焦距")
        fl_lbl.setFont(Theme.caption())
        fl_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        row2.addWidget(fl_lbl)

        self.focal = QSpinBox()
        self.focal.setRange(8, 2000)
        self.focal.setValue(50)
        self.focal.setSuffix(" mm")
        self.focal.setStyleSheet(self._spin_style())
        row2.addWidget(self.focal)

        rot_lbl = QLabel("旋转")
        rot_lbl.setFont(Theme.caption())
        rot_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        row2.addWidget(rot_lbl)

        self.rotation = QSlider(Qt.Orientation.Horizontal)
        self.rotation.setRange(0, 360)
        self.rotation.setValue(0)
        self.rotation.setFixedWidth(100)
        self.rotation.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {Theme.DIVIDER}; height: 4px; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {Theme.ACCENT}; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px;
            }}
        """)
        row2.addWidget(self.rotation)

        self.rot_val = QLabel("0°")
        self.rot_val.setFont(Theme.caption())
        self.rot_val.setStyleSheet(f"color: {Theme.ACCENT};")
        self.rot_val.setFixedWidth(28)
        row2.addWidget(self.rot_val)

        layout.addLayout(row2)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self.fov_label = QLabel("FOV: --×--")
        self.fov_label.setFont(Theme.font(11, bold=True))
        self.fov_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY};")
        info_row.addWidget(self.fov_label)

        self.res_label = QLabel("--\"/pixel")
        self.res_label.setFont(Theme.caption())
        self.res_label.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        info_row.addWidget(self.res_label)

        info_row.addStretch()

        self.toggle_btn = QPushButton("显示参考框")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setFixedHeight(24)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_SECONDARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 4px;
                padding: 2px 10px; font-size: 10px;
            }}
            QPushButton:checked {{
                background: {Theme.DANGER}30; color: {Theme.DANGER};
                border: 1px solid {Theme.DANGER};
            }}
            QPushButton:hover {{ border: 1px solid {Theme.ACCENT}; }}
        """)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        info_row.addWidget(self.toggle_btn)

        layout.addLayout(info_row)

        self.sensor_w.valueChanged.connect(self._emit_params)
        self.sensor_h.valueChanged.connect(self._emit_params)
        self.focal.valueChanged.connect(self._emit_params)
        self.rotation.valueChanged.connect(self._on_rotation)
        self.toggle_btn.toggled.connect(self._emit_params)

    def _spin_style(self):
        return f"""
            QDoubleSpinBox, QSpinBox {{
                background: {Theme.BG_CARD}; color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.DIVIDER}; border-radius: 4px;
                padding: 3px 6px; font-size: 11px;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{ border: 1px solid {Theme.ACCENT}; }}
        """

    def _set_sensor(self, w, h):
        self.sensor_w.setValue(w)
        self.sensor_h.setValue(h)

    def _on_rotation(self, val):
        self.rot_val.setText(f"{val}°")
        self._emit_params()

    def _emit_params(self):
        sw = self.sensor_w.value()
        sh = self.sensor_h.value()
        fl = self.focal.value()
        rot = self.rotation.value()
        show = self.toggle_btn.isChecked()

        fov_h = 2 * math.degrees(math.atan(sw / (2 * fl)))
        fov_v = 2 * math.degrees(math.atan(sh / (2 * fl)))
        fov_h_arcmin = fov_h * 60
        fov_h_arcsec = fov_h * 3600

        sw_px = int(sw * 100)
        sh_px = int(sh * 100)
        arcsec_per_px = fov_h_arcsec / sw_px if sw_px else 0

        self.fov_label.setText(f"FOV: {fov_h:.2f}°×{fov_v:.2f}°  ({fov_h_arcmin:.0f}′×{fov_v*60:.0f}′)")
        self.res_label.setText(f"{arcsec_per_px:.2f}\"/px @ {sw_px}×{sh_px}px" if arcsec_per_px else "")

        self.params_changed.emit({
            "fov_h_deg": fov_h,
            "fov_v_deg": fov_v,
            "rotation": rot,
            "show": show,
        })
