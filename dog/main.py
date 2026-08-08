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
# CONFIG & THEMES
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path.home() / ".desktop_dog_config.json"

DEFAULTS: dict = {
    "speed":         3,
    "scale":         1,
    "theme":         "shiba",
    "anim_ms":       150,
    "always_on_top": True,
    "mouse_chasing": True,
    "sound":         True,
    "pos_x":         -1,
    "pos_y":         -1,
}

THEMES: dict[str, str] = {'shiba': '🐕  Shiba Inu', 'golden': '🦮  Golden Retriever', 'black_lab': '🖤  Black Lab', 'dalmatian': '⚪⚫ Dalmatian', 'husky': '🐺  Husky'}
MESSAGES: list[str] = ['Woof! 🐶', 'Play fetch? 🎾', 'Wag wag wag! 🐾', '*sniffs your shoes*', 'Befriend me forever!', 'Did someone say TREATS?! 🦴', 'Good boy status: 100%', '*pant pant pant*', 'I brought you a stick! 🪵', 'AWOOOO! 🐺']

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
# AUDIO SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════════════

_SOUNDS_DIR = Path(__file__).parent / "sounds"

def _write_wav(path: Path, frames: list, sample_rate: int = 44100) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))

def _gen_synth_sound(path: Path, f0_start: float, f0_end: float, dur: float = 0.4) -> None:
    sr = 44100
    n = int(sr * dur)
    frames = []
    cp = 0.0
    for i in range(n):
        t = i / sr
        p = t / dur
        f0 = f0_start + (f0_end - f0_start) * (p ** 0.7)
        cp += 2 * math.pi * f0 / sr
        sig = math.sin(cp + 1.2 * math.sin(2 * math.pi * f0 * 1.5 * t))
        env = p / 0.1 if p < 0.1 else ((1 - p) / 0.2 if p > 0.8 else 1.0)
        val = max(-32768, min(32767, int(env * 0.45 * 32767 * sig)))
        frames.append(struct.pack("<h", val))
    _write_wav(path, frames, sr)

