"""Reel educativo ILUSTRADO (1080x1920, 30 fps): dibujos animados propios + subtítulos palabra a palabra + voz.

Uso: python3 tools/make_reel_ilustrado.py spec.json salida.mp4 [portada.jpg]

Spec:
{
  "tag": "QUIROPRAXIA · KINESIOLOGÍA · MEDICINA CHINA",
  "hook": "¿Sabías que tu columna tiene *33* vértebras?",   # para la portada
  "web": "acupuntura-chile.cl",
  "voz_id": 28,
  "escenas": [
    {"voz": "texto que se lee y se subtitula", "ilu": "columna", "regiones": [["7 cervicales", 0, 6], ...]},
    {"voz": "...", "ilu": "movimiento", "etiqueta": "Kinesiología"},
    {"voz": "...", "ilu": "meridianos", "etiqueta": "Medicina china"},
    {"voz": "...", "ilu": "cierre"}
  ]
}
Ilustraciones: punto (con "zona": cara|mano|pierna|oreja y opcional "puntos": ["Yintang"]), columna (vértebras 0-23: cervical 0-6, dorsal 7-18, lumbar 19-23), movimiento, meridianos, cierre (logo + web).
Todos los dibujos son originales y usan la paleta de la marca. Nunca copiar ilustraciones de otras cuentas.
"""
import json
import math
import os
import sys
import tempfile
import subprocess

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

CW, CH, SS = 800, 820, 2          # lienzo de la ilustración (se dibuja al doble y se reduce)
LINE = (236, 244, 250)
SOFT = (130, 170, 200)
BODY = (50, 88, 116)
BODY_L = (92, 134, 164)
OFF = 0.45                         # la voz entra un poco después de iniciar la escena


def new_canvas():
    return Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))


def sp(p):
    return (p[0] * SS, p[1] * SS)


def halo(dyn, r=14, k=0.9):
    """Resplandor suave para los elementos amarillos."""
    small = dyn.resize((dyn.width // 4, dyn.height // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r * SS / 4))
    g = small.resize(dyn.size, Image.BILINEAR)
    g.putalpha(g.getchannel("A").point(lambda v: int(v * k)))
    return Image.alpha_composite(g, dyn)



SKIN_L = (244, 208, 180)
SKIN_D = (176, 122, 98)
BONE_L = (240, 231, 214)
BONE_D = (196, 178, 152)
_BASES = {}


def mask_new():
    return Image.new("L", (CW * SS, CH * SS), 0)


def mline(dm, pts, w, v=255):
    dm.line([sp(q) for q in pts], fill=v, width=int(w * SS), joint="curve")
    for q in (pts[0], pts[-1]):
        r, (x, y) = w * SS / 2, sp(q)
        dm.ellipse((x - r, y - r, x + r, y + r), fill=v)


def shaded(mask, light=SKIN_L, dark=SKIN_D, r=26):
    """Rellena una silueta con degradado: bordes más oscuros, centro claro y luz desde arriba a la izquierda."""
    m = np.asarray(mask, dtype=np.float32) / 255
    b = np.asarray(mask.filter(ImageFilter.GaussianBlur(r * SS)), dtype=np.float32) / 255
    k = np.clip((b - 0.18) / 0.62, 0, 1)
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lit = 0.90 + 0.20 * ((1 - yy / h) * 0.55 + (1 - xx / w) * 0.45)
    col = np.array(dark, np.float32) + (np.array(light, np.float32) - np.array(dark, np.float32)) * k[..., None]
    col = np.clip(col * lit[..., None], 0, 255)
    return Image.fromarray(np.dstack([col, m * 255]).astype(np.uint8), "RGBA")


def soft(base, drawfn, blur=10):
    """Dibuja una sombra o brillo difuminado sobre la capa base."""
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    drawfn(ImageDraw.Draw(lay))
    lay = lay.filter(ImageFilter.GaussianBlur(blur * SS))
    # no se sale de la silueta
    a = np.minimum(np.asarray(lay.getchannel("A")), np.asarray(base.getchannel("A")))
    lay.putalpha(Image.fromarray(a))
    base.alpha_composite(lay)


def thick(d, pts, w, fill):
    d.line([sp(p) for p in pts], fill=fill, width=int(w * SS), joint="curve")
    for p in (pts[0], pts[-1]):
        r = w * SS / 2
        x, y = sp(p)
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def label(d, text, cx, cy, fill=YEL, fg=TEAL_D, size=38):
    f = font(size * SS)
    tw = d.textlength(text, font=f)
    x, y = cx * SS, cy * SS
    pad = 26 * SS
    d.rounded_rectangle((x - tw / 2 - pad, y - 34 * SS, x + tw / 2 + pad, y + 34 * SS), 34 * SS, fill=fill + (255,))
    d.text((x, y), text, font=f, fill=fg, anchor="mm")


def smooth(p, n=3):
    for _ in range(n):
        q = [p[0]]
        for i in range(len(p) - 1):
            a, b = p[i], p[i + 1]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1])
        p = q
    return p


