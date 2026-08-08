#!/usr/bin/env python3
"""
Desktop Cat — Enhanced Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A feature-rich interactive desktop companion with:
  • Clean state machine (Idle, Walk, Sleep, Chase, Happy, Angry)
  • Click to pet (happy animation + optional sound)
  • Double-click speech bubbles with cat messages
  • Drag anywhere on screen to reposition
  • Right-click context menu (pet, message, settings, quit)
  • Mouse chasing behaviour
  • System tray icon (requires pystray + Pillow)
  • Settings window with live sliders & dark theme
  • Pixel-art sprite scaling (1×, 2×, 3×, 4×)
  • Config persistence (~/.desktop_cat_config.json)
  • Graceful fallbacks when optional deps are missing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run:  python main.py
Deps: pip install pywin32 Pillow pystray  (all optional but recommended)
"""

import tkinter as tk
import random
import json
import threading
import wave
import struct
import math
from enum import Enum, auto
from pathlib import Path

# ─── Optional dependencies ────────────────────────────────────────────────────

try:
    from win32api import GetMonitorInfo, MonitorFromPoint
    _WIN32 = True
except ImportError:
    _WIN32 = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    _PIL = True
except ImportError:
    _PIL = False

try:
    import pystray
    _TRAY = True
except ImportError:
    _TRAY = False

try:
    import winsound
    _SOUND = True
except ImportError:
    _SOUND = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path.home() / ".desktop_cat_config.json"

DEFAULTS: dict = {
    "speed":         3,      # walk pixels per tick
    "scale":         1,      # sprite zoom (1–4)
    "theme":         "classic", # cat version / skin
    "anim_ms":       150,    # ms between animation frames
    "always_on_top": True,
    "mouse_chasing": True,
    "sound":         True,
    "pos_x":         -1,     # -1 = use default
    "pos_y":         -1,
}

THEMES: dict[str, str] = {
    "classic":   "🤍  Classic White",
    "black":     "🖤  Midnight Black",
    "orange":    "🧡  Orange Tabby",
    "calico":    "🤍🧡🖤 Calico Patch",
    "pink":      "🌸  Pastel Pink",
    "golden":    "🍯  Golden Honey",
    "cyberpunk": "⚡  Cyberpunk Neon",
}


def load_cfg() -> dict:
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text())
            cfg = DEFAULTS.copy()
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
            return cfg
    except Exception:
        pass
    return DEFAULTS.copy()


def save_cfg(cfg: dict) -> None:
    try:
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# SOUND SYNTHESIS  (pure Python — no extra dependencies)
# ═══════════════════════════════════════════════════════════════════════════════

_SOUNDS_DIR = Path(__file__).parent / "sounds"


def _write_wav(path: Path, frames: list, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))


# ── Shared voice-synthesis primitives ─────────────────────────────────────────

def _glottal_source(n: int, sr: int, f0_fn, rng,
                    jitter: float = 0.008,
                    shimmer: float = 0.022,
                    noise_lvl: float = 0.10) -> list:
    """
    Generate a glottal-like source signal suitable for vocal-tract filtering.

    Models the output of a cat's larynx as:
      • Band-limited sawtooth wave (harmonic-rich, like real vocal fold vibration)
      • Frequency jitter  – tiny random perturbation each cycle (~0.8 %)
      • Amplitude shimmer – tiny random amplitude variation (~2.2 %)
      • Aspiration noise  – high-passed breathy noise blended in (~10 %)

    f0_fn(t) → fundamental frequency in Hz at time t.
    Returns a list of n float samples.
    """
    pi2   = 2 * math.pi
    phase = 0.0

    # One-pole low-pass for aspiration noise (keeps it in 1-5 kHz band)
    lp_c = pi2 * 4500 / sr;  lp_c /= 1 + lp_c
    hp_c = 1.0 / (pi2 * 900 / sr + 1)
    lp_z = hp_y = hp_x = 0.0

    out = []
    for i in range(n):
        t  = i / sr
        f0 = f0_fn(t) * (1.0 + rng.gauss(0, jitter))   # add jitter
        f0 = max(60.0, f0)

        phase = (phase + f0 / sr) % 1.0

        # Bandlimited sawtooth: sum of harmonics up to Nyquist (max 16)
        nh  = min(16, int(sr / (2 * f0)))
        saw = sum(math.sin(pi2 * k * phase) / k for k in range(1, nh + 1)) * (2 / math.pi)

        # Shimmer
        amp = 1.0 + rng.gauss(0, shimmer)

        # Aspiration: white noise → LP → HP (band ~900-4500 Hz)
        asp = rng.uniform(-1.0, 1.0)
        lp_z = lp_c * asp + (1 - lp_c) * lp_z
        hp_y = hp_c * (hp_y + lp_z - hp_x);  hp_x = lp_z

        out.append(saw * amp * (1 - noise_lvl) + hp_y * noise_lvl)
    return out


def _resonator_cascade(samples: list, sr: int, formant_fn, block: int = 64) -> list:
    """
    Pass samples through cascaded all-pole resonator filters (vocal tract model).

    formant_fn(p) → [(freq_hz, bandwidth_hz), ...]
    p is 0..1 normalised progress through the signal.
    Filter coefficients are recomputed every `block` samples, giving smooth
    time-varying formant transitions with very low computational overhead.

    Each resonator uses the standard 2-pole transfer function:
        y[n] = 2R·cos(ω)·y[n-1] − R²·y[n-2] + (1−R)·x[n]
    where R = 1 − π·BW/sr.
    """
    n      = len(samples)
    num_f  = len(formant_fn(0.0))
    states = [(0.0, 0.0)] * num_f   # (y1, y2) per resonator

    result = []
    i = 0
    while i < n:
        p    = i / n
        fmts = formant_fn(p)

        # Compute resonator coefficients for this block
        coeffs = []
        for freq, bw in fmts:
            freq = max(20.0, min(freq, sr * 0.49))
            bw   = max(10.0, bw)
            R    = 1.0 - math.pi * bw / sr
            R    = max(0.0, min(R, 0.9999))
            w    = 2 * math.pi * freq / sr
            coeffs.append((2 * R * math.cos(w), -(R * R), 1 - R))

        blk_end = min(i + block, n)
        seg     = samples[i:blk_end]

        # Cascade: output of each resonator feeds the next
        for f_idx, (c1, c2, gain) in enumerate(coeffs):
            y1, y2   = states[f_idx]
            seg_out  = []
            for x in seg:
                y = c1 * y1 + c2 * y2 + x * gain
                seg_out.append(y)
                y2, y1 = y1, y
            states[f_idx] = (y1, y2)
            seg = seg_out

        result.extend(seg)
        i = blk_end

    return result


def _normalise_and_pack(samples: list, env_fn, master_gain: float = 0.50) -> list:
    """Normalise, apply amplitude envelope, and pack to 16-bit signed frames."""
    mx     = max(abs(s) for s in samples) or 1.0
    frames = []
    n      = len(samples)
    for i, s in enumerate(samples):
        s  /= mx
        env = env_fn(i / n)
        val = max(-32768, min(32767, int(env * master_gain * 32767 * s)))
        frames.append(struct.pack("<h", val))
    return frames


# ── Per-sound generators ───────────────────────────────────────────────────────

