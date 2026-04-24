#!/usr/bin/env python3
"""
update-polls.py  —  sækir nýjustu kosningakannanir með Claude AI og saumar
þær beint inn í index.html. Engin AI-kall í vafranum.

Notkun:
  ANTHROPIC_API_KEY=sk-ant-... ./update-polls.py
  eða settu lykil í ~/.anthropic-key (fyrsta lína)

Keyrir:
  1. Les núverandi POLLS_RAW úr HTML
  2. Biður Claude (með web_search) að finna kannanir sem ekki eru í safninu
  3. Sameinar við núverandi, reiknar D'Hondt í JS (gert á síðunni)
  4. Skrifar nýtt POLLS_RAW blokk í HTML, býr til .bak afrit

Ekkert pip install þarf — notar aðeins Python stdlib.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

HTML_PATH = Path(__file__).parent / "index.html"
MODEL = "claude-sonnet-4-5-20250929"
API_URL = "https://api.anthropic.com/v1/messages"
MAX_TOKENS = 4000
TODAY_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    key_file = Path.home() / ".anthropic-key"
    if key_file.exists():
        key = key_file.read_text().strip().splitlines()[0].strip()
        if key:
            return key
    print("VILLA: ANTHROPIC_API_KEY ekki sett. Settu env-breytu eða skráðu í ~/.anthropic-key", file=sys.stderr)
    sys.exit(1)


# Uppfært: POLLS_RAW var fært inn í POLLS_BY_MUNI = { rvk: [...], hafn: [...], ... }
# Við höldum áfram að uppfæra aðeins Reykjavíkur-blokkina (rvk) — hinir muni
# hafa enn sem komið er ekki nægilega reglulegar kannanir.
POLLS_BLOCK_RE = re.compile(
    r"(rvk:\s*\[)(.*?)(\n  \],)",
    re.DOTALL,
)


def read_current_polls(html: str) -> tuple[str, int, int]:
    """Returns (polls_block_content, start_offset, end_offset) fyrir rvk-blokkina."""
    m = POLLS_BLOCK_RE.search(html)
    if not m:
        print("VILLA: fann ekki POLLS_BY_MUNI.rvk blokk í HTML. Hefur sniðið breyst?", file=sys.stderr)
        sys.exit(1)
    return m.group(2), m.start(2), m.end(2)


def extract_poll_summaries(block: str) -> list[dict]:
    """Extract just {source, date} pairs from current polls, for prompting Claude."""
    # Simple regex for source: 'X', date: 'Y' — not a full JS parser
    summaries = []
    for m in re.finditer(r"source:\s*'([^']+)'[^}]*?date:\s*'([^']+)'", block):
        summaries.append({"source": m.group(1), "date": m.group(2)})
    return summaries


def call_claude(api_key: str, prompt: str) -> str:
    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace")
        print(f"VILLA frá Anthropic API ({e.code}): {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"VILLA við að tengjast Anthropic API: {e}", file=sys.stderr)
        sys.exit(1)
    # Extract text from content blocks (skipping tool_use / tool_result / server_tool_use)
    parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()


def build_prompt(existing: list[dict]) -> str:
    existing_lines = "\n".join(f"- {p['source']} · {p['date']}" for p in existing)
    return f"""Þú ert að halda við gagnagrunni um kosningakannanir fyrir borgarstjórnarkosningar Reykjavíkur 16. maí 2026. Dagur í dag er {TODAY_ISO}.

Kannanir nú þegar í safninu (EKKI endurtaka þessar — en þær mega vera til viðmiðunar):
{existing_lines}

Verkefni: Notaðu web_search til að finna kannanir um fylgi í borgarstjórnarkosningum Reykjavík 2026 sem EKKI eru í listanum að ofan. Leitaðu sérstaklega á:
  - kosningaspa.is (Baldur Héðinsson)
  - gallup.is (Þjóðarpúls — Reykjavík sérstaklega)
  - maskina.is eða Borgarviti
  - prosent.is
  - visir.is, mbl.is, ruv.is, dv.is, heimildin.is (nýleg fréttaumfjöllun)
  - is.wikipedia.org — grein um "Borgarstjórnarkosningar í Reykjavík 2026"

Skilaðu EINUNGIS JSON fylki — ekkert annað orð á undan eða eftir. Snið:

[
  {{
    "source": "Gallup / Þjóðarpúls",
    "method": "Netkönnun",
    "date": "1.–15. apríl 2026",
    "n": "—",
    "tag": "gallup",
    "data": {{"D": 27.6, "S": 23.2, "A": 13.5, "C": 10.0, "M": 10.7, "B": 3.9, "P": 3.5, "F": 3.8, "J": 2.5, "R": 1.5, "G": 0}},
    "url": "https://...",
    "note": "stutt samantekt — ein setning"
  }}
]