def along(path, u):
    """Punto a la fracción u (0-1) del recorrido de una polilínea."""
    seg = [math.dist(path[i], path[i + 1]) for i in range(len(path) - 1)]
    target = (u % 1.0) * sum(seg)
    for i, s in enumerate(seg):
        if target <= s:
            k = target / s if s else 0
            return (path[i][0] + (path[i + 1][0] - path[i][0]) * k, path[i][1] + (path[i + 1][1] - path[i][1]) * k)
        target -= s
    return path[-1]


# ---------------------------------------------------------------- columna
def vertebra_xy(i):
    y = 70 + i * 25
    return 400 + 36 * math.sin(2 * math.pi * (y - 70) / 620), y


def ilu_columna(t, lt, sc):
    im, dyn = new_canvas(), new_canvas()
    d, dd = ImageDraw.Draw(im), ImageDraw.Draw(dyn)
    regiones = sc.get("regiones") or [[sc.get("etiqueta", ""), 0, 23]]
    dur = max(0.1, sc["end"] - sc["start"])
    ri = min(len(regiones) - 1, int(max(0.0, lt - 0.4) / (dur - 0.6) * len(regiones)))
    name, a, b = regiones[ri]
    wave = (b - a) > 12
    pos = a + ((lt * 7) % (b - a + 8)) if wave else None
    sway = 4 * math.sin(t * 1.3)
    # nervios que salen de cada vértebra, con señales que viajan
    for i in range(24):
        x, y = vertebra_xy(i)
        w = 56 + (i / 23) * 62
        x0 = x + w / 2 + sway
        pts = smooth([(x0, y), (x0 + 50, y + 4), (x0 + 95 + (i % 2) * 18, y + 22)], 2)
        d.line([sp(p) for p in pts], fill=SOFT + (110,), width=2 * SS)
        if a <= i <= b:
            px, py = along(pts, (t * 0.9 + i * 0.17) % 1.0)
            r = 6 * SS
            dd.ellipse((px * SS - r, py * SS - r, px * SS + r, py * SS + r), fill=YEL + (255,))
    # sacro y cóccix
    sx, sy = vertebra_xy(23)
    sac = [(sx - 50 + sway, sy + 22), (sx + 50 + sway, sy + 22), (sx + 30 + sway, sy + 112), (sx + sway, sy + 138), (sx - 24 + sway, sy + 100)]
    d.polygon([sp(p) for p in sac], fill=BONE_D + (255,), outline=BONE_L + (255,))
    # vértebras
    for i in range(24):
        x, y = vertebra_xy(i)
        x += sway
        w = 56 + (i / 23) * 62
        lit = a <= i <= b
        if wave:
            lit = lit and abs(i - pos) < 3.2
        fl, fd = (YEL, (214, 158, 20)) if lit else (BONE_L, BONE_D)
        # apófisis espinosa (hacia atrás)
        thick(d, [(x - w / 2, y), (x - w / 2 - 30, y + 7)], 8, (fd if lit else BONE_D) + (255,))
        d.rounded_rectangle((sp((x - w / 2, y - 10)), sp((x + w / 2, y + 10))), 8 * SS, fill=fd + (255,))
        d.rounded_rectangle((sp((x - w / 2 + 2, y - 10)), sp((x + w / 2 - 2, y + 4))), 8 * SS, fill=fl + (255,))
        if i < 23:   # disco
            d.ellipse((sp((x - w / 2 + 8, y + 10)), sp((x + w / 2 - 8, y + 17))), fill=(120, 175, 210, 200))
    out = Image.alpha_composite(im, halo(dyn))
    od = ImageDraw.Draw(out)
    if name:
        y_mid = vertebra_xy((a + b) // 2)[1]
        label(od, name, 150, max(80, min(740, y_mid)))
    return out


# ---------------------------------------------------------------- movimiento (sentadilla)
def ilu_movimiento(t, lt, sc):
    im, dyn = new_canvas(), new_canvas()
    d, dd = ImageDraw.Draw(im), ImageDraw.Draw(dyn)
    a = 0.5 - 0.5 * math.cos(2 * math.pi * lt / 3.2)          # 0 de pie, 1 sentadilla
    ground = 700
    ankle = (400, ground)
    L1, L2, L3 = 190, 190, 215
    th = math.radians(34 * a)
    knee = (ankle[0] + L2 * math.sin(th), ankle[1] - L2 * math.cos(th))
    ph = math.radians(78 * a)
    hip = (knee[0] - L1 * math.sin(ph), knee[1] - L1 * math.cos(ph))
    ps = math.radians(38 * a)
    sho = (hip[0] + L3 * math.sin(ps), hip[1] - L3 * math.cos(ps))
    head = (sho[0] + 26 * math.sin(ps), sho[1] - 62 * math.cos(ps))
    hand = (sho[0] + 40 + 150 * a, sho[1] + 160 * (1 - a) * 0.9 + 6 * a)
    elbow = ((sho[0] + hand[0]) / 2, (sho[1] + hand[1]) / 2 + 20 * (1 - a))
    # suelo
    d.line([sp((120, ground + 26)), sp((680, ground + 26))], fill=SOFT + (200,), width=4 * SS)
    # extremidad trasera (más tenue) y delantera
    def limb(pts, w, base, hi):
        thick(d, pts, w, base + (255,))
        thick(d, [(q[0] - w * 0.16, q[1] - w * 0.1) for q in pts], w * 0.42, hi + (255,))
    for base, hi, dx in (((78, 118, 148), (110, 152, 182), -34), ((205, 225, 240), (248, 252, 255), 0)):
        limb([(ankle[0] + dx, ankle[1]), (knee[0] + dx, knee[1]), (hip[0] + dx, hip[1])], 32, base, hi)
    limb([hip, sho], 46, (205, 225, 240), (248, 252, 255))
    limb([sho, elbow, hand], 26, (205, 225, 240), (248, 252, 255))
    r = 54 * SS
    hx, hy = head[0] * SS, head[1] * SS
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(205, 225, 240, 255))
    d.ellipse((hx - r * 0.65 - 10 * SS, hy - r * 0.7, hx + r * 0.2 - 10 * SS, hy - r * 0.05), fill=(248, 252, 255, 255))
    # articulaciones resaltadas con arco de ángulo en la rodilla
    for p in (hip, knee, ankle):
        r = 15 * SS
        dd.ellipse((p[0] * SS - r, p[1] * SS - r, p[0] * SS + r, p[1] * SS + r), fill=YEL + (255,))
    v1 = (ankle[0] - knee[0], ankle[1] - knee[1])
    v2 = (hip[0] - knee[0], hip[1] - knee[1])
    a1 = math.degrees(math.atan2(v1[1], v1[0]))
    a2 = math.degrees(math.atan2(v2[1], v2[0]))
    rr = 62 * SS
    kx, ky = knee[0] * SS, knee[1] * SS
    lo, hi = sorted((a1, a2))
    if hi - lo > 180:
        lo, hi = hi, lo + 360
    dd.arc((kx - rr, ky - rr, kx + rr, ky + rr), lo, hi, fill=YEL + (255,), width=5 * SS)
    out = Image.alpha_composite(im, halo(dyn))
    od = ImageDraw.Draw(out)
    if sc.get("etiqueta"):
        label(od, sc["etiqueta"], 170, 40)
    # tres conceptos que se encienden por turnos
    words = ["Movimiento", "Fuerza", "Postura"]
    for k, wd in enumerate(words):
        on = int((lt / 3.2 * 3) % 3) == k
        label(od, wd, 150 + k * 250, 760, fill=YEL if on else (70, 108, 136), fg=TEAL_D if on else (200, 220, 235), size=30)
    return out


