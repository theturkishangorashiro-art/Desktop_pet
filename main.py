"""
Desktop Bird 🐦 — Pocket Bird Enhanced Edition
Based on Pocket-Bird by @matthew-r-callaghan
Featuring 34 Bird Species, 12 Wearable Hats, Authentic Wing-Flapping Animations,
Isolated Heart Particles (petting only), 1/3 Compact Size, Birdsong Voice Synthesis,
Mouse Chasing, Interactive Dragging, Speech Bubbles, and Catppuccin Dark UI.
"""

import os
import sys
import math
import json
import time
import wave
import random
import struct
import threading
from pathlib import Path
from enum import Enum, auto

import tkinter as tk

try:
    from PIL import Image, ImageTk, ImageDraw
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

try:
    import win32gui
    import win32con
    import win32api
    _WIN32 = True
except ImportError:
    _WIN32 = False


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG & METADATA
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path.home() / ".desktop_bird_config.json"

DEFAULTS: dict = {
    "speed":         3,          # movement speed
    "scale":         1,          # sprite scale (1x = 32px - 1/3 compact size)
    "species":       "bluebird", # default species
    "hat":           "none",     # default hat
    "anim_ms":       90,         # fast, smooth wing-flapping frame delay
    "always_on_top": True,
    "mouse_chasing": True,
    "sound":         True,
    "pos_x":         -1,
    "pos_y":         -1,
}

TUFTED_SPECIES = {"tuftedTitmouse", "redCardinal", "blueJay", "stellarsJay"}

