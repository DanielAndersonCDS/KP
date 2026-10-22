"""
Kessoku Paint - a small Photoshop-style image editor.

PySide6 UI, Catppuccin themes (Mocha by default), JetBrains Mono everywhere.

Tools : Hand, Crop (rect / Shift = square), Magic Wand, Brush, Eraser,
        Bucket Fill, Text (with instant drop shadow), Eyedropper
Image : Drop Shadow, Hue/Saturation (live preview), Upscale, Cut Out / Crop to selection
UI    : Catppuccin Mocha / Macchiato / Frappe / Latte  (View > Theme)

Run:  pip install -r requirements.txt && python kessoku_paint.py
"""
import sys
from pathlib import Path
from string import Template

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from scipy import ndimage
from PySide6.QtCore import QPoint, QRect, QRectF, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QActionGroup, QBrush, QColor, QFont, QFontDatabase,
                           QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap,
                           QShortcut, QTextOption)
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFontComboBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSpinBox,
                               QToolBar, QVBoxLayout, QWidget)

BASE_DIR = Path(__file__).resolve().parent
FONT = "JetBrains Mono"
ARGB = QImage.Format.Format_ARGB32_Premultiplied

# --------------------------------------------------------------------------- themes
PALETTES = {
    "Mocha": dict(rosewater="f5e0dc", mauve="cba6f7", red="f38ba8", peach="fab387", green="a6e3a1",
                  blue="89b4fa", lavender="b4befe", text="cdd6f4", subtext0="a6adc8",
                  overlay0="6c7086", surface2="585b70", surface1="45475a", surface0="313244",
                  base="1e1e2e", mantle="181825", crust="11111b"),
    "Macchiato": dict(rosewater="f4dbd6", mauve="c6a0f6", red="ed8796", peach="f5a97f", green="a6da95",
                      blue="8aadf4", lavender="b7bdf8", text="cad3f5", subtext0="a5adcb",
                      overlay0="6e738d", surface2="5b6078", surface1="494d64", surface0="363a4f",
                      base="24273a", mantle="1e2030", crust="181926"),
    "Frappe": dict(rosewater="f2d5cf", mauve="ca9ee6", red="e78284", peach="ef9f76", green="a6d189",
                   blue="8caaee", lavender="babbf1", text="c6d0f5", subtext0="a5adce",
                   overlay0="737994", surface2="626880", surface1="51576d", surface0="414559",
                   base="303446", mantle="292c3c", crust="232634"),
    "Latte": dict(rosewater="dc8a78", mauve="8839ef", red="d20f39", peach="fe640b", green="40a02b",
                  blue="1e66f5", lavender="7287fd", text="4c4f69", subtext0="6c6f85",
                  overlay0="9ca0b0", surface2="acb0be", surface1="bcc0cc", surface0="ccd0da",
                  base="eff1f5", mantle="e6e9ef", crust="dce0e8"),
}
PALETTES = {k: {n: "#" + v for n, v in p.items()} for k, p in PALETTES.items()}

QSS = Template("""
QWidget { background-color: $base; color: $text; font-family: "$font", monospace; }
QMainWindow, QDialog { background: $base; }
QLabel { background: transparent; }
QMenuBar { background: $mantle; }
QMenuBar::item { background: transparent; padding: 5px 10px; }
QMenuBar::item:selected { background: $surface0; border-radius: 4px; }
QMenu { background: $mantle; border: 1px solid $surface1; padding: 4px; }
QMenu::item { padding: 5px 24px; border-radius: 4px; }
QMenu::item:selected { background: $surface0; }
QMenu::separator { height: 1px; background: $surface1; margin: 4px 8px; }
QToolBar { background: $mantle; border: none; spacing: 4px; padding: 4px; }
QToolBar QLabel { padding: 0 2px 0 8px; color: $subtext0; }
QToolButton { background: transparent; border-radius: 6px; padding: 7px 10px; color: $text; }
QToolButton:hover { background: $surface0; }
QToolButton:checked { background: $mauve; color: $crust; }
QPushButton { background: $surface0; border: 1px solid $surface1; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: $surface1; }
QPushButton:default { border-color: $mauve; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background: $surface0; border: 1px solid $surface1; border-radius: 6px; padding: 4px 6px;
    selection-background-color: $mauve; selection-color: $crust; }
QComboBox QAbstractItemView { background: $mantle; selection-background-color: $surface1; }
QSlider::groove:horizontal { height: 4px; background: $surface1; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $mauve; border-radius: 2px; }
QSlider::handle:horizontal { background: $lavender; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }
QScrollArea#viewArea, QScrollArea#viewArea > QWidget { background: $crust; border: none; }
QScrollBar:vertical { background: $mantle; width: 12px; }
QScrollBar:horizontal { background: $mantle; height: 12px; }
QScrollBar::handle:vertical { background: $surface1; border-radius: 6px; min-height: 24px; }
QScrollBar::handle:horizontal { background: $surface1; border-radius: 6px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QStatusBar { background: $mantle; color: $subtext0; }
QStatusBar QLabel { padding: 0 8px; }
QGroupBox { border: 1px solid $surface1; border-radius: 6px; margin-top: 12px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: $mauve; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid $overlay0; border-radius: 3px; background: $surface0; }
QCheckBox::indicator:checked { background: $mauve; border-color: $mauve; }
QToolTip { background: $surface0; color: $text; border: 1px solid $surface1; }
""")