def _gen_meow(path: Path, sample_rate: int = 44100) -> None:
    """
    Realistic cat meow using SOURCE-FILTER voice synthesis.

    Source : bandlimited sawtooth + jitter + shimmer + aspiration noise
             (models the cat's laryngeal output)
    Filter : cascaded all-pole resonators at F1, F2, F3
             (models the cat's vocal tract shaping)

    Formant trajectory (cat vocal tract is ~4-5 cm, formants ≈3× human):
      'mmmm' onset → 'ee' vowel  → 'ow' vowel → tail
      F1  350 → 1 100 Hz  (mouth opens)
      F2 3000 → 1 600 Hz  (tongue body retracts, classic ee→ow shift)
      F3 4200 → 3 400 Hz  (third formant, adds brightness)
    """
    import random as _rnd
    rng = _rnd.Random(2024_01)
    sr  = sample_rate
    dur = 0.85
    n   = int(sr * dur)

    # ── F0 contour ──────────────────────────────────────────────────────
    def f0(t: float) -> float:
        p = t / dur
        if p < 0.22:   return 290 + 460 * (p / 0.22) ** 0.60   # slow rise
        elif p < 0.50: return 750 + 70  * ((p - 0.22) / 0.28)  # peak plateau
        elif p < 0.78: return 820 - 500 * ((p - 0.50) / 0.28)  # steep fall
        else:          return 320 - 90  * ((p - 0.78) / 0.22)  # tail

    # Natural vibrato (kicks in at ~25 % through)
    def f0_vib(t: float) -> float:
        p   = t / dur
        base = f0(t)
        if p > 0.25:
            depth = min((p - 0.25) / 0.14, 1.0) * 0.024
            base *= 1.0 + depth * math.sin(2 * math.pi * 5.6 * t)
        return base

    # ── Glottal source ──────────────────────────────────────────────────
    src = _glottal_source(n, sr, f0_vib, rng,
                          jitter=0.008, shimmer=0.022, noise_lvl=0.09)

    # ── Vocal-tract formant filter ───────────────────────────────────────
    def formants(p: float):
        # F1: low at 'ee', rises to open 'ow'
        F1 = 350  + 750  * min(p / 0.68, 1.0)    # 350  → 1100 Hz
        # F2: high at 'ee', falls to back 'ow'
        F2 = 3000 - 1400 * min(p / 0.68, 1.0)    # 3000 → 1600 Hz
        # F3: slight descent, adds air/brightness
        F3 = 4200 - 800  * min(p / 0.75, 1.0)    # 4200 → 3400 Hz
        return [(F1, 160), (F2, 220), (F3, 350)]

    filtered = _resonator_cascade(src, sr, formants)

    # ── Amplitude envelope ───────────────────────────────────────────────
    def env(p: float) -> float:
        if p < 0.11:  return (p / 0.11) ** 1.8   # slow 'm' onset
        elif p > 0.78: return ((1 - p) / 0.22) ** 0.80
        return 1.0

    _write_wav(path, _normalise_and_pack(filtered, env, 0.52), sr)


def _gen_happy_meow(path: Path, sr: int = 44100) -> None:
    """
    Happy cat chirp 'mrrp!' — source-filter synthesis.

    A short, bright, upward-sweeping trill.  Cats use this as a greeting
    or acknowledgement; it's characterised by a quick pitch rise, high F2
    (stays in the 'ee'-like region), and a snappy envelope.

    F0: 480 → 1 100 → 800 Hz  (rapid rise, slight fall)
    F1: 500 → 700 Hz           (small opening)
    F2: 3 200 → 2 600 Hz       (stays high = bright / cheerful)
    F3: 4 500 → 4 000 Hz
    """
    import random as _rnd
    rng = _rnd.Random(2024_02)
    dur = 0.40
    n   = int(sr * dur)

    def f0(t: float) -> float:
        p = t / dur
        if p < 0.50: return 480 + 620 * (p / 0.50) ** 0.55   # 480 → 1100 Hz
        else:        return 1100 - 300 * ((p - 0.50) / 0.50)  # 1100 → 800 Hz

    src = _glottal_source(n, sr, f0, rng,
                          jitter=0.006, shimmer=0.018, noise_lvl=0.07)

    def formants(p: float):
        F1 = 500 + 200  * min(p / 0.60, 1.0)   # 500  → 700  Hz
        F2 = 3200 - 600 * min(p / 0.60, 1.0)   # 3200 → 2600 Hz (stays bright)
        F3 = 4500 - 500 * min(p / 0.65, 1.0)   # 4500 → 4000 Hz
        return [(F1, 130), (F2, 200), (F3, 320)]

    filtered = _resonator_cascade(src, sr, formants)

    def env(p: float) -> float:
        if p < 0.06:  return p / 0.06            # instant attack
        elif p > 0.65: return ((1 - p) / 0.35) ** 0.7
        return 1.0

    _write_wav(path, _normalise_and_pack(filtered, env, 0.50), sr)