SPECIES_DATA = {
    "bluebird": {
        "name": "Eastern Bluebird 🐦",
        "latin": "Sialia sialis",
        "desc": "Native to North America and very social, though can be timid around people.",
        "spriteIndex": 0,
        "color": "#639bff"
    },
    "shimaEnaga": {
        "name": "Shima Enaga ❄️",
        "latin": "Aegithalos caudatus",
        "desc": "Small, fluffy white birds found in Hokkaido, Japan. Highly beloved nature icons!",
        "spriteIndex": 1,
        "color": "#d7ac93"
    },
    "tuftedTitmouse": {
        "name": "Tufted Titmouse 💜",
        "latin": "Baeolophus bicolor",
        "desc": "Native to the eastern United States, full of personality and charm.",
        "spriteIndex": 2,
        "color": "#b9abcf"
    },
    "europeanRobin": {
        "name": "European Robin 🧡",
        "latin": "Erithacus rubecula",
        "desc": "Native to western Europe. Friendly garden bird that loves searching for worms.",
        "spriteIndex": 3,
        "color": "#ffaf34"
    },
    "redCardinal": {
        "name": "Red Cardinal ❤️",
        "latin": "Cardinalis cardinalis",
        "desc": "Strikingly brilliant red bird with a sharp crest.",
        "spriteIndex": 4,
        "color": "#e83a1b"
    },
    "americanGoldfinch": {
        "name": "American Goldfinch 💛",
        "latin": "Spinus tristis",
        "desc": "Brilliant yellow plumage, loves sunflower and thistle seeds.",
        "spriteIndex": 5,
        "color": "#ffcc00"
    },
    "barnSwallow": {
        "name": "Barn Swallow 💙",
        "latin": "Hirundo rustica",
        "desc": "Agile flier with a fork tail, known for building cozy nests.",
        "spriteIndex": 6,
        "color": "#2252a9"
    },
    "mistletoebird": {
        "name": "Mistletoebird 🇦🇺",
        "latin": "Dicaeum hirundinaceum",
        "desc": "Native to Australia, brightly colored mistletoe enthusiast.",
        "spriteIndex": 7,
        "color": "#352e6d"
    },
    "scarletRobin": {
        "name": "Scarlet Robin ❤️",
        "latin": "Petroica boodang",
        "desc": "Vibrant Australian robin found in open eucalyptus woodlands.",
        "spriteIndex": 8,
        "color": "#fc5633"
    },
    "americanRobin": {
        "name": "American Robin 🧡",
        "latin": "Turdus migratorius",
        "desc": "Famous orange-breasted North American songbird.",
        "spriteIndex": 9,
        "color": "#eb7a3a"
    },
    "carolinaWren": {
        "name": "Carolina Wren 🤎",
        "latin": "Thryothorus ludovicianus",
        "desc": "Small bird with a loud, cheerful song and cocked tail.",
        "spriteIndex": 10,
        "color": "#a06030"
    },
    "blackCappedChickadee": {
        "name": "Black-capped Chickadee 🖤",
        "latin": "Poecile atricapillus",
        "desc": "Curious and brave songbird with a black cap and bib.",
        "spriteIndex": 11,
        "color": "#404040"
    },
    "blueJay": {
        "name": "Blue Jay 🪶",
        "latin": "Cyanocitta cristata",
        "desc": "Intelligent and vocal songbird with crest and blue feathers.",
        "spriteIndex": 12,
        "color": "#3070d0"
    },
    "darkEyedJunco": {
        "name": "Dark-eyed Junco 🩶",
        "latin": "Junco hyemalis",
        "desc": "Medium-sized sparrow known as a snowbird in North America.",
        "spriteIndex": 13,
        "color": "#606570"
    },
    "houseFinch": {
        "name": "House Finch ❤️",
        "latin": "Haemorhous mexicanus",
        "desc": "Cheerful red-headed finch common in parks and gardens.",
        "spriteIndex": 14,
        "color": "#d04040"
    },
    "redWingedBlackbird": {
        "name": "Red-winged Blackbird 🖤❤️",
        "latin": "Agelaius phoeniceus",
        "desc": "Black bird with vivid red and yellow shoulder patches.",
        "spriteIndex": 15,
        "color": "#202020"
    },
    "pigeon": {
        "name": "Rock Pigeon 🐦‍⬛",
        "latin": "Columba livia",
        "desc": "Urban acrobat with iridescent neck feathers.",
        "spriteIndex": 16,
        "color": "#808590"
    },
    "redAvadavat": {
        "name": "Red Avadavat ❤️",
        "latin": "Amandava amandava",
        "desc": "Sparrow-sized finch with white speckles on crimson feathers.",
        "spriteIndex": 17,
        "color": "#e02020"
    },
    "pinkRobin": {
        "name": "Pink Robin 🌸",
        "latin": "Petroica rodinogaster",
        "desc": "Rare, stunning pink-breasted robin from southeastern Australia.",
        "spriteIndex": 18,
        "color": "#ff60a0"
    },
    "spangledCotinga": {
        "name": "Spangled Cotinga 🩵",
        "latin": "Cotinga cayana",
        "desc": "Amazon rainforest bird with brilliant turquoise and purple throat.",
        "spriteIndex": 19,
        "color": "#00bcd4"
    },
    "elegantEuphonia": {
        "name": "Elegant Euphonia 💙💛",
        "latin": "Euphonia elegantissima",
        "desc": "Colorful songbird with blue cap, dark back, and yellow belly.",
        "spriteIndex": 20,
        "color": "#29b6f6"
    },
    "paintedBunting": {
        "name": "Painted Bunting 🎨",
        "latin": "Passerina ciris",
        "desc": "Most colorful bird in North America — blue head, green back, red belly.",
        "spriteIndex": 21,
        "color": "#ab47bc"
    },
    "redWarbler": {
        "name": "Red Warbler ❤️",
        "latin": "Cardellina rubra",
        "desc": "Bright red songbird with silver ear patches from Mexico.",
        "spriteIndex": 22,
        "color": "#ef5350"
    },
    "cubanTody": {
        "name": "Cuban Tody 🇨🇺",
        "latin": "Todus multicolor",
        "desc": "Tiny endemic Cuban bird with green coat, red chin, and pink flanks.",
        "spriteIndex": 23,
        "color": "#66bb6a"
    },
    "violetBackedStarling": {
        "name": "Violet-backed Starling 💜",
        "latin": "Cinnyricinclus leucogaster",
        "desc": "African starling with shimmering iridescent violet plumage.",
        "spriteIndex": 24,
        "color": "#7e57c2"
    },
    "stellarsJay": {
        "name": "Steller's Jay 💙",
        "latin": "Cyanocitta stelleri",
        "desc": "Mountain crest jay with deep blue and black plumage.",
        "spriteIndex": 25,
        "color": "#1e88e5"
    },
    "mourningDove": {
        "name": "Mourning Dove 🕊️",
        "latin": "Zenaida macroura",
        "desc": "Graceful dove with a soft, mournful cooing call.",
        "spriteIndex": 26,
        "color": "#bcaaa4"
    },
    "whiteWingedFairywren": {
        "name": "White-winged Fairywren 💙",
        "latin": "Malurus leucopterus",
        "desc": "Cobalt blue wren with pure white wing patches from Australia.",
        "spriteIndex": 27,
        "color": "#1565c0"
    },
    "littleCrow": {
        "name": "Little Crow ⬛",
        "latin": "Corvus bennetti",
        "desc": "Clever and adaptable Australian corvid.",
        "spriteIndex": 28,
        "color": "#212121"
    },
    "redpoll": {
        "name": "Redpoll ❤️",
        "latin": "Acanthis flammea",
        "desc": "Small northern finch with a bright red cap.",
        "spriteIndex": 29,
        "color": "#ec407a"
    },
    "pidgey": {
        "name": "Pidgey 🎮",
        "latin": "Avis pidgeot",
        "desc": "Classic pocket monster bird! Very docile and easy to catch.",
        "spriteIndex": 33,
        "color": "#ffb74d"
    }
}

HATS_DATA = {
    "none":           {"name": "No Hat 👒", "desc": "Natural feathered look!", "idx": -1},
    "top-hat":        {"name": "Top Hat 🎩", "desc": "The mark of a true gentlebird.", "idx": 1},
    "viking-helmet":  {"name": "Viking Helmet 🛡️", "desc": "Fierce warrior fashion!", "idx": 9},
    "cowboy-hat":     {"name": "Cowboy Hat 🤠", "desc": "Console cowboy attire.", "idx": 5},
    "fez":            {"name": "Fez 🪄", "desc": "Fezzes are cool.", "idx": 2},
    "wizard-hat":     {"name": "Wizard Hat 🧙‍♂️", "desc": "Grants terrifying mystical power to summon bread crumbs.", "idx": 3},
    "baseball-cap":  {"name": "Baseball Cap 🧢", "desc": "Always hitting fowl balls.", "idx": 4},
    "flower-hat":     {"name": "Flower Hat 🌸", "desc": "A cute dirt clod with flowers.", "idx": 7},
    "beanie":         {"name": "Beanie 🧶", "desc": "Keeps feathers warm on long migrations.", "idx": 6},
    "sun-hat":        {"name": "Sun Hat 👒", "desc": "Perfect for frolicking in flower fields.", "idx": 8},
    "straw-hat":      {"name": "Straw Hat 🌾", "desc": "Classic sunny day straw hat.", "idx": 10},
    "cordovan-hat":   {"name": "Cordovan Hat 🇪🇸", "desc": "Traditional Spanish hat for sword fights.", "idx": 0},
}