# ---------------------------------------------------------------- meridianos
def cuerpo_paths():
    smooth_ = lambda p: smooth(p, 3)
    L = [(346, 715), (352, 590), (362, 470), (372, 330), (385, 230), (396, 150)]
    R = [(800 - x, y) for x, y in L]
    AL = [(248, 465), (262, 360), (318, 250), (372, 215), (396, 170)]
    AR = [(800 - x, y) for x, y in AL]
    return [smooth_(p) for p in (L, R, AL, AR)]


def base_cuerpo():
    m = mask_new()
    dm = ImageDraw.Draw(m)
    dm.ellipse((sp((342, 62)), sp((458, 178))), fill=255)
    dm.rounded_rectangle((sp((308, 205)), sp((492, 475))), 60 * SS, fill=255)
    mline(dm, [(376, 180), (424, 180)], 40)
    for mx in (lambda x: x, lambda x: 800 - x):
        mline(dm, [(mx(318), 248), (mx(262), 360), (mx(248), 470)], 46)
        mline(dm, [(mx(360), 450), (mx(352), 590), (mx(346), 722)], 58)
    base = shaded(m, light=(120, 168, 200), dark=(40, 72, 98), r=20)
    d = ImageDraw.Draw(base)
    d.ellipse((sp((342, 62)), sp((458, 178))), outline=(170, 210, 235, 140), width=3 * SS)
    soft(base, lambda x: x.ellipse((sp((340, 70)), sp((420, 140))), fill=(210, 235, 250, 90)), 14)
    return base


