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
    d.polygon([sp(p) for p in sac], fill=BODY_L + (255,), outline=LINE + (255,))
    # vértebras
    for i in range(24):
        x, y = vertebra_xy(i)
        x += sway
        w = 56 + (i / 23) * 62
        lit = a <= i <= b
        if wave:
            lit = lit and abs(i - pos) < 3.2
        fill = YEL if lit else BODY_L
        # apófisis espinosa (hacia atrás)
        thick(d, [(x - w / 2, y), (x - w / 2 - 30, y + 7)], 8, (SOFT if not lit else YEL) + (255,))
        d.rounded_rectangle((sp((x - w / 2, y - 10)), sp((x + w / 2, y + 10))), 8 * SS, fill=fill + (255,), outline=LINE + (255,), width=2 * SS)
        if i < 23:   # disco
            d.ellipse((sp((x - w / 2 + 8, y + 10)), sp((x + w / 2 - 8, y + 17))), fill=(190, 220, 240, 150))
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
    for col, dx in (((90, 130, 160), -34), ((236, 244, 250), 0)):
        thick(d, [(ankle[0] + dx, ankle[1]), (knee[0] + dx, knee[1]), (hip[0] + dx, hip[1])], 30, col + (255,))
    thick(d, [hip, sho], 44, LINE + (255,))
    thick(d, [sho, elbow, hand], 24, LINE + (255,))
    r = 54 * SS
    hx, hy = head[0] * SS, head[1] * SS
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=LINE + (255,))
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
        label(od, wd, 150 + k * 250, 790, fill=YEL if on else (70, 108, 136), fg=TEAL_D if on else (200, 220, 235), size=30)
    return out


# ---------------------------------------------------------------- meridianos
def cuerpo_paths():
    smooth_ = lambda p: smooth(p, 3)
    L = [(346, 715), (352, 590), (362, 470), (372, 330), (385, 230), (396, 150)]
    R = [(800 - x, y) for x, y in L]
    AL = [(248, 465), (262, 360), (318, 250), (372, 215), (396, 170)]
    AR = [(800 - x, y) for x, y in AL]
    return [smooth_(p) for p in (L, R, AL, AR)]


def ilu_meridianos(t, lt, sc):
    im, dyn = new_canvas(), new_canvas()
    d, dd = ImageDraw.Draw(im), ImageDraw.Draw(dyn)
    for grow, col in ((10, BODY_L), (0, BODY)):
        d.ellipse((sp((342 - grow, 62 - grow)), sp((458 + grow, 178 + grow))), fill=col + (255,))
        d.rounded_rectangle((sp((308 - grow, 205 - grow)), sp((492 + grow, 475 + grow))), (60 + grow) * SS, fill=col + (255,))
        thick(d, [(376, 180), (424, 180)], 40 + 2 * grow, col + (255,))
        for mx in (lambda x: x, lambda x: 800 - x):
            thick(d, [(mx(318), 248), (mx(262), 360), (mx(248), 470)], 46 + 2 * grow, col + (255,))
            thick(d, [(mx(360), 450), (mx(352), 590), (mx(346), 722)], 58 + 2 * grow, col + (255,))
    paths = cuerpo_paths()
    for p in paths:
        d.line([sp(q) for q in p], fill=(150, 205, 235, 170), width=3 * SS)
        for k in range(4):
            x, y = along(p, (t * 0.28 + k / 4) % 1.0)
            r = 8 * SS
            dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=YEL + (255,))
    pts = [(400, 66), (250, 455), (550, 455), (352, 590), (448, 590), (346, 712), (454, 712), (400, 330)]
    for i, (x, y) in enumerate(pts):
        ph = (lt * 0.9 + i * 0.37) % 1.0
        r = (12 + 34 * ph) * SS
        dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), outline=YEL + (int(255 * (1 - ph)),), width=4 * SS)
        r0 = 9 * SS
        dd.ellipse((x * SS - r0, y * SS - r0, x * SS + r0, y * SS + r0), fill=YEL + (255,))
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
    "oreja": {"Shenmen": (418, 252, "parte alta de la oreja")},
}