MESSAGES = [
    "Chirp chirp! 🎶",
    "Did someone say BREAD CRUMBS?! 🍞",
    "Flap flap flutter! ✨",
    "*head bobs rhythmically*",
    "Looking for shiny things! 💎",
    "Preening my feathers~ 🪶",
    "Tweet tweet! 🐦",
    "High in the sky! ☁️",
    "*wiggles tail feathers*",
    "Warm breeze today! 🍃",
]


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
# AUDIO SYNTHESIS ENGINE (Birdsong Chirps & Melodies)
# ═══════════════════════════════════════════════════════════════════════════════

_SOUNDS_DIR = Path(__file__).parent / "sounds"

def _write_wav(path: Path, frames: list, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))

def _gen_bird_chirp(path: Path, f_start: float = 2200, f_peak: float = 3500, f_end: float = 1800, dur: float = 0.22) -> None:
    sr = 44100
    n = int(sr * dur)
    frames = []
    cp = 0.0
    for i in range(n):
        t = i / sr
        p = t / dur
        if p < 0.4:
            f0 = f_start + (f_peak - f_start) * (p / 0.4)
        else:
            f0 = f_peak + (f_end - f_peak) * ((p - 0.4) / 0.6)
        cp += 2 * math.pi * f0 / sr
        sig = math.sin(cp)
        env = math.sin(math.pi * p)
        val = max(-32768, min(32767, int(env * 0.5 * 32767 * sig)))
        frames.append(struct.pack("<h", val))
    _write_wav(path, frames, sr)

def ensure_bird_sounds() -> tuple[Path, Path, Path, Path]:
    _SOUNDS_DIR.mkdir(exist_ok=True)
    chirp_path  = _SOUNDS_DIR / "chirp.wav"
    melody_path = _SOUNDS_DIR / "melody.wav"
    happy_path  = _SOUNDS_DIR / "happy.wav"
    angry_path  = _SOUNDS_DIR / "angry.wav"

    if not chirp_path.exists():  _gen_bird_chirp(chirp_path, 2200, 3600, 1800, 0.22)
    if not melody_path.exists(): _gen_bird_chirp(melody_path, 1800, 3200, 2400, 0.35)
    if not happy_path.exists():  _gen_bird_chirp(happy_path, 2600, 4200, 2200, 0.28)
    if not angry_path.exists():  _gen_bird_chirp(angry_path, 1200, 800, 600, 0.30)

    return chirp_path, melody_path, happy_path, angry_path


def work_area() -> tuple[int, int]:
    if _WIN32:
        try:
            hmon = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
            mi = win32gui.GetMonitorInfo(hmon)
            wa = mi["Work"]
            return wa[2], wa[3]
        except Exception:
            pass
    r = tk.Tk(); r.withdraw()
    w, h = r.winfo_screenwidth(), r.winfo_screenheight()
    r.destroy()
    return w, h


class S(Enum):
    IDLE       = auto()
    BOB        = auto()
    FLY_L      = auto()
    FLY_R      = auto()
    HOP_L      = auto()
    HOP_R      = auto()
    TO_SLEEP   = auto()
    SLEEPING   = auto()
    FROM_SLEEP = auto()
    HAPPY      = auto()
    ANGRY      = auto()
    CHASE      = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTIC SPRITE LAYER RENDERER (Wing Flapping & Isolated Heart Particles)
# ═══════════════════════════════════════════════════════════════════════════════

