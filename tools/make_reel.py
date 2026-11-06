"""Genera un Reel educativo animado (1080x1920, 30 fps) desde un spec JSON.

Uso: python3 tools/make_reel.py spec.json salida.mp4 [portada.jpg]

Spec:
{
  "tag": "ACUPUNTURA · MIGRAÑAS",
  "hook": "¿Tus migrañas *siempre* vuelven?",      # *palabra* = resaltada en amarillo
  "hook_icon": "head",
  "points": [ {"title": "...", "body": "...", "icon": "needle"}, ... 3 o 4 ],
  "cta_line": "Evaluamos tu caso y armamos un plan a tu medida",
  "web": "acupuntura-chile.cl"
}
Iconos: head, wave, moon, leaf, needle, check, calendar, body, heart
"""
import json
import math
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa


def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def scaled(im, k):
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)


def build(spec):
    web = spec.get("web", "acupuntura-chile.cl")
    scenes, t = [], 0.0

    # --- gancho ---
    dur = 3.8
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
        dur = max(4.8, 2.4 + words * 0.30)
        els = [
            dict(layer=scaled(icon(p.get("icon", "leaf")), 0.80), cy=650, delay=0.0, float=True),
            dict(layer=text_layer(p["title"], 66, color=YEL, maxw=900, stroke=1), cy=1040, delay=0.25),
            dict(layer=text_layer(p["body"], 44, bold=False, maxw=880, line_h=1.3), cy=1290, delay=0.55),
        ]
        scenes.append(dict(start=t, end=t + dur, els=els, dots=(i, n)))
        t += dur

    # --- cierre ---
    dur = 4.6
    els = [
        dict(layer=scaled(icon("calendar"), 0.80), cy=650, delay=0.0, float=True),
        dict(layer=text_layer(spec["cta_line"], 62, maxw=900), cy=1020, delay=0.25),
        dict(layer=pill_layer("AcupunturaChile", 62, fill=WHITE, fg=(0, 110, 102), pad=(54, 24)), cy=1245, delay=0.6),
        dict(layer=text_layer(web, 44, color=(220, 240, 236), bold=False, maxw=800), cy=1360, delay=0.8),
        dict(layer=text_layer("Guarda y comparte este Reel", 38, color=YEL, maxw=800), cy=1465, delay=1.1),
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


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    cover = sys.argv[3] if len(sys.argv) > 3 else None
    scenes, total = build(spec)
    tag_layer = pill_layer(spec.get("tag", "ACUPUNTURA · BIENESTAR"), 40, fill=TEAL)
    n = int(total * FPS)
    if cover:
        frame_at(scenes, tag_layer, 2.3, total).convert("RGB").save(cover, quality=93)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame_at(scenes, tag_layer, i / FPS, total).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"ok {out} {total:.1f}s")


if __name__ == "__main__":
    main()