def ensure_sounds() -> tuple[Path, Path, Path, Path]:
    _SOUNDS_DIR.mkdir(exist_ok=True)
    meow_path  = _SOUNDS_DIR / "meow.wav"
    purr_path  = _SOUNDS_DIR / "purr.wav"
    happy_path = _SOUNDS_DIR / "happy.wav"
    angry_path = _SOUNDS_DIR / "angry.wav"

    if not meow_path.exists():  _gen_synth_sound(meow_path, 420, 750, 0.4)
    if not purr_path.exists():  _gen_synth_sound(purr_path, 130, 170, 0.8)
    if not happy_path.exists(): _gen_synth_sound(happy_path, 550, 950, 0.35)
    if not angry_path.exists(): _gen_synth_sound(angry_path, 220, 140, 0.6)

    return meow_path, purr_path, happy_path, angry_path


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
    WALK_L     = auto()
    WALK_R     = auto()
    TO_SLEEP   = auto()
    SLEEPING   = auto()
    FROM_SLEEP = auto()
    HAPPY      = auto()
    ANGRY      = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# SPRITE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class Sprites:
    DIR = Path(__file__).parent / "assets"

    def __init__(self, scale: int, theme: str = "shiba"):
        self.scale = max(1, int(scale))
        self.theme = theme if theme in THEMES else "shiba"
        self._cache: dict = {}

    @staticmethod
    def apply_theme(img, theme: str):
        if theme == "shiba" or not _PIL:
            return img
        import numpy as np
        arr = np.array(img, dtype=np.float32)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
        mask = a > 0
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

        out_r, out_g, out_b = r.copy(), g.copy(), b.copy()
        fur_mask = mask & (lum > 0.2)

        if theme == "black_lab" or theme == "silver" or theme == "dutch" or theme == "black":
            out_r[fur_mask] = 35 + lum[fur_mask] * 50
            out_g[fur_mask] = 35 + lum[fur_mask] * 50
            out_b[fur_mask] = 45 + lum[fur_mask] * 50
        elif theme == "golden" or theme == "fennec" or theme == "shiba":
            out_r[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 180)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 50)
        elif theme == "pink" or theme == "sakura":
            out_r[fur_mask] = np.minimum(255, lum[fur_mask] * 255)
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 170)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 200)
        elif theme == "cyber" or theme == "cyberpunk":
            out_r[fur_mask] = lum[fur_mask] * 20
            out_g[fur_mask] = np.minimum(255, lum[fur_mask] * 230)
            out_b[fur_mask] = np.minimum(255, lum[fur_mask] * 255)

        res = np.stack([out_r, out_g, out_b, a], axis=-1).astype(np.uint8)
        return Image.fromarray(res, "RGBA")

    def _load(self, name: str):
        key = (name, self.scale, self.theme)
        if key in self._cache:
            return self._cache[key]
        path = str(self.DIR / name)
        if _PIL:
            im = Image.open(path).convert("RGBA")
            if self.theme != "shiba":
                im = self.apply_theme(im, self.theme)
            if self.scale != 1:
                im = im.resize((im.width * self.scale, im.height * self.scale), Image.NEAREST)
            ph = ImageTk.PhotoImage(im)
        else:
            ph = tk.PhotoImage(file=path)
            if self.scale > 1:
                ph = ph.zoom(self.scale, self.scale)
        self._cache[key] = ph
        return ph

    def seq(self, *names):
        return [self._load(n) for n in names]

    def sprite_size(self) -> tuple[int, int]:
        if _PIL:
            im = Image.open(str(self.DIR / "idle1.png"))
            return im.width * self.scale, im.height * self.scale
        ph = self._load("idle1.png")
        return ph.width(), ph.height()

    def load_all(self) -> dict:
        return {
            "idle":       self.seq("idle1.png", "idle2.png", "idle3.png", "idle4.png"),
            "to_sleep":   self.seq("sleeping1.png", "sleeping2.png", "sleeping3.png", "sleeping4.png", "sleeping5.png", "sleeping6.png"),
            "sleeping":   self.seq("zzz1.png", "zzz2.png", "zzz3.png", "zzz4.png"),
            "from_sleep": self.seq("sleeping6.png", "sleeping5.png", "sleeping4.png", "sleeping3.png", "sleeping2.png", "sleeping1.png"),
            "walk_l":     self.seq("walkingleft1.png", "walkingleft2.png", "walkingleft3.png", "walkingleft4.png"),
            "walk_r":     self.seq("walkingright1.png", "walkingright2.png", "walkingright3.png", "walkingright4.png"),
            "angry":      self.seq("action1.png", "action2.png", "action3.png"),
            "happy":      self.seq("happy1.png", "happy2.png", "happy3.png", "happy4.png"),
        }

    def make_tray_image(self):
        if not _PIL:
            return None
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        fills = {'shiba': ('#d9822b', '#804000', '#e6953b'), 'golden': ('#f5b041', '#935116', '#f9e79f'), 'black_lab': ('#2c3e50', '#1a252f', '#566573'), 'dalmatian': ('#ecf0f1', '#7f8c8d', '#ffffff'), 'husky': ('#85929e', '#2c3e50', '#d6dbdf')}
        b_fill, o_c, e_fill = fills.get(self.theme, list(fills.values())[0])
        d.ellipse([4, 8, 28, 28], fill=b_fill, outline=o_c, width=1)
        d.ellipse([10, 14, 14, 18], fill="#222222")
        d.ellipse([18, 14, 22, 18], fill="#222222")
        return img