def ilu_meridianos(t, lt, sc):
    if "cuerpo" not in _BASES:
        _BASES["cuerpo"] = base_cuerpo()
    im = _BASES["cuerpo"].copy()
    dyn = new_canvas()
    dd = ImageDraw.Draw(im)
    dd2 = ImageDraw.Draw(dyn)
    for p in cuerpo_paths():
        dd.line([sp(q) for q in p], fill=(205, 232, 248, 190), width=3 * SS)
        for k in range(4):
            x, y = along(p, (t * 0.28 + k / 4) % 1.0)
            r = 8 * SS
            dd2.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=YEL + (255,))
    pts = [(400, 66), (250, 455), (550, 455), (352, 590), (448, 590), (346, 712), (454, 712), (400, 330)]
    for i, (x, y) in enumerate(pts):
        ph = (lt * 0.9 + i * 0.37) % 1.0
        r = (12 + 34 * ph) * SS
        dd2.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), outline=YEL + (int(255 * (1 - ph)),), width=4 * SS)
        r0 = 9 * SS
        dd2.ellipse((x * SS - r0, y * SS - r0, x * SS + r0, y * SS + r0), fill=YEL + (255,))
    out = Image.alpha_composite(im, halo(dyn))
    if sc.get("etiqueta"):
        label(ImageDraw.Draw(out), sc["etiqueta"], 190, 40)
    return out


# ---------------------------------------------------------------- puntos de acupuntura (zoom a una zona)
# nombre -> (x, y, pista en español). Coordenadas del lienzo 800x820.
PUNTOS = {
    "cara": {"Yintang": (400, 322, "entre las cejas"), "Taiyang": (232, 345, "en la sien"), "Taiyang ": (568, 345, "en la sien")},
    "mano": {"Hegu": (306, 432, "entre el pulgar y el índice")},
    "pierna": {"Zusanli": (436, 292, "cuatro dedos bajo la rodilla, por fuera")},
    "oreja": {"Shenmen": (406, 222, "parte alta de la oreja")},
}