class Sprites:
    """
    birb.png slice index mapping (10 slices of 32x32):
    0: base
    1: headDown
    2: heartOne
    3: heartTwo
    4: heartThree
    5: tuftBase
    6: tuftDown
    7: wingsUp
    8: wingsDown
    9: happyEye
    """
    DIR = Path(__file__).parent / "assets"

    def __init__(self, scale: int, species_key: str = "bluebird", hat_key: str = "none"):
        self.scale = max(1, int(scale))
        self.species_key = species_key if species_key in SPECIES_DATA else "bluebird"
        self.hat_key = hat_key if hat_key in HATS_DATA else "none"
        self._cache: dict = {}

        self.birb_img = Image.open(str(self.DIR / "birb.png")).convert("RGBA")
        self.species_img = Image.open(str(self.DIR / "species.png")).convert("RGBA")
        self.hats_img = Image.open(str(self.DIR / "hats.png")).convert("RGBA")

    def _render_layer_frame(self, slice_indices: list, flip_l: bool = False) -> ImageTk.PhotoImage:
        s_idx = SPECIES_DATA[self.species_key]["spriteIndex"]
        h_idx = HATS_DATA[self.hat_key]["idx"]
        has_tuft = self.species_key in TUFTED_SPECIES

        key = (tuple(slice_indices), s_idx, h_idx, self.scale, flip_l, has_tuft)
        if key in self._cache:
            return self._cache[key]

        s_mask = self.species_img.crop((s_idx * 32, 0, (s_idx + 1) * 32, 32))
        out = Image.new("RGBA", (32, 32), (0, 0, 0, 0))

        # 1. Color mask
        out.alpha_composite(s_mask)

        # 2. Base birb slices
        for idx in slice_indices:
            b_slice = self.birb_img.crop((idx * 32, 0, (idx + 1) * 32, 32))
            out.alpha_composite(b_slice)

        # 3. Crested bird tuft
        if has_tuft:
            tuft_idx = 6 if 1 in slice_indices else 5 # tuftDown if headDown else tuftBase
            t_slice = self.birb_img.crop((tuft_idx * 32, 0, (tuft_idx + 1) * 32, 32))
            out.alpha_composite(t_slice)

        # 4. Hat placement
        if h_idx >= 0 and h_idx * 12 < self.hats_img.width:
            h_frame = self.hats_img.crop((h_idx * 12, 0, (h_idx + 1) * 12, 12))
            # Adjust hat position if head is down vs normal
            hat_y = 2 if 1 in slice_indices else 1
            out.alpha_composite(h_frame, (10, hat_y))

        if flip_l:
            out = out.transpose(Image.FLIP_LEFT_RIGHT)

        if self.scale > 1:
            out = out.resize((32 * self.scale, 32 * self.scale), Image.NEAREST)

        ph = ImageTk.PhotoImage(out)
        self._cache[key] = ph
        return ph

    def sprite_size(self) -> tuple[int, int]:
        sz = 32 * self.scale
        return sz, sz

    def load_all(self) -> dict:
        # Authentic Pocket-Bird animation layer compositions:
        return {
            # Idle perching
            "idle": [
                self._render_layer_frame([0]),
            ],
            # Head bobbing
            "bob": [
                self._render_layer_frame([0]),
                self._render_layer_frame([1]),
            ],
            # Wing-flapping flying (authentic 4-frame flight cycle!)
            "fly_r": [
                self._render_layer_frame([0]),           # Base body
                self._render_layer_frame([0, 7]),        # Wings UP!
                self._render_layer_frame([1]),           # Head down
                self._render_layer_frame([0, 8]),        # Wings DOWN!
            ],
            "fly_l": [
                self._render_layer_frame([0], flip_l=True),
                self._render_layer_frame([0, 7], flip_l=True),
                self._render_layer_frame([1], flip_l=True),
                self._render_layer_frame([0, 8], flip_l=True),
            ],
            # Taskbar hopping
            "hop_r": [
                self._render_layer_frame([0]),
                self._render_layer_frame([1]),
            ],
            "hop_l": [
                self._render_layer_frame([0], flip_l=True),
                self._render_layer_frame([1], flip_l=True),
            ],
            # Sleeping (Tuck head under wing — NO HEARTS!)
            "to_sleep":   [self._render_layer_frame([1])],
            "sleeping":   [self._render_layer_frame([1])],
            "from_sleep": [self._render_layer_frame([0])],

            # Petting ONLY (Floating Heart particles!)
            "happy": [
                self._render_layer_frame([0, 9, 2]),    # Happy eye + Heart 1
                self._render_layer_frame([0, 9, 3]),    # Happy eye + Heart 2
                self._render_layer_frame([0, 9, 4]),    # Happy eye + Heart 3
                self._render_layer_frame([0, 9, 3]),    # Happy eye + Heart 2
            ],

            # Poke (Grumpy ruffle)
            "angry": [
                self._render_layer_frame([1, 8]),
                self._render_layer_frame([0, 7]),
            ],
        }

    def make_tray_image(self) -> Image.Image:
        s_idx = SPECIES_DATA[self.species_key]["spriteIndex"]
        h_idx = HATS_DATA[self.hat_key]["idx"]

        b_frame = self.birb_img.crop((0, 0, 32, 32))
        s_mask  = self.species_img.crop((s_idx * 32, 0, (s_idx + 1) * 32, 32))

        out = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        out.alpha_composite(s_mask)
        out.alpha_composite(b_frame)

        if h_idx >= 0 and h_idx * 12 < self.hats_img.width:
            h_frame = self.hats_img.crop((h_idx * 12, 0, (h_idx + 1) * 12, 12))
            out.alpha_composite(h_frame, (10, 1))

        return out


# ═══════════════════════════════════════════════════════════════════════════════
# SPEECH BUBBLE & MODAL DIALOGS
# ═══════════════════════════════════════════════════════════════════════════════