Kröfur:
1. AÐEINS raunverulegar kannanir með verifíeranlegum heimildum (url).
2. Flokkakóðar: A=Vinstrið (VG+Vor), B=Framsókn, C=Viðreisn, D=Sjálfstæðisflokkur, F=Flokkur fólksins, G=Góðan daginn, J=Sósíalistar, M=Miðflokkur, P=Píratar, R=Okkar borg, S=Samfylkingin. Skiptu út ef flokkur mælist ekki — alls ekki skálda upp tölur.
3. Prósentur með einum aukastaf ef birtar (annars heil tala).
4. tag: "gallup", "maskina", "baldur", "prosent", eða "annad".
5. Ef EKKERT nýtt finnst, skilaðu tómu fylki [].

JSON:"""


def parse_json_response(text: str) -> list[dict]:
    # Leyfa að svarið sé í ``` eða með smá texta fyrir
    t = text.strip()
    # Strip markdown fences
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```\s*$", "", t)
    # Finna fyrsta [ og síðasta ]
    start = t.find("[")
    end = t.rfind("]")
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"Fann ekki JSON fylki í svari: {text[:300]}")
    raw = t[start : end + 1]
    return json.loads(raw)


def validate_poll(p: dict) -> str | None:
    """Return error message if invalid, else None."""
    required = ("source", "date", "data", "tag")
    for k in required:
        if k not in p:
            return f"vantar '{k}'"
    if not isinstance(p.get("data"), dict):
        return "'data' verður að vera hlutur"
    parties = set("ABCDFGJMPRS")
    for code, v in p["data"].items():
        if code not in parties:
            return f"óþekktur flokkur: {code}"
        if not isinstance(v, (int, float)) or v < 0 or v > 60:
            return f"ógilt gildi fyrir {code}: {v}"
    tot = sum(v for v in p["data"].values() if isinstance(v, (int, float)))
    if tot < 80 or tot > 105:
        return f"heildarsumma ólíkleg: {tot:.1f}%"
    return None


def js_quote(s: str) -> str:
    """Escape string for use as JS single-quoted string."""
    return "'" + s.replace("\\", "\\\\").replace("'", r"\'").replace("\n", " ").strip() + "'"


def format_poll_js(p: dict) -> str:
    data_kv = ", ".join(f"{k}:{v}" for k, v in p["data"].items())
    return (
        "  {"
        f"source:{js_quote(p['source'])}, "
        f"method:{js_quote(p.get('method', ''))}, "
        f"date:{js_quote(p['date'])}, "
        f"n:{js_quote(p.get('n', '—'))}, "
        f"tag:{js_quote(p.get('tag', 'annad'))},\n"
        f"   data:{{{data_kv}}},\n"
        f"   url:{js_quote(p.get('url', ''))},\n"
        f"   note:{js_quote(p.get('note', ''))}}}"
    )


def main():
    api_key = load_api_key()
    if not HTML_PATH.exists():
        print(f"VILLA: {HTML_PATH} ekki til", file=sys.stderr)
        sys.exit(1)
    html = HTML_PATH.read_text(encoding="utf-8")
    block, start, end = read_current_polls(html)
    existing = extract_poll_summaries(block)
    print(f"Núverandi kannanir: {len(existing)}")
    for p in existing:
        print(f"  · {p['source']} — {p['date']}")

    print(f"\nKalla á Claude ({MODEL}) með web_search …")
    t0 = time.time()
    prompt = build_prompt(existing)
    raw = call_claude(api_key, prompt)
    dur = time.time() - t0
    print(f"  svar fékkst á {dur:.1f}s ({len(raw)} stafir)")

    try:
        new_polls = parse_json_response(raw)
    except Exception as e:
        print(f"VILLA: gat ekki þátt JSON: {e}", file=sys.stderr)
        print("Svar frá Claude:\n" + raw, file=sys.stderr)
        sys.exit(1)

    if not new_polls:
        print("\nEngar nýjar kannanir fundust. Ekkert breytt.")
        return

    # Validate
    valid = []
    for p in new_polls:
        err = validate_poll(p)
        if err:
            print(f"  ⚠︎ hoppa yfir {p.get('source','?')} — {err}")
            continue
        valid.append(p)

    if not valid:
        print("\nEngar gildar kannanir fundust. Ekkert breytt.")
        return

    print(f"\nNýjar kannanir ({len(valid)}):")
    for p in valid:
        pcs = ", ".join(f"{k}:{v}" for k, v in sorted(p["data"].items(), key=lambda kv: -kv[1])[:3])
        print(f"  + {p['source']} — {p['date']} — {pcs}…")

    # Byggja nýja POLLS_RAW blokk: nýjar fyrst, svo núverandi (þannig raðast efst = nýjast)
    new_js = ",\n".join(format_poll_js(p) for p in valid)
    new_block = "\n" + new_js + ",\n" + block.lstrip("\n")

    # Backup
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = HTML_PATH.with_suffix(f".html.bak.{ts}")
    backup.write_bytes(HTML_PATH.read_bytes())
    print(f"\nAfrit vistað: {backup.name}")

    # Skrifa uppfært HTML
    updated = html[:start] + new_block + html[end:]
    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"Uppfærði {HTML_PATH.name} — bætti við {len(valid)} könnun{'' if len(valid)==1 else 'um'}.")


if __name__ == "__main__":
    main()