def base_cara():
    m = mask_new()
    dm = ImageDraw.Draw(m)
    dm.ellipse((sp((205, 130)), sp((595, 640))), fill=255)
    for ex in (205, 595):
        dm.ellipse((sp((ex - 30, 340)), sp((ex + 30, 440))), fill=255)
    dm.rounded_rectangle((sp((330, 570)), sp((470, 790))), 40 * SS, fill=255)
    base = shaded(m)
    mh = mask_new()
    dh = ImageDraw.Draw(mh)
    dh.ellipse((sp((186, 96)), sp((614, 470))), fill=255)
    dh.ellipse((sp((228, 188)), sp((572, 540))), fill=0)
    base.alpha_composite(shaded(mh, light=(104, 76, 64), dark=(38, 26, 24), r=14))
    d = ImageDraw.Draw(base)
    soft(base, lambda x: x.ellipse((sp((330, 400)), sp((470, 500))), fill=(150, 100, 80, 90)), 22)   # sombra de nariz
    for sx in (1, -1):
        mx = (lambda x: x) if sx == 1 else (lambda x: 800 - x)
        d.polygon([sp((mx(310), 334)), sp((mx(346), 311)), sp((mx(388), 318)), sp((mx(388), 330)), sp((mx(346), 325)), sp((mx(312), 344))], fill=(62, 42, 34, 255))
        cx = mx(345)
        d.ellipse((sp((cx - 36, 347)), sp((cx + 36, 377))), fill=(252, 250, 247, 255))
        d.ellipse((sp((cx - 12, 349)), sp((cx + 12, 375))), fill=(92, 62, 44, 255))
        d.ellipse((sp((cx - 5, 358)), sp((cx + 5, 368))), fill=(20, 14, 12, 255))
        d.ellipse((sp((cx - 9, 352)), sp((cx - 3, 358))), fill=(255, 255, 255, 255))
        d.arc((sp((cx - 36, 340)), sp((cx + 36, 384))), 200, 340, fill=(80, 52, 42, 255), width=4 * SS)
    d.line([sp((394, 385)), sp((389, 452))], fill=(200, 146, 120, 200), width=4 * SS)
    d.arc((sp((372, 440)), sp((428, 480))), 20, 160, fill=(150, 100, 82, 255), width=4 * SS)
    d.polygon([sp((352, 524)), sp((380, 509)), sp((400, 516)), sp((420, 509)), sp((448, 524)), sp((400, 532))], fill=(190, 100, 102, 255))
    d.ellipse((sp((362, 524)), sp((438, 558))), fill=(206, 122, 120, 255))
    return base


def base_mano():
    m = mask_new()
    dm = ImageDraw.Draw(m)
    dm.rounded_rectangle((sp((300, 330)), sp((520, 600))), 70 * SS, fill=255)
    dm.rounded_rectangle((sp((332, 570)), sp((490, 705))), 40 * SS, fill=255)
    dedos = [([(338, 380), (338, 175)], 46), ([(402, 360), (402, 125)], 48), ([(464, 380), (464, 165)], 46),
             ([(516, 410), (528, 250)], 38), ([(312, 540), (232, 470), (190, 378)], 50)]
    for pts, w in dedos:
        mline(dm, pts, w)
    base = shaded(m, r=16)
    d = ImageDraw.Draw(base)
    for pts, w in dedos:
        x, y = pts[-1]
        d.ellipse((sp((x - w * 0.34, y - 6)), sp((x + w * 0.34, y + 34))), fill=(250, 222, 210, 255), outline=(204, 150, 130, 255), width=2 * SS)
    for x in (338, 402, 464):
        d.line([sp((x - 14, 398)), sp((x + 14, 398))], fill=(190, 136, 112, 200), width=3 * SS)
        d.line([sp((x - 12, 408)), sp((x + 12, 408))], fill=(190, 136, 112, 120), width=2 * SS)
        d.line([sp((x, 430)), sp((x + (5 if x > 400 else -3), 575))], fill=(196, 144, 118, 150), width=4 * SS)
    return base


def base_pierna():
    m = mask_new()
    dm = ImageDraw.Draw(m)
    poly = [(332, 140), (468, 140), (486, 330), (448, 640), (352, 640), (314, 330)]
    dm.polygon([sp(q) for q in smooth(poly, 2)], fill=255)
    dm.ellipse((sp((320, 628)), sp((480, 715))), fill=255)
    base = shaded(m, r=30)
    d = ImageDraw.Draw(base)
    soft(base, lambda x: x.ellipse((sp((356, 78)), sp((444, 176))), fill=(255, 238, 222, 120)), 12)     # rótula
    d.arc((sp((350, 70)), sp((450, 190))), 20, 340, fill=(176, 122, 98, 150), width=3 * SS)
    d.line([sp((400, 215)), sp((397, 620))], fill=(190, 136, 110, 170), width=4 * SS)
    soft(base, lambda x: x.ellipse((sp((318, 260)), sp((372, 440))), fill=(150, 100, 78, 90)), 18)    # gemelo
    for i, x in enumerate((345, 372, 400, 428, 455)):
        d.ellipse((sp((x - 13, 690)), sp((x + 13, 714))), fill=(248, 218, 205, 255), outline=(190, 136, 112, 255), width=2 * SS)
    return base