def _gen_angry_meow(path: Path, sr: int = 44100) -> None:
    """
    Angry cat yowl — source-filter synthesis with growl-phase roughness.

    Two phases:
      1. Growl  (0–30 %): low F0 (135–310 Hz), higher jitter/shimmer/noise
                           to get that rough, threatening texture
      2. Yowl   (30–100%): pitch rockets to 750 Hz, formants shift to a
                            more open/harsh vowel, then tail off

    Amplitude tremolo during the growl (20 Hz wobble) adds the shaky,
    threatening quality of an angry cat.
    """
    import random as _rnd
    rng = _rnd.Random(2024_03)
    dur = 0.88
    n   = int(sr * dur)

    def f0(t: float) -> float:
        p = t / dur
        if p < 0.28:   return 135 + 185 * (p / 0.28)            # 135 → 320 Hz  growl
        elif p < 0.56: return 320 + 400 * ((p - 0.28) / 0.28)   # 320 → 720 Hz  rise
        elif p < 0.78: return 720 + 40  * ((p - 0.56) / 0.22)   # 720 → 760 Hz  peak
        else:          return 760 - 400 * ((p - 0.78) / 0.22)   # 760 → 360 Hz  tail

    # More jitter + shimmer + noise during the growl phase
    def f0_rough(t: float) -> float:
        p    = t / dur
        base = f0(t)
        extra_j = 0.025 * max(0.0, 1 - p / 0.30)   # extra jitter in growl
        return base * (1.0 + rng.gauss(0, extra_j))

    # Higher noise level overall for angry roughness
    src = _glottal_source(n, sr, f0_rough, rng,
                          jitter=0.015, shimmer=0.045, noise_lvl=0.22)

    def formants(p: float):
        if p < 0.28:
            # Growl: narrow, low formants
            F1 = 350  + 150 * (p / 0.28)         # 350 → 500 Hz
            F2 = 1500 + 500 * (p / 0.28)         # 1500 → 2000 Hz
            F3 = 2800 + 400 * (p / 0.28)         # 2800 → 3200 Hz
        else:
            q  = (p - 0.28) / 0.72
            F1 = 500  + 700  * min(q / 0.70, 1.0)  # 500  → 1200 Hz (opens wide)
            F2 = 2000 + 600  * min(q / 0.65, 1.0)  # 2000 → 2600 Hz (harsh vowel)
            F3 = 3200 + 600  * min(q / 0.70, 1.0)  # 3200 → 3800 Hz
        return [(F1, 200), (F2, 280), (F3, 400)]

    filtered = _resonator_cascade(src, sr, formants)

    def env(p: float) -> float:
        if p < 0.03:   e = p / 0.03
        elif p > 0.86: e = (1 - p) / 0.14
        else:          e = 1.0
        # Aggressive tremolo in the growl phase
        if p < 0.35:
            depth = min(p / 0.10, 1.0) * 0.25
            e *= 1.0 - depth + depth * abs(math.sin(2 * math.pi * 22 * p / dur * dur))
        return e

    _write_wav(path, _normalise_and_pack(filtered, env, 0.54), sr)


    """
    Realistic cat meow using FM synthesis + formant transitions.

    Real meow anatomy:
      • A nasal 'm' onset  (quiet, ~300 Hz)
      • Rising 'ee' vowel  (high 2nd formant, pitch peaks ~700-800 Hz)
      • Falling 'ow' vowel (2nd formant drops, pitch ~350 Hz)
      • Gentle tail-off
    FM synthesis gives the rich voice-like harmonic content;
    a sweeping second-formant sinusoid adds the ee→ow timbral shift.
    """
    dur = 0.80
    n   = int(sample_rate * dur)
    frames = []
    carrier_phase = 0.0          # persistent phase accumulator

    for i in range(n):
        t = i / sample_rate
        p = t / dur              # 0 → 1

        # ── Fundamental frequency contour ────────────────────────────
        # Modelled on actual cat meow spectrograms:
        #   onset ~320 Hz  →  peak ~750 Hz  →  tail ~280 Hz
        if p < 0.22:
            f0 = 320 + 430 * (p / 0.22) ** 0.65        # slow rise
        elif p < 0.52:
            f0 = 750 + 60  * ((p - 0.22) / 0.30)       # slight peak wobble
        elif p < 0.78:
            f0 = 810 - 470 * ((p - 0.52) / 0.26)       # steep fall
        else:
            f0 = 340 - 80  * ((p - 0.78) / 0.22)       # tail

        # ── FM modulation index (harmonic richness) ───────────────────
        # Higher index = more harmonics = brighter / more nasal sound
        # Peaks in the 'ee' vowel section, softer at start/end
        mod_idx = 1.4 + 2.8 * math.sin(math.pi * min(p / 0.85, 1.0))

        # Modulator frequency: f0/2 gives sub-harmonic warmth
        modulator = math.sin(2 * math.pi * (f0 / 2.2) * t)

        # Advance carrier phase (avoids discontinuities when f0 changes)
        carrier_phase += 2 * math.pi * f0 / sample_rate
        carrier = math.sin(carrier_phase + mod_idx * modulator)

        # ── Second formant: 'ee' (≈2200 Hz) → 'ow' (≈800 Hz) ─────────
        # This is the key timbral shift that separates meow from a plain beep
        f2 = 2200 - 1500 * min(p / 0.65, 1.0)
        formant = 0.28 * math.sin(2 * math.pi * f2 * t)

        sig = (carrier + formant) / 1.28

        # ── Amplitude envelope ────────────────────────────────────────
        # Slow nasal 'm' onset, full sustain, smooth decay
        if p < 0.13:
            env = (p / 0.13) ** 1.8     # gradual attack
        elif p > 0.76:
            env = ((1 - p) / 0.24) ** 0.75
        else:
            env = 1.0

        # ── Natural vibrato (kicks in mid-vowel) ──────────────────────
        if p > 0.25:
            depth = min((p - 0.25) / 0.18, 1.0) * 0.028
            sig *= 1.0 + depth * math.sin(2 * math.pi * 5.8 * t)

        val = max(-32768, min(32767, int(env * 0.44 * 32767 * sig)))
        frames.append(struct.pack("<h", val))

    _write_wav(path, frames, sample_rate)


def _gen_purr(path: Path, sample_rate: int = 44100) -> None:
    """
    Realistic cat purr using filtered noise + asymmetric amplitude modulation.

    Real purr anatomy:
      • Cats purr at 20–30 Hz (both inhale and exhale)
      • Each burst is a short rough rumble (noise filtered ~80–350 Hz)
      • The exhale burst is louder/longer than the inhale
      • A low 50–100 Hz resonance adds warmth (chest/throat cavity)
    """
    import random as _rnd
    rng = _rnd.Random(99991)       # fixed seed → same WAV every regeneration

    dur = 1.60
    n   = int(sample_rate * dur)

    # ── One-pole low-pass filter  (removes harsh high-freq content) ──
    # y[n] = a*x[n] + (1-a)*y[n-1],  cutoff ≈ 380 Hz
    lp_a  = 2 * math.pi * 380 / sample_rate
    lp_a /= 1 + lp_a
    lp_z  = 0.0

    # ── One-pole high-pass filter  (removes DC and sub-20 Hz rumble) ─
    # y[n] = hp*(y[n-1] + x[n] - x[n-1]),  cutoff ≈ 70 Hz
    hp_rc = 1.0 / (2 * math.pi * 70 / sample_rate + 1)
    hp_y  = 0.0
    hp_x  = 0.0

    purr_rate = 26.0   # Hz  (typical domestic cat)
    frames = []

    for i in range(n):
        t = i / sample_rate
        p = t / dur

        # ── Filtered noise source (throat texture) ────────────────────
        x = rng.uniform(-1.0, 1.0)
        lp_z = lp_a * x + (1 - lp_a) * lp_z          # low-pass
        hp_xn = lp_z
        hp_y  = hp_rc * (hp_y + hp_xn - hp_x)         # high-pass
        hp_x  = hp_xn
        noise = hp_y

        # ── Asymmetric purr modulation ────────────────────────────────
        # cycle: 0.0 → 1.0 within each purr period
        cycle = math.fmod(purr_rate * t, 1.0)
        if cycle < 0.58:
            # Exhale phase: louder, hanning-shaped burst
            bp = cycle / 0.58
            mod = math.sin(math.pi * bp) ** 1.2   # smooth bell shape
        else:
            # Inhale phase: quieter, shorter rumble
            ip = (cycle - 0.58) / 0.42
            mod = 0.22 * math.sin(math.pi * ip)

        # ── Throat resonance tones (body cavity warmth) ───────────────
        resonance = (
            0.18 * math.sin(2 * math.pi *  50 * t)
            + 0.12 * math.sin(2 * math.pi * 100 * t)
            + 0.06 * math.sin(2 * math.pi * 150 * t)
        )

        # Mix noise (rough texture) + resonance (warmth)
        sig = (noise * 0.72 + resonance) * mod

        # ── Global envelope (fade in / sustain / fade out) ────────────
        env = (p / 0.14) if p < 0.14 else ((1 - p) / 0.16 if p > 0.84 else 1.0)

        val = max(-32768, min(32767, int(env * 0.58 * 32767 * sig)))
        frames.append(struct.pack("<h", val))

    _write_wav(path, frames, sample_rate)


