#!/bin/bash
# Fetch recent git activity from the gaian-chronicle repo
REPO_DIR="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 1
echo "## Recent Repository Activity"
echo ""
git log --oneline --since="24 hours ago" --no-merges 2>/dev/null
COMMITS=$(git log --oneline --since="24 hours ago" --no-merges 2>/dev/null | wc -l)
if [ "$COMMITS" -eq 0 ]; then
    echo "(No commits in last 24 hours)"
fi
echo ""
echo "Last 5 commits:"
git log --oneline -5 2>/dev/null
echo ""
echo "Changed files (last commit):"
git diff --name-only HEAD~1 HEAD 2>/dev/null