def soft_c(base, drawfn, blur=10):
    """Como soft(), pero mezcla el color sin oscurecer los bordes (desenfoque con alfa premultiplicado)."""
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    drawfn(ImageDraw.Draw(lay))
    lay = lay.convert("RGBa").filter(ImageFilter.GaussianBlur(blur * SS)).convert("RGBA")
    a = np.minimum(np.asarray(lay.getchannel("A")), np.asarray(base.getchannel("A")))
    lay.putalpha(Image.fromarray(a))
    base.alpha_composite(lay)


def base_oreja():
    """Oreja de aspecto suave y pálido (dibujo propio): hélix con surco, antihélix en Y, fosa triangular, concha, trago y lóbulo."""
    contorno = [(398, 108), (468, 116), (538, 166), (584, 258), (600, 370), (582, 482), (538, 574), (484, 654), (432, 706),
                (386, 712), (350, 690), (336, 642), (338, 590), (330, 540), (322, 480), (330, 420), (336, 350),
                (334, 290), (320, 240), (300, 200), (282, 170), (288, 136), (318, 116), (358, 106)]
    m = mask_new()
    dm = ImageDraw.Draw(m)
    dm.polygon([sp(q) for q in smooth(contorno, 4)], fill=255)
    base = shaded(m, light=(253, 233, 220), dark=(226, 160, 142), r=34)
    ROSA, OSC, LUZ = (222, 134, 122), (196, 100, 92), (255, 248, 240)

    def trazo(tr, w, col, dx=0, dy=0):
        return lambda x: thick(x, [(q[0] + dx, q[1] + dy) for q in tr], w, col)

    # hélix: reborde claro con surco salmón en su cara interior
    rim = smooth([(322, 176), (362, 132), (440, 130), (512, 178), (550, 262), (562, 372), (542, 470), (504, 556)], 2)
    surco = smooth([(352, 192), (388, 162), (440, 164), (490, 204), (514, 272), (524, 370), (508, 458), (474, 536)], 2)
    soft_c(base, trazo(rim, 30, ROSA + (150,), 7, 10), 8)
    soft_c(base, trazo(rim, 22, (255, 240, 230, 200)), 6)
    soft_c(base, trazo(surco, 9, ROSA + (215,)), 2.5)
    soft_c(base, trazo(surco, 4, OSC + (150,), 1, 1), 1.5)
    # escafa (entre hélix y antihélix): sombra suave
    soft_c(base, trazo(smooth([(430, 210), (468, 250), (478, 330), (468, 420), (446, 500)], 2), 40, ROSA + (150,)), 12)
    # antihélix en Y
    tallo = smooth([(412, 560), (430, 480), (442, 400), (442, 318)], 2)
    sup = smooth([(442, 318), (454, 262), (448, 212), (418, 182)], 2)
    inf = smooth([(442, 318), (400, 282), (356, 258), (322, 244)], 2)
    for tr in (tallo, sup, inf):
        soft_c(base, trazo(tr, 40, OSC + (175,), 9, 12), 8)
    for tr in (tallo, sup, inf):
        soft_c(base, trazo(tr, 34, (255, 238, 226, 255)), 6)
    for tr in (tallo, sup, inf):
        soft_c(base, trazo(tr, 10, LUZ + (220,), -6, -7), 5)
    # surco profundo bajo la rama inferior (línea salmón más marcada)
    linea = smooth([(324, 262), (366, 282), (410, 306), (440, 340)], 2)
    soft_c(base, trazo(linea, 9, (212, 108, 98, 230)), 2.5)
    # fosa triangular (zona de Shenmen): hondonada suave entre las ramas
    soft_c(base, lambda x: x.polygon([sp((352, 190)), sp((430, 196)), sp((438, 262)), sp((350, 240))], fill=ROSA + (120,)), 8)
    # concha, conducto y trago
    soft_c(base, lambda x: x.ellipse((sp((338, 322)), sp((440, 500))), fill=OSC + (150,)), 14)
    soft_c(base, lambda x: x.ellipse((sp((350, 392)), sp((392, 446))), fill=(170, 84, 78, 215)), 6)
    tr_pts = smooth([(330, 392), (352, 380), (372, 410), (366, 462), (334, 478), (322, 440)], 3)
    soft_c(base, lambda x: x.polygon([sp((q[0] + 6, q[1] + 8)) for q in tr_pts], fill=OSC + (120,)), 5)
    soft_c(base, lambda x: x.polygon([sp(q) for q in tr_pts], fill=(255, 238, 226, 255)), 3)
    soft_c(base, trazo(smooth([(334, 392), (354, 392), (368, 414)], 2), 5, ROSA + (200,)), 2)
    # antitrago y lóbulo
    soft_c(base, lambda x: x.ellipse((sp((404, 548)), sp((470, 604))), fill=OSC + (110,)), 7)
    soft_c(base, lambda x: x.ellipse((sp((398, 538)), sp((462, 592))), fill=(255, 238, 226, 255)), 4)
    for (px, py, rr, al) in ((400, 650, 34, 70), (450, 630, 26, 60), (380, 610, 22, 50), (430, 680, 20, 55)):
        soft_c(base, lambda x, px=px, py=py, rr=rr, al=al: x.ellipse((sp((px - rr, py - rr)), sp((px + rr, py + rr))), fill=ROSA + (al,)), 10)
    # más ancha (la silueta sale del dibujo alargado): se ensancha un 20 % con el borde izquierdo fijo
    k, ax = 1.20, 300 * SS
    x0, x1 = int(270 * SS), int(640 * SS)
    franja = base.crop((x0, 0, x1, base.height)).resize((int((x1 - x0) * k), base.height), Image.LANCZOS)
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    out.alpha_composite(franja, (int(ax - (ax - x0) * k), 0))
    return out


