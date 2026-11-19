"""Edita VIDEOS PROPIOS de Julio (grabados a cámara) como Reel 1080x1920: cortes de silencio, planos cerrados (zoom y paneo),
gancho de texto en los primeros 3 segundos, motion graphics (etiquetas con rebote, barrido de luz, subtítulos palabra por palabra),
mejora de voz y cierre de marca.

Uso: python3 tools/editar_video.py spec.json salida.mp4 [portada.jpg]

Spec:
{
  "tag": "TIP DE ACUPUNTURA", "hook": "¿Dolor de *cabeza* leve?", "web": "acupuntura-chile.cl",
  "gancho": {"titulo": "¿Dolor de *cabeza* leve?", "chip": "Tip de acupuntura con tus manos", "hasta": 4.8},
  "fuentes": {"tip": "/ruta/video1.mov", "cta": "/ruta/video2.mov"},
  "aviso": "Tip educativo: no reemplaza una evaluación",              # línea pequeña permanente
  "cierre": {"texto": "Guárdalo y envíaselo a alguien que lo necesite", "linea": "Escríbenos por WhatsApp o redes", "dur": 3.4},
  "segmentos": [            # cada uno: tramo de AUDIO de una fuente (se cortan los silencios entre ellos)
    {"id": "a1", "fuente": "tip", "ini": 0.58, "fin": 5.80, "texto": "texto hablado (subtítulos)", "pausa": 0.15,
     "planos": [ {"t": 0.0, "dur": 2.4, "fuente": "tip", "ini": 10.9, "zoom": [1.0, 1.12], "cx": 0.5, "cy": 0.35},
                 {"t": 2.4, "ini": 3.4, "zoom": [1.25, 1.35], "cx": 0.5, "cy": 0.38} ],      # opcional; t relativo al segmento
     "etiquetas": [ {"desde": 2.0, "hasta": 7.0, "texto": "① Zona", "tipo": "info"} ] }          # tipo: info | ok | no
  ]
}
Si un segmento no trae "planos", se usa su propio video con un zoom suave. El audio y el video de la misma fuente quedan sincronizados.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa
from PIL import Image, ImageDraw, ImageEnhance
import numpy as np

FPS_ = FPS if "FPS" in globals() else 30
SW, SH = 480, 854                      # tamaño de las fuentes (se detecta abajo)


def ease(u):
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


def rebote(u):
    u = max(0.0, min(1.0, u))
    c = 1.70158
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def sonda(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip().split(",")
    return int(r[0]), int(r[1])


def audio_fuente(path):
    wavp = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "48000", wavp], check=True)
    w = wave.open(wavp)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x, w.getframerate()


class Lector:
    """Lee cuadros de una fuente (fps fijo) de forma secuencial."""

    def __init__(self, path, ini, dur, w, h):
        self.n = w * h * 3
        self.w, self.h = w, h
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{ini:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", path, "-vf", f"fps={FPS}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.ultimo = None

    def siguiente(self):
        b = self.p.stdout.read(self.n)
        if len(b) == self.n:
            self.ultimo = Image.frombytes("RGB", (self.w, self.h), b)
        return self.ultimo

    def cerrar(self):
        try:
            self.p.stdout.close()
            self.p.kill()
        except Exception:
            pass


def encuadre(src, zoom, cx, cy):
    """Recorte (zoom y centro relativos) de un cuadro fuente, llevado a 1080x1920 con una versión suave de nitidez."""
    w, h = src.size
    cw, ch = w / zoom, h / zoom
    x0 = min(max(cx * w - cw / 2, 0), w - cw)
    y0 = min(max(cy * h - ch / 2, 0), h - ch)
    f = src.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    return f


def degradados():
    a = np.zeros((H, W, 4), np.uint8)
    y = np.arange(H)[:, None].astype(np.float32)
    top = np.clip(1 - y / 560, 0, 1) ** 1.6 * 170
    bot = np.clip((y - 1180) / 740, 0, 1) ** 1.4 * 200
    a[..., 3] = np.clip(top + bot, 0, 255).astype(np.uint8)[:, :1].repeat(W, axis=1)
    return Image.fromarray(a, "RGBA")


def barrido():
    h = 160
    a = np.zeros((h, W, 4), np.uint8)
    prof = np.clip(1 - np.abs(np.linspace(-1, 1, h)), 0, 1) ** 2
    a[..., 0], a[..., 1], a[..., 2] = 170, 215, 255
    a[..., 3] = (prof[:, None] * 80).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def con_alpha(layer, a):
    if a >= 1:
        return layer
    lay = layer.copy()
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return lay


def con_escala(layer, s):
    if abs(s - 1) < 0.01:
        return layer
    return layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)


def tiempos(texto, a0, a1):
    words = texto.split()
    wts = [len(w) + 2 + (5 if w[-1:] in ",.?!:;" else 0) for w in words]
    tot = float(sum(wts))
    out, acc = [], 0.0
    for w, wt in zip(words, wts):
        out.append(a0 + (a1 - a0) * acc / tot)
        acc += wt
    return words, out


_CAP = {}


def subtitulo(words, starts, tt, n=3):
    if tt < starts[0]:
        return None
    idx = max(i for i, s in enumerate(starts) if s <= tt)
    c0 = (idx // n) * n
    chunk = words[c0:c0 + n]
    key = (tuple(chunk), idx - c0)
    if key not in _CAP:
        marked = " ".join(f"*{w}*" if k == idx - c0 else w for k, w in enumerate(chunk))
        _CAP[key] = text_layer(marked, 80, maxw=940, line_h=1.12, stroke=5)
    return _CAP[key]


def main():
    global SW, SH
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    cover = sys.argv[3] if len(sys.argv) > 3 else None
    fuentes = spec["fuentes"]
    dims = {k: sonda(v) for k, v in fuentes.items()}
    aud = {k: audio_fuente(v) for k, v in fuentes.items()}
    SR = 48000

    # ---- línea de tiempo (audio sin silencios)
    t = 0.0
    segs = []
    for s in spec["segmentos"]:
        dur = s["fin"] - s["ini"]
        s = dict(s)
        s["t0"], s["t1"] = t, t + dur
        s["words"], s["starts"] = tiempos(s["texto"], t + 0.04, t + dur - 0.08)
        t += dur + float(s.get("pausa", 0.15))
        segs.append(s)
    total_video = segs[-1]["t1"] + 0.3
    cierre = spec.get("cierre", {})
    dur_cierre = float(cierre.get("dur", 3.4))
    total = total_video + dur_cierre

    # ---- pista de audio
    pista = np.zeros(int((total + 0.5) * SR), dtype=np.float32)
    for s in segs:
        x, sr = aud[s["fuente"]]
        a = x[int(s["ini"] * sr):int(s["fin"] * sr)].copy()
        fi = min(len(a) // 4, int(0.02 * sr))
        a[:fi] *= np.linspace(0, 1, fi)
        a[-fi:] *= np.linspace(1, 0, fi)
        i0 = int(s["t0"] * SR)
        pista[i0:i0 + len(a)] += a[: len(pista) - i0]
    wavp = os.path.join(tempfile.mkdtemp(), "audio.wav")
    pk = np.clip(pista, -1, 1)
    w = wave.open(wavp, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((pk * 32767).astype(np.int16).tobytes())
    w.close()

    # ---- planos de video (en línea de tiempo)
    planos = []
    for s in segs:
        dur = s["t1"] - s["t0"]
        pl = s.get("planos") or [{"t": 0.0, "fuente": s["fuente"], "ini": s["ini"], "zoom": [1.0, 1.1], "cx": 0.5, "cy": 0.5}]
        for k, p in enumerate(pl):
            p = dict(p)
            p.setdefault("fuente", s["fuente"])
            ini_rel = float(p["t"])
            fin_rel = float(pl[k + 1]["t"]) if k + 1 < len(pl) else dur
            if k == len(pl) - 1:
                fin_rel = dur + float(s.get("pausa", 0.15)) if s is not segs[-1] else dur + 0.3
            p["a"], p["b"] = s["t0"] + ini_rel, s["t0"] + fin_rel
            p.setdefault("ini", s["ini"] + ini_rel)
            p.setdefault("zoom", [1.0, 1.1])
            planos.append(p)
    planos[0]["a"] = 0.0
    planos[-1]["b"] = total_video

    # ---- elementos gráficos
    degr = degradados()
    BAR = barrido()
    logo_top = logo(250)
    logo_l = logo(420)
    web = spec.get("web", "acupuntura-chile.cl")
    web_l = text_layer(web, 50, color=YEL, bold=False, maxw=800)
    save_l = text_layer(cierre.get("texto", "Guárdalo y envíaselo a alguien que lo necesite"), 42, maxw=860)
    linea_l = text_layer(cierre.get("linea", ""), 36, color=(205, 222, 236), bold=False, maxw=860) if cierre.get("linea") else None
    aviso_c = text_layer("Ante síntomas intensos o nuevos, consulta a un profesional de salud", 30, color=(205, 222, 236), bold=False, maxw=860, line_h=1.2)
    peq = text_layer(spec.get("aviso", ""), 27, color=(235, 242, 248), bold=False, maxw=940) if spec.get("aviso") else None
    g = spec.get("gancho")
    if g:
        g_tit = text_layer(g["titulo"], 108, maxw=940, line_h=1.08, stroke=6)
        g_chip = chip_layer(g["chip"], "info", 44) if g.get("chip") else None
    chips = []
    for s in segs:
        for e in s.get("etiquetas", []):
            chips.append((s["t0"] + float(e["desde"]), s["t0"] + float(e["hasta"]), chip_layer(e["texto"], e.get("tipo", "info"), 46), e.get("y", 400)))
    if cover:
        import make_reel as mr
        mr.portada({"tag": spec.get("tag", ""), "hook": spec.get("hook", g["titulo"] if g else "")}, cover)

    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wavp,
         "-af", "highpass=f=80,afftdn=nr=10:nf=-45,acompressor=threshold=-22dB:ratio=3:attack=5:release=90,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000",
         "-ac", "2", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    n = int(total * FPS)
    pi, lector, plano = -1, None, None
    for fi in range(n):
        tt = fi / FPS
        if tt < total_video:
            while pi + 1 < len(planos) and tt >= planos[pi + 1]["a"] - 1e-6:
                pi += 1
                if lector:
                    lector.cerrar()
                plano = planos[pi]
                sw, sh = dims[plano["fuente"]]
                lector = Lector(fuentes[plano["fuente"]], plano["ini"], plano["b"] - plano["a"], sw, sh)
            src = lector.siguiente()
            lt = tt - plano["a"]
            u = lt / max(0.1, plano["b"] - plano["a"])
            z0, z1 = plano["zoom"]
            z = z0 + (z1 - z0) * u
            z *= 1 + 0.07 * (1 - ease(lt / 0.35)) if pi > 0 else 1.0           # golpe de zoom al cortar
            cx = plano["cx"] if not isinstance(plano.get("cx"), list) else plano["cx"][0] + (plano["cx"][1] - plano["cx"][0]) * ease(u * 1.4)
            cy = plano.get("cy", 0.5)
            cy = cy if not isinstance(cy, list) else cy[0] + (cy[1] - cy[0]) * ease(u * 1.4)
            f = encuadre(src, z, cx, cy)
            f = ImageEnhance.Contrast(f).enhance(1.06)
            f = ImageEnhance.Color(f).enhance(1.10).convert("RGBA")
            f.alpha_composite(degr)
            paste_center(f, logo_top, 110, ease(tt / 0.5))
            seg = next((s for s in segs if s["t0"] - 0.05 <= tt <= s["t1"] + 0.10), None)
            # gancho
            if g and tt < g.get("hasta", 4.8) + 0.4:
                ta = ease(tt / 0.25)
                tb = min(1.0, (g.get("hasta", 4.8) + 0.4 - tt) / 0.4)
                paste_center(f, con_alpha(con_escala(g_tit, 0.6 + 0.4 * rebote(tt / 0.5)), ta * tb), 520)
                if g_chip:
                    paste_center(f, con_alpha(con_escala(g_chip, 0.6 + 0.4 * rebote((tt - 0.35) / 0.5)), min(1, max(0, (tt - 0.35) / 0.2)) * tb), 700)
            # etiquetas de pasos
            for a, b, lay, yy in chips:
                if a <= tt <= b:
                    ia = min(1.0, (tt - a) / 0.35)
                    ib = min(1.0, (b - tt) / 0.25)
                    paste_center(f, con_alpha(con_escala(lay, 0.6 + 0.4 * rebote((tt - a) / 0.45)), ia * ib), yy)
            # subtítulos palabra por palabra
            if seg:
                cap = subtitulo(seg["words"], seg["starts"], tt)
                if cap is not None:
                    paste_center(f, cap, 1400, min(1.0, (tt - seg["t0"]) / 0.15 + 0.4))
            if peq:
                paste_center(f, peq, 1560, 0.85)
            if lt < 0.4 and pi > 0:
                f.alpha_composite(BAR, (0, int(-160 + (H + 160) * ease(lt / 0.4))))
        else:
            lt = tt - total_video
            f = bg_frame(tt)
            ia = ease(lt / 0.4)
            paste_center(f, logo_l, 800, ease((lt - 0.1) / 0.5))
            paste_center(f, web_l, 1070, ease((lt - 0.4) / 0.5))
            if linea_l:
                paste_center(f, linea_l, 1160, ease((lt - 0.6) / 0.5))
            paste_center(f, save_l, 1290, ease((lt - 0.8) / 0.5))
            paste_center(f, aviso_c, 1470, ease((lt - 1.0) / 0.5))
            if lt < 0.4:
                f.alpha_composite(BAR, (0, int(-160 + (H + 160) * ease(lt / 0.4))))
        d = ImageDraw.Draw(f)
        d.rounded_rectangle((90, 1620, 90 + int((W - 180) * tt / total), 1630), 5, fill=YEL + (230,))
        ff.stdin.write(f.convert("RGB").tobytes())
    if lector:
        lector.cerrar()
    ff.stdin.close()
    ff.wait()
    print(f"ok {out} {total:.1f}s")


if __name__ == "__main__":
    main()
