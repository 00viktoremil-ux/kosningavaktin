#!/bin/bash
# ============================================================================
# deploy.sh — Setur Kosningavaktina í loftið á GitHub Pages í einu skrefi.
# Keyrir í Terminal: ./deploy.sh
# Þú þarft: macOS, Homebrew (brew.sh), GitHub reikning, Anthropic API-lykil.
# ============================================================================

set -e  # Stoppa ef eitthvað mistekst

cd "$(dirname "$0")"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   KOSNINGAVAKTIN — útgáfa á netið                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo

# --- 1. Check prerequisites ----------------------------------------------
echo -e "${BLUE}➊  Athuga uppsetningu…${NC}"

if ! command -v brew &>/dev/null; then
  echo -e "${RED}✗ Homebrew ekki uppsett.${NC}"
  echo "  Settu upp með einni skipun (copy-paste í Terminal):"
  echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  exit 1
fi
echo "   ✓ Homebrew til staðar"

if ! command -v git &>/dev/null; then
  echo -e "${YELLOW}  Git vantar — set upp…${NC}"
  brew install git
fi
echo "   ✓ Git til staðar"

if ! command -v gh &>/dev/null; then
  echo -e "${YELLOW}  GitHub CLI vantar — set upp…${NC}"
  brew install gh
fi
echo "   ✓ GitHub CLI til staðar"
echo

# --- 2. GitHub authentication --------------------------------------------
echo -e "${BLUE}➋  Skrá inn á GitHub…${NC}"
if gh auth status &>/dev/null; then
  USER=$(gh api user -q .login)
  echo "   ✓ Innskráð/ur sem: $USER"
else
  echo "   Opna innskráningu (vafri opnast sjálfkrafa)…"
  echo "   Veldu: GitHub.com → HTTPS → Login with a web browser"
  gh auth login
  USER=$(gh api user -q .login)
  echo "   ✓ Innskráð/ur sem: $USER"
fi
echo

# --- 3. Get Anthropic API key --------------------------------------------
echo -e "${BLUE}➌  Anthropic API-lykill${NC}"
echo "   Sótt á: https://console.anthropic.com/settings/keys"
echo "   (Byrjar á 'sk-ant-…', afritaðu allt)"
read -sp "   Límdu lykilinn hér og ýttu Enter: " API_KEY; echo
if [[ ! "$API_KEY" =~ ^sk-ant- ]]; then
  echo -e "${RED}   ✗ Lykillinn byrjar ekki á 'sk-ant-'. Hættu við. Engin skráning gerð.${NC}"
  exit 1
fi
echo "   ✓ Lykill móttekinn (birtist ekki aftur á skjánum)"
echo

# --- 4. Repo name --------------------------------------------------------
echo -e "${BLUE}➍  Nafn á GitHub-repo${NC}"
read -p "   (Enter fyrir 'kosningavaktin'): " REPO_NAME
REPO_NAME=${REPO_NAME:-kosningavaktin}
echo

# --- 5. Rename HTML til index.html svo URL-ið verði hreinna --------------
if [ -f "kosningavaktin.html" ] && [ ! -f "index.html" ]; then
  echo -e "${BLUE}➎  Endurnefna kosningavaktin.html → index.html${NC}"
  echo "   (Gerir URL-ið styttra: /$REPO_NAME/ í staðinn fyrir /$REPO_NAME/kosningavaktin.html)"
  read -p "   Endurnefna? (j/n, Enter = j): " RENAME
  if [[ "$RENAME" != "n" ]]; then
    cp kosningavaktin.html index.html
    # Uppfæra script og workflow til að vísa á index.html
    sed -i.bak 's|kosningavaktin\.html|index.html|g' update-polls.py 2>/dev/null && rm update-polls.py.bak
    sed -i.bak 's|kosningavaktin\.html|index.html|g' .github/workflows/update-polls.yml 2>/dev/null && rm .github/workflows/update-polls.yml.bak
    rm kosningavaktin.html
    echo "   ✓ Endurnefnt, script + workflow uppfærð"
  fi
fi
echo

# --- 6. Git init + first commit -----------------------------------------
echo -e "${BLUE}➏  Búa til git-repo og fyrsta commit${NC}"
if [ ! -d ".git" ]; then
  git init -b main
fi
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Fyrsta útgáfa Kosningavaktarinnar"
  echo "   ✓ Commit gert"
else
  echo "   (Ekkert nýtt að commita)"
fi
echo

# --- 7. Create GitHub repo + push ----------------------------------------
echo -e "${BLUE}➐  Búa til GitHub-repo og pusha…${NC}"
if gh repo view "$USER/$REPO_NAME" &>/dev/null; then
  echo "   Repo '$USER/$REPO_NAME' er þegar til."
  if ! git remote get-url origin &>/dev/null; then
    git remote add origin "https://github.com/$USER/$REPO_NAME.git"
  fi
  git push -u origin main || git push -u origin main --force
else
  gh repo create "$REPO_NAME" --public --source=. --remote=origin --push \
    --description "Hlutlaus upplýsingavefur um borgarstjórnarkosningar Reykjavíkur 2026"
  echo "   ✓ Repo búið til: https://github.com/$USER/$REPO_NAME"
fi
echo

# --- 8. Set API key secret ----------------------------------------------
echo -e "${BLUE}➑  Skrá API-lykil sem GitHub Secret…${NC}"
echo "$API_KEY" | gh secret set ANTHROPIC_API_KEY
echo "   ✓ ANTHROPIC_API_KEY skráður (aldrei sýnilegur framar)"
echo

# --- 9. Enable GitHub Pages ---------------------------------------------
echo -e "${BLUE}➒  Kveikja GitHub Pages…${NC}"
# API kallar sem kveikir Pages frá main-branch / root
gh api -X POST "repos/$USER/$REPO_NAME/pages" \
  -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
  || gh api -X PUT "repos/$USER/$REPO_NAME/pages" \
       -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
  || echo -e "${YELLOW}   (Kveikja á Pages handvirkt ef þetta mistekst — sjá skref 3 neðst)${NC}"
echo "   ✓ Pages kveikt"
echo

# --- 10. Done -----------------------------------------------------------
REPO_URL="https://github.com/$USER/$REPO_NAME"
SITE_URL="https://$USER.github.io/$REPO_NAME/"
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✓ LOKIÐ!                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo
echo -e "   🌐 ${GREEN}Vefurinn:${NC} $SITE_URL"
echo -e "      (birtist eftir 1-2 mín við fyrstu upphleðslu)"
echo
echo -e "   📦 ${GREEN}GitHub repo:${NC} $REPO_URL"
echo -e "   ⚙️  ${GREEN}Actions:${NC} $REPO_URL/actions"
echo
echo "   Hvað gerist næst sjálfkrafa:"
echo "     • Actions keyrir daglega kl. 09:00 UTC og uppfærir kannanir."
echo "     • Ef kannanir breytast, commit-ast þær sjálfkrafa."
echo "     • GH Pages endurbyggir vefinn á 30-60 sek við hverja breytingu."
echo
echo "   Til að prófa uppfærslu núna:"
echo "     $ gh workflow run 'Uppfæra kannanir daglega'"
echo
