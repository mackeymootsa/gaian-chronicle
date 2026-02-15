#!/bin/bash
# ============================================================
# Weather data fetcher for Tela pulse
# Fetches current Stockholm weather from SMHI open API
# Station: Stockholm-Bromma Flygplats (97200) — has live data
# No authentication required
# ============================================================

STATION="97200"
STATION_NAME="Stockholm-Bromma Flygplats"
BASE_URL="https://opendata-download-metobs.smhi.se/api/version/1.0"

WEATHER_DATA=""

fetch_param() {
    local param_id="$1"
    local param_name="$2"
    local result
    result=$(curl -s --max-time 10 \
        "${BASE_URL}/parameter/${param_id}/station/${STATION}/period/latest-hour/data.json" \
        2>/dev/null)
    
    if [ $? -eq 0 ] && echo "$result" | jq -e '.value[0]' >/dev/null 2>&1; then
        local value=$(echo "$result" | jq -r '.value[0].value // empty' 2>/dev/null)
        local timestamp=$(echo "$result" | jq -r '.value[0].date // 0' 2>/dev/null)
        local quality=$(echo "$result" | jq -r '.value[0].quality // "?"' 2>/dev/null)
        if [ -n "$value" ]; then
            local iso_time=$(date -u -d @$((timestamp / 1000)) +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")
            WEATHER_DATA="${WEATHER_DATA}${param_name}: ${value} (${iso_time}, quality: ${quality})\n"
        fi
    fi
}

fetch_param 1 "Air temperature (°C)"
fetch_param 6 "Relative humidity (%)"
fetch_param 4 "Wind speed (m/s)"
fetch_param 3 "Wind direction (degrees)"
fetch_param 7 "Precipitation last hour (mm)"
fetch_param 9 "Air pressure (hPa)"

if [ -n "$WEATHER_DATA" ]; then
    echo "## Live Weather Data — ${STATION_NAME} (SMHI Station ${STATION})"
    echo "Source: SMHI Open Data API (opendata-download-metobs.smhi.se)"
    echo "All values [SYNTHETIC/REMOTE]"
    echo ""
    echo -e "$WEATHER_DATA"
else
    echo "## Weather Data: UNAVAILABLE"
    echo "SMHI API unreachable or returned no data."
fi