class Bubble:
    def __init__(self, parent: tk.Tk, pet_x: int, pet_y: int, pet_w: int, scale: int):
        self.top = tk.Toplevel(parent)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.wm_attributes("-transparentcolor", "#010101")
        self.top.config(bg="#010101")

        msg = random.choice(MESSAGES)
        frm = tk.Frame(self.top, bg="#1e1e2e", padx=12, pady=8, bd=1, relief="solid")
        frm.config(highlightbackground="#cba6f7", highlightthickness=1)
        frm.pack()

        lbl = tk.Label(frm, text=msg, font=("Segoe UI", 9, "bold"), bg="#1e1e2e", fg="#cdd6f4")
        lbl.pack()

        self.top.update_idletasks()
        bw, bh = self.top.winfo_width(), self.top.winfo_height()
        bx = max(10, pet_x + (pet_w - bw) // 2)
        by = max(10, pet_y - bh - 8)
        self.top.geometry(f"{bw}x{bh}+{bx}+{by}")
        self.top.after(3500, self.close)

    def close(self):
        try:
            self.top.destroy()
        except Exception:
            pass


class VersionSelectorWin:
    BG, SURFACE, OVERLAY, TEXT, SUBTEXT, ACCENT, GREEN, HEADER = (
        "#1e1e2e", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#cba6f7", "#a6e3a1", "#181825"
    )

    def __init__(self, parent: tk.Tk, current_theme: str, on_select):
        self._on_select = on_select
        self.top = tk.Toplevel(parent)
        self.top.title("🎨 Select Version")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)

        hdr = tk.Frame(self.top, bg=self.HEADER, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎨 Choose Version", font=("Segoe UI", 12, "bold"), bg=self.HEADER, fg=self.ACCENT).pack(anchor="w")

        body = tk.Frame(self.top, bg=self.BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        for key, label in THEMES.items():
            is_active = (key == current_theme)
            bg_col = self.SURFACE if not is_active else self.OVERLAY
            fg_col = self.GREEN if is_active else self.TEXT
            border_txt = " ✓ ACTIVE" if is_active else ""

            btn = tk.Button(
                body, text=f"{label}{border_txt}",
                font=("Segoe UI", 10, "bold" if is_active else "normal"),
                bg=bg_col, fg=fg_col, activebackground=self.ACCENT, activeforeground=self.BG,
                relief="flat", cursor="hand2", anchor="w", padx=12, pady=6,
                command=lambda k=key: self._choose(k),
            )
            btn.pack(fill="x", pady=3)

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.top.geometry(f"330x410+{(sw-330)//2}+{(sh-410)//2}")

    def _choose(self, theme_key: str):
        self._on_select(theme_key)
        self.top.destroy()


class SettingsWin:
    BG, SURFACE, OVERLAY, TEXT, SUBTEXT, ACCENT, GREEN, HEADER = (
        "#1e1e2e", "#313244", "#45475a", "#cdd6f4", "#a6adc8", "#cba6f7", "#a6e3a1", "#181825"
    )

    def __init__(self, parent: tk.Tk, cfg: dict, on_apply):
        self._cfg = cfg.copy()
        self._on_apply = on_apply
        self.top = tk.Toplevel(parent)
        self.top.title("Desktop Dog 🐶 — Settings")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.config(bg=self.BG)

        hdr = tk.Frame(self.top, bg=self.HEADER, pady=12, padx=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐶  Desktop Dog 🐶", font=("Segoe UI", 14, "bold"), bg=self.HEADER, fg=self.ACCENT).pack()

        body = tk.Frame(self.top, bg=self.BG, padx=20, pady=10)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Appearance", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.ACCENT).pack(anchor="w", pady=(5, 2))
        
        # Theme dropdown
        t_row = tk.Frame(body, bg=self.BG); t_row.pack(fill="x", pady=3)
        tk.Label(t_row, text="Dog Version", font=("Segoe UI", 9), bg=self.BG, fg=self.TEXT, width=18, anchor="w").pack(side="left")
        curr_t = self._cfg.get("theme", "shiba")
        t_var = tk.StringVar(value=THEMES.get(curr_t, list(THEMES.values())[0]))
        def on_t_sel(val):
            for k, lbl in THEMES.items():
                if lbl == val: self._cfg["theme"] = k; break
        opt = tk.OptionMenu(t_row, t_var, *THEMES.values(), command=on_t_sel)
        opt.config(bg=self.SURFACE, fg=self.TEXT, font=("Segoe UI", 9), highlightthickness=0, bd=1)
        opt.pack(side="right", fill="x", expand=True)

        foot = tk.Frame(self.top, bg=self.HEADER, pady=10, padx=16)
        foot.pack(fill="x", side="bottom")
        tk.Button(foot, text="Apply & Save", font=("Segoe UI", 9, "bold"), bg=self.ACCENT, fg=self.BG, relief="flat", command=self._save).pack(side="right", padx=4)
        tk.Button(foot, text="Cancel", font=("Segoe UI", 9), bg=self.SURFACE, fg=self.TEXT, relief="flat", command=self.top.destroy).pack(side="right", padx=4)

        sw, sh = parent.winfo_screenwidth(), parent.winfo_screenheight()
        self.top.geometry(f"340x420+{(sw-340)//2}+{(sh-420)//2}")

    def _save(self):
        self._on_apply(self._cfg)
        save_cfg(self._cfg)
        self.top.destroy()


class DesktopPet:
    _DRAG_THRESHOLD = 4

    def __init__(self):
        self.cfg = load_cfg()
        self.screen_w, self.screen_h = work_area()
        self._build_window()

        self.state     = S.IDLE
        self.frame_idx = 0
        self.tick      = 0
        self._reload_sprites()
        self._meow_path, self._purr_path, self._happy_path, self._angry_path = ensure_sounds()

        self.x = int(self.screen_w * 0.75) if self.cfg["pos_x"] < 0 else self.cfg["pos_x"]
        self.y = self.screen_h - self._h if self.cfg["pos_y"] < 0 else self.cfg["pos_y"]

        self._dragging       = False
        self._drag_orig_x    = 0
        self._drag_orig_y    = 0
        self._drag_win_x     = 0
        self._drag_win_y     = 0
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
        theme = self.cfg.get("theme", "shiba")
        mgr = Sprites(scale, theme)
        self._frames = mgr.load_all()
        self._w, self._h = mgr.sprite_size()
        self._sprite_mgr = mgr
        state_key = {S.IDLE: "idle", S.WALK_L: "walk_l", S.WALK_R: "walk_r", S.SLEEPING: "sleeping", S.HAPPY: "happy", S.ANGRY: "angry"}.get(self.state, "idle")
        frames = self._frames.get(state_key, self._frames["idle"])
        self.current_frame = frames[self.frame_idx % len(frames)]
        self.label.config(image=self.current_frame)

    def _launch_tray(self):
        try:
            img = self._sprite_mgr.make_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("Desktop Dog 🐶", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Say Something", lambda *_: self.window.after(0, self._show_bubble)),
                pystray.MenuItem("Settings", lambda *_: self.window.after(0, self._open_settings)),
                pystray.MenuItem("Quit", lambda *_: self.window.after(0, self.window.destroy)),
            )
            self._tray_icon = pystray.Icon("desktop_dog", img, "Desktop Dog 🐶", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except Exception:
            pass

    def _on_right_click(self, event):
        menu = tk.Menu(self.window, tearoff=0, bg="#1e1e2e", fg="#cdd6f4")
        menu.add_command(label="🐶  Pet Me!", command=self._pet)
        menu.add_command(label="😾  Poke (Angry!)", command=self._anger)
        menu.add_command(label="💬  Say Something", command=self._show_bubble)
        menu.add_separator()
        menu.add_command(label="🎨  Dog Version Selector...", command=self._open_version_selector)
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

    def _open_version_selector(self):
        curr = self.cfg.get("theme", "shiba")
        VersionSelectorWin(self.window, curr, self._switch_theme)

    def _switch_theme(self, theme_key: str):
        if self.cfg.get("theme") != theme_key:
            self.cfg["theme"] = theme_key
            save_cfg(self.cfg)
            self._reload_sprites()

    def _play(self, path: Path):
        if self.cfg["sound"] and _SOUND:
            threading.Thread(target=lambda: winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC), daemon=True).start()

    def _show_bubble(self):
        self._play(self._meow_path)
        if self._bubble: self._bubble.close()
        self._bubble = Bubble(self.window, self.x, self.y, self._w, int(self.cfg["scale"]))

    def _open_settings(self):
        SettingsWin(self.window, self.cfg, self._apply_settings)

    def _apply_settings(self, new_cfg: dict):
        self.cfg.update(new_cfg)
        self._reload_sprites()

    def _set_state(self, new_state: S):
        self.state = new_state
        self.frame_idx = 0
        self.tick = 0

    def _loop(self):
        self.tick += 1
        state_key = {S.IDLE: "idle", S.WALK_L: "walk_l", S.WALK_R: "walk_r", S.SLEEPING: "sleeping", S.HAPPY: "happy", S.ANGRY: "angry"}.get(self.state, "idle")
        frames = self._frames.get(state_key, self._frames["idle"])

        self.frame_idx = (self.frame_idx + 1) % len(frames)
        self.current_frame = frames[self.frame_idx]
        self.label.config(image=self.current_frame)

        if self.state == S.HAPPY and self.tick > 20: self._set_state(S.IDLE)
        elif self.state == S.ANGRY and self.tick > 25: self._set_state(S.IDLE)
        elif self.state == S.IDLE and self.tick > 45:
            r = random.random()
            if r < 0.35: self._set_state(S.WALK_L)
            elif r < 0.70: self._set_state(S.WALK_R)
            elif r < 0.85: self._set_state(S.SLEEPING)
        elif self.state in (S.WALK_L, S.WALK_R):
            dx = -self.cfg["speed"] if self.state == S.WALK_L else self.cfg["speed"]
            self.x += dx
            self.x = max(0, min(self.screen_w - self._w, self.x))
            if self.tick > 50: self._set_state(S.IDLE)
        elif self.state == S.SLEEPING and self.tick > 120:
            self._set_state(S.IDLE)

        self.window.geometry(f"{self._w}x{self._h}+{self.x}+{self.y}")
        self.window.after(self.cfg["anim_ms"], self._loop)


if __name__ == "__main__":
    DesktopPet()