def _gen_happy_meow(path: Path, sr: int = 44100) -> None:
    """
    Happy cat chirp 'mrrp!' — bright, short, ascending.
    Cats make this quick trill as a greeting or expression of delight.
      • Short duration (~0.38 s)
      • Rapid pitch rise: 420 Hz → 1050 Hz → 700 Hz
      • High FM modulation index = sparkly, cheerful timbre
      • Fast attack, snappy decay
    """
    dur = 0.38
    n   = int(sr * dur)
    frames = []
    cp = 0.0                     # persistent carrier phase

    for i in range(n):
        t = i / sr
        p = t / dur

        # Quick rising chirp pitch contour
        if p < 0.55:
            f0 = 420 + 630 * (p / 0.55) ** 0.55   # 420 → 1050 Hz  (fast rise)
        else:
            f0 = 1050 - 350 * ((p - 0.55) / 0.45)  # 1050 → 700 Hz  (gentle fall)

        # Bright FM — high mod index makes it sparkly/cheerful
        mi = 2.4 + 2.0 * math.sin(math.pi * p)
        modulator = math.sin(2 * math.pi * (f0 / 1.75) * t)
        cp += 2 * math.pi * f0 / sr
        sig = math.sin(cp + mi * modulator)

        # Snappy envelope: instant attack, quick tail
        env = (p / 0.05) if p < 0.05 else ((1 - p) / 0.32 if p > 0.68 else 1.0)

        val = max(-32768, min(32767, int(env * 0.46 * 32767 * sig)))
        frames.append(struct.pack("<h", val))

    _write_wav(path, frames, sr)


def _gen_angry_meow(path: Path, sr: int = 44100) -> None:
    """
    Angry cat yowl — starts as a low growl, erupts into a harsh yowl.
      • Low-frequency growl phase (140–300 Hz) with noise + tremolo
      • Rapid rise into harsh yowl (300–730 Hz)
      • Very high FM modulation index → buzzy, aggressive character
      • Noise mixed in during growl phase for rough texture
    """
    import random as _rnd
    rng = _rnd.Random(77777)     # fixed seed → reproducible WAV

    dur = 0.82
    n   = int(sr * dur)

    # Low-pass filter for noise component (keep growl warm, not hissy)
    lp_a = 2 * math.pi * 320 / sr
    lp_a /= 1 + lp_a
    lp_z  = 0.0

    frames = []
    cp = 0.0

    for i in range(n):
        t = i / sr
        p = t / dur

        # Pitch: deep growl → aggressive yowl peak → tail off
        if p < 0.28:
            f0 = 135 + 175 * (p / 0.28)            # 135 → 310 Hz  (growl)
        elif p < 0.55:
            f0 = 310 + 370 * ((p - 0.28) / 0.27)  # 310 → 680 Hz  (yowl rise)
        elif p < 0.78:
            f0 = 680 + 70  * ((p - 0.55) / 0.23)  # 680 → 750 Hz  (yowl peak)
        else:
            f0 = 750 - 380 * ((p - 0.78) / 0.22)  # 750 → 370 Hz  (tail)

        # Modulation index: very high + rapid variation in growl phase
        # (the rapid variation is what gives the "angry rumble" texture)
        if p < 0.32:
            mi = 5.5 + 3.0 * math.sin(2 * math.pi * 14 * t)
        else:
            mi = 3.2 + 1.6 * math.sin(math.pi * p)

        modulator = math.sin(2 * math.pi * f0 * 1.45 * t)
        cp += 2 * math.pi * f0 / sr
        carrier = math.sin(cp + mi * modulator)

        # Noise: prominent in growl phase, fades during yowl
        x = rng.uniform(-1.0, 1.0)
        lp_z = lp_a * x + (1 - lp_a) * lp_z
        noise_amt = max(0.0, 0.38 - 0.38 * (p / 0.45))
        sig = carrier * (1 - noise_amt) + lp_z * noise_amt

        # Hard attack, flat sustain, abrupt cutoff (cat stops mid-yowl)
        if p < 0.035:
            env = p / 0.035
        elif p > 0.87:
            env = (1 - p) / 0.13
        else:
            env = 1.0

        # Angry tremolo during growl (shaky, threatening)
        if p < 0.38:
            depth = min(p / 0.12, 1.0) * 0.20
            env *= 1.0 - depth + depth * abs(math.sin(2 * math.pi * 20 * t))

        val = max(-32768, min(32767, int(env * 0.52 * 32767 * sig)))
        frames.append(struct.pack("<h", val))

    _write_wav(path, frames, sr)


def ensure_sounds() -> tuple[Path, Path, Path, Path]:
    """(Re)generate all four cat WAV files. Returns (meow, purr, happy, angry)."""
    _SOUNDS_DIR.mkdir(exist_ok=True)
    meow_path  = _SOUNDS_DIR / "meow.wav"
    purr_path  = _SOUNDS_DIR / "purr.wav"
    happy_path = _SOUNDS_DIR / "happy.wav"
    angry_path = _SOUNDS_DIR / "angry.wav"
    _gen_meow(meow_path)
    _gen_purr(purr_path)
    _gen_happy_meow(happy_path)
    _gen_angry_meow(angry_path)
    return meow_path, purr_path, happy_path, angry_path


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def work_area() -> tuple[int, int]:
    """Return (screen_width, work_area_height) excluding taskbar."""
    if _WIN32:
        try:
            info = GetMonitorInfo(MonitorFromPoint((0, 0)))
            wa = info["Work"]
            return wa[2], wa[3]
        except Exception:
            pass
    # Tkinter fallback
    r = tk.Tk()
    r.withdraw()
    w = r.winfo_screenwidth()
    h = r.winfo_screenheight() - 48
    r.destroy()
    return w, h


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════════

class S(Enum):
    IDLE       = auto()
    TO_SLEEP   = auto()
    SLEEPING   = auto()
    FROM_SLEEP = auto()
    WALK_L     = auto()
    WALK_R     = auto()
    CHASE      = auto()
    HAPPY      = auto()
    ANGRY      = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# CAT MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

