"""
Filter evacuation_centers.csv to only include centers within Marikina City boundary.

Strategy (hybrid):
  1. OSM city boundary polygon + corrective patches for known OSM gaps
  2. Operator/district label overrides:
       - "Marikina City Schools Division" in operator  →  force INCLUDE
       - San Mateo / QC / Cainta / Pasig district labels →  force EXCLUDE
  3. Sanity checks on 20 ground-truth points; aborts if any check fails.
"""
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import osmnx as ox
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# -------------------------------------------------------------------
# 1. Build corrected Marikina boundary
# -------------------------------------------------------------------
print("Fetching OSM boundary for Marikina City...")
marikina_gdf = ox.geocode_to_gdf("Marikina City, Philippines")
osm_poly = marikina_gdf.geometry.iloc[0]
print(f"  OSM bounds: {tuple(round(v, 4) for v in osm_poly.bounds)}")

# OSM Santolan data is incomplete — the barangay's southern edge meets
# Pasig City at roughly lat 14.608-14.612, but the city polygon starts at
# lat 14.617.  Southern limit 14.608 safely excludes Bagumbayan, QC
# (lat 14.607) while covering Santolan HS (14.615), Octagon (14.610).
# Eastern limit 121.107 keeps us out of Cainta territory.
south_patch = Polygon([
    (121.074, 14.608),
    (121.074, 14.625),
    (121.107, 14.625),
    (121.107, 14.608),
])

# The OSM polygon cuts off around lat 14.675 in the Nangka corridor, missing
# official Marikina centers (Felicidad Village 14.677, Ynares 14.676).
# This rectangular patch recovers them.  Eastern limit 121.120 is safely
# inside the Fortune/Concepcion area; western limit 121.095 avoids the QC
# border where Don Antonio Heights (QC) sits at lon ~121.080.
north_patch = Polygon([
    (121.095, 14.675),
    (121.095, 14.681),
    (121.120, 14.681),
    (121.120, 14.675),
])

marikina = unary_union([osm_poly, south_patch, north_patch])
print(f"  Corrected bounds: {tuple(round(v, 4) for v in marikina.bounds)}")

# -------------------------------------------------------------------
# 2. Label-based override rules (most reliable signal)
# -------------------------------------------------------------------
# If operator string contains any of these → definitely outside Marikina
FORCE_EXCLUDE_SUBSTRINGS = [
    "San Mateo District of Rizal Schools Division",
    "School District VIII Quezon City Schools Division",
    "Cainta I District",
    "Cainta II District",
    "District IV Pasig City Schools Division",
    # 'Sampaloc V District of Manila' omitted — those two Fugoso schools
    # are physically in Marikina's Parang barangay per coordinates + barangay label
]
# If operator string contains any of these → definitely inside Marikina
FORCE_INCLUDE_SUBSTRINGS = [
    "District I Marikina City Schools Division",
    "District II Marikina City Schools Division",
]


def is_in_marikina(row) -> bool:
    op = str(row.get("operator") or "")
    for s in FORCE_INCLUDE_SUBSTRINGS:
        if s in op:
            return True
    for s in FORCE_EXCLUDE_SUBSTRINGS:
        if s in op:
            return False
    return marikina.contains(Point(row["longitude"], row["latitude"]))


