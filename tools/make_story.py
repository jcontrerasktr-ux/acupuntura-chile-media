"""Genera una historia (1080x1920 JPEG) desde un spec JSON.

Uso: python3 tools/make_story.py spec.json salida.jpg

Tipos:
  {"type": "mito",  "tag": "MITO O VERDAD", "mito": "...", "verdad": "..."}
  {"type": "tip",   "tag": "TIP DE BIENESTAR", "icon": "leaf", "title": "...", "body": "..."}
  {"type": "pregunta", "tag": "PREGUNTA", "question": "...", "hint": "Responde por mensaje directo"}
Todo el contenido queda dentro de la zona segura de historias (y 250 a 1580).
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from lib import *  # noqa


def scaled(im, k):
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)


def stack(img, items, y0, gap=34, ymax=1470):
    """Coloca capas una bajo otra. items: lista de capas RGBA. Devuelve y final."""
    y = y0
    for it in items:
        img.alpha_composite(it, (int(W / 2 - it.width / 2), int(y)))
        y += it.height + gap
    return y


def fit_text(text, size, **kw):
    """Reduce el tamaño de letra hasta que el texto sea razonable (máx. ~7 líneas)."""
    while size > 30:
        lay = text_layer(text, size, **kw)
        if lay.height <= size * 1.3 * 7:
            return lay
        size -= 4
    return text_layer(text, size, **kw)


def layout(spec):
    img = bg_frame(3.0)
    tag = pill_layer(spec.get("tag", "ACUPUNTURA · BIENESTAR"), 40, fill=TEAL)
    kind = spec.get("type", "tip")
    items = [logo(250), tag]
    if kind == "mito":
        items += [pill_layer("MITO", 50, fill=CORAL, pad=(50, 16)), fit_text(spec["mito"], 62, maxw=900),
                  pill_layer("VERDAD", 50, fill=(60, 140, 110), pad=(50, 16)), fit_text(spec["verdad"], 50, bold=False, maxw=900, line_h=1.3)]
    elif kind == "pregunta":
        items += [scaled(icon("body"), 0.55), fit_text(spec["question"], 74, maxw=900, stroke=1),
                  text_layer(spec.get("hint", "Responde por mensaje directo"), 40, color=YEL, maxw=800)]
    else:
        items += [scaled(icon(spec.get("icon", "leaf")), 0.6), fit_text(spec["title"], 68, color=YEL, maxw=900, stroke=1),
                  fit_text(spec["body"], 46, bold=False, maxw=880, line_h=1.3)]
    gap = 24
    total_h = sum(i.height for i in items) + gap * (len(items) - 1)
    y0 = 280 + max(0, (1200 - total_h) // 2) if total_h < 1200 else 280
    stack(img, items, y0, gap)
    footer_brand(img, 1530, spec.get("web", "acupuntura-chile.cl"))
    return img, y0 + total_h


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    img, bottom = layout(spec)
    if bottom > 1510:
        print(f"AVISO: el contenido llega a y={bottom}; acorta el texto.")
    img.convert("RGB").save(sys.argv[2], quality=93)
    print("ok", sys.argv[2], "fin contenido y =", bottom)


if __name__ == "__main__":
    main()
