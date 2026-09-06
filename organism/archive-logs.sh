#!/bin/bash
# Optional manual archival. Pulse also archives old logs before daily rollover.
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
exec python3 - "$SCRIPT_DIR" "${NURSERY_DIR:-/var/opt/quadrumvirate/nursery}" <<'PY'
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from runtime import archive_daily_log, mind_lock

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
failed = False
for mind in ("tela", "nowa", "tecton"):
    mind_dir = Path(sys.argv[2]) / mind
    if not mind_dir.exists():
        continue
    try:
        with mind_lock(mind_dir):
            archived = archive_daily_log(mind_dir / "daily_log.md", today)
            if archived:
                print(f"Archived {mind}: {archived}")
    except BlockingIOError:
        print(f"SKIP: {mind} has an active runtime job")
    except (OSError, ValueError) as error:
        print(f"ERROR: {mind}: {error}", file=sys.stderr)
        failed = True
sys.exit(1 if failed else 0)
PY
