"""Genera un carrusel de Instagram (láminas JPEG de 1080x1350, formato 4:5) desde un spec JSON.

Uso: python3 tools/make_carrusel.py spec.json carpeta_salida/
Crea carpeta_salida/lamina-01.jpg, lamina-02.jpg, ... (2 a 10 láminas).

Spec:
{
  "web": "acupuntura-chile.cl",
  "laminas": [
    {"tipo": "portada", "tag": "GUÍA PARA GUARDAR", "icono": "body", "titulo": "5 pausas de *1 minuto* para tu jornada", "sub": "Desliza para verlas"},
    {"tipo": "paso", "n": 1, "icono": "wave", "titulo": "Cambia de postura", "texto": "Cada hora, párate y camina un poco.", "guia": "saluda"},
    {"tipo": "cierre", "titulo": "Guarda y comparte", "texto": "Si el dolor es intenso o nuevo, consulta a un profesional.", "guia": "quieta"}
  ]
}
Íconos: leaf, moon, body, head, wave, curve. Guía: personaje propio de AcupunturaChile ("saluda" o "quieta").
Usa solo el logo de assets/. Todo el contenido queda dentro de la zona central (el perfil recorta los lados).
"""
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa
import make_reel_ilustrado as mri  # noqa

CW_, CH_ = 1080, 1350


def fondo():
    bg = bg_frame(3.0)
    y0 = (H - CH_) // 2
    return bg.crop((0, y0, W, y0 + CH_))


def guia(lam, im):
    g = lam.get("guia")
    if not g:
        return
    lay = mri.guia_layer(1.0, g)
    lay = lay.resize((lay.width // mri.SS, lay.height // mri.SS), Image.LANCZOS)
    rec = lay.crop((10, 440, 280, 820))
    rec = rec.resize((int(rec.width * 1.0), int(rec.height * 1.0)), Image.LANCZOS)
    im.alpha_composite(rec, (50, CH_ - rec.height - 30))


def esc(ic, k):
    return ic.resize((int(ic.width * k), int(ic.height * k)), Image.LANCZOS)


def lamina(lam, i, n, web):
    im = fondo()
    tipo = lam.get("tipo", "paso")
    if tipo == "portada":
        lg = logo(300)
        im.alpha_composite(lg, (CW_ // 2 - lg.width // 2, 70))
        tag = pill_layer(lam.get("tag", "GUÍA PARA GUARDAR"), 38, fill=TEAL)
        im.alpha_composite(tag, (CW_ // 2 - tag.width // 2, 440))
        ic = esc(icon(lam.get("icono", "leaf")), 0.62)
        im.alpha_composite(ic, (CW_ // 2 - ic.width // 2, 520))
        t = text_layer(lam["titulo"], 78, color=WHITE, maxw=900, stroke=1)
        im.alpha_composite(t, (CW_ // 2 - t.width // 2, 860))
        if lam.get("sub"):
            sb = pill_layer(lam["sub"], 38, fill=YEL, fg=TEAL_D)
            im.alpha_composite(sb, (CW_ // 2 - sb.width // 2, 860 + t.height + 40))
        footer_brand(im, 1260, web)
    elif tipo == "cierre":
        lg = logo(300)
        im.alpha_composite(lg, (CW_ // 2 - lg.width // 2, 50))
        t = text_layer(lam.get("titulo", "Guarda y comparte"), 70, color=YEL, maxw=860, stroke=1)
        im.alpha_composite(t, (CW_ // 2 - t.width // 2, 400))
        tx = text_layer(lam["texto"], 40, bold=False, maxw=840, line_h=1.28)
        im.alpha_composite(tx, (CW_ // 2 - tx.width // 2, 400 + t.height + 24))
        footer_brand(im, 1250, web)
        guia(lam, im)
    else:
        lg = logo(150)
        im.alpha_composite(lg, (80, 50))
        ct = pill_layer(f"{i}/{n}", 32, fill=TEAL_M)
        im.alpha_composite(ct, (CW_ - 80 - ct.width, 80))
        if lam.get("n") is not None:
            num = pill_layer(str(lam["n"]), 70, fill=YEL, fg=TEAL_D, pad=(40, 10))
            im.alpha_composite(num, (80, 260))
        t = text_layer(lam["titulo"], 86, color=YEL, maxw=900, align="left", stroke=1)
        im.alpha_composite(t, (80, 390))
        tx = text_layer(lam["texto"], 56, bold=False, maxw=880, align="left", line_h=1.3)
        im.alpha_composite(tx, (80, 390 + t.height + 36))
        if lam.get("icono"):
            ic = esc(icon(lam["icono"]), 0.62)
            im.alpha_composite(ic, (CW_ - ic.width - 40, CH_ - ic.height - 90))
        wl = text_layer(web, 32, color=(230, 240, 248), bold=False, maxw=600)
        im.alpha_composite(wl, (CW_ // 2 - wl.width // 2 + 120, CH_ - 70))
        guia(lam, im)
    return im.convert("RGB")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    lams = spec["laminas"]
    assert 2 <= len(lams) <= 10, "un carrusel lleva de 2 a 10 láminas"
    for i, lam in enumerate(lams, 1):
        im = lamina(lam, i, len(lams), spec.get("web", "acupuntura-chile.cl"))
        path = os.path.join(out, f"lamina-{i:02d}.jpg")
        im.save(path, quality=92)
        print("ok", path, im.size)


if __name__ == "__main__":
    main()
