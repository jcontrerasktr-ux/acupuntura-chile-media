"""Utilidades comunes: marca, fondos, textos e iconos para Reels e historias de AcupunturaChile."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT_DIRS = ["/usr/share/fonts/truetype/google-fonts", "/usr/share/fonts/truetype/dejavu"]

TEAL = (57, 93, 119)      # azul de marca (logo)
TEAL_D = (18, 36, 52)
TEAL_M = (40, 72, 98)
YEL = (255, 205, 40)
WHITE = (255, 255, 255)
MINT = (170, 210, 235)
CORAL = (240, 96, 90)
INK = (25, 25, 25)


def font(size, bold=True):
    for d in FONT_DIRS:
        for name in ([f"Poppins-{'Bold' if bold else 'Medium'}.ttf"] + (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"])):
            try:
                return ImageFont.truetype(f"{d}/{name}", size)
            except OSError:
                continue
    return ImageFont.load_default()


# ---------------- fondo ----------------
_BG = None
_BLOBS = None


def _blob(size, color, alpha):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.sqrt((xx - size / 2) ** 2 + (yy - size / 2) ** 2) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** 2 * alpha
    return a[..., None] * np.array(color, dtype=np.float32)


def bg_frame(t=0.0):
    """Fondo degradado verde-azulado con manchas de luz que se mueven despacio."""
    global _BG, _BLOBS
    if _BG is None:
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        _BG = np.array(TEAL_D, np.float32) * (1 - yy) + np.array(TEAL_M, np.float32) * yy
        _BG = np.repeat(_BG, W, axis=1)
        _BLOBS = [_blob(900, (70, 125, 170), 0.55), _blob(760, (95, 150, 195), 0.32), _blob(820, (50, 100, 150), 0.5)]
    a = _BG.copy()
    cfg = [(0.15, 0.20, 0.35, 0.0), (0.85, 0.55, 0.30, 2.1), (0.30, 0.90, 0.28, 4.2)]
    for blob, (cx, cy, sp, ph) in zip(_BLOBS, cfg):
        s = blob.shape[0]
        x = int(cx * W - s / 2 + 90 * math.sin(t * sp + ph))
        y = int(cy * H - s / 2 + 110 * math.cos(t * sp * 0.8 + ph))
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + s), min(H, y + s)
        if x1 > x0 and y1 > y0:
            a[y0:y1, x0:x1] += blob[y0 - y:y1 - y, x0 - x:x1 - x]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


# ---------------- texto ----------------
def parse_marked(text):
    """'Hola *mundo*' -> [('Hola ', False), ('mundo', True)]"""
    parts, hl, cur = [], False, ""
    for ch in text:
        if ch == "*":
            if cur:
                parts.append((cur, hl))
            cur, hl = "", not hl
        else:
            cur += ch
    if cur:
        parts.append((cur, hl))
    return parts


def wrap_words(text, fnt, maxw):
    """Devuelve líneas; cada línea es lista de palabras; cada palabra es lista de (trozo, resaltado)."""
    import re
    words, cur = [], []
    for seg, hl in parse_marked(text):
        for p in re.split(r"(\s+)", seg):
            if not p:
                continue
            if p.isspace():
                if cur:
                    words.append(cur)
                    cur = []
            else:
                cur.append((p, hl))
    if cur:
        words.append(cur)
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    flat = lambda w: "".join(p for p, _ in w)
    lines, line = [], []
    for w in words:
        trial = line + [w]
        width = d.textlength(" ".join(flat(x) for x in trial), font=fnt)
        if width <= maxw or not line:
            line = trial
        else:
            lines.append(line)
            line = [w]
    if line:
        lines.append(line)
    return lines


def text_layer(text, size, color=WHITE, hl_color=YEL, bold=True, maxw=900, line_h=1.22, align="center", stroke=0):
    """Capa RGBA (recortada) con texto envuelto. Devuelve la imagen."""
    fnt = font(size, bold)
    lines = wrap_words(text, fnt, maxw)
    lh = int(size * line_h)
    h = lh * len(lines) + 20
    im = Image.new("RGBA", (maxw + 40, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        total = d.textlength(" ".join("".join(p for p, _ in w) for w in line), font=fnt)
        x = (im.width - total) / 2 if align == "center" else 20
        y = 10 + i * lh
        for w in line:
            for part, hl in w:
                d.text((x, y), part, font=fnt, fill=(hl_color if hl else color) + (255,), stroke_width=stroke, stroke_fill=(10, 20, 24, 255))
                x += d.textlength(part, font=fnt)
            x += d.textlength(" ", font=fnt)
    return im


def pill_layer(text, size=46, fill=(74, 124, 160), fg=WHITE, pad=(44, 20), bold=True):
    fnt = font(size, bold)
    d0 = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    tw = d0.textlength(text, font=fnt)
    w, h = int(tw + pad[0] * 2), int(size * 1.25 + pad[1] * 2)
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + w, 26 + h), h // 2, fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), h // 2, fill=fill + (245,))
    d.text((20 + pad[0], 20 + pad[1] - 2), text, font=fnt, fill=fg + (255,))
    return im


def paste_center(frame, layer, cy, alpha=1.0, dy=0, cx=W // 2):
    if alpha <= 0:
        return
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2 + dy)))


# ---------------- iconos (capa RGBA 520x520) ----------------
ICON = 520


def _glow(im, radius=14, strength=1.0):
    g = im.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        g.putalpha(g.getchannel("A").point(lambda v: int(min(255, v * strength))))
    return Image.alpha_composite(g, im)


def icon(name, color=MINT, accent=YEL):
    im = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = ICON // 2
    if name == "head":
        pts = [(300, 60), (400, 80), (470, 140), (495, 220), (500, 280), (522, 335), (556, 405), (522, 425), (516, 452),
               (527, 482), (516, 506), (526, 532), (506, 572), (480, 622), (430, 642), (402, 700), (410, 800),
               (180, 800), (190, 680), (130, 620), (95, 520), (85, 400), (110, 250), (180, 130)]
        for _ in range(4):
            q = []
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
            pts = q
        k = 0.58
        poly = [(60 + k * x, 20 + k * y) for x, y in pts]
        d.polygon(poly, fill=(40, 70, 90, 255))
        d.line(poly + [poly[0]], fill=color + (255,), width=5, joint="curve")
        cx, cy = 60 + k * 340, 20 + k * 250
        for r in (44, 78, 112):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent + (200,), width=5)
        d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=accent + (255,))
    elif name == "wave":
        pts = [(30, c), (130, c), (170, c - 20), (210, c + 20), (250, c - 150), (300, c + 150), (340, c - 40), (380, c), (490, c)]
        d.line(pts, fill=accent + (255,), width=14, joint="curve")
    elif name == "moon":
        d.ellipse((90, 90, 430, 430), fill=color + (255,))
        d.ellipse((170, 60, 480, 370), fill=(0, 0, 0, 0))
        im2 = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(im2)
        d2.ellipse((90, 90, 430, 430), fill=color + (255,))
        cut = Image.new("L", (ICON, ICON), 0)
        ImageDraw.Draw(cut).ellipse((180, 40, 520, 380), fill=255)
        im2.paste((0, 0, 0, 0), mask=cut)
        im = im2
        d = ImageDraw.Draw(im)
        for (x, y, r) in [(380, 120, 10), (440, 240, 7), (330, 70, 6)]:
            d.ellipse((x - r, y - r, x + r, y + r), fill=accent + (255,))
    elif name == "leaf":
        leaf = [(c, 60), (c + 150, 160), (c + 170, 300), (c + 80, 430), (c, 460), (c - 80, 430), (c - 170, 300), (c - 150, 160)]
        for _ in range(3):
            q = []
            for i in range(len(leaf)):
                a, b = leaf[i], leaf[(i + 1) % len(leaf)]
                q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
            leaf = q
        d.polygon(leaf, fill=color + (255,))
        d.line([(c, 90), (c, 500)], fill=TEAL_D + (255,), width=10)
        for y in (200, 280, 360):
            d.line([(c, y + 40), (c + 70, y)], fill=TEAL_D + (255,), width=7)
            d.line([(c, y + 40), (c - 70, y)], fill=TEAL_D + (255,), width=7)
    elif name == "needle":
        d.line([(120, 90), (330, 360)], fill=(235, 240, 245, 255), width=8)
        d.ellipse((98, 66, 142, 110), fill=accent + (255,))
        for r in (40, 70, 100):
            d.ellipse((330 - r, 360 - r, 330 + r, 360 + r), outline=accent + (170,), width=5)
        d.ellipse((315, 345, 345, 375), fill=accent + (255,))
        d.arc((40, 300, 480, 500), 200, 340, fill=color + (255,), width=6)
    elif name == "check":
        d.ellipse((60, 60, 460, 460), fill=TEAL + (255,))
        d.line([(150, 270), (225, 345), (375, 175)], fill=WHITE + (255,), width=34, joint="curve")
    elif name == "calendar":
        d.rounded_rectangle((70, 100, 450, 450), 36, fill=WHITE + (255,))
        d.rounded_rectangle((70, 100, 450, 190), 36, fill=TEAL + (255,))
        d.rectangle((70, 150, 450, 190), fill=TEAL + (255,))
        for i in range(3):
            for j in range(3):
                d.rounded_rectangle((115 + i * 108, 215 + j * 76, 175 + i * 108, 265 + j * 76), 10, fill=(accent if (i, j) == (1, 1) else (200, 225, 222)) + (255,))
        d.rounded_rectangle((150, 60, 180, 130), 12, fill=INK + (255,))
        d.rounded_rectangle((340, 60, 370, 130), 12, fill=INK + (255,))
    elif name == "body":
        d.ellipse((c - 60, 40, c + 60, 160), fill=color + (255,))
        d.rounded_rectangle((c - 90, 180, c + 90, 380), 50, fill=color + (255,))
        d.line([(c, 190), (c, 440)], fill=accent + (255,), width=10)
        for y in (230, 290, 350, 410):
            d.ellipse((c - 12, y - 12, c + 12, y + 12), fill=accent + (255,))
    else:  # heart
        d.polygon([(c, 440), (70, 220), (110, 110), (220, 100), (c, 190), (300, 100), (410, 110), (450, 220)], fill=CORAL + (255,))
    return _glow(im, 12, 0.8)


_LOGO = None


def logo(width):
    """Logo blanco de AcupunturaChile (assets/logo_blanco.png) con ancho dado."""
    global _LOGO
    if _LOGO is None:
        path = __file__.rsplit("/", 2)[0] + "/assets/logo_blanco.png"
        _LOGO = Image.open(path).convert("RGBA")
    h = int(_LOGO.height * width / _LOGO.width)
    return _LOGO.resize((width, h), Image.LANCZOS)


def footer_brand(img, y=1520, web="acupuntura-chile.cl"):
    t = text_layer(web, 40, color=(230, 240, 248), bold=False, maxw=700)
    img.alpha_composite(t, (int(W / 2 - t.width / 2), y))
