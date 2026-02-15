#!/bin/bash
# ============================================================
# Migrate from flat nursery to repo-based Quadrumvirate
# Run on juuri after cloning the repo
# ============================================================

set -euo pipefail

REPO_DIR="/opt/gaian-chronicle"
OLD_NURSERY="/var/opt/quadrumvirate/nursery"
NEW_NURSERY="/var/opt/quadrumvirate/nursery"

echo "=== Quadrumvirate Migration ==="
echo ""

# 1. Check repo exists
if [ ! -d "$REPO_DIR/organism" ]; then
    echo "ERROR: Repo not found at $REPO_DIR"
    echo "Clone it first: git clone <url> $REPO_DIR"
    exit 1
fi

# 2. Stop cron
echo "Step 1: Disable cron (comment out pulse lines manually if needed)"
echo "  Run: crontab -e"
echo ""

# 3. Create per-mind directories
echo "Step 2: Creating per-mind runtime directories..."
mkdir -p "${NEW_NURSERY}/tela"
mkdir -p "${NEW_NURSERY}/nowa"
mkdir -p "${NEW_NURSERY}/tecton"

# 4. Migrate Tela's existing state
echo "Step 3: Migrating Tela's runtime state..."
if [ -f "${OLD_NURSERY}/memory.json" ]; then
    cp "${OLD_NURSERY}/memory.json" "${NEW_NURSERY}/tela/memory.json"
    echo "  ✓ memory.json"
fi
if [ -f "${OLD_NURSERY}/daily_log.md" ]; then
    cp "${OLD_NURSERY}/daily_log.md" "${NEW_NURSERY}/tela/daily_log.md"
    echo "  ✓ daily_log.md"
fi
if [ -f "${OLD_NURSERY}/budget_tracker.json" ]; then
    cp "${OLD_NURSERY}/budget_tracker.json" "${NEW_NURSERY}/tela/budget.json"
    echo "  ✓ budget.json (renamed from budget_tracker.json)"
fi
if [ -f "${OLD_NURSERY}/pulse.log" ]; then
    cp "${OLD_NURSERY}/pulse.log" "${NEW_NURSERY}/tela/pulse.log"
    echo "  ✓ pulse.log"
fi
if [ -f "${OLD_NURSERY}/error.log" ]; then
    cp "${OLD_NURSERY}/error.log" "${NEW_NURSERY}/tela/error.log"
    echo "  ✓ error.log"
fi
if [ -f "${OLD_NURSERY}/pulse_brief.md" ]; then
    cp "${OLD_NURSERY}/pulse_brief.md" "${NEW_NURSERY}/tela/pulse_brief.md"
    echo "  ✓ pulse_brief.md"
fi

# 5. Ensure .env is still in place
echo ""
if [ -f "${OLD_NURSERY}/.env" ]; then
    echo "Step 4: .env found at ${OLD_NURSERY}/.env ✓"
else
    echo "Step 4: WARNING — .env not found. Create it:"
    echo "  cat > ${OLD_NURSERY}/.env << 'EOF'"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    echo "  export OPENAI_API_KEY=sk-..."
    echo "  export GOOGLE_API_KEY=AI..."
    echo "  EOF"
    echo "  chmod 600 ${OLD_NURSERY}/.env"
fi

echo ""
echo "Step 5: Update crontab to use new pulse script:"
echo ""
echo "  # Tela - hourly"
echo "  0 * * * * . ${OLD_NURSERY}/.env && cd ${REPO_DIR} && NURSERY_DIR=${NEW_NURSERY} /usr/bin/python3 organism/pulse.py tela"
echo ""
echo "Step 6: Test manually:"
echo "  source ${OLD_NURSERY}/.env"
echo "  cd ${REPO_DIR}"
echo "  NURSERY_DIR=${NEW_NURSERY} python3 organism/pulse.py tela"
echo "  cat ${NEW_NURSERY}/tela/daily_log.md | tail -20"
echo ""
echo "=== Migration complete ==="
