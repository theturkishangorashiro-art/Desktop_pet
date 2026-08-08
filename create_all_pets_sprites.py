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
    gray = "#cccccc"
    pink = "#ff80ab"
    black = "#212121"

    if state == "sleep":
        d.ellipse([14, 36, 48, 56], fill=white, outline=gray, width=2)
        d.ellipse([30, 32, 50, 50], fill=white, outline=gray, width=2)
        d.ellipse([34, 40, 48, 52], fill=white)
        d.arc([40, 38, 46, 44], start=0, end=180, fill=black, width=2)
        return img

    bob = 2 if frame % 2 == 1 and state == "walk" else 0
    hop = (1 if frame % 2 == 0 else -2) * 4 if state == "walk" else 0

    # Cotton Tail
    d.ellipse([8, 38 + bob, 18, 48 + bob], fill=white, outline=gray)

    # Feet
    d.ellipse([16 + hop, 46, 26 + hop, 56], fill=white, outline=gray)
    d.ellipse([32 - hop, 46, 42 - hop, 56], fill=white, outline=gray)

    # Body
    d.ellipse([14, 28 + bob, 46, 50 + bob], fill=white, outline=gray, width=2)

    # Head
    hx, hy = 34, 14 + bob
    if state == "happy": hy -= 4
    d.ellipse([hx, hy, hx + 22, hy + 22], fill=white, outline=gray, width=2)

    # Ears (wiggling)
    ear_w = [-2, 0, 2, 0][frame % 4]
    d.ellipse([hx + 2 + ear_w, hy - 18, hx + 8 + ear_w, hy + 4], fill=white, outline=gray)
    d.ellipse([hx + 4 + ear_w, hy - 16, hx + 6 + ear_w, hy + 2], fill=pink)
    d.ellipse([hx + 14 - ear_w, hy - 18, hx + 20 - ear_w, hy + 4], fill=white, outline=gray)
    d.ellipse([hx + 16 - ear_w, hy - 16, hx + 18 - ear_w, hy + 2], fill=pink)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 4, hy + 6, hx + 9, hy + 11], start=180, end=360, fill=black, width=2)
        d.arc([hx + 13, hy + 6, hx + 18, hy + 11], start=180, end=360, fill=black, width=2)
    else:
        d.ellipse([hx + 4, hy + 6, hx + 8, hy + 11], fill=pink)
        d.ellipse([hx + 14, hy + 6, hx + 18, hy + 11], fill=pink)

    d.polygon([(hx + 10, hy + 13), (hx + 12, hy + 13), (hx + 11, hy + 15)], fill=pink)

    return img


# 3. 🐼 PANDA SPRITES
def draw_panda(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = "#ffffff"
    black = "#212121"

    if state == "sleep":
        d.ellipse([12, 32, 52, 56], fill=white, outline=black, width=2)
        d.ellipse([34, 30, 54, 50], fill=white, outline=black, width=2)
        d.ellipse([44, 32, 52, 40], fill=black) # ear
        d.arc([42, 38, 48, 44], start=0, end=180, fill=black, width=2) # eye
        return img

    bob = 1 if frame % 2 == 1 and state == "walk" else 0
    leg = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0

    # Legs & Arms
    d.rectangle([18 + leg, 44, 24 + leg, 56], fill=black)
    d.rectangle([34 - leg, 44, 40 - leg, 56], fill=black)

    # Body
    d.ellipse([14, 26 + bob, 46, 48 + bob], fill=white, outline=black, width=2)
    d.ellipse([16, 28 + bob, 44, 38 + bob], fill=black) # dark panda vest

    # Head
    hx, hy = 34, 12 + bob
    if state == "happy": hy -= 2
    d.ellipse([hx, hy, hx + 24, hy + 24], fill=white, outline=black, width=2)

    # Round Panda Ears
    d.ellipse([hx + 1, hy - 4, hx + 9, hy + 6], fill=black)
    d.ellipse([hx + 15, hy - 4, hx + 23, hy + 6], fill=black)

    # Eye Patches
    d.ellipse([hx + 3, hy + 6, hx + 10, hy + 14], fill=black)
    d.ellipse([hx + 14, hy + 6, hx + 21, hy + 14], fill=black)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 5, hy + 8, hx + 9, hy + 12], start=180, end=360, fill=white, width=2)
        d.arc([hx + 15, hy + 8, hx + 19, hy + 12], start=180, end=360, fill=white, width=2)
    else:
        d.ellipse([hx + 5, hy + 8, hx + 8, hy + 12], fill=white)
        d.ellipse([hx + 16, hy + 8, hx + 19, hy + 12], fill=white)

    d.ellipse([hx + 10, hy + 15, hx + 14, hy + 18], fill=black)

    return img


