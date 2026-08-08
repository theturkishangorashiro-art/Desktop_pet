import os
from PIL import Image, ImageDraw

def make_sprites(animal_dir, draw_fn):
    os.makedirs(f"{animal_dir}/assets", exist_ok=True)
    w, h = 64, 64

    # Idle (4 frames)
    for i in range(4):
        img = draw_fn(frame=i, state="idle")
        img.save(f"{animal_dir}/assets/idle{i+1}.png")

    # Walk right (4 frames)
    for i in range(4):
        img = draw_fn(frame=i, state="walk")
        img.save(f"{animal_dir}/assets/walkingright{i+1}.png")
        # Walk left (flipped)
        img_l = img.transpose(Image.FLIP_LEFT_RIGHT)
        img_l.save(f"{animal_dir}/assets/walkingleft{i+1}.png")

    # Sleeping (6 frames)
    for i in range(6):
        img = draw_fn(frame=i, state="sleep")
        img.save(f"{animal_dir}/assets/sleeping{i+1}.png")

    # ZZZ sleeping (4 frames)
    for i in range(4):
        img = draw_fn(frame=i, state="sleep")
        d = ImageDraw.Draw(img)
        d.text((44 + i * 2, 10 - i * 2), "z", fill="#8888ff")
        img.save(f"{animal_dir}/assets/zzz{i+1}.png")

    # Happy (4 frames)
    for i in range(4):
        img = draw_fn(frame=i, state="happy")
        img.save(f"{animal_dir}/assets/happy{i+1}.png")

    # Action / Angry (3 frames)
    for i in range(3):
        img = draw_fn(frame=i, state="action")
        img.save(f"{animal_dir}/assets/action{i+1}.png")
        img.save(f"{animal_dir}/assets/angry.png")


# 1. 🦊 FOX SPRITES
def draw_fox(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    orange = "#e65100"
    dark_orange = "#bf360c"
    white = "#ffffff"
    black = "#212121"

    if state == "sleep":
        d.ellipse([14, 34, 50, 56], fill=orange, outline=dark_orange, width=2)
        d.ellipse([32, 30, 52, 50], fill=orange, outline=dark_orange, width=2)
        d.polygon([(36, 32), (30, 42), (40, 38)], fill=dark_orange) # ear
        d.arc([42, 38, 48, 44], start=0, end=180, fill=black, width=2) # eye
        d.ellipse([10, 38, 26, 54], fill=white, outline=orange) # bushy tail
        return img

    bob = 1 if frame % 2 == 1 and state == "walk" else 0
    leg = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0

    # Bushy Tail
    tail_w = [-4, 0, 4, 0][frame % 4]
    d.polygon([(16, 34), (4 + tail_w, 20), (14, 44)], fill=orange)
    d.polygon([(4 + tail_w, 20), (0 + tail_w, 16), (8 + tail_w, 26)], fill=white)

    # Legs
    d.rectangle([18 + leg, 44, 22 + leg, 56], fill=black)
    d.rectangle([34 - leg, 44, 38 - leg, 56], fill=black)

    # Body
    d.ellipse([14, 28 + bob, 44, 48 + bob], fill=orange, outline=dark_orange, width=2)
    d.ellipse([22, 32 + bob, 38, 46 + bob], fill=white) # chest

    # Head
    hx, hy = 36, 12 + bob
    if state == "happy": hy -= 3
    d.polygon([(hx, hy + 8), (hx + 24, hy + 8), (hx + 12, hy + 24)], fill=orange) # pointy snout
    d.polygon([(hx + 4, hy + 14), (hx + 20, hy + 14), (hx + 12, hy + 24)], fill=white) # white muzzle

    # Ears
    d.polygon([(hx + 2, hy + 8), (hx - 2, hy - 4), (hx + 8, hy + 4)], fill=black)
    d.polygon([(hx + 22, hy + 8), (hx + 26, hy - 4), (hx + 16, hy + 4)], fill=black)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 4, hy + 6, hx + 10, hy + 12], start=180, end=360, fill=black, width=2)
        d.arc([hx + 14, hy + 6, hx + 20, hy + 12], start=180, end=360, fill=black, width=2)
    else:
        d.ellipse([hx + 5, hy + 6, hx + 9, hy + 12], fill=black)
        d.ellipse([hx + 15, hy + 6, hx + 19, hy + 12], fill=black)
    d.ellipse([hx + 10, hy + 21, hx + 14, hy + 25], fill=black) # nose

    return img


