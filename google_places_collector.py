"""
Google Places Data Collector for Municipalities
================================================
Reads a CSV with municipalities (name, latitude, longitude),
runs a Nearby Search for each municipality via the Google Maps
Places API, and saves results to Excel.

Requirements:
    pip install requests pandas openpyxl shapely tqdm

Usage:
    1. Set your API key in API_KEY below
    2. Set the path to your input CSV in INPUT_CSV
    3. Run: python google_places_collector.py

Input CSV format (minimum required columns):
    municipality, region, latitude, longitude, snai_class
"""

import requests
import pandas as pd
import time
import os
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these values before running
# ─────────────────────────────────────────────────────────────────
API_KEY    = "YOUR_GOOGLE_API_KEY"              # <-- insert your Google Maps API key
INPUT_CSV  = "data/your_municipalities.csv"     # <-- path to your municipality CSV
OUTPUT_XLS = "data/output_services.xlsx"        # output Excel file
RADIUS_M   = 5000                               # search radius in metres (default: 5 km)
DELAY_SEC  = 0.2                                # pause between requests (avoids rate limiting)

# Leave empty [] to query ALL Google Places types
# Or specify a subset, e.g. ["hospital", "pharmacy", "school"]
PLACE_TYPES = []

# ─────────────────────────────────────────────────────────────────
# GOOGLE PLACES API ENDPOINTS
# ─────────────────────────────────────────────────────────────────
BASE_URL   = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# Full list of Google Places categories used when PLACE_TYPES = []
ALL_PLACE_TYPES = [
    "accounting", "airport", "amusement_park", "aquarium", "art_gallery",
    "atm", "bakery", "bank", "bar", "beauty_salon", "bicycle_store",
    "book_store", "bowling_alley", "bus_station", "cafe", "campground",
    "car_dealer", "car_rental", "car_repair", "car_wash", "casino",
    "cemetery", "church", "city_hall", "clothing_store", "convenience_store",
    "courthouse", "dentist", "department_store", "doctor", "drugstore",
    "electrician", "electronics_store", "embassy", "fire_station",
    "florist", "funeral_home", "furniture_store", "gas_station", "gym",
    "hair_care", "hardware_store", "hindu_temple", "home_goods_store",
    "hospital", "insurance_agency", "jewelry_store", "laundry", "lawyer",
    "library", "light_rail_station", "liquor_store", "local_government_office",
    "locksmith", "lodging", "meal_delivery", "meal_takeaway", "mosque",
    "movie_rental", "movie_theater", "moving_company", "museum", "night_club",
    "painter", "park", "parking", "pet_store", "pharmacy", "physiotherapist",
    "plumber", "police", "post_office", "primary_school", "real_estate_agency",
    "restaurant", "roofing_contractor", "rv_park", "school", "secondary_school",
    "shoe_store", "shopping_mall", "spa", "stadium", "storage", "store",
    "subway_station", "supermarket", "synagogue", "taxi_stand", "tourist_attraction",
    "train_station", "transit_station", "travel_agency", "university",
    "veterinary_care", "zoo",
]


# ─────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def nearby_search(lat, lng, radius, place_type=None, page_token=None):
    """Execute a Nearby Search and return (results, next_page_token)."""
    params = {
        "location": f"{lat},{lng}",
        "radius":   radius,
        "key":      API_KEY,
    }
    if place_type:
        params["type"] = place_type
    if page_token:
        params["pagetoken"] = page_token

    resp = requests.get(BASE_URL, params=params, timeout=10)
    data = resp.json()

    status = data.get("status", "")
    if status not in ("OK", "ZERO_RESULTS"):
        print(f"  [WARN] Status: {status} — {data.get('error_message', '')}")

    return data.get("results", []), data.get("next_page_token")


def collect_all_places(lat, lng, radius, place_types):
    """
    Collect all POIs around (lat, lng) within radius metres.
    Deduplicates by place_id across all category queries.
    Returns at most 3 pages (60 results) per type.
    """
    types_to_query = place_types if place_types else ALL_PLACE_TYPES
    all_places = {}  # place_id → result dict

    for ptype in types_to_query:
        page_token = None
        page = 0
        while True:
            if page_token:
                time.sleep(2)  # Google requires ~2s before using next_page_token
            results, next_token = nearby_search(lat, lng, radius, ptype, page_token)
            for place in results:
                pid = place.get("place_id")
                if pid and pid not in all_places:
                    all_places[pid] = place
            page += 1
            if not next_token or page >= 3:
                break
            page_token = next_token
        time.sleep(DELAY_SEC)

    return list(all_places.values())


def parse_place(place, municipality, region):
    """Flatten a Places API result into a dict row."""
    types    = ", ".join(place.get("types", []))
    geometry = place.get("geometry", {}).get("location", {})
    status   = place.get("business_status", "")
    return {
        "municipality":        municipality,
        "region":              region,
        "name":                place.get("name", ""),
        "formatted_address":   place.get("vicinity", ""),
        "place_id":            place.get("place_id", ""),
        "latitude":            geometry.get("lat", ""),
        "longitude":           geometry.get("lng", ""),
        "rating":              place.get("rating", "No rating available"),
        "user_ratings_total":  place.get("user_ratings_total", 0),
        "types":               types,
        "business_status":     status if status else "No business status available",
        "permanently_closed":  place.get("permanently_closed", False),
    }


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    if API_KEY == "YOUR_GOOGLE_API_KEY":
        raise ValueError("Please set your Google Maps API key in API_KEY before running.")

    municipalities = pd.read_csv(INPUT_CSV)
    required_cols  = {"municipality", "region", "latitude", "longitude"}
    missing        = required_cols - set(municipalities.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {missing}")

    all_rows = []

    for _, row in tqdm(municipalities.iterrows(), total=len(municipalities),
                       desc="Collecting POIs"):
        municipality = row["municipality"]
        region       = row["region"]
        lat          = row["latitude"]
        lng          = row["longitude"]

        places = collect_all_places(lat, lng, RADIUS_M, PLACE_TYPES)

        for place in places:
            all_rows.append(parse_place(place, municipality, region))

        print(f"  {municipality}: {len(places)} POIs collected")

    df = pd.DataFrame(all_rows)
    df.to_excel(OUTPUT_XLS, index=False)
    print(f"\nDone. {len(df)} total POIs saved to {OUTPUT_XLS}")


if __name__ == "__main__":
    main()
