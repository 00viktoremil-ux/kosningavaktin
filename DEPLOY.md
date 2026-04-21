# Setja Kosningavaktina í loftið

Þessi leiðbeining er fyrir þig sem hefur aldrei publish-að vef áður. **Heildartími: ~10 mín.** Kostnaður: ekkert.

---

## Hvað þú þarft áður en þú byrjar

- **Mac** með aðgangi að Terminal (þú ert nú þegar þar)
- **Homebrew** (uppsett — tékkaði nú þegar) ✓
- **GitHub reikningur** (frítt á https://github.com/join) — 2 mín ef þú hefur ekki
- **Anthropic API-lykill** — útskýrt í skrefi 2

---

## Skref 1 — Opna Terminal

Ef þú ert ekki þegar með Terminal opið:
- Ýttu **⌘ + mellibil** (Spotlight)
- Skrifaðu `Terminal` og ýttu **Enter**

---

## Skref 2 — Sækja Anthropic API-lykil

1. Opnaðu í vafra: **https://console.anthropic.com/settings/keys**
2. Innskráðu þig eða búa til reikning (frítt að prófa, en kostar lítið eftir fyrstu $5)
3. Smelltu á **„Create Key"** efst í hægra horni
4. Gefðu honum nafn (t.d. „Kosningavaktin") og smelltu **Create Key**
5. **Afritaðu** strenginn sem birtist (byrjar á `sk-ant-api03-…`) — þú sérð hann aðeins einu sinni!
6. Límdu hann í nótubók tímabundið, eða haltu vafraflipanum opnum

---

## Skref 3 — Keyra uppsetningarskriptið

Í Terminal, skrifaðu eftirfarandi (eða afritaðu-límdu):

```sh
cd /Users/viktoremil/Claude
./deploy.sh
```

Skriptið mun gera þetta sjálfkrafa:

| Skref | Hvað gerist |
|-------|-------------|
| ➊ | Athugar að þú hafir Homebrew, git og gh uppsett (setur upp ef vantar) |
| ➋ | Skráir þig inn á GitHub (vafri opnast sjálfkrafa — smelltu „Authorize") |
| ➌ | Biður um API-lykilinn þinn (límdu inn, ýttu Enter) |
| ➍ | Biður um nafn á repo-inu (Enter = kosningavaktin) |
| ➎ | Endurnefnir HTML-skrána í index.html (svo URL-ið verði stutt) |
| ➏ | Býr til git-repo og fyrsta commit |
| ➐ | Býr til GitHub-repo og pushar |
| ➑ | Skráir API-lykilinn sem „Secret" (aldrei sýnilegur aftur) |
| ➒ | Kveikir á GitHub Pages |
| ✓ | Sýnir URL-ið á vefnum þínum |

---

## Eftir keyrslu

Skriptið skilar þér URL á vefnum, eitthvað eins og:

```
🌐 https://þittnafn.github.io/kosningavaktin/
```

- **Vefurinn birtist eftir 1-2 mínútur** við fyrstu upphleðslu
- Vefurinn endurbyggir sjálfkrafa hvert skipti sem þú pushar breytingum
- **Kannanir uppfærast sjálfkrafa** á hverjum morgni kl. 09 UTC

---

## Prófa sjálfvirkni

Til að prófa að Actions virki NÚNA (án þess að bíða til morguns), keyrðu:

```sh
cd /Users/viktoremil/Claude
gh workflow run "Uppfæra kannanir daglega"
```

Bíddu 2 mín og skoðaðu síðan:

```sh
gh run watch
```

Eða farðu í vafrann á `https://github.com/þittnafn/kosningavaktin/actions`.

---

## Ef eitthvað misheppnast

### „gh: command not found" eftir keyrslu skripts
Skriptið á að hafa sett upp gh sjálfvirkt. Keyrðu handvirkt:
```sh
brew install gh
./deploy.sh
```

### „Pages mistókst að virkjast"
Handvirkt í vafra:
1. Farðu á `https://github.com/þittnafn/kosningavaktin/settings/pages`
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/ (root)**
4. Smelltu **Save**

### Actions workflow mistekst
1. Farðu á `https://github.com/þittnafn/kosningavaktin/actions`
2. Smelltu á rauða X-ið til að sjá villuboð
3. Algeng mistök:
   - API-lykill útrunninn → búa til nýjan og setja sem Secret aftur
   - Anthropic credit búið → sjá https://console.anthropic.com/settings/billing

### „Permission denied" við `./deploy.sh`
```sh
chmod +x deploy.sh
./deploy.sh
```

---

## Breyta einhverju síðar

Alltaf sama rútínan:

```sh
cd /Users/viktoremil/Claude
# ... breyta kosningavaktin.html eða index.html ...
git add .
git commit -m "Lýsing á breytingunni"
git push
```

Vefurinn endurbyggir sjálfkrafa á 30-60 sek.

---

## Uppfæra myndir af frambjóðendum

```sh
cd /Users/viktoremil/Claude
./add-photo.py --list                           # sýnir hverja vantar
./add-photo.py A-3 https://dæmi.is/mynd.jpg     # bætir mynd
git add . && git commit -m "Bæti mynd af A-3" && git push
```

---

## Custom lén (t.d. kosningavaktin.is)

Ef þú vilt vefinn á eigin léni (kostar ~1000 kr/ári hjá Isnic):

1. Kauptu lénið
2. Stilltu DNS CNAME record: `kosningavaktin.is` → `þittnafn.github.io`
3. Í GitHub repo: **Settings → Pages → Custom domain** → skrifaðu lénið
4. GitHub stillir SSL sjálfkrafa (getur tekið ~10 mín)

---

## Öryggi — hvað er öruggt og hvað ekki

✅ **Öruggt:**
- API-lykillinn er í GitHub Secrets — enginn sér hann, ekki einu sinni þú (eftir upptöku)
- Vefurinn sjálfur (HTML-ið sem notendur sjá) inniheldur ENGAN API-lykil
- `.gitignore` hindrar að `.anthropic-key`, .bak-afrit og logs komist í git

⚠️ **Passa:**
- Ef þú lekar API-lykli í commit skaltu STRAX:
  1. Endurheimta á https://console.anthropic.com/settings/keys (revoke gamla, búa til nýjan)
  2. Uppfæra Secret í GitHub
- Ef repo verður private í framtíðinni þarftu GitHub Pro fyrir Pages á private repo

---

## Hvað ef ég skil ekkert af þessu?

Hringdu í einhvern sem þekkir git (flestir forritarar) eða sendu mér skjáskot af villuboðum. Skriptið er byggt til að gera 95% sjálft — þú þarft bara að fylgja leiðbeiningum á skjánum og líma inn API-lykilinn einu sinni.
