"""Genera un Reel educativo animado (1080x1920, 30 fps) desde un spec JSON.

Uso: python3 tools/make_reel.py spec.json salida.mp4 [portada.jpg]

Spec:
{
  "tag": "ACUPUNTURA · MIGRAÑAS",
  "hook": "¿Tus migrañas *siempre* vuelven?",      # *palabra* = resaltada en amarillo
  "hook_icon": "head",
  "points": [ {"title": "...", "body": "...", "icon": "needle"}, ... 3 o 4 ],
  "cta_line": "Evaluamos tu caso y armamos un plan a tu medida",
  "web": "acupuntura-chile.cl",
  "voz": true,            # opcional: narración con voz sintética en español
  "voz_id": 28            # 28 = mujer (ef_dora), 29 = hombre (em_alex)
}
Iconos: head, wave, moon, leaf, needle, check, calendar, body, heart
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa
import numpy as np


def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def scaled(im, k):
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)


def narracion(spec):
    """Texto que se lee en voz alta en cada escena: gancho, puntos y cierre."""
    hook = spec["hook"].replace("*", "")
    pts = [f'{p["title"]}. {p["body"]}' for p in spec["points"]]
    cta = spec["cta_line"].rstrip(".") + ". Agenda tu hora en AcupunturaChile."
    return [hook] + pts + [cta]


def build(spec, vd=None):
    """vd: duraciones (s) de la voz por escena, o None si el Reel va sin voz."""
    web = spec.get("web", "acupuntura-chile.cl")
    scenes, t = [], 0.0
    fit = lambda base, i, pad: max(base, vd[i] + pad) if vd else base

    # --- gancho ---
    dur = fit(3.8, 0, 0.9)
    els = [
        dict(layer=text_layer(spec["hook"], 100, maxw=900, stroke=2), cy=860, delay=0.1),
        dict(layer=scaled(icon(spec.get("hook_icon", "head")), 0.62), cy=1330, delay=0.5, float=True),
    ]
    scenes.append(dict(start=t, end=t + dur, els=els, dots=None))
    t += dur

    # --- puntos ---
    n = len(spec["points"])
    for i, p in enumerate(spec["points"]):
        words = len(p["body"].split())
        dur = fit(max(4.8, 2.4 + words * 0.30), i + 1, 0.9)
        els = [
            dict(layer=scaled(icon(p.get("icon", "leaf")), 0.80), cy=650, delay=0.0, float=True),
            dict(layer=text_layer(p["title"], 66, color=YEL, maxw=900, stroke=1), cy=1040, delay=0.25),
            dict(layer=text_layer(p["body"], 44, bold=False, maxw=880, line_h=1.3), cy=1290, delay=0.55),
        ]
        scenes.append(dict(start=t, end=t + dur, els=els, dots=(i, n)))
        t += dur

    # --- cierre ---
    dur = fit(4.6, n + 1, 1.2)
    els = [
        dict(layer=scaled(icon("calendar"), 0.55), cy=560, delay=0.0, float=True),
        dict(layer=text_layer(spec["cta_line"], 60, maxw=900), cy=850, delay=0.25),
        dict(layer=logo(400), cy=1160, delay=0.6),
        dict(layer=text_layer(web, 44, color=(230, 240, 248), bold=False, maxw=800), cy=1400, delay=0.9),
        dict(layer=text_layer("Guarda y comparte este Reel", 38, color=YEL, maxw=800), cy=1480, delay=1.2),
    ]
    scenes.append(dict(start=t, end=t + dur, els=els, dots=None))
    t += dur
    return scenes, t


def dots_layer(i, n):
    w = n * 54 + 20
    im = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(n):
        x = 30 + k * 54
        d.ellipse((x - 11, 14, x + 11, 36), fill=(YEL if k == i else (90, 130, 130)) + (255,))
    return im


def frame_at(scenes, tag_layer, t, total):
    f = bg_frame(t)
    sc = next((s for s in scenes if s["start"] <= t < s["end"]), scenes[-1])
    lt = t - sc["start"]
    out_a = min(1.0, (sc["end"] - t) / 0.3) if sc is not scenes[-1] else 1.0
    for el in sc["els"]:
        u = ease((lt - el["delay"]) / 0.45)
        a = u * out_a
        dy = (1 - u) * 60 + (14 * math.sin(t * 2.2) if el.get("float") else 0)
        paste_center(f, el["layer"], el["cy"], a, dy)
    if sc["dots"]:
        paste_center(f, dots_layer(*sc["dots"]), 1520, ease(lt / 0.3) * out_a)
    paste_center(f, tag_layer, 330, ease(t / 0.5))
    # barra de progreso fina
    d = ImageDraw.Draw(f)
    d.rounded_rectangle((90, 1620, 90 + int((W - 180) * t / total), 1630), 5, fill=YEL + (230,))
    return f


def portada(spec, path):
    """Portada 1080x1920 en azul liso del logo (#395D77), logo arriba y gancho grande.
    Todo queda en la franja central (y 240-1680) que recorta la grilla del perfil."""
    img = Image.new("RGBA", (W, H), TEAL + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-200, 560, W + 200, 1500), fill=(255, 255, 255, 22))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
    items = [logo(440), pill_layer(spec.get("tag", "ACUPUNTURA · BIENESTAR"), 36, fill=TEAL_M),
             text_layer(spec["hook"], 92, maxw=900, stroke=0),
             text_layer(spec.get("web", "acupuntura-chile.cl"), 42, color=YEL, bold=False, maxw=800)]
    gap = 46
    total = sum(i.height for i in items) + gap * (len(items) - 1)
    y = 240 + max(0, (1440 - total) // 2)
    for it in items:
        img.alpha_composite(it, (int(W / 2 - it.width / 2), int(y)))
        y += it.height + gap
    img.convert("RGB").save(path, quality=93)
    print("portada", path, "contenido hasta y =", int(y - gap))


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    cover = sys.argv[3] if len(sys.argv) > 3 else None
    voz_wav = None
    vd = None
    if spec.get("voz"):
        import voz as vozmod
        sid = int(spec.get("voz_id", 28))
        clips = [vozmod.sintetizar(t, sid=sid, velocidad=float(spec.get("voz_velocidad", 1.0))) for t in narracion(spec)]
        vd = [len(x) / sr for x, sr in clips]
    scenes, total = build(spec, vd)
    if vd:
        sr = clips[0][1]
        pista = np.zeros(int((total + 0.5) * sr), dtype=np.float32)
        for sc, (x, _), off in zip(scenes, clips, [0.25] + [0.4] * (len(scenes) - 2) + [0.5]):
            i0 = int((sc["start"] + off) * sr)
            pista[i0:i0 + len(x)] += x[: len(pista) - i0]
        voz_wav = os.path.join(tempfile.mkdtemp(), "voz.wav")
        vozmod.guardar_wav(pista, sr, voz_wav)
    tag_layer = pill_layer(spec.get("tag", "ACUPUNTURA · BIENESTAR"), 40, fill=TEAL)
    n = int(total * FPS)
    if cover:
        portada(spec, cover)
    if voz_wav:
        entrada_audio = ["-i", voz_wav, "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000", "-ac", "2"]
    else:
        entrada_audio = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         *entrada_audio, "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame_at(scenes, tag_layer, i / FPS, total).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"ok {out} {total:.1f}s")


if __name__ == "__main__":
    main()