# 4. 🐧 PENGUIN SPRITES
def draw_penguin(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    black = "#263238"
    white = "#ffffff"
    orange = "#ff9800"

    if state == "sleep":
        d.ellipse([16, 32, 48, 56], fill=black)
        d.ellipse([22, 34, 42, 54], fill=white)
        d.arc([26, 36, 32, 40], start=0, end=180, fill=black, width=2)
        d.arc([36, 36, 42, 40], start=0, end=180, fill=black, width=2)
        d.polygon([(32, 38), (36, 38), (34, 42)], fill=orange)
        return img

    waddle = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0
    flap = [-4, 0, 4, 0][frame % 4]

    # Orange Feet
    d.polygon([(20 + waddle, 52), (28 + waddle, 52), (24 + waddle, 58)], fill=orange)
    d.polygon([(36 - waddle, 52), (44 - waddle, 52), (40 - waddle, 58)], fill=orange)

    # Body
    d.ellipse([16 + waddle, 18, 48 + waddle, 54], fill=black)
    d.ellipse([22 + waddle, 22, 42 + waddle, 52], fill=white)

    # Flippers
    d.ellipse([10 + waddle, 26 + flap, 18 + waddle, 42 + flap], fill=black)
    d.ellipse([46 + waddle, 26 - flap, 54 + waddle, 42 - flap], fill=black)

    # Head
    hx, hy = 20 + waddle, 10
    if state == "happy": hy -= 2
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


# 5. 🐶 DOG SPRITES
def draw_dog(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tan = "#d9822b"
    dark_brown = "#804000"
    cream = "#f5c999"
    black = "#201000"

    if state == "sleep":
        d.ellipse([12, 32, 52, 56], fill=tan, outline=dark_brown, width=2)
        d.ellipse([34, 30, 54, 50], fill=tan, outline=dark_brown, width=2)
        d.polygon([(36, 32), (32, 42), (40, 38)], fill=dark_brown)
        d.arc([42, 38, 48, 44], start=0, end=180, fill=black, width=2)
        d.ellipse([48, 40, 52, 44], fill=black)
        return img

    bob = 1 if frame % 2 == 1 and state == "walk" else 0
    leg = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0
    wag = [-4, 0, 4, 0][frame % 4]

    # Tail
    d.line([(16, 36), (12 + wag, 24)], fill=tan, width=4)

    # Legs
    d.rectangle([18 + leg, 44, 23 + leg, 56], fill=tan, outline=dark_brown)
    d.rectangle([34 - leg, 44, 39 - leg, 56], fill=tan, outline=dark_brown)

    # Body
    d.ellipse([14, 28 + bob, 44, 48 + bob], fill=tan, outline=dark_brown, width=2)
    d.ellipse([18, 32 + bob, 38, 48 + bob], fill=cream)

    # Head
    hx, hy = 36, 14 + bob
    if state == "happy": hy -= 2
    d.ellipse([hx, hy, hx + 22, hy + 22], fill=tan, outline=dark_brown, width=2)
    d.ellipse([hx + 6, hy + 8, hx + 18, hy + 20], fill=cream)

    # Floppy Ears
    d.polygon([(hx + 2, hy + 4), (hx - 4, hy + 14), (hx + 6, hy + 12)], fill=dark_brown)
    d.polygon([(hx + 18, hy + 4), (hx + 24, hy + 14), (hx + 14, hy + 12)], fill=dark_brown)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 8, hy + 6, hx + 12, hy + 10], start=180, end=360, fill=black, width=2)
        d.arc([hx + 14, hy + 6, hx + 18, hy + 10], start=180, end=360, fill=black, width=2)
    else:
        d.ellipse([hx + 8, hy + 6, hx + 12, hy + 11], fill=black)
        d.ellipse([hx + 15, hy + 6, hx + 19, hy + 11], fill=black)
        d.ellipse([hx + 9, hy + 7, hx + 11, hy + 9], fill="#ffffff")
        d.ellipse([hx + 16, hy + 7, hx + 18, hy + 9], fill="#ffffff")

    d.polygon([(hx + 11, hy + 12), (hx + 15, hy + 12), (hx + 13, hy + 15)], fill=black)
    if state == "happy" or state == "action":
        d.ellipse([hx + 11, hy + 15, hx + 15, hy + 19], fill="#ff7675") # tongue

    return img


