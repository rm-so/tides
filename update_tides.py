#!/usr/bin/env python3
"""Builds index.html: Acadia Beach tide calendar with fresh data embedded.
Tides: Canadian Hydrographic Service (CHS) official predictions, nearest station.
Weather: Open-Meteo hourly air temperature. Stdlib only. Run daily (see README below)."""
import json, math, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LAT, LON = 49.271, -123.235          # Acadia Beach, Vancouver
DAYS = 32
TZ = ZoneInfo("America/Vancouver")
IWLS = "https://api-iwls.dfo-mpo.gc.ca/api/v1"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "acadia-tide-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))

def tides():
    stations = get(f"{IWLS}/stations")
    near = sorted(
        (km(LAT, LON, s["latitude"], s["longitude"]), s) for s in stations
        if s.get("latitude") is not None)
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    for dist, s in near[:15]:                      # try nearest stations until one has hi/lo predictions
        rows = []
        try:
            for i in range(0, DAYS, 15):
                a, b = start + timedelta(days=i), start + timedelta(days=min(i + 15, DAYS))
                q = urllib.parse.urlencode({"time-series-code": "wlp-hilo",
                    "from": a.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": b.strftime("%Y-%m-%dT%H:%M:%SZ")})
                rows += get(f"{IWLS}/stations/{s['id']}/data?{q}")
        except Exception:
            continue
        if rows:
            out = {}
            for r in rows:
                t = datetime.fromisoformat(r["eventDate"].replace("Z", "+00:00")).astimezone(TZ)
                out[t] = r["value"]
            text = "\n".join(f"{t:%Y-%m-%d %H:%M}, {v}" for t, v in sorted(out.items()))
            name = f"{s['officialName']} (CHS, {dist:.1f} km from beach)"
            return text, name
    raise SystemExit("No CHS station with high/low predictions found")

def weather():
    q = urllib.parse.urlencode({"latitude": LAT, "longitude": LON, "hourly": "temperature_2m",
                                "timezone": "America/Vancouver", "forecast_days": 16, "past_days": 1})
    return json.dumps(get("https://api.open-meteo.com/v1/forecast?" + q))

if __name__ == "__main__":
    t, name = tides()
    w = weather()
    html = open("spanish-banks-tides.html", encoding="utf-8").read()
    pre = "<script>window.PRELOAD=" + json.dumps({"tides": t, "wx": w, "station": name}).replace("</", "<\\/") + "</script>"
    open("index.html", "w", encoding="utf-8").write(html.replace("<!--PRELOAD-->", pre))
    print("index.html written —", name, "—", len(t.splitlines()), "tide events")
