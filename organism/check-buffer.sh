#!/bin/bash
# Quick check: what is Tela saying?
NURSERY="${NURSERY_DIR:-/var/opt/quadrumvirate/nursery}"
for mind in tela nowa tecton; do
    mem="$NURSERY/$mind/memory.json"
    if [ -f "$mem" ]; then
        buf=$(python3 -c "import json; m=json.loads(open('$mem').read()); b=m.get('buffer',[]); print('\n'.join(b) if b else '(silence)')")
        echo "=== $mind ==="
        echo "$buf"
        echo ""
    fi
done
