"""Baixa as fontes do Google Fonts e gera subsets locais em fonts/.

O conjunto de caracteres e extraido do proprio index.html: Playfair Display
recebe apenas os caracteres do <h1> e Inter os do restante da pagina, mais o
SAFETY_SET abaixo para aguentar pequenos ajustes de texto.

IMPORTANTE: rode este script sempre que o texto da pagina mudar.

    python tools/subset-fonts.py
"""
import io
import os
import re
import sys
import urllib.request

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@400..600"
    "&family=Playfair+Display:ital,wght@0,700;1,400"
    "&display=swap"
)

# Chrome moderno para o Google devolver woff2.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Margem de seguranca: numeros, pontuacao e acentos do portugues.
SAFETY_SET = "0123456789.,;:!?()-–—/%&@'’\"“”ºª©°+ÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "fonts")
HTML_PATH = os.path.join(ROOT, "index.html")

FACE_RE = re.compile(
    r"/\*\s*(?P<subset>[\w\-\[\]]+)\s*\*/\s*@font-face\s*\{(?P<body>[^}]*)\}", re.S
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def strip_tags(markup: str) -> str:
    markup = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", markup, flags=re.S)
    markup = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
    markup = re.sub(r"<[^>]+>", " ", markup)
    return markup.replace("&nbsp;", " ").replace("&amp;", "&")


def page_charsets() -> dict:
    html = open(HTML_PATH, encoding="utf-8").read()
    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    headline = "".join(re.findall(r"<h1\b[^>]*>(.*?)</h1>", body, flags=re.S))

    everything = strip_tags(body)
    display_chars = set(strip_tags(headline)) | set(SAFETY_SET)
    text_chars = set(everything) | set(SAFETY_SET)

    keep = lambda chars: "".join(sorted(c for c in chars if c.isprintable()))
    return {"playfair": keep(display_chars), "inter": keep(text_chars)}


def field(body: str, name: str) -> str:
    match = re.search(rf"{name}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else ""


def main() -> None:
    from fontTools import subset

    os.makedirs(OUT_DIR, exist_ok=True)
    charsets = page_charsets()
    css = fetch(CSS_URL).decode("utf-8")

    seen = set()
    for match in FACE_RE.finditer(css):
        if match.group("subset") != "latin":
            continue
        body = match.group("body")
        family = field(body, "font-family").strip("'\" ")
        style = field(body, "font-style")
        url_match = re.search(r"url\((https://[^)]+\.woff2)\)", body)
        if not url_match:
            continue

        slug = family.lower().replace(" ", "-")
        name = f"{slug}{'-italic' if 'italic' in style else ''}.woff2"
        if name in seen:
            continue
        seen.add(name)

        text = charsets["playfair"] if slug.startswith("playfair") else charsets["inter"]
        raw = fetch(url_match.group(1))

        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk"]
        options.desubroutinize = True
        options.drop_tables += ["DSIG"]
        options.name_IDs = []
        options.name_legacy = False
        options.notdef_outline = True

        font = subset.load_font(io.BytesIO(raw), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=text)
        subsetter.subset(font)

        out_path = os.path.join(OUT_DIR, name)
        subset.save_font(font, out_path, options)
        font.close()
        print(
            f"{name}: {len(raw) / 1024:.1f} KiB -> {os.path.getsize(out_path) / 1024:.1f} KiB"
            f" ({len(text)} caracteres)"
        )


if __name__ == "__main__":
    sys.exit(main())