# 2. 🐰 BUNNY SPRITES
def draw_bunny(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = "#f5f5f5"
    grey = "#e0e0e0"
    pink = "#ff80ab"
    dark = "#333333"

    if state == "sleep":
        d.ellipse([14, 36, 50, 56], fill=white, outline=grey, width=2)
        d.ellipse([34, 32, 54, 52], fill=white, outline=grey, width=2)
        d.ellipse([24, 38, 42, 46], fill=pink) # ears down
        d.arc([44, 40, 50, 46], start=0, end=180, fill=dark, width=2)
        return img

    hop = 4 if (frame % 2 == 1 and state == "walk") or state == "happy" else 0
    ear_w = [-2, 0, 2, 0][frame % 4]

    # Tail puff
    d.ellipse([10, 38 - hop, 18, 46 - hop], fill=white, outline=grey)

    # Feet
    d.ellipse([16, 50 - hop, 26, 58 - hop], fill=grey)
    d.ellipse([32, 50 - hop, 42, 58 - hop], fill=grey)

    # Body
    d.ellipse([16, 28 - hop, 46, 52 - hop], fill=white, outline=grey, width=2)

    # Head
    hx, hy = 24, 16 - hop
    d.ellipse([hx, hy, hx + 24, hy + 24], fill=white, outline=grey, width=2)

    # Ears (wiggling)
    d.ellipse([hx + 2 + ear_w, hy - 18, hx + 10 + ear_w, hy + 4], fill=white, outline=grey, width=2)
    d.ellipse([hx + 4 + ear_w, hy - 16, hx + 8 + ear_w, hy + 2], fill=pink)
    d.ellipse([hx + 14 - ear_w, hy - 18, hx + 22 - ear_w, hy + 4], fill=white, outline=grey, width=2)
    d.ellipse([hx + 16 - ear_w, hy - 16, hx + 20 - ear_w, hy + 2], fill=pink)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 4, hy + 8, hx + 10, hy + 14], start=180, end=360, fill=dark, width=2)
        d.arc([hx + 14, hy + 8, hx + 20, hy + 14], start=180, end=360, fill=dark, width=2)
    else:
        d.ellipse([hx + 5, hy + 8, hx + 9, hy + 13], fill=dark)
        d.ellipse([hx + 15, hy + 8, hx + 19, hy + 13], fill=dark)
    d.polygon([(hx + 11, hy + 14), (hx + 15, hy + 14), (hx + 13, hy + 17)], fill=pink) # nose

    return img


