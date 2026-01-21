import os
import math
import requests
from PIL import Image, ImageDraw, ImageFont

GOAL = int(os.getenv("GOAL", "10000"))
CHANNEL = os.getenv("CHANNEL", "").strip()  # channel id OU handle selon endpoint choisi

# iPhone 1170x2532 (tu peux changer)
W = int(os.getenv("W", "1170"))
H = int(os.getenv("H", "2532"))

OUT_PATH = "wallpaper.png"


def nice_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def load_font(size: int):
    # GitHub Actions a souvent DejaVu
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def fetch_subs_livecounts(channel: str) -> int:
    """
    IMPORTANT:
    Livecounts n'est pas une API officielle YouTube.
    Ça peut changer. Mais c'est le moyen "sans clé" le plus simple.
    """
    # Endpoint souvent utilisé par des wrappers non officiels.
    # Si jamais ça casse un jour, on remplacera par l'API YouTube officielle (clé).
    url = f"https://livecounts.io/api/youtube-live-subscriber-counter/{channel}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    # Selon les variantes d’API, le champ peut changer.
    # On tente plusieurs clés possibles.
    for k in ["counts", "subscriberCount", "subscribers", "count"]:
        if k in data and isinstance(data[k], (int, float, str)):
            try:
                return int(data[k])
            except Exception:
                pass

    # Certains formats mettent la valeur dans un sous-objet
    if "data" in data and isinstance(data["data"], dict):
        for k in ["subscribers", "subscriberCount", "count"]:
            if k in data["data"]:
                return int(data["data"][k])

    raise RuntimeError(f"Impossible de lire les abonnés depuis Livecounts. Réponse: {data}")


def render_wallpaper(subs: int):
    p = 0.0 if GOAL <= 0 else max(0.0, min(1.0, subs / GOAL))
    pct = int(round(p * 100))

    img = Image.new("RGB", (W, H), (10, 10, 16))
    draw = ImageDraw.Draw(img)

    # dégradé simple
    for y in range(H):
        v = int(10 + (y / H) * 20)
        draw.line([(0, y), (W, y)], fill=(v, v, v + 10))

    pad = int(W * 0.08)
    top = int(H * 0.18)

    title_font = load_font(int(H * 0.035))
    big_font = load_font(int(H * 0.06))
    small_font = load_font(int(H * 0.03))

    draw.text((pad, top), "Road to 10 000", fill=(230, 230, 240), font=title_font)

    line1 = f"{nice_int(subs)} / {nice_int(GOAL)} abonnés"
    draw.text((pad, top + int(H * 0.06)), line1, fill=(255, 255, 255), font=big_font)

    draw.text((pad, top + int(H * 0.135)), f"{pct}%", fill=(180, 220, 255), font=big_font)

    # barre
    bar_x = pad
    bar_y = top + int(H * 0.23)
    bar_w = W - 2 * pad
    bar_h = int(H * 0.03)
    radius = bar_h // 2

    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=radius,
        fill=(40, 40, 55),
        outline=(80, 80, 110),
        width=2,
    )

    fill_w = int(math.floor(bar_w * p))
    if fill_w > 0:
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
            radius=radius,
            fill=(80, 170, 255),
        )

    remaining = max(0, GOAL - subs)
    draw.text(
        (pad, bar_y + bar_h + int(H * 0.02)),
        f"Encore {nice_int(remaining)} pour atteindre {nice_int(GOAL)}",
        fill=(200, 200, 210),
        font=small_font,
    )

    img.save(OUT_PATH, "PNG", optimize=True)


if __name__ == "__main__":
    if not CHANNEL:
        raise SystemExit("Tu dois définir CHANNEL (channel id/handle selon endpoint).")

    subs = fetch_subs_livecounts(CHANNEL)
    render_wallpaper(subs)
    print(f"OK -> {OUT_PATH} (subs={subs})")