BASES_ZONA = {"cara": base_cara, "mano": base_mano, "pierna": base_pierna, "oreja": base_oreja}


def ilu_punto(t, lt, sc):
    zona = sc["zona"]
    if zona not in _BASES:
        _BASES[zona] = BASES_ZONA[zona]()
    im = _BASES[zona].copy()
    dyn = new_canvas()
    dd = ImageDraw.Draw(dyn)
    elegidos = [n for n in PUNTOS[zona] if (not sc.get("puntos")) or n.strip() in sc["puntos"]]
    for n in elegidos:
        x, y, _ = PUNTOS[zona][n]
        for k in range(3):
            ph = ((lt * 0.7) + k / 3) % 1.0
            r = (16 + 80 * ph) * SS
            dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), outline=YEL + (int(255 * (1 - ph) ** 1.3),), width=5 * SS)
        r = (15 + 3 * math.sin(lt * 5)) * SS
        dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=YEL + (255,))
        dd.ellipse((x * SS - r * 0.45, y * SS - r * 0.45, x * SS + r * 0.45, y * SS + r * 0.45), fill=(255, 250, 220, 255))
    out = Image.alpha_composite(im, halo(dyn, r=18, k=1.0))
    od = ImageDraw.Draw(out)
    nombres = sorted({n.strip() for n in elegidos})
    pistas = {n.strip(): PUNTOS[zona][n][2] for n in elegidos}
    label(od, nombres[0] if len(nombres) == 1 else " · ".join(nombres), 400, 772, size=36)
    if len(nombres) == 1:
        f = font(26 * SS, False)
        tw = od.textlength(pistas[nombres[0]], font=f)
        od.rounded_rectangle((400 * SS - tw / 2 - 16 * SS, 706 * SS, 400 * SS + tw / 2 + 16 * SS, 742 * SS), 18 * SS, fill=TEAL_D + (225,))
        od.text((400 * SS, 724 * SS), pistas[nombres[0]], font=f, fill=(225, 238, 247, 255), anchor="mm")
    if sc.get("etiqueta"):
        label(od, sc["etiqueta"], 190, 40)
    return out


ILU = {"punto": ilu_punto, "columna": ilu_columna, "movimiento": ilu_movimiento, "meridianos": ilu_meridianos}


# ---------------------------------------------------------------- subtítulos
def trim_voz(x, sr):
    amp = np.abs(x)
    idx = np.where(amp > 0.02)[0]
    if len(idx) == 0:
        return 0.0, len(x) / sr
    return idx[0] / sr, (idx[-1] + 1) / sr


def tiempos_palabras(texto, a0, a1):
    words = texto.split()
    wts = [len(w) + 2 + (5 if w[-1:] in ",.?!:;" else 0) for w in words]
    tot = float(sum(wts))
    out, acc = [], 0.0
    for w, wt in zip(words, wts):
        out.append(OFF + a0 + (a1 - a0) * acc / tot)
        acc += wt
    return words, out


