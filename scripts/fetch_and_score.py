import csv, json, math, time
import requests

PARIS_LAT, PARIS_LON = 48.8566, 2.3522
EMISSIONS_FACTOR_KG_PER_KM = 0.15  # DEFRA-style short-haul factor -- verify/update

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def fetch_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,precipitation_sum,sunshine_duration",
        "timezone": "auto", "forecast_days": 7,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    avg_temp = sum(daily["temperature_2m_max"]) / len(daily["temperature_2m_max"])
    total_precip = sum(daily["precipitation_sum"])
    avg_sunshine = sum(daily["sunshine_duration"]) / len(daily["sunshine_duration"])
    return avg_temp, total_precip, avg_sunshine

def normalize(values, invert=False):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    scaled = [(v - lo) / (hi - lo) for v in values]
    return [1 - s for s in scaled] if invert else scaled

def main():
    with open("data/capitals.csv") as f:
        rows = list(csv.DictReader(f))

    destinations = []
    for row in rows:
        if row["capital"] == "Paris":
            continue
        lat, lon = float(row["lat"]), float(row["lon"])
        distance_km = haversine_km(PARIS_LAT, PARIS_LON, lat, lon)
        avg_temp, total_precip, avg_sunshine = fetch_weather(lat, lon)
        destinations.append({
            "country": row["country"], "capital": row["capital"],
            "lat": lat, "lon": lon,
            "distance_km": round(distance_km, 1),
            "co2_kg_roundtrip": round(2 * distance_km * EMISSIONS_FACTOR_KG_PER_KM, 1),
            "avg_max_temp": round(avg_temp, 1),
            "total_precip_mm": round(total_precip, 1),
            "avg_sunshine_s": round(avg_sunshine, 0),
        })
        time.sleep(0.5)  # be polite to a free, shared API

    temp_scores = normalize([d["avg_max_temp"] for d in destinations])
    sun_scores = normalize([d["avg_sunshine_s"] for d in destinations])
    rain_scores = normalize([d["total_precip_mm"] for d in destinations], invert=True)
    co2_scores = normalize([d["co2_kg_roundtrip"] for d in destinations], invert=True)

    for d, t, s, rn, c in zip(destinations, temp_scores, sun_scores, rain_scores, co2_scores):
        d["weather_score"] = round((t + s + rn) / 3, 3)
        d["co2_score"] = round(c, 3)
        d["final_score"] = round((d["weather_score"] + d["co2_score"]) / 2, 3)

    destinations.sort(key=lambda d: d["final_score"], reverse=True)

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "emissions_factor_kg_per_km": EMISSIONS_FACTOR_KG_PER_KM,
        "destinations": destinations,
    }
    with open("docs/data/rankings.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