class Bubble:
    def __init__(self, parent: tk.Tk, pet_x: int, pet_y: int, pet_w: int, scale: int, custom_msg: str = None):
        self.top = tk.Toplevel(parent)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.wm_attributes("-transparentcolor", "#010101")
        self.top.config(bg="#010101")

        msg = custom_msg if custom_msg else random.choice(MESSAGES)
        frm = tk.Frame(self.top, bg="#1e1e2e", padx=10, pady=6, bd=1, relief="solid")
        frm.config(highlightbackground="#89b4fa", highlightthickness=1)
        frm.pack()

        lbl = tk.Label(frm, text=msg, font=("Segoe UI", 8, "bold"), bg="#1e1e2e", fg="#cdd6f4")
        lbl.pack()

        self.top.update_idletasks()
        bw, bh = self.top.winfo_width(), self.top.winfo_height()
        bx = max(10, pet_x + (pet_w - bw) // 2)
        by = max(10, pet_y - bh - 6)
        self.top.geometry(f"{bw}x{bh}+{bx}+{by}")
        self.top.after(3500, self.close)

    def close(self):
        try:
            self.top.destroy()
        except Exception:
            pass


class SpeciesSelectorWin:
    BG, SURFACE, OVERLAY, TEXT, SUBTEXT, ACCENT, GREEN, HEADER = (
        "#1e1e2e", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#89b4fa", "#a6e3a1", "#181825"
    )

    def __init__(self, parent: tk.Tk, current_species: str, current_hat: str, scale: int, on_select):
        self._on_select = on_select
        self.top = tk.Toplevel(parent)
        self.top.title("🐦 Select Bird Species")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)

        hdr = tk.Frame(self.top, bg=self.HEADER, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐦 Choose Bird Species (34 Species)", font=("Segoe UI", 12, "bold"), bg=self.HEADER, fg=self.ACCENT).pack(anchor="w")

        canvas = tk.Canvas(self.top, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.top, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.BG)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        scrollbar.pack(side="right", fill="y", pady=8)

        self._img_cache = []

        for key, data in SPECIES_DATA.items():
            is_active = (key == current_species)
            bg_col = self.SURFACE if not is_active else self.OVERLAY
            fg_col = self.GREEN if is_active else self.TEXT
            active_lbl = " ✓ ACTIVE" if is_active else ""

            row = tk.Frame(scroll_frame, bg=bg_col, padx=8, pady=6, bd=1, relief="solid")
            row.config(highlightbackground=self.ACCENT if is_active else self.SURFACE)
            row.pack(fill="x", pady=4, padx=4)

            prev_mgr = Sprites(2, key, current_hat)
            img = prev_mgr._render_layer_frame([0])
            self._img_cache.append(img)

            img_lbl = tk.Label(row, image=img, bg=bg_col)
            img_lbl.pack(side="left", padx=(0, 8))

            txt_box = tk.Frame(row, bg=bg_col)
            txt_box.pack(side="left", fill="both", expand=True)

            title_lbl = tk.Label(txt_box, text=f"{data['name']}{active_lbl}", font=("Segoe UI", 10, "bold"), bg=bg_col, fg=fg_col, anchor="w")
            title_lbl.pack(fill="x")

            latin_lbl = tk.Label(txt_box, text=f"Latin: {data['latin']}", font=("Segoe UI", 8, "italic"), bg=bg_col, fg=self.SUBTEXT, anchor="w")
            latin_lbl.pack(fill="x")

            desc_lbl = tk.Label(txt_box, text=data['desc'], font=("Segoe UI", 8), bg=bg_col, fg=self.TEXT, anchor="w", wraplength=250, justify="left")
            desc_lbl.pack(fill="x")

            btn = tk.Button(row, text="Select", font=("Segoe UI", 8, "bold"), bg=self.ACCENT, fg=self.BG, relief="flat", command=lambda k=key: self._choose(k))
            btn.pack(side="right", padx=4)

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.top.geometry(f"440x550+{(sw-440)//2}+{(sh-550)//2}")

    def _choose(self, species_key: str):
        self._on_select(species_key)
        self.top.destroy()


class HatClosetWin:
    BG, SURFACE, OVERLAY, TEXT, SUBTEXT, ACCENT, GREEN, HEADER = (
        "#1e1e2e", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#89b4fa", "#a6e3a1", "#181825"
    )

    def __init__(self, parent: tk.Tk, current_species: str, current_hat: str, on_select):
        self._on_select = on_select
        self.top = tk.Toplevel(parent)
        self.top.title("🎩 Wearable Hat Closet")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)

        hdr = tk.Frame(self.top, bg=self.HEADER, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎩 Bird Hat Closet (12 Wearable Hats)", font=("Segoe UI", 12, "bold"), bg=self.HEADER, fg=self.ACCENT).pack(anchor="w")

        body = tk.Frame(self.top, bg=self.BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        self._img_cache = []

        for key, data in HATS_DATA.items():
            is_active = (key == current_hat)
            bg_col = self.SURFACE if not is_active else self.OVERLAY
            fg_col = self.GREEN if is_active else self.TEXT
            border_txt = " ✓ ACTIVE" if is_active else ""

            row = tk.Frame(body, bg=bg_col, padx=8, pady=4, bd=1, relief="solid")
            row.config(highlightbackground=self.ACCENT if is_active else self.SURFACE)
            row.pack(fill="x", pady=3)

            prev_mgr = Sprites(2, current_species, key)
            img = prev_mgr._render_layer_frame([0])
            self._img_cache.append(img)

            img_lbl = tk.Label(row, image=img, bg=bg_col)
            img_lbl.pack(side="left", padx=(0, 8))

            txt_box = tk.Frame(row, bg=bg_col)
            txt_box.pack(side="left", fill="both", expand=True)

            t_lbl = tk.Label(txt_box, text=f"{data['name']}{border_txt}", font=("Segoe UI", 9, "bold"), bg=bg_col, fg=fg_col, anchor="w")
            t_lbl.pack(fill="x")
            d_lbl = tk.Label(txt_box, text=data['desc'], font=("Segoe UI", 8), bg=bg_col, fg=self.SUBTEXT, anchor="w")
            d_lbl.pack(fill="x")

            btn = tk.Button(row, text="Equip", font=("Segoe UI", 8, "bold"), bg=self.ACCENT, fg=self.BG, relief="flat", command=lambda k=key: self._choose(k))
            btn.pack(side="right", padx=4)

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.top.geometry(f"420x580+{(sw-420)//2}+{(sh-580)//2}")

    def _choose(self, hat_key: str):
        self._on_select(hat_key)
        self.top.destroy()


class SettingsWin:
    BG, SURFACE, OVERLAY, TEXT, SUBTEXT, ACCENT, GREEN, HEADER = (
        "#1e1e2e", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#89b4fa", "#a6e3a1", "#181825"
    )

    def __init__(self, parent: tk.Tk, cfg: dict, on_apply):
        self._cfg = cfg.copy()
        self._on_apply = on_apply
        self.top = tk.Toplevel(parent)
        self.top.title("Desktop Bird — Settings")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)

        hdr = tk.Frame(self.top, bg=self.HEADER, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐦  Desktop Bird Settings", font=("Segoe UI", 14, "bold"), bg=self.HEADER, fg=self.ACCENT).pack()

        body = tk.Frame(self.top, bg=self.BG, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Appearance & Behavior", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.ACCENT).pack(anchor="w", pady=(5, 2))
        
        # Scale slider
        s_row = tk.Frame(body, bg=self.BG); s_row.pack(fill="x", pady=3)
        tk.Label(s_row, text="Size Scale (1x = 32px)", font=("Segoe UI", 9), bg=self.BG, fg=self.TEXT, width=18, anchor="w").pack(side="left")
        s_scale = tk.Scale(s_row, from_=1, to=4, orient="horizontal", bg=self.BG, fg=self.TEXT, highlightthickness=0, bd=0)
        s_scale.set(self._cfg.get("scale", 1))
        s_scale.pack(side="right", fill="x", expand=True)

        # Speed slider
        sp_row = tk.Frame(body, bg=self.BG); sp_row.pack(fill="x", pady=3)
        tk.Label(sp_row, text="Flight/Hop Speed", font=("Segoe UI", 9), bg=self.BG, fg=self.TEXT, width=18, anchor="w").pack(side="left")
        sp_scale = tk.Scale(sp_row, from_=1, to=12, orient="horizontal", bg=self.BG, fg=self.TEXT, highlightthickness=0, bd=0)
        sp_scale.set(self._cfg.get("speed", 3))
        sp_scale.pack(side="right", fill="x", expand=True)

        # Checkboxes
        c1_var = tk.BooleanVar(value=bool(self._cfg.get("always_on_top", True)))
        c1 = tk.Checkbutton(body, text="Always on Top", variable=c1_var, bg=self.BG, fg=self.TEXT, selectcolor=self.SURFACE, activebackground=self.BG, activeforeground=self.ACCENT)
        c1.pack(anchor="w", pady=2)

        c2_var = tk.BooleanVar(value=bool(self._cfg.get("mouse_chasing", True)))
        c2 = tk.Checkbutton(body, text="Mouse Chasing (bird follows cursor)", variable=c2_var, bg=self.BG, fg=self.TEXT, selectcolor=self.SURFACE, activebackground=self.BG, activeforeground=self.ACCENT)
        c2.pack(anchor="w", pady=2)

        c3_var = tk.BooleanVar(value=bool(self._cfg.get("sound", True)))
        c3 = tk.Checkbutton(body, text="Enable Bird Chirps & Audio", variable=c3_var, bg=self.BG, fg=self.TEXT, selectcolor=self.SURFACE, activebackground=self.BG, activeforeground=self.ACCENT)
        c3.pack(anchor="w", pady=2)

        foot = tk.Frame(self.top, bg=self.HEADER, pady=10, padx=16)
        foot.pack(fill="x", side="bottom")
        
        def _do_save():
            self._cfg["scale"] = s_scale.get()
            self._cfg["speed"] = sp_scale.get()
            self._cfg["always_on_top"] = c1_var.get()
            self._cfg["mouse_chasing"] = c2_var.get()
            self._cfg["sound"] = c3_var.get()
            self._save()

        tk.Button(foot, text="Apply & Save", font=("Segoe UI", 9, "bold"), bg=self.ACCENT, fg=self.BG, relief="flat", command=_do_save).pack(side="right", padx=4)
        tk.Button(foot, text="Cancel", font=("Segoe UI", 9), bg=self.SURFACE, fg=self.TEXT, relief="flat", command=self.top.destroy).pack(side="right", padx=4)

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.top.geometry(f"360x440+{(sw-360)//2}+{(sh-440)//2}")

    def _save(self):
        self._on_apply(self._cfg)
        save_cfg(self._cfg)
        self.top.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DESKTOP BIRD PET APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class DesktopBird:
    _DRAG_THRESHOLD = 3

    def __init__(self):
        self.cfg = load_cfg()
        self.screen_w, self.screen_h = work_area()

        self.state     = S.IDLE
        self.frame_idx = 0
        self.tick      = 0
        self._chase_dir = "r"
        self._w, self._h = 32, 32

        self.x = int(self.screen_w * 0.75) if self.cfg.get("pos_x", -1) < 0 else self.cfg["pos_x"]
        self.y = self.screen_h - self._h if self.cfg.get("pos_y", -1) < 0 else self.cfg["pos_y"]

        self._build_window()
        self._reload_sprites()
        self._chirp_path, self._melody_path, self._happy_path, self._angry_path = ensure_bird_sounds()

        self._dragging       = False
        self._drag_orig_x    = 0
        self._drag_orig_y    = 0
        self._drag_win_x     = 0
        self._drag_win_y     = 0
        self._prev_mouse_x   = -999
        self._prev_mouse_y   = -999
        self._bubble         = None
        self._settings       = None
        self._tray_icon      = None

        if _TRAY: self._launch_tray()

        self.window.after(self.cfg["anim_ms"], self._loop)
        self.window.mainloop()

    def _build_window(self):
        self.window = tk.Tk()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", bool(self.cfg["always_on_top"]))
        self.window.wm_attributes("-transparentcolor", "black")
        self.window.config(bg="black")

        self.label = tk.Label(self.window, bd=0, bg="black")
        self.label.pack()

        self.label.bind("<ButtonPress-1>",   self._on_press)
        self.label.bind("<B1-Motion>",       self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Double-Button-1>", self._on_double)
        self.label.bind("<Button-3>",        self._on_right_click)
        self.window.bind("<Escape>",         lambda e: self.window.destroy())

    def _on_press(self, event):
        self._drag_orig_x = event.x_root
        self._drag_orig_y = event.y_root
        self._drag_win_x  = self.x
        self._drag_win_y  = self.y
        self._dragging    = False

    def _on_drag(self, event):
        dx = event.x_root - self._drag_orig_x
        dy = event.y_root - self._drag_orig_y
        if not self._dragging and (abs(dx) > self._DRAG_THRESHOLD or abs(dy) > self._DRAG_THRESHOLD):
            self._dragging = True
        if self._dragging:
            self.x = self._drag_win_x + dx
            self.y = self._drag_win_y + dy
            self.window.geometry(f"{self._w}x{self._h}+{self.x}+{self.y}")

    def _on_release(self, event):
        if self._dragging:
            self.cfg["pos_x"] = self.x
            self.cfg["pos_y"] = self.y
            save_cfg(self.cfg)
            self._set_state(S.IDLE)
        else:
            self._pet()
        self._dragging = False

    def _on_double(self, event):
        if not self._dragging:
            self._show_bubble()

    def _reload_sprites(self):
        scale = int(self.cfg["scale"])
        species_key = self.cfg.get("species", "bluebird")
        hat_key = self.cfg.get("hat", "none")

        mgr = Sprites(scale, species_key, hat_key)
        self._frames = mgr.load_all()
        self._w, self._h = mgr.sprite_size()
        self._sprite_mgr = mgr

        frames = self._current_frames()
        self.current_frame = frames[self.frame_idx % len(frames)]
        self.label.config(image=self.current_frame)
        self._clamp_position()

    def _launch_tray(self):
        try:
            img = self._sprite_mgr.make_tray_image()
            s_name = SPECIES_DATA.get(self.cfg.get("species", "bluebird"), {}).get("name", "Bird")
            menu = pystray.Menu(
                pystray.MenuItem(f"🐦 Desktop Bird — {s_name}", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Say Something", lambda *_: self.window.after(0, self._show_bubble)),
                pystray.MenuItem("Species Selector...", lambda *_: self.window.after(0, self._open_species_selector)),
                pystray.MenuItem("Hat Closet...", lambda *_: self.window.after(0, self._open_hat_closet)),
                pystray.MenuItem("Settings", lambda *_: self.window.after(0, self._open_settings)),
                pystray.MenuItem("Quit", lambda *_: self.window.after(0, self.window.destroy)),
            )
            self._tray_icon = pystray.Icon("desktop_bird", img, "Desktop Bird", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except Exception:
            pass

    def _on_right_click(self, event):
        s_name = SPECIES_DATA.get(self.cfg.get("species", "bluebird"), {}).get("name", "Bird")
        menu = tk.Menu(self.window, tearoff=0, bg="#1e1e2e", fg="#cdd6f4")
        menu.add_command(label=f"🐦  Pet {s_name}", command=self._pet)
        menu.add_command(label="😾  Poke (Grumpy!)", command=self._anger)
        menu.add_command(label="💬  Say Something", command=self._show_bubble)
        menu.add_separator()
        menu.add_command(label="🎨  Bird Species Selector...", command=self._open_species_selector)
        menu.add_command(label="🎩  Wearable Hat Closet...", command=self._open_hat_closet)
        menu.add_separator()
        menu.add_command(label="⚙️   Settings", command=self._open_settings)
        menu.add_separator()
        menu.add_command(label="❌  Quit", command=self.window.destroy)
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()

    def _pet(self, event=None):
        if self.state in (S.SLEEPING, S.TO_SLEEP):
            self._anger()
        else:
            self._set_state(S.HAPPY)
            self._play(self._happy_path)

    def _anger(self):
        self._set_state(S.ANGRY)
        self._play(self._angry_path)

    def _open_species_selector(self):
        curr_sp = self.cfg.get("species", "bluebird")
        curr_hat = self.cfg.get("hat", "none")
        scale = int(self.cfg.get("scale", 1))
        SpeciesSelectorWin(self.window, curr_sp, curr_hat, scale, self._switch_species)

    def _open_hat_closet(self):
        curr_sp = self.cfg.get("species", "bluebird")
        curr_hat = self.cfg.get("hat", "none")
        HatClosetWin(self.window, curr_sp, curr_hat, self._switch_hat)

    def _switch_species(self, species_key: str):
        if self.cfg.get("species") != species_key:
            self.cfg["species"] = species_key
            save_cfg(self.cfg)
            self._reload_sprites()

    def _switch_hat(self, hat_key: str):
        if self.cfg.get("hat") != hat_key:
            self.cfg["hat"] = hat_key
            save_cfg(self.cfg)
            self._reload_sprites()

    def _play(self, path: Path):
        if self.cfg["sound"] and _SOUND:
            threading.Thread(target=lambda: winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC), daemon=True).start()

    def _show_bubble(self):
        self._play(self._chirp_path)
        if self._bubble: self._bubble.close()
        s_data = SPECIES_DATA.get(self.cfg.get("species", "bluebird"), {})
        custom_txt = f"{s_data.get('name', 'Bird')}\n\"{random.choice(MESSAGES)}\""
        self._bubble = Bubble(self.window, self.x, self.y, self._w, int(self.cfg["scale"]), custom_msg=custom_txt)

    def _open_settings(self):
        SettingsWin(self.window, self.cfg, self._apply_settings)

    def _apply_settings(self, new_cfg: dict):
        scale_changed = int(new_cfg["scale"]) != int(self.cfg["scale"])
        sp_changed = new_cfg.get("species") != self.cfg.get("species")
        hat_changed = new_cfg.get("hat") != self.cfg.get("hat")
        self.cfg.update(new_cfg)
        self.window.attributes("-topmost", bool(self.cfg["always_on_top"]))
        if scale_changed or sp_changed or hat_changed:
            self._reload_sprites()
            self._clamp_position()

    def _set_state(self, new_state: S):
        self.state = new_state
        self.frame_idx = 0
        self.tick = 0

    def _current_frames(self):
        if self.state == S.CHASE:
            return self._frames["fly_l" if self._chase_dir == "l" else "fly_r"]
        return {
            S.IDLE:       self._frames["idle"],
            S.BOB:        self._frames["bob"],
            S.FLY_L:      self._frames["fly_l"],
            S.FLY_R:      self._frames["fly_r"],
            S.HOP_L:      self._frames["hop_l"],
            S.HOP_R:      self._frames["hop_r"],
            S.TO_SLEEP:   self._frames["to_sleep"],
            S.SLEEPING:   self._frames["sleeping"],
            S.FROM_SLEEP: self._frames["from_sleep"],
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

        # Mouse chasing
        if (self.cfg["mouse_chasing"]
                and self.state not in (S.SLEEPING, S.TO_SLEEP, S.HAPPY, S.ANGRY, S.CHASE)
                and not self._dragging):
            moved = (abs(mx - self._prev_mouse_x) > 10 or abs(my - self._prev_mouse_y) > 10)
            if moved:
                self._set_state(S.CHASE)

        self._prev_mouse_x = mx
        self._prev_mouse_y = my

        speed = int(self.cfg["speed"])

        if self.state == S.IDLE:
            if self.tick > random.randint(15, 40):
                self._pick_random_state()

        elif self.state == S.BOB:
            if self.tick > 25:
                self._set_state(S.IDLE)

        elif self.state == S.TO_SLEEP:
            if self.tick > 10:
                self._set_state(S.SLEEPING)

        elif self.state == S.SLEEPING:
            if self.tick > random.randint(60, 160):
                self._set_state(S.FROM_SLEEP)

        elif self.state == S.FROM_SLEEP:
            if self.tick > 10:
                self._set_state(S.IDLE)

        elif self.state in (S.HOP_L, S.HOP_R, S.FLY_L, S.FLY_R):
            is_flying = self.state in (S.FLY_L, S.FLY_R)
            move_speed = speed * 2 if is_flying else speed
            dx = -move_speed if self.state in (S.HOP_L, S.FLY_L) else move_speed
            self.x += dx
            if self.x <= 0 or self.x >= self.screen_w - self._w:
                self._clamp_position()
                self._set_state(S.IDLE)
            elif self.tick > random.randint(30, 80):
                self._set_state(S.IDLE)

        elif self.state == S.CHASE:
            cx = self.x + self._w // 2
            cy = self.y + self._h // 2
            dx = mx - cx
            dy = my - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < 20 or self.tick > 60:
                self._set_state(S.BOB)
                self._play(self._chirp_path)
            else:
                chase_speed = min(speed * 2, 14)
                self.x += int(dx / dist * chase_speed)
                self.y += int(dy / dist * chase_speed)
                self._clamp_position()
                self._chase_dir = "l" if dx < 0 else "r"

        elif self.state == S.HAPPY:
            if self.tick > 20: self._set_state(S.IDLE)

        elif self.state == S.ANGRY:
            if self.tick > 15: self._set_state(S.IDLE)

    def _pick_random_state(self):
        choice = random.choices(
            [S.IDLE, S.BOB, S.HOP_L, S.HOP_R, S.FLY_L, S.FLY_R, S.TO_SLEEP],
            weights=[25, 20, 15, 15, 12, 12, 1,],
        )[0]
        if choice == S.BOB and self.cfg["sound"]:
            self._play(self._melody_path)
        self._set_state(choice)

    def _clamp_position(self):
        if hasattr(self, "x") and hasattr(self, "y") and hasattr(self, "_w") and hasattr(self, "_h"):
            self.x = max(0, min(self.screen_w - self._w, self.x))
            self.y = max(0, min(self.screen_h - self._h, self.y))

    def _loop(self):
        if not self._dragging:
            self._update_state()
        self._advance_frame()
        self.label.config(image=self.current_frame)
        self.window.geometry(f"{self._w}x{self._h}+{self.x}+{self.y}")
        self.window.after(self.cfg["anim_ms"], self._loop)


if __name__ == "__main__":
    DesktopBird()