def zona_cara(d):
    d.ellipse((sp((205, 130)), sp((595, 640))), fill=BODY + (255,), outline=BODY_L + (255,), width=5 * SS)
    for ex in (205, 595):
        d.ellipse((sp((ex - 28, 340)), sp((ex + 28, 440))), fill=BODY + (255,), outline=BODY_L + (255,), width=4 * SS)
    for sx in (-1, 1):
        cx = 400 + sx * 88
        thick(d, [(cx - 52, 330), (cx - 10 * sx, 306), (cx + 52, 322)] if sx == -1 else [(cx - 52, 322), (cx + 10, 306), (cx + 52, 330)], 9, LINE + (255,))
        d.ellipse((sp((cx - 32, 346)), sp((cx + 32, 376))), outline=LINE + (255,), width=4 * SS)
        d.ellipse((sp((cx - 9, 354)), sp((cx + 9, 372))), fill=LINE + (255,))
    thick(d, [(400, 380), (392, 455), (416, 462)], 5, SOFT + (255,))
    d.arc((sp((340, 490)), sp((460, 560))), 20, 160, fill=SOFT + (255,), width=5 * SS)


def zona_mano(d):
    for grow, col in ((8, BODY_L), (0, BODY)):
        d.rounded_rectangle((sp((300 - grow, 330 - grow)), sp((520 + grow, 600 + grow))), (70 + grow) * SS, fill=col + (255,))
        d.rounded_rectangle((sp((332 - grow, 570 - grow)), sp((490 + grow, 705 + grow))), (40 + grow) * SS, fill=col + (255,))
        for pts, w in (([(338, 380), (338, 175)], 46), ([(402, 360), (402, 125)], 48), ([(464, 380), (464, 165)], 46),
                       ([(516, 410), (528, 250)], 38), ([(312, 540), (232, 470), (190, 378)], 50)):
            thick(d, pts, w + 2 * grow, col + (255,))
    for x in (338, 402, 464):
        d.line([sp((x, 420)), sp((x + (6 if x > 400 else -2), 560))], fill=BODY_L + (140,), width=3 * SS)


def zona_pierna(d):
    for grow, col in ((8, BODY_L), (0, BODY)):
        poly = [(332 - grow, 140), (468 + grow, 140), (486 + grow, 330), (448 + grow, 640), (352 - grow, 640), (314 - grow, 330)]
        d.polygon([sp(p) for p in smooth(poly, 2)], fill=col + (255,))
        d.ellipse((sp((320 - grow, 628 - grow)), sp((480 + grow, 715 + grow))), fill=col + (255,))
    d.ellipse((sp((350, 70)), sp((470, 190))), outline=LINE + (255,), width=4 * SS)
    d.line([sp((400, 215)), sp((396, 620))], fill=SOFT + (170,), width=4 * SS)


def zona_oreja(d):
    for grow, col in ((8, BODY_L), (0, BODY)):
        d.ellipse((sp((270 - grow, 110 - grow)), sp((540 + grow, 700 + grow))), fill=col + (255,))
    d.ellipse((sp((320, 175)), sp((490, 600))), outline=LINE + (255,), width=5 * SS)
    d.ellipse((sp((360, 380)), sp((450, 500))), fill=(40, 72, 98, 255), outline=SOFT + (255,), width=3 * SS)
    d.polygon([sp((380, 232)), sp((456, 246)), sp((408, 300))], outline=SOFT + (255,), width=3 * SS)
    thick(d, [(360, 330), (395, 255), (440, 200)], 6, SOFT + (255,))


ZONAS = {"cara": zona_cara, "mano": zona_mano, "pierna": zona_pierna, "oreja": zona_oreja}


def ilu_punto(t, lt, sc):
    im, dyn = new_canvas(), new_canvas()
    d, dd = ImageDraw.Draw(im), ImageDraw.Draw(dyn)
    zona = sc["zona"]
    ZONAS[zona](d)
    elegidos = [n for n in PUNTOS[zona] if (not sc.get("puntos")) or n.strip() in sc["puntos"]]
    for n in elegidos:
        x, y, _ = PUNTOS[zona][n]
        for k in range(3):
            ph = ((lt * 0.7) + k / 3) % 1.0
            r = (16 + 80 * ph) * SS
            dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), outline=YEL + (int(255 * (1 - ph) ** 1.3),), width=5 * SS)
        r = (15 + 3 * math.sin(lt * 5)) * SS
        dd.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=YEL + (255,))
    out = Image.alpha_composite(im, halo(dyn, r=18, k=1.0))
    od = ImageDraw.Draw(out)
    nombres = sorted({n.strip() for n in elegidos})
    pistas = {n.strip(): PUNTOS[zona][n][2] for n in elegidos}
    label(od, nombres[0] if len(nombres) == 1 else " · ".join(nombres), 400, 772, size=36)
    if len(nombres) == 1:
        f = font(26 * SS, False)
        od.text((400 * SS, 724 * SS), pistas[nombres[0]], font=f, fill=(215, 230, 240, 255), anchor="mm")
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
    save_l = text_layer("Guarda y comparte este Reel", 40, maxw=800)
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
