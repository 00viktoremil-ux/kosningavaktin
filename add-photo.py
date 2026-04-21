#!/usr/bin/env python3
"""
add-photo.py  —  bætir myndslóð inn í PHOTOS-hlutinn í kosningavaktin.html.

Notkun:
  ./add-photo.py S-11 https://example.com/photo.jpg
  ./add-photo.py --list                                  # sýnir hverja vantar
  ./add-photo.py --check                                 # prófar allar núverandi slóðir (HTTP 200?)
  ./add-photo.py --from-url https://party.is/candidates  # fetch-ar síðu og gefur hugmyndir

Lykill er 'PartyLetter-Num', t.d. D-1 fyrir Hildur Björnsdóttur, A-2 fyrir Líf Magneudóttur.
Býr til afrit (.bak.YYYYMMDD-HHMMSS) fyrir hverja breytingu.
"""
from __future__ import annotations
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

HTML = Path(__file__).parent / "kosningavaktin.html"
KEY_RE = re.compile(r"^[A-Z]-\d+$")

# Listi yfir framboð — (kóði, nafn, fjöldi frambjóðenda á lista)
PARTY_LIST = [
    ('A', 'Vinstrið', 46),
    ('B', 'Framsóknarflokkurinn', 46),
    ('C', 'Viðreisn', 46),
    ('D', 'Sjálfstæðisflokkurinn', 46),
    ('F', 'Flokkur fólksins', 46),
    ('G', 'Góðan daginn', 23),
    ('J', 'Sósíalistaflokkur Íslands', 46),
    ('M', 'Miðflokkurinn', 46),
    ('P', 'Píratar', 46),
    ('R', 'Okkar borg', 23),
    ('S', 'Samfylkingin', 46),
]


def read_html() -> str:
    return HTML.read_text(encoding="utf-8")


def write_html(s: str) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = HTML.with_suffix(f".html.bak.photo-{ts}")
    backup.write_bytes(HTML.read_bytes())
    HTML.write_text(s, encoding="utf-8")
    print(f"✓ Afrit: {backup.name}")


def get_photos(html: str) -> dict[str, str]:
    """Les PHOTOS-hlutinn úr HTML. Snýr {'S-1': 'url', ...}."""
    m = re.search(r"const PHOTOS\s*=\s*\{(.*?)\};", html, re.DOTALL)
    if not m:
        print("VILLA: fann ekki PHOTOS blokk.", file=sys.stderr)
        sys.exit(1)
    block = m.group(1)
    photos = {}
    # Matcha 'A-1': 'url' eða "A-1": "url"
    for em in re.finditer(r"['\"]([A-Z]-\d+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", block):
        photos[em.group(1)] = em.group(2)
    return photos


def insert_photo(html: str, key: str, url: str) -> str:
    """Bætir einni línu við PHOTOS-hlutinn (rétt fyrir ofan lokandi }; )."""
    if not KEY_RE.match(key):
        raise ValueError(f"Ólöglegur lykill '{key}'. Verður að vera t.d. 'S-11' eða 'D-1'.")
    m = re.search(r"(const PHOTOS\s*=\s*\{.*?)(};)", html, re.DOTALL)
    if not m:
        raise RuntimeError("fann ekki PHOTOS-hlutinn.")
    existing = m.group(1)
    # Ef lykillinn er til, skipti út gildinu
    key_re = re.compile(r"(['\"])" + re.escape(key) + r"\1\s*:\s*['\"][^'\"]*['\"]\s*,?")
    if key_re.search(existing):
        replaced = key_re.sub(f"'{key}': '{url}',", existing, count=1)
        new_html = html[: m.start()] + replaced + "};" + html[m.end():]
        return new_html
    # Ekki til — bætum við fyrir lokatáknið
    new_entry = f"  '{key}': '{url}',\n"
    new_html = html[: m.start()] + existing.rstrip() + "\n" + new_entry + "};" + html[m.end():]
    return new_html


def check_url(url: str, timeout: float = 10) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "kosningavaktin/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            if r.status == 200 and ct.startswith("image/"):
                return True, f"200 {ct}"
            return False, f"{r.status} {ct}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]


def cand_name_for(html: str, key: str) -> str:
    """Grípur nafn frambjóðanda úr RAW-fylkinu miðað við key (t.d. 'A-3')."""
    p, n = key.split("-")
    # RAW = [['A',1,'Sanna Magdalena Mörtudóttir',...], ...]
    pat = rf"\['{p}',{n},'([^']+)'"
    m = re.search(pat, html)
    return m.group(1) if m else "?"


def cmd_list(html: str) -> None:
    photos = get_photos(html)
    missing_per_party = {}
    for (code, name, n) in PARTY_LIST:
        missing = []
        for i in range(1, n + 1):
            k = f"{code}-{i}"
            if k not in photos:
                missing.append((i, cand_name_for(html, k)))
        missing_per_party[code] = missing
    print(f"\nMyndir í safni: {len(photos)}\n")
    for (code, name, n) in PARTY_LIST:
        miss = missing_per_party[code]
        have = n - len(miss)
        status = "✓" if have == n else ("~" if have > 0 else "·")
        print(f"  {status} {code} {name}: {have}/{n}")
        if miss and len(miss) < 10:
            for (i, nm) in miss:
                print(f"       · {code}-{i} {nm}")
        elif miss:
            for (i, nm) in miss[:3]:
                print(f"       · {code}-{i} {nm}")
            print(f"       … og {len(miss)-3} í viðbót")


def cmd_check(html: str) -> None:
    photos = get_photos(html)
    print(f"Prófa {len(photos)} slóðir…\n")
    bad = []
    for key, url in sorted(photos.items()):
        ok, msg = check_url(url)
        mark = "✓" if ok else "✗"
        name = cand_name_for(html, key)
        print(f"  {mark} {key:6s} {name[:28]:30s} {msg}")
        if not ok:
            bad.append(key)
    if bad:
        print(f"\n{len(bad)} brotnar slóðir: {', '.join(bad)}")
    else:
        print("\nAllar slóðir virka.")


def cmd_add(html: str, key: str, url: str) -> None:
    ok, msg = check_url(url)
    if not ok:
        print(f"⚠  Slóðin gaf ekki gilt myndsvar: {msg}")
        ans = input("Bæta samt við? [j/N] ").strip().lower()
        if ans != "j":
            print("Hætt við.")
            return
    new_html = insert_photo(html, key, url)
    write_html(new_html)
    name = cand_name_for(new_html, key)
    print(f"✓ {key} ({name}) skráð: {url}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    html = read_html()
    if args[0] == "--list":
        cmd_list(html)
    elif args[0] == "--check":
        cmd_check(html)
    elif len(args) == 2 and KEY_RE.match(args[0]):
        cmd_add(html, args[0], args[1])
    else:
        print("Notkun:")
        print("  ./add-photo.py --list             # hvað vantar?")
        print("  ./add-photo.py --check            # prófar allar slóðir")
        print("  ./add-photo.py S-11 <mynd-url>    # bæta við")


if __name__ == "__main__":
    main()