# 6. 🐮 COW SPRITES
def draw_cow(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white = "#ffffff"
    black = "#212121"
    pink = "#ffb7b2"
    horn = "#e0e0e0"

    if state == "sleep":
        d.ellipse([10, 32, 54, 58], fill=white, outline=black, width=2)
        d.ellipse([14, 36, 26, 48], fill=black) # spot
        d.ellipse([32, 28, 54, 52], fill=white, outline=black, width=2)
        d.ellipse([40, 40, 54, 52], fill=pink) # snout
        d.arc([44, 36, 50, 42], start=0, end=180, fill=black, width=2) # eye
        return img

    bob = 1 if frame % 2 == 1 and state == "walk" else 0
    leg = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0
    tail = [-3, 0, 3, 0][frame % 4]

    # Tail
    d.line([(14, 34), (8 + tail, 46)], fill=white, width=3)
    d.ellipse([6 + tail, 44, 10 + tail, 48], fill=black)

    # Legs & Hooves
    d.rectangle([18 + leg, 44, 24 + leg, 56], fill=white, outline=black)
    d.rectangle([18 + leg, 52, 24 + leg, 56], fill=black)
    d.rectangle([34 - leg, 44, 40 - leg, 56], fill=white, outline=black)
    d.rectangle([34 - leg, 52, 40 - leg, 56], fill=black)

    # Body
    d.ellipse([12, 26 + bob, 46, 48 + bob], fill=white, outline=black, width=2)
    # Spots
    d.ellipse([16, 30 + bob, 28, 42 + bob], fill=black)
    d.ellipse([32, 34 + bob, 42, 46 + bob], fill=black)

    # Udder
    d.ellipse([24, 42 + bob, 32, 48 + bob], fill=pink)

    # Head
    hx, hy = 36, 12 + bob
    if state == "happy": hy -= 2
    d.ellipse([hx, hy, hx + 24, hy + 24], fill=white, outline=black, width=2)
    # Head spot
    d.ellipse([hx + 2, hy + 2, hx + 12, hy + 12], fill=black)

    # Horns
    d.polygon([(hx + 4, hy + 4), (hx + 2, hy - 4), (hx + 8, hy + 2)], fill=horn, outline=black)
    d.polygon([(hx + 20, hy + 4), (hx + 22, hy - 4), (hx + 16, hy + 2)], fill=horn, outline=black)

    # Ears
    d.polygon([(hx + 2, hy + 8), (hx - 4, hy + 12), (hx + 4, hy + 14)], fill=pink)
    d.polygon([(hx + 22, hy + 8), (hx + 28, hy + 12), (hx + 20, hy + 14)], fill=pink)

    # Snout
    d.ellipse([hx + 4, hy + 12, hx + 20, hy + 22], fill=pink, outline="#e08080")
    d.ellipse([hx + 7, hy + 15, hx + 10, hy + 18], fill=black) # nostril 1
    d.ellipse([hx + 14, hy + 15, hx + 17, hy + 18], fill=black) # nostril 2

    # Eyes
    if state == "happy":
        d.arc([hx + 6, hy + 5, hx + 10, hy + 9], start=180, end=360, fill=black, width=2)
        d.arc([hx + 14, hy + 5, hx + 18, hy + 9], start=180, end=360, fill=black, width=2)
    else:
        d.ellipse([hx + 6, hy + 5, hx + 10, hy + 9], fill=black)
        d.ellipse([hx + 14, hy + 5, hx + 18, hy + 9], fill=black)

    return img


# 7. 🦬 BUFFALO SPRITES
def draw_buffalo(frame=0, state="idle"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark_brown = "#3e2723"
    mid_brown = "#5d4037"
    light_brown = "#8d6e63"
    black = "#1b0000"
    horn = "#b0bec5"

    if state == "sleep":
        d.ellipse([10, 30, 54, 58], fill=dark_brown, outline=black, width=2)
        d.ellipse([14, 26, 36, 48], fill=mid_brown) # hump
        d.ellipse([32, 28, 54, 52], fill=dark_brown, outline=black, width=2)
        d.arc([44, 38, 50, 44], start=0, end=180, fill=black, width=2) # eye
        return img

    bob = 1 if frame % 2 == 1 and state == "walk" else 0
    leg = (1 if frame % 2 == 0 else -1) * 3 if state == "walk" else 0
    tail = [-3, 0, 3, 0][frame % 4]

    # Tail
    d.line([(14, 34), (8 + tail, 46)], fill=dark_brown, width=3)
    d.ellipse([6 + tail, 44, 10 + tail, 48], fill=black)

    # Legs
    d.rectangle([18 + leg, 44, 24 + leg, 56], fill=dark_brown, outline=black)
    d.rectangle([34 - leg, 44, 40 - leg, 56], fill=dark_brown, outline=black)

    # Large Hump & Body
    d.ellipse([12, 20 + bob, 38, 44 + bob], fill=mid_brown) # shaggy hump
    d.ellipse([14, 26 + bob, 46, 48 + bob], fill=dark_brown, outline=black, width=2)

    # Head
    hx, hy = 34, 14 + bob
    if state == "happy": hy -= 2
    d.ellipse([hx, hy, hx + 26, hy + 26], fill=dark_brown, outline=black, width=2)
    d.ellipse([hx + 4, hy + 2, hx + 22, hy + 18], fill=mid_brown) # shaggy head

    # Large Curved Horns
    d.arc([hx - 4, hy - 4, hx + 12, hy + 12], start=90, end=270, fill=horn, width=3)
    d.arc([hx + 14, hy - 4, hx + 30, hy + 12], start=270, end=90, fill=horn, width=3)

    # Eyes & Nose
    if state == "happy":
        d.arc([hx + 6, hy + 8, hx + 10, hy + 12], start=180, end=360, fill=black, width=2)
        d.arc([hx + 16, hy + 8, hx + 20, hy + 12], start=180, end=360, fill=black, width=2)
    else:
        d.ellipse([hx + 6, hy + 8, hx + 10, hy + 12], fill=black)
        d.ellipse([hx + 16, hy + 8, hx + 20, hy + 12], fill=black)

    d.ellipse([hx + 8, hy + 18, hx + 18, hy + 24], fill=black) # snout/nose

    return img


print("Generating all pet sprites...")
make_sprites("fox", draw_fox)
make_sprites("bunny", draw_bunny)
make_sprites("panda", draw_panda)
make_sprites("penguin", draw_penguin)
make_sprites("dog", draw_dog)
make_sprites("cow", draw_cow)
make_sprites("buffalo", draw_buffalo)
print("All pet sprites generated successfully!")