MESSAGES = [
    "Nyaa~ ♪",
    "Pet me! (=^･ω･^=)",
    "I can haz snack? 🐟",
    "*purrs loudly*",
    "Meow? ( ˘ω˘ )",
    "zzz… huh? 😺",
    "This is my territory now.",
    "*knocks your files off the desk*",
    "I see you working. I approve.",
    "Did you pet me enough? No.",
    "Purrfectly content~ ♡",
    "I'm helping by sitting here.",
    "Meow meow meow! 🐾",
    "Focus? What focus? 😼",
    "I require immediate attention.",
    "Your lap is mine now. Deal with it.",
    "Have you considered more pets?",
    "Mrrrow… (╹◡╹)♡",
]


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class Sprites:
    """Loads, scales (nearest-neighbour), colors and caches sprite frames."""

    DIR = Path(__file__).parent / "assets"

    def __init__(self, scale: int, theme: str = "classic"):
        self.scale = max(1, int(scale))
        self.theme = theme if theme in THEMES else "classic"
        self._cache: dict = {}

    @staticmethod
    def apply_theme(img: "Image.Image", theme: str) -> "Image.Image":
        """Transform white/light-grey cat sprite into custom theme RGBA colors."""
        if theme == "classic" or not _PIL:
            return img
        import numpy as np

        arr = np.array(img, dtype=np.float32)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
        mask = a > 0

        # Luminance of non-transparent pixels (0 to 1)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

        out_r, out_g, out_b = r.copy(), g.copy(), b.copy()

        if theme == "black":
            # Sleek dark charcoal/black cat with deep contrast
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = 30 + (lum[fur_mask] * 60)
            out_g[fur_mask] = 32 + (lum[fur_mask] * 62)
            out_b[fur_mask] = 40 + (lum[fur_mask] * 65)
            outline = mask & (lum <= 0.2)
            out_r[outline] = 10; out_g[outline] = 10; out_b[outline] = 14

        elif theme == "orange":
            # Warm Ginger / Orange Tabby cat
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 150)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 45)
            outline = mask & (lum <= 0.2)
            out_r[outline] = 85; out_g[outline] = 38; out_b[outline] = 10

        elif theme == "calico":
            # Tri-color patch (White, Orange, Charcoal patches)
            h, w = arr.shape[:2]
            yy, xx = np.ogrid[:h, :w]
            patch1 = ((xx // 9 + yy // 9) % 3 == 1) & mask & (lum > 0.28)
            patch2 = ((xx // 9 + yy // 9) % 3 == 2) & mask & (lum > 0.28)
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = lum[fur_mask] * 245
            out_g[fur_mask] = lum[fur_mask] * 240
            out_b[fur_mask] = lum[fur_mask] * 235
            # Orange patches
            out_r[patch1] = lum[patch1] * 245
            out_g[patch1] = lum[patch1] * 125
            out_b[patch1] = lum[patch1] * 35
            # Black patches
            out_r[patch2] = lum[patch2] * 40
            out_g[patch2] = lum[patch2] * 40
            out_b[patch2] = lum[patch2] * 45

        elif theme == "pink":
            # Soft Sakura / Pastel Pink cat
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 180)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 215)
            outline = mask & (lum <= 0.2)
            out_r[outline] = 120; out_g[outline] = 60; out_b[outline] = 95

        elif theme == "golden":
            # Warm Golden Honey cat
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 205)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 65)
            outline = mask & (lum <= 0.2)
            out_r[outline] = 95; out_g[outline] = 68; out_b[outline] = 15

        elif theme == "cyberpunk":
            # Cyberpunk Neon: Cyan body with Magenta outline accents
            fur_mask = mask & (lum > 0.2)
            out_r[fur_mask] = lum[fur_mask] * 30
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 230)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            outline = mask & (lum <= 0.2)
            out_r[outline] = 200; out_g[outline] = 20; out_b[outline] = 190

        res = np.stack([out_r, out_g, out_b, a], axis=-1).astype(np.uint8)
        return Image.fromarray(res, "RGBA")

    # ------------------------------------------------------------------
    def _load(self, name: str):
        key = (name, self.scale, self.theme)
        if key in self._cache:
            return self._cache[key]
        path = str(self.DIR / name)
        if _PIL:
            im = Image.open(path).convert("RGBA")
            if self.theme != "classic":
                im = self.apply_theme(im, self.theme)
            if self.scale != 1:
                im = im.resize(
                    (im.width * self.scale, im.height * self.scale),
                    Image.NEAREST,
                )
            ph = ImageTk.PhotoImage(im)
        else:
            ph = tk.PhotoImage(file=path)
            if self.scale > 1:
                ph = ph.zoom(self.scale, self.scale)
        self._cache[key] = ph
        return ph

    def seq(self, *names):
        return [self._load(n) for n in names]

    # ------------------------------------------------------------------
    def sprite_size(self) -> tuple[int, int]:
        """(width, height) of a scaled idle frame."""
        if _PIL:
            im = Image.open(str(self.DIR / "idle1.png"))
            return im.width * self.scale, im.height * self.scale
        ph = self._load("idle1.png")
        return ph.width(), ph.height()

    # ------------------------------------------------------------------
    def load_all(self) -> dict:
        return {
            "idle": self.seq(
                "idle1.png", "idle2.png", "idle3.png", "idle4.png",
            ),
            "to_sleep": self.seq(
                "sleeping1.png", "sleeping2.png", "sleeping3.png",
                "sleeping4.png", "sleeping5.png", "sleeping6.png",
            ),
            "sleeping": self.seq(
                "zzz1.png", "zzz2.png", "zzz3.png", "zzz4.png",
            ),
            "from_sleep": self.seq(
                "sleeping6.png", "sleeping5.png", "sleeping4.png",
                "sleeping3.png", "sleeping2.png", "sleeping1.png",
            ),
            "walk_l": self.seq(
                "walkingleft1.png", "walkingleft2.png",
                "walkingleft3.png", "walkingleft4.png",
            ),
            "walk_r": self.seq(
                "walkingright1.png", "walkingright2.png",
                "walkingright3.png", "walkingright4.png",
            ),
            "angry": self.seq("angry.png", "angry.png", "angry.png"),
            "happy": self.seq(
                "idle3.png", "idle4.png", "idle3.png", "idle2.png",
            ),
        }

    # ------------------------------------------------------------------
    def make_tray_image(self) -> "Image.Image | None":
        """32×32 pixel cat face for system tray matching current theme."""
        if not _PIL:
            return None
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        fills = {
            "classic":   ("#aaaaaa", "#777777", "#ffbbbb"),
            "black":     ("#333333", "#111111", "#ffdd44"),
            "orange":    ("#ff9933", "#cc5500", "#ffee88"),
            "calico":    ("#e8ded1", "#333333", "#ff9933"),
            "pink":      ("#ffb6c1", "#e68a9a", "#ffffff"),
            "golden":    ("#e6b800", "#997a00", "#77ff77"),
            "cyberpunk": ("#00f0ff", "#ff007f", "#ff00ff"),
        }
        body_fill, outline_c, ear_fill = fills.get(self.theme, fills["classic"])

        # Body / face ellipse
        d.ellipse([4, 9, 28, 29], fill=body_fill, outline=outline_c, width=1)
        # Ears
        d.polygon([(4, 13), (0, 4), (9, 11)], fill=body_fill)
        d.polygon([(28, 13), (32, 4), (23, 11)], fill=body_fill)
        d.polygon([(5, 12), (2, 5), (9, 11)], fill=ear_fill)
        d.polygon([(27, 12), (30, 5), (23, 11)], fill=ear_fill)
        # Eyes
        d.ellipse([10, 16, 14, 21], fill="#222222")
        d.ellipse([18, 16, 22, 21], fill="#222222")
        d.ellipse([11, 16, 13, 18], fill="#ffffff")
        d.ellipse([19, 16, 21, 18], fill="#ffffff")
        # Nose
        d.polygon([(14, 23), (18, 23), (16, 25)], fill="#ff99aa")
        # Whiskers
        d.line([(0, 22), (12, 23)], fill="#888888", width=1)
        d.line([(20, 23), (32, 22)], fill="#888888", width=1)
        return img



# ═══════════════════════════════════════════════════════════════════════════════
# SPEECH BUBBLE
# ═══════════════════════════════════════════════════════════════════════════════

