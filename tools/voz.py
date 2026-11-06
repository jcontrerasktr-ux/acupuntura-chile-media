"""Voz sintética en español (Kokoro vía sherpa-onnx) para los Reels.

Requiere: pip install --break-system-packages -r tools/requirements.txt
El modelo (~350 MB) se descarga solo desde GitHub la primera vez en /tmp/modelos_voz.
Voces: 28 = ef_dora (mujer), 29 = em_alex (hombre).
"""
import os
import subprocess
import wave

import numpy as np

DIR = os.environ.get("VOZ_DIR", "/tmp/modelos_voz")
MODELO = os.path.join(DIR, "kokoro-multi-lang-v1_0")
URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2"
_tts = None


def asegurar_modelo():
    if os.path.exists(os.path.join(MODELO, "model.onnx")):
        return
    os.makedirs(DIR, exist_ok=True)
    tar = os.path.join(DIR, "kokoro.tar.bz2")
    subprocess.run(["curl", "-sSL", "--retry", "3", "-o", tar, URL], check=True)
    subprocess.run(["tar", "xjf", tar, "-C", DIR], check=True)
    os.remove(tar)


def _motor():
    global _tts
    if _tts is None:
        import sherpa_onnx as so
        asegurar_modelo()
        d = MODELO
        cfg = so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(kokoro=so.OfflineTtsKokoroModelConfig(
            model=f"{d}/model.onnx", voices=f"{d}/voices.bin", tokens=f"{d}/tokens.txt",
            data_dir=f"{d}/espeak-ng-data", dict_dir=f"{d}/dict",
            lexicon=f"{d}/lexicon-us-en.txt,{d}/lexicon-zh.txt", lang="es"), num_threads=4))
        _tts = so.OfflineTts(cfg)
    return _tts


def sintetizar(texto, sid=28, velocidad=1.0):
    """Devuelve (muestras float32, frecuencia)."""
    a = _motor().generate(texto, sid=sid, speed=velocidad)
    if not a.samples:
        raise RuntimeError(f"La voz no generó audio para: {texto!r}")
    return np.clip(np.array(a.samples, dtype=np.float32), -1, 1), a.sample_rate


def guardar_wav(x, sr, ruta):
    with wave.open(ruta, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
