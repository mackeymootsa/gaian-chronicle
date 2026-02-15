#!/usr/bin/env python3
"""
Calculate sunrise, sunset, and daylight duration for Stockholm.
No API needed — uses standard astronomical formulas.
Outputs markdown suitable for pulse context.
"""

import math
from datetime import datetime, timezone, timedelta

# Stockholm coordinates
LAT = 59.3293
LON = 18.0686

def sun_times(date, lat=LAT, lon=LON):
    """Calculate sunrise and sunset times using NOAA algorithm."""
    # Day of year
    n = date.timetuple().tm_yday

    # Solar noon approximation
    lng_hour = lon / 15.0

    # Sunrise
    t_rise = n + ((6 - lng_hour) / 24)
    # Sunset
    t_set = n + ((18 - lng_hour) / 24)

    # Sun's mean anomaly
    M_rise = (0.9856 * t_rise) - 3.289
    M_set = (0.9856 * t_set) - 3.289

    def calc_time(M, t):
        # Sun's true longitude
        L = M + (1.916 * math.sin(math.radians(M))) + \
            (0.020 * math.sin(2 * math.radians(M))) + 282.634
        L = L % 360

        # Right ascension
        RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L))))
        RA = RA % 360

        L_quad = (L // 90) * 90
        RA_quad = (RA // 90) * 90
        RA = RA + (L_quad - RA_quad)
        RA = RA / 15  # Convert to hours

        # Sun's declination
        sin_dec = 0.39782 * math.sin(math.radians(L))
        cos_dec = math.cos(math.asin(sin_dec))

        # Hour angle
        cos_H = (math.cos(math.radians(90.833)) -
                 (sin_dec * math.sin(math.radians(lat)))) / \
                (cos_dec * math.cos(math.radians(lat)))

        if cos_H > 1:
            return None  # No sunrise (polar night)
        if cos_H < -1:
            return None  # No sunset (midnight sun)

        return cos_H, RA, lng_hour, t

    result_rise = calc_time(M_rise, t_rise)
    result_set = calc_time(M_set, t_set)

    if result_rise is None or result_set is None:
        return None, None

    cos_H_rise, RA_rise, lng_hour, t_r = result_rise
    cos_H_set, RA_set, _, t_s = result_set

    # Sunrise hour angle (rising = 360 - acos)
    H_rise = 360 - math.degrees(math.acos(cos_H_rise))
    H_rise = H_rise / 15

    # Sunset hour angle
    H_set = math.degrees(math.acos(cos_H_set))
    H_set = H_set / 15

    # Local mean time
    T_rise = H_rise + RA_rise - (0.06571 * t_r) - 6.622
    T_set = H_set + RA_set - (0.06571 * t_s) - 6.622

    # UTC
    UT_rise = (T_rise - lng_hour) % 24
    UT_set = (T_set - lng_hour) % 24

    return UT_rise, UT_set


def hours_to_hhmm(h):
    """Convert decimal hours to HH:MM string."""
    hours = int(h)
    minutes = int((h - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"


def main():
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    sunrise_utc, sunset_utc = sun_times(today)
    sunrise_y, sunset_y = sun_times(yesterday)

    if sunrise_utc is None:
        print("## Daylight [CALCULATED]")
        print("Polar night or midnight sun — no standard sunrise/sunset.")
        return

    daylight_hours = sunset_utc - sunrise_utc
    if daylight_hours < 0:
        daylight_hours += 24

    # CET = UTC + 1 (winter), CEST = UTC + 2 (summer)
    # February = CET
    sunrise_local = (sunrise_utc + 1) % 24
    sunset_local = (sunset_utc + 1) % 24

    # Yesterday's daylight for delta
    if sunrise_y is not None and sunset_y is not None:
        daylight_y = sunset_y - sunrise_y
        if daylight_y < 0:
            daylight_y += 24
        delta_minutes = (daylight_hours - daylight_y) * 60
        delta_str = f"{delta_minutes:+.1f} min vs yesterday"
    else:
        delta_str = "no comparison available"

    print(f"## Daylight — {today.isoformat()} [CALCULATED]")
    print(f"- Sunrise: {hours_to_hhmm(sunrise_local)} CET ({hours_to_hhmm(sunrise_utc)} UTC)")
    print(f"- Sunset: {hours_to_hhmm(sunset_local)} CET ({hours_to_hhmm(sunset_utc)} UTC)")
    print(f"- Daylight: {hours_to_hhmm(daylight_hours)} ({delta_str})")
    print(f"- Location: Stockholm (59.33°N, 18.07°E)")


if __name__ == "__main__":
    main()