# -------------------------------------------------------------------
# 3. Sanity checks
# -------------------------------------------------------------------
checks = [
    # -- Must be INSIDE Marikina --
    # Official centers that OSM polygon initially missed
    ("Felicidad Village BktBall Ct (OFFICIAL)", 14.677958, 121.11044, True),
    ("Ynares Basketball Ct (OFFICIAL)", 14.67614, 121.109565, True),
    ("Ynarez Covered Court (OFFICIAL)", 14.676524, 121.115822, True),
    # Santolan barangay (south of OSM polygon)
    ("Santolan High School — Marikina D-I", 14.615572, 121.083435, True),
    ("Santolan Multi Purpose Hall", 14.612125, 121.086604, True),
    ("Octagon Multi-Purpose Hall", 14.610544, 121.09724, True),
    # Core Marikina centers
    ("Nangka Gym (OFFICIAL)", 14.672471, 121.108408, True),
    ("Barangka ES (OFFICIAL)", 14.633452, 121.081943, True),
    ("Kapitan Moy ES — Marikina D-II", 14.649095, 121.118601, True),
    ("Morning Dew Montessori (San Roque)", 14.622564, 121.104711, True),

    # -- Must be OUTSIDE Marikina --
    # Labeled non-Marikina districts
    ("Bagumbayan ES — QC District VIII", 14.607894, 121.082761, False),
    ("Manggahan ES — Pasig District IV", 14.600342, 121.09504, False),
    ("Balanti ES — Cainta II District", 14.6362, 121.108522, False),
    ("Banaba ES — San Mateo District", 14.672684, 121.112736, False),
    ("Ampid I ES — San Mateo District", 14.67774, 121.116886, False),
    ("Francisco Felix — Karangalan (Cainta)", 14.604493, 121.105748, False),
    ("Governor Isidro Rodriguez (Cainta)", 14.626993, 121.108351, False),
    # Named for another city
    ("Bright Morning School of QC", 14.673951, 121.081479, False),
    ("Don Antonio Club House (QC)", 14.679597, 121.080097, False),
    # Too far south
    ("Senior Citizen's Hall (too south)", 14.601144, 121.100742, False),
]

print("\nSanity checks:")
all_ok = True
for name, lat, lon, expected in checks:
    # Build a fake row for the override-aware check
    fake_row = {"latitude": lat, "longitude": lon, "operator": ""}
    # Apply operator overrides from known entries
    operator_map = {
        (14.607894, 121.082761): "School District VIII Quezon City Schools Division, DepEd",
        (14.600342, 121.09504):  "District IV Pasig City Schools Division, DepEd",
        (14.6362,   121.108522): "Cainta II District",
        (14.672684, 121.112736): "San Mateo District of Rizal Schools Division, DepEd",
        (14.67774,  121.116886): "San Mateo District of Rizal Schools Division, DepEd",
        (14.604493, 121.105748): "Cainta I District",
        (14.626993, 121.108351): "Cainta II District",
        (14.649095, 121.118601): "District II Marikina City Schools Division, DepEd",
        (14.615572, 121.083435): "District I Marikina City Schools Division, DepEd",
        (14.633452, 121.081943): "District I Marikina City Schools Division, DepEd",
    }
    fake_row["operator"] = operator_map.get((lat, lon), "")
    result = is_in_marikina(fake_row)
    status = "OK  " if result == expected else "FAIL"
    if result != expected:
        all_ok = False
    print(f"  [{status}] expected={expected} got={result}  {name}")

print(f"  All checks passed: {all_ok}")
if not all_ok:
    print("\nAborted — fix boundary patches or override rules and rerun.")
    sys.exit(1)

# -------------------------------------------------------------------
# 4. Load CSV and filter
# -------------------------------------------------------------------
csv_path = os.path.join(
    os.path.dirname(__file__), "..", "app", "data", "evacuation_centers.csv"
)
df = pd.read_csv(csv_path)
print(f"\nTotal centers loaded: {len(df)}")

inside_mask = df.apply(is_in_marikina, axis=1)
df_inside  = df[inside_mask].copy()
df_outside = df[~inside_mask].copy()

print(f"Inside  Marikina: {len(df_inside)}")
print(f"Outside Marikina ({len(df_outside)}):")
for _, row in df_outside.iterrows():
    op = row["operator"] if pd.notna(row.get("operator")) else ""
    print(f"  [{row['latitude']:.4f}, {row['longitude']:.4f}] {row['name']}  |  {op}")

# -------------------------------------------------------------------
# 5. Write filtered CSV
# -------------------------------------------------------------------
df_inside.to_csv(csv_path, index=False)
print(f"\nSaved filtered CSV: {len(df_inside)} centers kept, {len(df_outside)} removed.")
