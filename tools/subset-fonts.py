"""Baixa as fontes do Google Fonts e gera subsets locais em fonts/.

Rode novamente se o texto da pagina passar a usar caracteres fora do CHARSET.
"""
import io
import os
import re
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

# ASCII imprimivel + acentuacao do portugues + pontuacao tipografica.
CHARSET = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ"
    + "áàâãäéèêëíìîïóòôõöúùûüçñ"
    + "ºª©®°–—‘’“”…•€"
)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")

FACE_RE = re.compile(
    r"/\*\s*(?P<subset>[\w\-\[\]]+)\s*\*/\s*@font-face\s*\{(?P<body>[^}]*)\}", re.S
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def field(body: str, name: str) -> str:
    match = re.search(rf"{name}\s*:\s*([^;]+);", body)
    return match.group(1).strip() if match else ""


def slug(family: str, style: str, weight: str) -> str:
    base = family.strip("'\" ").lower().replace(" ", "-")
    suffix = "-italic" if "italic" in style else ""
    return f"{base}{suffix}.woff2"


def main() -> None:
    from fontTools import subset

    os.makedirs(OUT_DIR, exist_ok=True)
    css = fetch(CSS_URL).decode("utf-8")

    seen = set()
    for match in FACE_RE.finditer(css):
        if match.group("subset") != "latin":
            continue
        body = match.group("body")
        family = field(body, "font-family")
        style = field(body, "font-style")
        weight = field(body, "font-weight")
        url_match = re.search(r"url\((https://[^)]+\.woff2)\)", body)
        if not url_match:
            continue

        name = slug(family, style, weight)
        if name in seen:
            continue
        seen.add(name)

        raw = fetch(url_match.group(1))
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk"]
        options.desubroutinize = True
        options.drop_tables += ["DSIG"]
        options.name_IDs = ["*"]
        options.name_legacy = False
        options.notdef_outline = True

        font = subset.load_font(io.BytesIO(raw), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=CHARSET)
        subsetter.subset(font)

        out_path = os.path.join(OUT_DIR, name)
        subset.save_font(font, out_path, options)
        font.close()
        print(f"{name}: {len(raw) / 1024:.1f} KiB -> {os.path.getsize(out_path) / 1024:.1f} KiB")


if __name__ == "__main__":
    main()
