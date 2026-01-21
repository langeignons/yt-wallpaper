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


import re
import requests

def _parse_count(text: str) -> int:
    """
    Convertit '100', '1.2K', '1,2 k', '1,2 M' etc -> int
    """
    t = text.strip().lower()
    t = t.replace("\u202f", " ").replace("\xa0", " ")  # espaces insécables
    t = t.replace("abonnés", "").replace("subscribers", "").strip()

    # garde uniquement chiffres, . , K M
    m = re.search(r"([\d\.,\s]+)\s*([km]?)", t)
    if not m:
        raise RuntimeError(f"Impossible de parser le nombre: '{text}'")

    num = m.group(1).strip().replace(" ", "")
    suffix = m.group(2)

    # normalisation virgule -> point
    num = num.replace(",", ".")
    val = float(num)

    if suffix == "k":
        val *= 1000
    elif suffix == "m":
        val *= 1_000_000

    return int(val)

def fetch_subs_scrape(channel_id: str) -> int:
    """
    Récupère les abonnés depuis la page YouTube (sans API).
    channel_id doit être du type UC...
    """
    if not channel_id.startswith("UC"):
        raise RuntimeError("Pour cette méthode, CHANNEL doit être un Channel ID qui commence par 'UC'.")

    url = f"https://www.youtube.com/channel/{channel_id}/about"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",  # on force l'anglais pour faciliter le parsing
    }

    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    html = r.text

    # YouTube embed souvent le compteur dans du JSON dans le HTML
    # On cherche une occurrence type: "subscriberCountText":{"simpleText":"100 subscribers"}
    patterns = [
        r'"subscriberCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"\s*\}',
        r'"subscriberCountText"\s*:\s*\{\s*"accessibility"\s*:\s*\{\s*"accessibilityData"\s*:\s*\{\s*"label"\s*:\s*"([^"]+)"',
    ]

    for pat in patterns:
        m = re.search(pat, html)
        if m:
            text = m.group(1)
            # ex: "100 subscribers" ou "1.2K subscribers"
            return _parse_count(text)

    # fallback: parfois "100 subscribers" apparait ailleurs
    m2 = re.search(r'([\d\.,]+)\s*(K|M)?\s*subscribers', html, re.IGNORECASE)
    if m2:
        raw = m2.group(0)
        return _parse_count(raw)

    raise RuntimeError("Impossible de trouver subscriberCountText dans la page YouTube (format changé / page différente).")



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
