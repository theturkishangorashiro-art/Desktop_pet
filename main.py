"""
Desktop Pet Launcher 🐾
Choose your desktop companion: Desktop Cat (Shiro) or Desktop Bird (Pocket-Bird)!
"""

import sys
import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent
CAT_MAIN = REPO_DIR / "cat" / "main.py"
BIRD_MAIN = REPO_DIR / "bird" / "main.py"

def launch_cat():
    print("🐱 Launching Desktop Cat (Shiro)...")
    subprocess.Popen([sys.executable, str(CAT_MAIN)], cwd=str(REPO_DIR / "cat"))

def launch_bird():
    print("🐦 Launching Desktop Bird (Pocket-Bird)...")
    subprocess.Popen([sys.executable, str(BIRD_MAIN)], cwd=str(REPO_DIR / "bird"))

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if "cat" in cmd:
            launch_cat()
            return
        elif "bird" in cmd:
            launch_bird()
            return
        elif "both" in cmd:
            launch_cat()
            launch_bird()
            return

    import tkinter as tk
    root = tk.Tk()
    root.title("Desktop Pet Launcher 🐾")
    root.resizable(False, False)
    root.geometry("380x280")
    root.config(bg="#1e1e2e")

    hdr = tk.Frame(root, bg="#181825", pady=12)
    hdr.pack(fill="x")
    tk.Label(hdr, text="🐾 Desktop Pet Launcher", font=("Segoe UI", 14, "bold"), bg="#181825", fg="#89b4fa").pack()
    tk.Label(hdr, text="Choose your interactive desktop companion", font=("Segoe UI", 9), bg="#181825", fg="#a6adc8").pack()

    body = tk.Frame(root, bg="#1e1e2e", pady=20, padx=20)
    body.pack(fill="both", expand=True)

    btn_cat = tk.Button(
        body, text="🐱  Launch Desktop Cat (Shiro)", font=("Segoe UI", 11, "bold"),
        bg="#313244", fg="#a6e3a1", activebackground="#45475a", activeforeground="#a6e3a1",
        relief="flat", pady=8, command=lambda: [launch_cat(), root.destroy()]
    )
    btn_cat.pack(fill="x", pady=6)

    btn_bird = tk.Button(
        body, text="🐦  Launch Desktop Bird (Pocket-Bird)", font=("Segoe UI", 11, "bold"),
        bg="#313244", fg="#89b4fa", activebackground="#45475a", activeforeground="#89b4fa",
        relief="flat", pady=8, command=lambda: [launch_bird(), root.destroy()]
    )
    btn_bird.pack(fill="x", pady=6)

    btn_both = tk.Button(
        body, text="✨  Launch BOTH Pets Together!", font=("Segoe UI", 10, "bold"),
        bg="#45475a", fg="#cdd6f4", activebackground="#585b70", activeforeground="#cdd6f4",
        relief="flat", pady=6, command=lambda: [launch_cat(), launch_bird(), root.destroy()]
    )
    btn_both.pack(fill="x", pady=6)

    root.mainloop()

if __name__ == "__main__":
    main()