_CACHE = {}


def caption_layer(words, starts, lt, n=3):
    idx = max(0, max([i for i, s in enumerate(starts) if s <= lt] or [0]))
    c0 = (idx // n) * n
    chunk = words[c0:c0 + n]
    key = (tuple(chunk), idx - c0)
    if key not in _CACHE:
        marked = " ".join(f"*{w}*" if k == idx - c0 else w for k, w in enumerate(chunk))
        _CACHE[key] = text_layer(marked, 78, maxw=900, line_h=1.15, stroke=1)
    return _CACHE[key]


# ---------------------------------------------------------------- armado
def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    cover = sys.argv[3] if len(sys.argv) > 3 else None
    import voz as vozmod
    sid = int(spec.get("voz_id", 28))
    escenas = spec["escenas"]
    clips = [vozmod.sintetizar(e["voz"], sid=sid, velocidad=float(spec.get("voz_velocidad", 1.0))) for e in escenas]
    t = 0.0
    for e, (x, sr) in zip(escenas, clips):
        a0, a1 = trim_voz(x, sr)
        e["words"], e["starts"] = tiempos_palabras(e["voz"], a0, a1)
        dur = OFF + len(x) / sr + (1.3 if e["ilu"] == "cierre" else 0.8)
        e["start"], e["end"] = t, t + max(3.2, dur)
        t = e["end"]
    total = t
    sr = clips[0][1]
    pista = np.zeros(int((total + 0.5) * sr), dtype=np.float32)
    for e, (x, _) in zip(escenas, clips):
        i0 = int((e["start"] + OFF) * sr)
        pista[i0:i0 + len(x)] += x[: len(pista) - i0]
    wav = os.path.join(tempfile.mkdtemp(), "voz.wav")
    vozmod.guardar_wav(pista, sr, wav)

    web = spec.get("web", "acupuntura-chile.cl")
    tag = pill_layer(spec.get("tag", "ACUPUNTURA · BIENESTAR"), 34, fill=TEAL_M)
    if cover:
        import make_reel as mr
        mr.portada(spec, cover)

    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", wav, "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000", "-ac", "2", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    logo_l = logo(420)
    web_l = text_layer(web, 46, color=YEL, bold=False, maxw=800)
    save_l = text_layer(spec.get("cierre_texto", "Guarda y comparte este Reel"), 40, maxw=800)
    aviso = text_layer("Ante síntomas intensos o nuevos, consulta a un profesional de salud", 30, color=(205, 222, 236), bold=False, maxw=860, line_h=1.2)
    n = int(total * FPS)
    for fi in range(n):
        tt = fi / FPS
        f = bg_frame(tt)
        sc = next((e for e in escenas if e["start"] <= tt < e["end"]), escenas[-1])
        lt = tt - sc["start"]
        a_in = ease(lt / 0.45)
        a_out = min(1.0, (sc["end"] - tt) / 0.3) if sc is not escenas[-1] else 1.0
        al = a_in * a_out
        paste_center(f, tag, 330, ease(tt / 0.5))
        paste_center(f, caption_layer(sc["words"], sc["starts"], lt), 520, al)
        if sc["ilu"] == "cierre":
            paste_center(f, logo_l, 1010, ease((lt - 0.2) / 0.5) * a_out)
            paste_center(f, web_l, 1290, ease((lt - 0.5) / 0.5) * a_out)
            paste_center(f, save_l, 1370, ease((lt - 0.8) / 0.5) * a_out)
            paste_center(f, aviso, 1500, ease((lt - 1.0) / 0.5) * a_out)
        else:
            k, cy = (1.0, 1105) if sc["ilu"] == "punto" else (1.15, 1150)
            ill = ILU[sc["ilu"]](tt, lt, sc).resize((int(CW * k), int(CH * k)), Image.LANCZOS)
            paste_center(f, ill, cy, al, dy=(1 - ease(lt / 0.5)) * 50)
        d = ImageDraw.Draw(f)
        d.rounded_rectangle((90, 1620, 90 + int((W - 180) * tt / total), 1630), 5, fill=YEL + (230,))
        ff.stdin.write(f.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"ok {out} {total:.1f}s")


if __name__ == "__main__":
    main()
