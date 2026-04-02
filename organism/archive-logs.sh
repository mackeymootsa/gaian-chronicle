#!/bin/bash
# Archive old daily logs. Run manually or via weekly cron.
NURSERY="${NURSERY_DIR:-/var/opt/quadrumvirate/nursery}"
for mind in tela nowa tecton; do
    dir="$NURSERY/$mind"
    log="$dir/daily_log.md"
    if [ -f "$log" ]; then
        date_in_log=$(head -1 "$log" | grep -oP '\d{4}-\d{2}-\d{2}')
        today=$(date -u +%Y-%m-%d)
        if [ "$date_in_log" != "$today" ] && [ -n "$date_in_log" ]; then
            archive="$dir/archive"
            mkdir -p "$archive"
            cp "$log" "$archive/daily_log_${date_in_log}.md"
            echo "Archived $mind log from $date_in_log"
        fi
    fi
done