# 3. 🐼 PANDA SPRITES
def draw_panda(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = "#ffffff"
    black = "#212121"
    grey = "#e0e0e0"

    if state == "sleep":
        d.ellipse([12, 30, 52, 56], fill=white, outline=grey, width=2) # body
        d.ellipse([14, 30, 26, 54], fill=black) # arm
        d.ellipse([32, 28, 54, 50], fill=white, outline=grey, width=2) # head
        d.ellipse([36, 26, 44, 34], fill=black) # ear
        d.ellipse([42, 36, 48, 44], fill=black) # eye patch
        d.arc([43, 37, 47, 43], start=0, end=180, fill=white, width=1)
        return img

    waddle = 2 if frame % 2 == 1 and state == "walk" else 0
    arm_y = -2 if state == "happy" else 0

    # Legs
    d.rectangle([18, 46, 26, 58], fill=black)
    d.rectangle([38, 46, 46, 58], fill=black)

    # Body
    d.ellipse([14, 24 + waddle, 50, 52 + waddle], fill=white, outline=grey, width=2)
    d.ellipse([14, 24 + waddle, 50, 36 + waddle], fill=black) # black shoulder band

    # Arms
    d.ellipse([10, 28 + arm_y + waddle, 20, 44 + arm_y + waddle], fill=black)
    d.ellipse([44, 28 + arm_y + waddle, 54, 44 + arm_y + waddle], fill=black)

    # Head
    hx, hy = 20, 10 + waddle
    # Ears
    d.ellipse([hx - 2, hy - 4, hx + 8, hy + 8], fill=black)
    d.ellipse([hx + 16, hy - 4, hx + 26, hy + 8], fill=black)

    # Face
    d.ellipse([hx, hy, hx + 24, hy + 24], fill=white, outline=grey, width=2)

    # Eye patches
    d.ellipse([hx + 3, hy + 8, hx + 10, hy + 16], fill=black)
    d.ellipse([hx + 14, hy + 8, hx + 21, hy + 16], fill=black)
    if state == "happy":
        d.arc([hx + 4, hy + 9, hx + 9, hy + 14], start=180, end=360, fill=white, width=2)
        d.arc([hx + 15, hy + 9, hx + 20, hy + 14], start=180, end=360, fill=white, width=2)
    else:
        d.ellipse([hx + 5, hy + 10, hx + 8, hy + 13], fill=white)
        d.ellipse([hx + 16, hy + 10, hx + 19, hy + 13], fill=white)

    # Nose
    d.ellipse([hx + 10, hy + 16, hx + 14, hy + 19], fill=black)

    return img


# 4. 🐧 PENGUIN SPRITES
def draw_penguin(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    black = "#263238"
    white = "#ffffff"
    orange = "#ff9800"

    if state == "sleep":
        d.ellipse([16, 28, 48, 54], fill=black)
        d.ellipse([22, 32, 42, 52], fill=white)
        d.ellipse([30, 20, 48, 38], fill=black)
        d.arc([36, 28, 42, 34], start=0, end=180, fill=white, width=2)
        d.polygon([(46, 30), (52, 32), (46, 34)], fill=orange)
        return img

    tilt = 3 if frame % 2 == 1 and state == "walk" else 0
    flap = 4 if state == "happy" or frame % 2 == 1 else 0

    # Feet
    d.ellipse([20 - tilt, 52, 32 - tilt, 60], fill=orange)
    d.ellipse([32 + tilt, 52, 44 + tilt, 60], fill=orange)

    # Body
    d.ellipse([16, 22, 48, 56], fill=black)
    d.ellipse([22, 26, 42, 52], fill=white) # tummy

    # Flippers
    d.ellipse([8 - flap, 28, 18, 44], fill=black)
    d.ellipse([46, 28, 56 + flap, 44], fill=black)

    # Head
    hx, hy = 20, 10
    d.ellipse([hx, hy, hx + 24, hy + 22], fill=black)
    d.ellipse([hx + 4, hy + 12, hx + 20, hy + 22], fill=white)

    # Beak
    d.polygon([(hx + 10, hy + 12), (hx + 14, hy + 12), (hx + 12, hy + 17)], fill=orange)

    # Eyes
    if state == "happy":
        d.arc([hx + 4, hy + 6, hx + 9, hy + 11], start=180, end=360, fill=white, width=2)
        d.arc([hx + 15, hy + 6, hx + 20, hy + 11], start=180, end=360, fill=white, width=2)
    else:
        d.ellipse([hx + 5, hy + 6, hx + 9, hy + 10], fill=white)
        d.ellipse([hx + 15, hy + 6, hx + 19, hy + 10], fill=white)
        d.ellipse([hx + 6, hy + 7, hx + 8, hy + 9], fill=black)
        d.ellipse([hx + 16, hy + 7, hx + 18, hy + 9], fill=black)

    return img


print("Generating all pet sprites...")
make_sprites("fox", draw_fox)
make_sprites("bunny", draw_bunny)
make_sprites("panda", draw_panda)
make_sprites("penguin", draw_penguin)
print("All pet sprites generated successfully!")