class Bubble:
    """A small auto-dismissing speech bubble Toplevel."""

    # Catppuccin-inspired palette
    BG     = "#fffbe6"
    BORDER = "#e8a000"
    TEXT   = "#2d2a1e"

    def __init__(self, root: tk.Tk, cat_x: int, cat_y: int,
                 cat_w: int, scale: int):
        msg = random.choice(MESSAGES)
        self._top = tk.Toplevel(root)
        top = self._top
        top.overrideredirect(True)
        top.attributes("-topmost", True)

        font_size = max(8, 8 + scale)
        font = ("Segoe UI", font_size, "bold")

        # Outer frame acts as border
        outer = tk.Frame(top, bg=self.BORDER, padx=2, pady=2)
        outer.pack()
        inner = tk.Frame(outer, bg=self.BG, padx=10, pady=6)
        inner.pack()
        tk.Label(
            inner, text=msg, font=font,
            bg=self.BG, fg=self.TEXT, wraplength=280,
        ).pack()

        # Arrow indicator (▼) below bubble
        tk.Label(top, text="▼", font=("Segoe UI", 8),
                 bg=self.BORDER, fg=self.BG).pack(pady=(0, 0))

        top.update_idletasks()
        bw = top.winfo_reqwidth()
        bh = top.winfo_reqheight()

        sw = top.winfo_screenwidth()
        bx = max(0, min(cat_x + cat_w // 2 - bw // 2, sw - bw))
        by = max(0, cat_y - bh - 4)

        top.geometry(f"+{bx}+{by}")

        # Fade-out after 3.5 s
        top.after(3500, self.close)

    def close(self):
        try:
            self._top.destroy()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsWin:
    """Dark-themed settings Toplevel."""

    # Catppuccin Mocha palette
    BG      = "#1e1e2e"
    SURFACE = "#313244"
    OVERLAY = "#45475a"
    TEXT    = "#cdd6f4"
    SUBTEXT = "#a6adc8"
    ACCENT  = "#cba6f7"   # mauve
    GREEN   = "#a6e3a1"
    YELLOW  = "#f9e2af"
    HEADER  = "#181825"

    def __init__(self, parent: tk.Tk, cfg: dict, on_apply):
        self._cfg = cfg.copy()
        self._on_apply = on_apply
        self._parent = parent

        self.top = tk.Toplevel(parent)
        self.top.title("🐱 Desktop Cat — Settings")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)
        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy)

        self._build()
        # Centre on screen
        self.top.update_idletasks()
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w, h = 380, 510
        self.top.geometry(f"{w}x{h}+{(sw - w)//2}+{(sh - h)//2}")

    # ------------------------------------------------------------------
    def _build(self):
        # ── Header ──────────────────────────────────────────────────
        hdr = tk.Frame(self.top, bg=self.HEADER, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐱  Desktop Cat",
                 font=("Segoe UI", 15, "bold"),
                 bg=self.HEADER, fg=self.ACCENT).pack()
        tk.Label(hdr, text="Customise your desktop companion",
                 font=("Segoe UI", 9),
                 bg=self.HEADER, fg=self.SUBTEXT).pack()

        # ── Content ─────────────────────────────────────────────────
        body = tk.Frame(self.top, bg=self.BG, padx=22)
        body.pack(fill="both", expand=True)

        def section(label: str):
            tk.Frame(body, bg=self.OVERLAY, height=1).pack(fill="x", pady=(14, 0))
            tk.Label(body, text=label,
                     font=("Segoe UI", 9, "bold"),
                     bg=self.BG, fg=self.ACCENT, anchor="w").pack(fill="x", pady=(4, 2))

        def slider_row(label: str, key: str,
                       lo: float, hi: float, res: float = 1):
            row = tk.Frame(body, bg=self.BG)
            row.pack(fill="x", pady=3)

            tk.Label(row, text=label, font=("Segoe UI", 9),
                     bg=self.BG, fg=self.TEXT,
                     width=20, anchor="w").pack(side="left")

            val_var = tk.DoubleVar(value=self._cfg.get(key, lo))
            val_lbl = tk.Label(row, textvariable=val_var,
                               font=("Segoe UI", 9, "bold"),
                               bg=self.BG, fg=self.YELLOW, width=5)
            val_lbl.pack(side="right")

            def cmd(v, k=key, vv=val_var, r=res):
                fv = round(float(v) / r) * r
                display = int(fv) if r >= 1 else round(fv, 1)
                vv.set(display)
                self._cfg[k] = display

            scl = tk.Scale(
                row, from_=lo, to=hi, orient="horizontal",
                resolution=res, showvalue=False,
                bg=self.BG, fg=self.TEXT,
                troughcolor=self.OVERLAY,
                highlightbackground=self.BG,
                activebackground=self.ACCENT,
                command=cmd,
            )
            scl.set(self._cfg.get(key, lo))
            scl.pack(side="left", fill="x", expand=True, padx=(6, 6))

        def toggle_row(label: str, key: str):
            row = tk.Frame(body, bg=self.BG)
            row.pack(fill="x", pady=3)
            var = tk.BooleanVar(value=bool(self._cfg.get(key, False)))

            def cmd(k=key, v=var):
                self._cfg[k] = v.get()

            ck = tk.Checkbutton(
                row, text=label, variable=var, command=cmd,
                font=("Segoe UI", 9),
                bg=self.BG, fg=self.TEXT,
                selectcolor=self.SURFACE,
                activebackground=self.BG, activeforeground=self.TEXT,
                relief="flat", highlightthickness=0,
            )
            ck.pack(side="left")

        # Behaviour
        section("⚙️   Behaviour")
        slider_row("Walk Speed  (px/tick)", "speed",   1, 10)
        slider_row("Anim Speed  (ms/frame)", "anim_ms", 50, 500, 10)

        # Appearance
        section("🎨  Appearance")
        slider_row("Sprite Scale  (× pixels)", "scale", 1, 4)

        # Cat Version / Skin selector
        theme_row = tk.Frame(body, bg=self.BG)
        theme_row.pack(fill="x", pady=4)
        tk.Label(theme_row, text="Cat Version", font=("Segoe UI", 9),
                 bg=self.BG, fg=self.TEXT, width=20, anchor="w").pack(side="left")

        curr_theme = self._cfg.get("theme", "classic")
        theme_var = tk.StringVar(value=THEMES.get(curr_theme, THEMES["classic"]))

        def on_theme_select(selected_label):
            for k, label in THEMES.items():
                if label == selected_label:
                    self._cfg["theme"] = k
                    break

        theme_opt = tk.OptionMenu(
            theme_row, theme_var, *THEMES.values(), command=on_theme_select
        )
        theme_opt.config(
            bg=self.SURFACE, fg=self.TEXT,
            activebackground=self.OVERLAY, activeforeground=self.TEXT,
            font=("Segoe UI", 9), highlightthickness=0, bd=1, relief="flat"
        )
        theme_opt["menu"].config(
            bg=self.SURFACE, fg=self.TEXT,
            activebackground=self.ACCENT, activeforeground=self.BG,
            font=("Segoe UI", 9)
        )
        theme_opt.pack(side="right", fill="x", expand=True)

        # Options
        section("🔧  Options")
        toggle_row("Always on Top",    "always_on_top")
        toggle_row("Mouse Chasing",    "mouse_chasing")
        toggle_row("Sound Effects",    "sound")

        # ── Buttons ─────────────────────────────────────────────────
        foot = tk.Frame(self.top, bg=self.HEADER, pady=14, padx=22)
        foot.pack(fill="x", side="bottom")

        def apply_and_close():
            self._on_apply(self._cfg)
            save_cfg(self._cfg)
            self.top.destroy()

        tk.Button(
            foot, text="  Apply & Save  ",
            font=("Segoe UI", 10, "bold"),
            bg=self.ACCENT, fg=self.BG,
            relief="flat", cursor="hand2",
            pady=7, padx=4,
            command=apply_and_close,
        ).pack(side="right", padx=4)

        tk.Button(
            foot, text="  Cancel  ",
            font=("Segoe UI", 10),
            bg=self.SURFACE, fg=self.TEXT,
            relief="flat", cursor="hand2",
            pady=7, padx=4,
            command=self.top.destroy,
        ).pack(side="right", padx=4)

        tk.Button(
            foot, text="  Reset  ",
            font=("Segoe UI", 10),
            bg=self.OVERLAY, fg=self.SUBTEXT,
            relief="flat", cursor="hand2",
            pady=7, padx=4,
            command=self._reset,
        ).pack(side="left", padx=4)

    def _reset(self):
        self._cfg.update(DEFAULTS)
        # Rebuild to reflect reset values
        for w in self.top.winfo_children():
            w.destroy()
        self._build()