# --------------------------------------------------------------------------- helpers
def qimage_to_pil(q: QImage) -> Image.Image:
    q = q.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombuffer("RGBA", (q.width(), q.height()), bytes(q.constBits()),
                            "raw", "RGBA", q.bytesPerLine(), 1).copy()


def pil_to_qimage(p: Image.Image) -> QImage:
    p = p.convert("RGBA")
    w, h = p.size
    q = QImage(p.tobytes("raw", "RGBA"), w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
    return q.convertToFormat(ARGB)


def mask_to_qimage(mask: np.ndarray) -> QImage:
    h, w = mask.shape
    a = np.zeros((h, w, 4), np.uint8)
    a[mask] = 255
    return QImage(a.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy().convertToFormat(ARGB)


def mask_to_pil(mask: np.ndarray) -> Image.Image:
    return Image.fromarray((mask * 255).astype(np.uint8))


def selection_overlay(mask: np.ndarray, fill_hex: str) -> QImage:
    """Tinted fill + black/white dashed outline, so it reads on any image."""
    h, w = mask.shape
    a = np.zeros((h, w, 4), np.uint8)
    c = QColor(fill_hex)
    a[mask] = (c.red(), c.green(), c.blue(), 60)
    edge = mask & ~ndimage.binary_erosion(mask, border_value=0)
    ys, xs = np.nonzero(edge)
    on = ((xs + ys) // 3) % 2 == 0
    a[ys[on], xs[on]] = (0, 0, 0, 255)
    a[ys[~on], xs[~on]] = (255, 255, 255, 255)
    return QImage(a.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy().convertToFormat(ARGB)


def flood_mask(arr: np.ndarray, x: int, y: int, tol: int, contiguous: bool) -> np.ndarray:
    ref = arr[y, x].astype(np.int16)
    close = np.abs(arr.astype(np.int16) - ref).max(axis=2) <= tol
    if not contiguous:
        return close
    labels, _ = ndimage.label(close)
    return labels == labels[y, x]


def make_shadow(size, mask: Image.Image, dx, dy, blur, opacity, rgb) -> Image.Image:
    m = Image.new("L", size, 0)
    m.paste(mask, (dx, dy))
    if blur > 0:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    m = m.point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", size, tuple(rgb) + (255,))
    sh.putalpha(m)
    return sh


def load_fonts():
    for f in (BASE_DIR / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))


def rgb_of(c: QColor):
    return (c.red(), c.green(), c.blue())


# --------------------------------------------------------------------------- widgets
class ColorButton(QPushButton):
    changed = Signal(QColor)

    def __init__(self, color):
        super().__init__()
        self._c = QColor(color)
        self.setFixedSize(36, 26)
        self.clicked.connect(self._pick)
        self._paint()

    def color(self):
        return QColor(self._c)

    def set_color(self, c):
        self._c = QColor(c)
        self._paint()

    def _paint(self):
        self.setStyleSheet(f"QPushButton{{background:{self._c.name()};"
                           f"border:2px solid #7f849c;border-radius:6px;}}")

    def _pick(self):
        c = QColorDialog.getColor(self._c, self, "Pick a color", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.set_color(c)
            self.changed.emit(c)


class SliderDialog(QDialog):
    """Generic live-preview dialog: a column of labelled sliders (+ optional colour)."""
    changed = Signal()

    def __init__(self, title, specs, parent, color=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        self.sliders, self.labels = [], []
        self.timer = QTimer(self, singleShot=True, interval=60)
        self.timer.timeout.connect(self.changed.emit)
        for label, lo, hi, default in specs:
            row = QHBoxLayout()
            name = QLabel(label)
            name.setFixedWidth(110)
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi)
            s.setValue(default)
            val = QLabel(str(default))
            val.setFixedWidth(40)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            s.valueChanged.connect(lambda v, l=val: (l.setText(str(v)), self.timer.start()))
            row.addWidget(name), row.addWidget(s), row.addWidget(val)
            lay.addLayout(row)
            self.sliders.append(s)
        self.color_btn = None
        if color is not None:
            row = QHBoxLayout()
            row.addWidget(QLabel("Color"))
            self.color_btn = ColorButton(color)
            self.color_btn.changed.connect(lambda _: self.timer.start())
            row.addWidget(self.color_btn)
            row.addStretch()
            lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self):
        return [s.value() for s in self.sliders]

    def color(self):
        return self.color_btn.color() if self.color_btn else None


class TextDialog(QDialog):
    def __init__(self, parent, color):
        super().__init__(parent)
        self.setWindowTitle("Insert text")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("Type your text...")
        self.edit.setFixedHeight(90)
        lay.addWidget(self.edit)

        form = QFormLayout()
        self.font_box = QFontComboBox()
        self.font_box.setCurrentFont(QFont(FONT))      # JetBrains Mono by default
        self.size = QSpinBox()
        self.size.setRange(4, 3000)
        self.size.setValue(64)
        self.bold, self.italic = QCheckBox("Bold"), QCheckBox("Italic")
        style = QHBoxLayout()
        style.addWidget(self.bold), style.addWidget(self.italic), style.addStretch()
        self.color = ColorButton(color)
        form.addRow("Font", self.font_box)
        form.addRow("Size (px)", self.size)
        form.addRow("Style", style)
        form.addRow("Color", self.color)
        lay.addLayout(form)

        self.shadow = QGroupBox("Drop shadow")
        self.shadow.setCheckable(True)
        self.shadow.setChecked(True)
        sf = QFormLayout(self.shadow)
        self.dx, self.dy = QSpinBox(), QSpinBox()
        for s, v in ((self.dx, 6), (self.dy, 6)):
            s.setRange(-500, 500)
            s.setValue(v)
        self.blur, self.opacity = QSpinBox(), QSpinBox()
        self.blur.setRange(0, 200), self.blur.setValue(8)
        self.opacity.setRange(0, 100), self.opacity.setValue(70)
        self.sh_color = ColorButton(QColor(0, 0, 0))
        sf.addRow("Offset X", self.dx)
        sf.addRow("Offset Y", self.dy)
        sf.addRow("Blur", self.blur)
        sf.addRow("Opacity %", self.opacity)
        sf.addRow("Color", self.sh_color)
        lay.addWidget(self.shadow)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.edit.setFocus()

    def params(self):
        return dict(text=self.edit.toPlainText(), family=self.font_box.currentFont().family(),
                    size=self.size.value(), bold=self.bold.isChecked(), italic=self.italic.isChecked(),
                    color=self.color.color(), shadow=self.shadow.isChecked(),
                    dx=self.dx.value(), dy=self.dy.value(), blur=self.blur.value(),
                    opacity=self.opacity.value() / 100, sh_color=self.sh_color.color())


class UpscaleDialog(QDialog):
    def __init__(self, parent, w, h):
        super().__init__(parent)
        self.setWindowTitle("Upscale image")
        form = QFormLayout(self)
        self.factor = QComboBox()
        self.factor.addItems(["2x", "3x", "4x"])
        self.method = QComboBox()
        self.method.addItems(["Lanczos (sharpest)", "Bicubic (smoother)"])
        self.sharpen = QSpinBox()
        self.sharpen.setRange(0, 300)
        self.sharpen.setValue(80)
        self.info = QLabel()
        form.addRow("Scale", self.factor)
        form.addRow("Method", self.method)
        form.addRow("Sharpen %", self.sharpen)
        form.addRow(self.info)
        self._wh = (w, h)
        self.factor.currentIndexChanged.connect(self._upd)
        self._upd()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def scale(self):
        return self.factor.currentIndex() + 2

    def _upd(self):
        s = self.scale()
        self.info.setText(f"{self._wh[0]}x{self._wh[1]}  ->  {self._wh[0]*s}x{self._wh[1]*s}")


class NewDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New image")
        form = QFormLayout(self)
        self.w, self.h = QSpinBox(), QSpinBox()
        for s, v in ((self.w, 1200), (self.h, 800)):
            s.setRange(1, 12000)
            s.setValue(v)
        self.bg = QComboBox()
        self.bg.addItems(["White", "Black", "Transparent"])
        form.addRow("Width", self.w)
        form.addRow("Height", self.h)
        form.addRow("Background", self.bg)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def background(self):
        return [QColor("white"), QColor("black"), QColor(0, 0, 0, 0)][self.bg.currentIndex()]


# --------------------------------------------------------------------------- canvas
class Canvas(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.image = QImage(1, 1, ARGB)
        self.zoom = 1.0
        self.sel = None            # bool ndarray (h, w) or None
        self.sel_alpha = None      # QImage mask used to clip painting
        self.sel_overlay = None
        self.crop_rect = None
        self.drag_start = None
        self.stroke = self.stroke_base = None
        self.last = None
        self.panning = False
        self.setMouseTracking(True)
        self.refresh_theme()

    # ----- state
    def refresh_theme(self):
        pal = self.main.pal
        pm = QPixmap(16, 16)
        pm.fill(QColor(pal["surface0"]))
        q = QPainter(pm)
        q.fillRect(0, 0, 8, 8, QColor(pal["surface1"]))
        q.fillRect(8, 8, 8, 8, QColor(pal["surface1"]))
        q.end()
        self.checker = QBrush(pm)
        self.set_selection(self.sel)

    def set_image(self, img: QImage):
        self.image = img
        if self.sel is not None and self.sel.shape != (img.height(), img.width()):
            self.sel = None
            self.sel_alpha = self.sel_overlay = None
        self.crop_rect = None
        self.update_size()
        self.update()

    def update_size(self):
        self.setFixedSize(max(1, int(self.image.width() * self.zoom)),
                          max(1, int(self.image.height() * self.zoom)))

    def set_selection(self, mask):
        self.sel = mask
        if mask is None or not mask.any():
            self.sel = self.sel_alpha = self.sel_overlay = None
        else:
            self.sel_alpha = mask_to_qimage(mask)
            self.sel_overlay = selection_overlay(mask, self.main.pal["mauve"])
        self.update()

    # ----- painting
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), self.checker)
        p.scale(self.zoom, self.zoom)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom < 1)
        p.drawImage(0, 0, self.image)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        if self.sel_overlay is not None:
            p.drawImage(0, 0, self.sel_overlay)
        if self.crop_rect is not None:
            W, H, r = self.image.width(), self.image.height(), self.crop_rect
            dim = QColor(0, 0, 0, 150)
            p.fillRect(0, 0, W, r.top(), dim)
            p.fillRect(0, r.bottom() + 1, W, H - r.bottom() - 1, dim)
            p.fillRect(0, r.top(), r.left(), r.height(), dim)
            p.fillRect(r.right() + 1, r.top(), W - r.right() - 1, r.height(), dim)
            pen = QPen(QColor(self.main.pal["mauve"]), 2)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)

    # ----- input
    def pos_img(self, e):
        pt = e.position()
        return QPoint(int(pt.x() // self.zoom), int(pt.y() // self.zoom))

    def mousePressEvent(self, e):
        tool = self.main.tool
        if e.button() == Qt.MouseButton.MiddleButton or (e.button() == Qt.MouseButton.LeftButton and tool == "hand"):
            self.panning = True
            self.pan_last = e.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        pt = self.pos_img(e)
        if tool in ("brush", "eraser"):
            self.main.push_undo()
            self.stroke = QImage(self.image.size(), ARGB)
            self.stroke.fill(Qt.GlobalColor.transparent)
            self.stroke_base = self.image.copy()
            self.last = pt
            self.paint_segment(pt, pt)
        elif tool == "crop":
            W, H = self.image.width(), self.image.height()
            self.drag_start = QPoint(min(max(pt.x(), 0), W), min(max(pt.y(), 0), H))
            self.crop_rect = None
            self.update()
        elif tool == "wand":
            self.main.wand_click(pt, e.modifiers())
        elif tool == "bucket":
            self.main.bucket_click(pt)
        elif tool == "text":
            self.main.text_click(pt)
        elif tool == "picker":
            self.main.pick_color(pt)

    def mouseMoveEvent(self, e):
        pt = self.pos_img(e)
        self.main.show_pos(pt)
        if self.panning:
            g = e.globalPosition().toPoint()
            d = g - self.pan_last
            self.pan_last = g
            hb, vb = self.main.scroll.horizontalScrollBar(), self.main.scroll.verticalScrollBar()
            hb.setValue(hb.value() - d.x())
            vb.setValue(vb.value() - d.y())
        elif self.stroke is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.paint_segment(self.last, pt)
            self.last = pt
        elif self.drag_start is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.update_crop(pt, bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier))

    def mouseReleaseEvent(self, e):
        if self.panning:
            self.panning = False
            self.main.apply_cursor()
        self.stroke = self.stroke_base = self.last = None
        if self.drag_start is not None:
            self.drag_start = None
            if self.crop_rect is not None and (self.crop_rect.width() < 2 or self.crop_rect.height() < 2):
                self.crop_rect = None
            self.update()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.main.set_zoom(self.zoom * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15))
            e.accept()
        else:
            e.ignore()

    # ----- tool internals
    def update_crop(self, pt, square):
        s, W, H = self.drag_start, self.image.width(), self.image.height()
        x1, y1 = min(max(pt.x(), 0), W), min(max(pt.y(), 0), H)
        dx, dy = x1 - s.x(), y1 - s.y()
        if square:
            room_x = W - s.x() if dx >= 0 else s.x()
            room_y = H - s.y() if dy >= 0 else s.y()
            side = min(max(abs(dx), abs(dy)), room_x, room_y)
            dx, dy = side * (1 if dx >= 0 else -1), side * (1 if dy >= 0 else -1)
        xa, xb = sorted((s.x(), s.x() + dx))
        ya, yb = sorted((s.y(), s.y() + dy))
        self.crop_rect = QRect(xa, ya, xb - xa, yb - ya)
        self.main.status_msg(f"Crop {self.crop_rect.width()} x {self.crop_rect.height()}  -  Enter to apply, Esc to cancel")
        self.update()

    def paint_segment(self, a, b):
        m = self.main
        eraser = m.tool == "eraser"
        sp = QPainter(self.stroke)
        sp.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0, 0, 0) if eraser else QColor(m.color.red(), m.color.green(), m.color.blue()),
                   m.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        sp.setPen(pen)
        sp.drawLine(a, b)
        sp.end()
        pad = m.size // 2 + 3
        dirty = QRect(a, b).normalized().adjusted(-pad, -pad, pad, pad).intersected(self.image.rect())
        if dirty.isEmpty():
            return
        piece = self.stroke.copy(dirty)
        if self.sel_alpha is not None:                       # selection limits painting
            mp = QPainter(piece)
            mp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            mp.drawImage(0, 0, self.sel_alpha.copy(dirty))
            mp.end()
        p = QPainter(self.image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawImage(dirty.topLeft(), self.stroke_base, dirty)     # reset dirty area (keeps opacity uniform)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut if eraser
                             else QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setOpacity(1.0 if eraser else m.opacity / 100)
        p.drawImage(dirty.topLeft(), piece)
        p.end()
        self.update()


# --------------------------------------------------------------------------- main window
TOOLS = [("hand", "Hand", "H"), ("crop", "Crop", "C"), ("wand", "Magic Wand", "W"),
         ("brush", "Brush", "B"), ("eraser", "Eraser", "E"), ("bucket", "Bucket Fill", "G"),
         ("text", "Text", "T"), ("picker", "Eyedropper", "I")]
HINTS = {
    "hand": "Drag to pan (middle mouse always pans). Ctrl+wheel zooms.",
    "crop": "Drag a rectangle (hold Shift for a perfect square), Enter applies, Esc cancels.",
    "wand": "Click to select similar colors. Shift = add, Alt/Ctrl = subtract. Enter crops to it.",
    "brush": "Paint. Painting is limited to the selection if there is one. [ and ] change size.",
    "eraser": "Erase to transparency (limited to the selection).",
    "bucket": "Fill similar colors (limited to the selection). Tolerance in the options bar.",
    "text": "Click where the text should go.",
    "picker": "Click to pick a color from the image.",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kessoku Paint")
        self.resize(1400, 880)
        self.settings = QSettings("Kessoku", "KessokuPaint")
        theme = self.settings.value("theme", "Mocha")
        self.theme = theme if theme in PALETTES else "Mocha"
        self.pal = PALETTES[self.theme]
        self.tool = "brush"
        self.color = QColor(self.pal["mauve"])
        self.size, self.opacity, self.tol, self.contiguous = 24, 100, 32, True
        self.undo_stack, self.redo_stack = [], []
        self.path = None

        self.canvas = Canvas(self)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("viewArea")
        self.scroll.setWidget(self.canvas)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.scroll)

        self.pos_label, self.zoom_label, self.size_label = QLabel(""), QLabel(""), QLabel("")
        self.statusBar().addPermanentWidget(self.pos_label)
        self.statusBar().addPermanentWidget(self.size_label)
        self.statusBar().addPermanentWidget(self.zoom_label)

        self._build_menus()
        self._build_toolbars()
        self.apply_theme(self.theme)
        self.new_image(1200, 800, QColor("white"))
        self.set_tool("brush")
        if FONT not in QFontDatabase.families():
            self.status_msg(f"'{FONT}' is not installed - install it or drop the .ttf files in ./fonts")

    # ----- UI construction
    def _act(self, text, slot, shortcut=None, menu=None):
        a = QAction(text, self)
        a.triggered.connect(lambda _=False: slot())
        if shortcut:
            a.setShortcut(QKeySequence(shortcut) if isinstance(shortcut, str) else shortcut)
        if menu is not None:
            menu.addAction(a)
        return a

    def _build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu("&File")
        self._act("New...", self.new_dialog, "Ctrl+N", f)
        self._act("Open...", self.open_file, "Ctrl+O", f)
        self._act("Save As...", self.save_file, "Ctrl+S", f)
        f.addSeparator()
        self._act("Quit", self.close, "Ctrl+Q", f)

        e = mb.addMenu("&Edit")
        self._act("Undo", self.undo, "Ctrl+Z", e)
        self._act("Redo", self.redo, "Ctrl+Shift+Z", e)
        e.addSeparator()
        self._act("Fill Selection with Color", self.fill_selection, "Alt+Backspace", e)
        self._act("Delete Selection (make transparent)", self.delete_selection, "Delete", e)

        s = mb.addMenu("&Select")
        self._act("Select All", self.select_all, "Ctrl+A", s)
        self._act("Deselect", self.deselect, "Ctrl+D", s)
        self._act("Invert Selection", self.invert_selection, "Ctrl+Shift+I", s)

        i = mb.addMenu("&Image")
        self._act("Apply Crop / Crop to Selection", self.apply_crop, "Return", i)
        self._act("Cut Out Selection (transparent background)", lambda: self.crop_to_selection(True), "Ctrl+Shift+X", i)
        i.addSeparator()
        self._act("Hue / Saturation...", self.hue_sat, "Ctrl+U", i)
        self._act("Drop Shadow...", self.drop_shadow, "Ctrl+Shift+D", i)
        self._act("Upscale...", self.upscale, "Ctrl+Shift+U", i)
        QShortcut(QKeySequence("Enter"), self, activated=self.apply_crop)
        QShortcut(QKeySequence("Escape"), self, activated=self.cancel)
        QShortcut(QKeySequence("["), self, activated=lambda: self.size_slider.setValue(self.size_slider.value() - 4))
        QShortcut(QKeySequence("]"), self, activated=lambda: self.size_slider.setValue(self.size_slider.value() + 4))

        v = mb.addMenu("&View")
        self._act("Zoom In", lambda: self.set_zoom(self.canvas.zoom * 1.25), "Ctrl+=", v)
        self._act("Zoom Out", lambda: self.set_zoom(self.canvas.zoom / 1.25), "Ctrl+-", v)
        self._act("Fit on Screen", self.fit, "Ctrl+0", v)
        self._act("Actual Size (100%)", lambda: self.set_zoom(1.0), "Ctrl+1", v)
        tm = v.addMenu("Theme")
        grp = QActionGroup(self)
        for name in PALETTES:
            a = QAction("Catppuccin " + name, self, checkable=True, checked=(name == self.theme))
            a.triggered.connect(lambda _=False, n=name: self.apply_theme(n))
            grp.addAction(a)
            tm.addAction(a)

    def _build_toolbars(self):
        tb = QToolBar("Tools")
        tb.setMovable(False)
        tb.setOrientation(Qt.Orientation.Vertical)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb)
        self.tool_group = QActionGroup(self)
        self.tool_actions = {}
        for key, name, sc in TOOLS:
            a = QAction(f"{name}  {sc}", self, checkable=True)
            a.setShortcut(sc)
            a.setToolTip(HINTS[key])
            a.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addAction(a)
            tb.addAction(a)
            self.tool_actions[key] = a

        ob = QToolBar("Options")
        ob.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ob)
        self.color_btn = ColorButton(self.color)
        self.color_btn.changed.connect(lambda c: setattr(self, "color", c))
        ob.addWidget(QLabel("Color"))
        ob.addWidget(self.color_btn)

        def slider(label, lo, hi, val, setter, width=130):
            ob.addWidget(QLabel(label))
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi)
            s.setValue(val)
            s.setFixedWidth(width)
            lab = QLabel(str(val))
            lab.setFixedWidth(40)
            s.valueChanged.connect(lambda v: (setter(v), lab.setText(str(v))))
            ob.addWidget(s)
            ob.addWidget(lab)
            return s

        self.size_slider = slider("Size", 1, 300, self.size, lambda v: setattr(self, "size", v))
        slider("Opacity", 1, 100, self.opacity, lambda v: setattr(self, "opacity", v))
        slider("Tolerance", 0, 160, self.tol, lambda v: setattr(self, "tol", v))
        cb = QCheckBox("Contiguous")
        cb.setChecked(True)
        cb.toggled.connect(lambda v: setattr(self, "contiguous", v))
        ob.addSeparator()
        ob.addWidget(cb)

    # ----- theme / tools / status
    def apply_theme(self, name):
        self.theme, self.pal = name, PALETTES[name]
        self.settings.setValue("theme", name)
        QApplication.instance().setStyleSheet(QSS.substitute(font=FONT, **self.pal))
        self.canvas.refresh_theme()

    def set_tool(self, key):
        self.tool = key
        self.tool_actions[key].setChecked(True)
        if key != "crop":
            self.canvas.crop_rect = None
            self.canvas.update()
        self.apply_cursor()
        self.status_msg(HINTS[key])

    def apply_cursor(self):
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor if self.tool == "hand" else Qt.CursorShape.CrossCursor)

    def status_msg(self, msg):
        self.statusBar().showMessage(msg)

    def show_pos(self, pt):
        self.pos_label.setText(f"{pt.x()}, {pt.y()}")

    def set_zoom(self, z):
        self.canvas.zoom = min(max(z, 0.05), 32.0)
        self.canvas.update_size()
        self.canvas.update()
        self.zoom_label.setText(f"{round(self.canvas.zoom * 100)}%")

    def fit(self):
        vp, im = self.scroll.viewport().size(), self.canvas.image
        self.set_zoom(min(vp.width() / im.width(), vp.height() / im.height()) * 0.96)

    def cancel(self):
        self.canvas.crop_rect = None
        self.canvas.update()

    # ----- document / undo
    def set_image(self, img):
        self.canvas.set_image(img)
        self.size_label.setText(f"{img.width()} x {img.height()} px")

    def push_undo(self, img=None):
        self.undo_stack.append(img if img is not None else self.canvas.image.copy())
        del self.undo_stack[:-30]
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.canvas.image.copy())
            self.set_image(self.undo_stack.pop())

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.canvas.image.copy())
            self.set_image(self.redo_stack.pop())

    def new_image(self, w, h, bg):
        img = QImage(w, h, ARGB)
        img.fill(bg)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canvas.set_selection(None)
        self.set_image(img)
        self.set_zoom(1.0)

    def new_dialog(self):
        d = NewDialog(self)
        if d.exec():
            self.new_image(d.w.value(), d.h.value(), d.background())
            self.fit()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)")
        if not path:
            return
        try:
            pil = ImageOps.exif_transpose(Image.open(path))
        except Exception as ex:
            QMessageBox.warning(self, "Open failed", str(ex))
            return
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canvas.set_selection(None)
        self.set_image(pil_to_qimage(pil))
        self.path = path
        self.setWindowTitle(f"Kessoku Paint - {Path(path).name}")
        self.fit() if self.canvas.image.width() > 1000 or self.canvas.image.height() > 700 else self.set_zoom(1.0)

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save image", self.path or "untitled.png",
                                              "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp)")
        if not path:
            return
        pil = qimage_to_pil(self.canvas.image)
        if path.lower().endswith((".jpg", ".jpeg", ".bmp")):
            bg = Image.new("RGB", pil.size, "white")
            bg.paste(pil, mask=pil.getchannel("A"))
            pil = bg
        pil.save(path)
        self.status_msg(f"Saved {path}")

    # ----- selection
    def select_all(self):
        im = self.canvas.image
        self.canvas.set_selection(np.ones((im.height(), im.width()), bool))

    def deselect(self):
        self.canvas.set_selection(None)

    def invert_selection(self):
        im, sel = self.canvas.image, self.canvas.sel
        self.canvas.set_selection(np.ones((im.height(), im.width()), bool) if sel is None else ~sel)

    def wand_click(self, pt, mods):
        im = self.canvas.image
        if not (0 <= pt.x() < im.width() and 0 <= pt.y() < im.height()):
            return
        arr = np.array(qimage_to_pil(im))
        m = flood_mask(arr, pt.x(), pt.y(), self.tol, self.contiguous)
        cur = self.canvas.sel
        if cur is not None:
            if mods & Qt.KeyboardModifier.ShiftModifier:
                m = cur | m
            elif mods & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ControlModifier):
                m = cur & ~m
        self.canvas.set_selection(m)
        self.status_msg(f"Selected {int(m.sum()):,} px - Enter crops to it, Ctrl+Shift+X cuts it out")

    # ----- pixel operations
    def _commit_pil(self, pil):
        self.push_undo()
        self.set_image(pil_to_qimage(pil))

    def bucket_click(self, pt):
        im = self.canvas.image
        if not (0 <= pt.x() < im.width() and 0 <= pt.y() < im.height()):
            return
        arr = np.array(qimage_to_pil(im))
        m = flood_mask(arr, pt.x(), pt.y(), self.tol, self.contiguous)
        if self.canvas.sel is not None:
            m &= self.canvas.sel
        self._blend(arr, m)
        self._commit_pil(Image.fromarray(arr))

    def _blend(self, arr, mask):
        op, c = self.opacity / 100, self.color
        new = np.array([c.red(), c.green(), c.blue(), 255], np.float32)
        arr[mask] = (arr[mask].astype(np.float32) * (1 - op) + new * op).round().astype(np.uint8)

    def fill_selection(self):
        if self.canvas.sel is None:
            return
        arr = np.array(qimage_to_pil(self.canvas.image))
        self._blend(arr, self.canvas.sel)
        self._commit_pil(Image.fromarray(arr))

    def delete_selection(self):
        if self.canvas.sel is None:
            return
        arr = np.array(qimage_to_pil(self.canvas.image))
        arr[self.canvas.sel] = 0
        self._commit_pil(Image.fromarray(arr))

    def pick_color(self, pt):
        im = self.canvas.image
        if 0 <= pt.x() < im.width() and 0 <= pt.y() < im.height():
            c = im.pixelColor(pt)
            self.color = QColor(c.red(), c.green(), c.blue())
            self.color_btn.set_color(self.color)

    # ----- crop
    def apply_crop(self):
        c = self.canvas
        if c.crop_rect is not None and c.crop_rect.width() > 0 and c.crop_rect.height() > 0:
            r = c.crop_rect
            self.push_undo()
            self.set_image(c.image.copy(r))
            self.fit() if self.canvas.zoom > 1 else None
        elif c.sel is not None:
            self.crop_to_selection(False)

    def crop_to_selection(self, cut_out):
        sel = self.canvas.sel
        if sel is None:
            self.status_msg("Make a selection with the Magic Wand first")
            return
        ys, xs = np.nonzero(sel)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        arr = np.array(qimage_to_pil(self.canvas.image))
        if cut_out:
            arr[~sel] = 0
        self.push_undo()
        self.canvas.set_selection(None)
        self.set_image(pil_to_qimage(Image.fromarray(arr[y0:y1, x0:x1])))
        self.set_zoom(self.canvas.zoom)

    # ----- live-preview effects
    def live_dialog(self, title, specs, func, color=None):
        base = self.canvas.image.copy()
        dlg = SliderDialog(title, specs, self, color)

        def refresh():
            self.canvas.set_image(func(base, dlg.values(), dlg.color()))

        dlg.changed.connect(refresh)
        refresh()
        if dlg.exec():
            refresh()
            self.push_undo(base)
        else:
            self.canvas.set_image(base)

    def _masked(self, pil_new, pil_old):
        if self.canvas.sel is not None:
            return Image.composite(pil_new, pil_old, mask_to_pil(self.canvas.sel))
        return pil_new

    def hue_sat(self):
        def func(base, v, _c):
            hue, sat, lit = v
            pil = qimage_to_pil(base)
            alpha = pil.getchannel("A")
            h, s, val = [np.array(ch) for ch in pil.convert("RGB").convert("HSV").split()]
            h = ((h.astype(np.int16) + int(round(hue / 360 * 256))) % 256).astype(np.uint8)
            s = np.clip(s.astype(np.float32) * (1 + sat / 100), 0, 255).astype(np.uint8)
            out = Image.merge("HSV", [Image.fromarray(h), Image.fromarray(s), Image.fromarray(val)]).convert("RGB")
            if lit:
                a = np.array(out).astype(np.float32)
                a = a + (255 - a) * lit / 100 if lit > 0 else a * (1 + lit / 100)
                out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
            out = out.convert("RGBA")
            out.putalpha(alpha)
            return pil_to_qimage(self._masked(out, pil))

        self.live_dialog("Hue / Saturation", [("Hue", -180, 180, 0), ("Saturation", -100, 100, 0),
                                              ("Lightness", -100, 100, 0)], func)

    def drop_shadow(self):
        pil = qimage_to_pil(self.canvas.image)
        if self.canvas.sel is None and pil.getchannel("A").getextrema()[0] == 255:
            QMessageBox.information(self, "Drop shadow",
                                    "Select something first (Magic Wand), or work on an image with a "
                                    "transparent background.\n\nTip: the Text tool has its own instant shadow.")
            return

        def func(base, v, color):
            dx, dy, blur, op = v
            pil = qimage_to_pil(base)
            if self.canvas.sel is not None:
                mask = mask_to_pil(self.canvas.sel)
                sh = make_shadow(pil.size, mask, dx, dy, blur, op / 100, rgb_of(color))
                out = Image.composite(pil, Image.alpha_composite(pil, sh), mask)
            else:
                sh = make_shadow(pil.size, pil.getchannel("A"), dx, dy, blur, op / 100, rgb_of(color))
                out = Image.alpha_composite(sh, pil)
            return pil_to_qimage(out)

        self.live_dialog("Drop Shadow", [("Offset X", -200, 200, 12), ("Offset Y", -200, 200, 12),
                                         ("Blur", 0, 100, 14), ("Opacity %", 0, 100, 65)],
                         func, QColor(0, 0, 0))

    def upscale(self):
        im = self.canvas.image
        d = UpscaleDialog(self, im.width(), im.height())
        if not d.exec():
            return
        s = d.scale()
        if im.width() * im.height() * s * s > 120_000_000:
            QMessageBox.warning(self, "Too large", "That result would exceed ~120 megapixels.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            pil = qimage_to_pil(im)
            res = Image.LANCZOS if d.method.currentIndex() == 0 else Image.BICUBIC
            up = pil.resize((pil.width * s, pil.height * s), res)
            if d.sharpen.value():
                rgb = up.convert("RGB").filter(ImageFilter.UnsharpMask(1.4, d.sharpen.value(), 2))
                rgb = rgb.convert("RGBA")
                rgb.putalpha(up.getchannel("A"))
                up = rgb
            self.push_undo()
            self.set_image(pil_to_qimage(up))
            self.fit()
        finally:
            QApplication.restoreOverrideCursor()

    # ----- text
    def text_click(self, pt):
        d = TextDialog(self, self.color)
        if not d.exec():
            return
        p = d.params()
        if not p["text"].strip():
            return
        im = self.canvas.image
        layer = QImage(im.size(), ARGB)
        layer.fill(Qt.GlobalColor.transparent)
        qp = QPainter(layer)
        qp.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        f = QFont(p["family"])
        f.setPixelSize(p["size"])
        f.setBold(p["bold"])
        f.setItalic(p["italic"])
        qp.setFont(f)
        qp.setPen(p["color"])
        qp.drawText(QRectF(pt.x(), pt.y(), im.width() * 2, im.height() * 2), p["text"],
                    QTextOption(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop))
        qp.end()
        base, txt = qimage_to_pil(im), qimage_to_pil(layer)
        if p["shadow"]:
            sh = make_shadow(base.size, txt.getchannel("A"), p["dx"], p["dy"], p["blur"],
                             p["opacity"], rgb_of(p["sh_color"]))
            base = Image.alpha_composite(base, sh)
        self._commit_pil(Image.alpha_composite(base, txt))


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("kessoku.paint")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Kessoku Paint")
    load_fonts()
    app.setFont(QFont(FONT, 10))
    icon = BASE_DIR / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
