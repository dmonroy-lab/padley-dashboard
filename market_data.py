#!/usr/bin/env python3
"""
Padly Pricing Engine - Market Data Processing
Date: 2026-11-01
Source: Facebook Marketplace Montreal
"""

import json
from datetime import date

# Raw data from Facebook Marketplace scraping
# 135 total listings collected, 129 filtered (excluding private rooms/Padly), 114 classified by bedrooms

# Montreal-wide results (from 135 listings, general pool)
montreal_results = [
    {"neighborhood": "Montreal (tous arrondissements)", "type": "Studio", "beds": 0, "N": 10, "median": 1375, "avg": 1378, "min": 1100, "max": 1630, "aggressive": 1238, "fair": 1348, "premium": 1485},
    {"neighborhood": "Montreal (tous arrondissements)", "type": "1 hab.", "beds": 1, "N": 39, "median": 1350, "avg": 1376, "min": 725, "max": 2200, "aggressive": 1215, "fair": 1323, "premium": 1458},
    {"neighborhood": "Montreal (tous arrondissements)", "type": "2 hab.", "beds": 2, "N": 36, "median": 1600, "avg": 1713, "min": 865, "max": 3500, "aggressive": 1440, "fair": 1568, "premium": 1728},
    {"neighborhood": "Montreal (tous arrondissements)", "type": "3 hab.", "beds": 3, "N": 25, "median": 1800, "avg": 1995, "min": 700, "max": 4120, "aggressive": 1620, "fair": 1764, "premium": 1944},
    {"neighborhood": "Montreal (tous arrondissements)", "type": "4 hab.", "beds": 4, "N": 4, "median": 1713, "avg": 1709, "min": 665, "max": 2745, "aggressive": 1542, "fair": 1679, "premium": 1850},
]

# Longueuil data (separate city, 4 listings found - insufficient by bedroom type)
longueuil_raw = [
    {"title": "1 Bed 1 Bath - Apartment", "price": 1200, "beds": 1},
    {"title": "Appartement de 3 chambres et 2 salles de bain", "price": 2325, "beds": 3},
    {"title": "2 Beds 1 Bath Apartment", "price": 2075, "beds": 2},
    {"title": "2 chambres à coucher 1 salle de bain Appartement", "price": 1500, "beds": 2},
]

# Note: Neighborhood-specific data (Hochelaga, Rosemont, Plateau, etc.) could not be
# distinguished from listing cards as Facebook only shows city-level location ("Montréal, QC")
# for all Montreal borough listings. The neighborhood query searches listing text,
# but most listings don't mention specific neighborhoods in titles.

# Target neighborhoods for Padly
neighborhoods = [
    "Hochelaga", "Rosemont", "Plateau", "CDN", "Ahuntsic",
    "Montreal Nord", "Anjou", "Verdun", "Saint-Laurent", "Mercier",
    "RDP", "Saint-Léonard", "Ville-Marie", "Longueuil"
]

today = date.today().strftime("%Y-%m-%d")
city = "Montreal"
source = "Facebook Marketplace"

# Build rows for Google Sheets
# Format: [date, city, neighborhood, type, source, N, median, avg, min, max, aggressive, fair, premium]
def build_rows():
    rows = []

    # Montreal-wide rows (best available data)
    for r in montreal_results:
        if r["N"] >= 3:
            rows.append([
                today, city, r["neighborhood"], r["type"], source,
                r["N"], r["median"], r["avg"], r["min"], r["max"],
                r["aggressive"], r["fair"], r["premium"]
            ])

    return rows

rows = build_rows()
print(f"Total rows to insert: {len(rows)}")
for row in rows:
    print(row)

print("\n--- Summary ---")
print(f"Date: {today}")
print(f"Total listings collected: 135")
print(f"Total listings valid (after filtering): 129")
print(f"Total listings classified by bedrooms: 114")
print(f"Rows with N>=3: {len(rows)}")