# ═══════════════════════════════════════════════════════════════════════════════
# DESKTOP CAT
# ═══════════════════════════════════════════════════════════════════════════════

class DesktopCat:
    """Main application class."""

    _DRAG_THRESHOLD = 4   # px before drag is recognised

    def __init__(self):
        self.cfg = load_cfg()
        self.screen_w, self.screen_h = work_area()

        # Build main window first (needed for PhotoImage)
        self._build_window()

        # Initial State
        self.state      = S.IDLE
        self.frame_idx  = 0
        self.tick       = 0    # frames in current state

        # Now load sprites
        self._reload_sprites()

        # Generate / locate sound files (pure-Python synthesis, runs once)
        self._meow_path, self._purr_path, self._happy_path, self._angry_path = ensure_sounds()

        if self.cfg["pos_x"] >= 0 and self.cfg["pos_y"] >= 0:
            self.x = self.cfg["pos_x"]
            self.y = self.cfg["pos_y"]
        else:
            self.x = int(self.screen_w * 0.75)
            self.y = self.screen_h - self._h
        self._chase_dir = "r"  # "l" or "r"

        # Input state
        self._dragging       = False
        self._drag_orig_x    = 0
        self._drag_orig_y    = 0
        self._drag_win_x     = 0
        self._drag_win_y     = 0
        self._prev_mouse_x   = -999
        self._prev_mouse_y   = -999

        # Overlays
        self._bubble: Bubble | None        = None
        self._settings: SettingsWin | None = None

        # System tray
        self._tray_icon = None
        if _TRAY and _PIL:
            self._launch_tray()

        # Kick off loop
        self.window.after(self.cfg["anim_ms"], self._loop)
        self.window.mainloop()

    # ──────────────────────────────────────────────────────────────────
    # WINDOW & SPRITES
    # ──────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.window = tk.Tk()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", bool(self.cfg["always_on_top"]))
        self.window.wm_attributes("-transparentcolor", "black")
        self.window.config(bg="black", highlightbackground="black")

        self.label = tk.Label(self.window, bd=0, bg="black")
        self.label.pack()

        # Bindings
        self.label.bind("<ButtonPress-1>",   self._on_press)
        self.label.bind("<B1-Motion>",       self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Double-Button-1>", self._on_double)
        self.label.bind("<Button-3>",        self._on_right_click)
        self.window.bind("<Escape>",         lambda e: self._quit())

    def _reload_sprites(self):
        scale = int(self.cfg["scale"])
        theme = self.cfg.get("theme", "classic")
        mgr = Sprites(scale, theme)
        self._frames = mgr.load_all()
        self._w, self._h = mgr.sprite_size()
        self._sprite_mgr = mgr
        # Keep frame index valid for current state
        state_key = {
            S.IDLE: "idle", S.WALK_L: "walk_l", S.WALK_R: "walk_r",
            S.TO_SLEEP: "to_sleep", S.SLEEPING: "sleeping", S.FROM_SLEEP: "from_sleep",
            S.ANGRY: "angry", S.HAPPY: "happy"
        }.get(self.state, "idle")
        frames = self._frames.get(state_key, self._frames["idle"])
        self.current_frame = frames[self.frame_idx % len(frames)]
        self.label.config(image=self.current_frame)

    # ──────────────────────────────────────────────────────────────────
    # SYSTEM TRAY
    # ──────────────────────────────────────────────────────────────────

    def _launch_tray(self):
        img = self._sprite_mgr.make_tray_image()
        if img is None:
            return
        try:
            # Theme submenu for System Tray
            theme_items = [
                pystray.MenuItem(
                    label,
                    lambda *_, k=key: self.window.after(0, lambda: self._switch_theme(k))
                )
                for key, label in THEMES.items()
            ]

            menu = pystray.Menu(
                pystray.MenuItem("Desktop Cat 🐱", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Cat Version", pystray.Menu(*theme_items)),
                pystray.MenuItem("Show / Hide",
                                 lambda *_: self.window.after(0, self._tray_toggle)),
                pystray.MenuItem("Say Something",
                                 lambda *_: self.window.after(0, self._show_bubble)),
                pystray.MenuItem("Settings",
                                 lambda *_: self.window.after(0, self._open_settings)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit",
                                 lambda *_: self.window.after(0, self._quit)),
            )
            self._tray_icon = pystray.Icon("desktop_cat", img, "Desktop Cat", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except Exception as exc:
            print(f"[Tray] {exc}")

    def _tray_toggle(self):
        if self.window.state() == "withdrawn":
            self.window.deiconify()
        else:
            self.window.withdraw()

    # ──────────────────────────────────────────────────────────────────
    # INPUT HANDLERS
    # ──────────────────────────────────────────────────────────────────

    def _on_press(self, event):
        self._drag_orig_x = event.x_root
        self._drag_orig_y = event.y_root
        self._drag_win_x  = self.x
        self._drag_win_y  = self.y
        self._dragging    = False

    def _on_drag(self, event):
        dx = event.x_root - self._drag_orig_x
        dy = event.y_root - self._drag_orig_y
        if not self._dragging and (abs(dx) > self._DRAG_THRESHOLD
                                   or abs(dy) > self._DRAG_THRESHOLD):
            self._dragging = True
        if self._dragging:
            self.x = self._drag_win_x + dx
            self.y = self._drag_win_y + dy
            self._clamp_position()
            self._apply_geometry()

    def _on_release(self, event):
        if self._dragging:
            self.cfg["pos_x"] = self.x
            self.cfg["pos_y"] = self.y
            save_cfg(self.cfg)
            self._set_state(S.IDLE)
        else:
            # It was a clean click → pet!
            self._pet()
        self._dragging = False

    def _on_double(self, event):
        if not self._dragging:
            self._show_bubble()

    def _on_right_click(self, event):
        menu = tk.Menu(
            self.window, tearoff=0,
            bg="#1e1e2e", fg="#cdd6f4",
            activebackground="#cba6f7", activeforeground="#1e1e2e",
            font=("Segoe UI", 9), bd=0, relief="flat",
        )
        menu.add_command(label="🐾  Pet Me!",         command=self._pet)
        menu.add_command(label="😾  Poke (Angry!)",   command=self._anger)
        menu.add_command(label="💬  Say Something",   command=self._show_bubble)
        menu.add_separator()

        # Cat Version Submenu
        theme_menu = tk.Menu(
            menu, tearoff=0,
            bg="#1e1e2e", fg="#cdd6f4",
            activebackground="#cba6f7", activeforeground="#1e1e2e",
            font=("Segoe UI", 9), bd=0, relief="flat",
        )
        for t_key, t_label in THEMES.items():
            def set_theme(k=t_key):
                self._switch_theme(k)
            theme_menu.add_command(label=t_label, command=set_theme)

        menu.add_cascade(label="🎨  Cat Version",     menu=theme_menu)
        menu.add_command(label="⚙️   Settings",       command=self._open_settings)
        menu.add_separator()
        menu.add_command(label="❌  Quit",            command=self._quit)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ──────────────────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────────────────

    def _pet(self):
        """Left-click: happy chirp if awake, angry yowl if disturbed mid-sleep."""
        if self.state in (S.SLEEPING, S.TO_SLEEP):
            # How dare you wake me!
            self._set_state(S.ANGRY)
            self._play(self._angry_path)
        else:
            self._set_state(S.HAPPY)
            self._play(self._happy_path)

    def _anger(self):
        """Trigger the angry state with an angry meow (e.g. from right-click Poke)."""
        self._set_state(S.ANGRY)
        self._play(self._angry_path)

    def _play(self, path: Path) -> None:
        """Play a WAV file asynchronously (no-op if sound disabled)."""
        if self.cfg["sound"] and _SOUND:
            threading.Thread(
                target=lambda: winsound.PlaySound(
                    str(path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                ),
                daemon=True,
            ).start()

    def _show_bubble(self):
        self._play(self._meow_path)
        if self._bubble:
            self._bubble.close()
        self._bubble = Bubble(self.window, self.x, self.y, self._w,
                              int(self.cfg["scale"]))

    def _open_settings(self):
        if self._settings and self._settings.top.winfo_exists():
            self._settings.top.lift()
            return
        self._settings = SettingsWin(self.window, self.cfg, self._apply_settings)

    def _switch_theme(self, theme_key: str):
        """Switch cat version skin dynamically."""
        if self.cfg.get("theme") != theme_key:
            self.cfg["theme"] = theme_key
            save_cfg(self.cfg)
            self._reload_sprites()

    def _apply_settings(self, new_cfg: dict):
        scale_changed = int(new_cfg["scale"]) != int(self.cfg["scale"])
        theme_changed = new_cfg.get("theme") != self.cfg.get("theme")
        self.cfg.update(new_cfg)
        self.window.attributes("-topmost", bool(self.cfg["always_on_top"]))
        if scale_changed or theme_changed:
            self._reload_sprites()
            # Re-clamp so cat isn't partially off-screen
            self._clamp_position()

    # ──────────────────────────────────────────────────────────────────
    # STATE MACHINE
    # ──────────────────────────────────────────────────────────────────

    def _set_state(self, new: S):
        self.state     = new
        self.frame_idx = 0
        self.tick      = 0

    def _current_frames(self):
        """Return the frame list for the current state."""
        if self.state == S.CHASE:
            return self._frames["walk_l" if self._chase_dir == "l" else "walk_r"]
        return {
            S.IDLE:       self._frames["idle"],
            S.TO_SLEEP:   self._frames["to_sleep"],
            S.SLEEPING:   self._frames["sleeping"],
            S.FROM_SLEEP: self._frames["from_sleep"],
            S.WALK_L:     self._frames["walk_l"],
            S.WALK_R:     self._frames["walk_r"],
            S.HAPPY:      self._frames["happy"],
            S.ANGRY:      self._frames["angry"],
        }.get(self.state, self._frames["idle"])

    def _advance_frame(self):
        frames = self._current_frames()
        self.frame_idx = (self.frame_idx + 1) % len(frames)
        self.current_frame = frames[self.frame_idx]

    def _update_state(self):
        self.tick += 1
        mx = self.window.winfo_pointerx()
        my = self.window.winfo_pointery()

        # ── Mouse chasing ───────────────────────────────────────────
        if (self.cfg["mouse_chasing"]
                and self.state not in (S.SLEEPING, S.TO_SLEEP,
                                       S.HAPPY, S.ANGRY, S.CHASE)
                and not self._dragging):
            moved = (abs(mx - self._prev_mouse_x) > 8
                     or abs(my - self._prev_mouse_y) > 8)
            if moved:
                self._set_state(S.CHASE)

        self._prev_mouse_x = mx
        self._prev_mouse_y = my

        # ── Transitions ─────────────────────────────────────────────
        speed = int(self.cfg["speed"])

        if self.state == S.IDLE:
            if self.tick > random.randint(15, 50):
                self._pick_random_state()

        elif self.state == S.TO_SLEEP:
            frames = self._frames["to_sleep"]
            if self.frame_idx >= len(frames) - 1:
                self._set_state(S.SLEEPING)

        elif self.state == S.SLEEPING:
            if self.tick > random.randint(60, 180):
                self._set_state(S.FROM_SLEEP)

        elif self.state == S.FROM_SLEEP:
            frames = self._frames["from_sleep"]
            if self.frame_idx >= len(frames) - 1:
                self._set_state(S.IDLE)

        elif self.state == S.WALK_L:
            self.x -= speed
            if self.x <= 0:
                self.x = 0
                self._set_state(S.IDLE)
            elif self.tick > random.randint(25, 70):
                self._set_state(S.IDLE)

        elif self.state == S.WALK_R:
            self.x += speed
            if self.x >= self.screen_w - self._w:
                self.x = self.screen_w - self._w
                self._set_state(S.IDLE)
            elif self.tick > random.randint(25, 70):
                self._set_state(S.IDLE)

        elif self.state == S.CHASE:
            cat_cx = self.x + self._w // 2
            cat_cy = self.y + self._h // 2
            dx = mx - cat_cx
            dy = my - cat_cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < 24 or self.tick > 50:
                self._set_state(S.IDLE)
            else:
                chase_speed = min(speed * 2, 14)
                self.x += int(dx / dist * chase_speed)
                self.y += int(dy / dist * chase_speed)
                self._clamp_position()
                self._chase_dir = "l" if dx < 0 else "r"

        elif self.state == S.HAPPY:
            if self.tick > 18:
                self._set_state(S.IDLE)

        elif self.state == S.ANGRY:
            if self.tick > 12:
                self._set_state(S.IDLE)

    def _pick_random_state(self):
        choice = random.choices(
            [S.IDLE, S.WALK_L, S.WALK_R, S.TO_SLEEP],
            weights=[35, 22, 22, 21],
        )[0]
        self._set_state(choice)

    # ──────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────────────────────────────

    def _loop(self):
        if not self._dragging:
            self._update_state()
        self._advance_frame()
        self.label.configure(image=self.current_frame)
        self._apply_geometry()
        delay = max(16, int(self.cfg["anim_ms"]))
        self.window.after(delay, self._loop)

    # ──────────────────────────────────────────────────────────────────
    # GEOMETRY
    # ──────────────────────────────────────────────────────────────────

    def _clamp_position(self):
        self.x = max(0, min(self.x, self.screen_w - self._w))
        self.y = max(0, min(self.y, self.screen_h - self._h))

    def _apply_geometry(self):
        self.window.geometry(f"{self._w}x{self._h}+{self.x}+{self.y}")

    # ──────────────────────────────────────────────────────────────────
    # QUIT
    # ──────────────────────────────────────────────────────────────────

    def _quit(self):
        save_cfg(self.cfg)
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        try:
            self.window.destroy()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    DesktopCat()
