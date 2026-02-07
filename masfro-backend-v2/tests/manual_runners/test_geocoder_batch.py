
import logging
import sys
import os
import argparse
from typing import List, Tuple

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.ml_models.location_geocoder import LocationGeocoder
from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_batch_test(category: str, locations: List[str], geocoder: LocationGeocoder):
    print(f"\n--- Testing Category: {category} ---")
    hits = 0
    
    for loc in locations:
        print(f"Query: '{loc}'...", end=" ", flush=True)
        coords = geocoder.get_coordinates(loc)
        
        if coords:
            print(f"✅ FOUND: {coords}")
            hits += 1
        else:
            print("❌ NOT FOUND")
            
    print(f"Score: {hits}/{len(locations)} ({hits/len(locations)*100:.1f}%)")
    return hits, len(locations)

if __name__ == "__main__":
    # Force LLM usage
    llm_service = LLMService()
    geocoder = LocationGeocoder(llm_service=llm_service)
    
    print("=== Location Geocoder Batch Stress Test ===")
    
    # 1. Clear Marikina Locations (Should all be found via CSV or LLM)
    marikina_locations = [
        "Marikina Sports Park",
        "Sports Complex",
        "Marikina City Hall",
        "City Hall",
        "Riverbanks Center",
        "Riverbanks Mall",
        "SM Marikina",
        "Amang Rodriguez Memorial Medical Center",
        "Amang Rodriguez",
        "Marikina Public Market",
        "Public Market",
        "Teodora Alonzo Elementary School",
        "Marikina High School",
        "MHS",
        "PLMar",
        "Pamantasan ng Lungsod ng Marikina",
        "Concepcion Uno Barangay Hall",
        "Barangka",
        "Jesus dela Pena",
        "Tumana",
        "Malanday",
        "Nangka",
        "Fortune",
        "Sto Nino",
        "Sta Elena",
        "San Roque",
        "Kalumpang",
        "Industrial Valley Complex",
        "IVC",
        "Loyola Grand Villas",
        "Provident Village",
        "Rancho Estate",
        "SSS Village",
        "Marikina Heights",
        "Parang",
        "Concepcion Dos",
    ]
    
    # 2. Strict Rejection Test (Should all be NOT FOUND)
    out_of_bounds = [
        "Manila Cathedral",
        "Quezon Memorial Circle",
        "SM Megamall",
        "Makati Medical Center",
        "Rizal Park",
        "Eastwood City",
        "Cubao Expo",
        "UP Diliman",
        "Ateneo de Manila", # Tricky: Near border, but technically QC
        "Sta. Lucia East Grand Mall", # Tricky: Border of Marikina/Cainta
    ]
    
    # 3. Fuzzy/Slang Test (Should mostly be found via LLM)
    fuzzy_slang = [
        "near the sports complex",
        "at the back of city hall",
        "provident village gate 1",
        "concepcion church", # Should match Immaculate Concepcion
        "bayan", # Colloquial for city center/market
        "ola church", # Our Lady of the Abandoned
        "marikina bridge",
        "tumana bridge",
        "st. gabriel", # Debugging specific user issue
        "st gabriel church",
        "saint gabriel street", 
    ]

    total_hits = 0
    total_queries = 0
    
    # Run Tests
    h1, t1 = run_batch_test("Standard Marikina Locations", marikina_locations, geocoder)
    total_hits += h1; total_queries += t1
    
    print("\n--- Testing Category: Out of Bounds (Expect 0 hits) ---")
    h2, t2 = run_batch_test("Strict Rejection", out_of_bounds, geocoder)
    # For this category, 0 hits is PERFECT score
    print(f"Rejection Score: {t2 - h2}/{t2} rejected ({(t2-h2)/t2*100:.1f}%)")
    
    h3, t3 = run_batch_test("Fuzzy & Contextual", fuzzy_slang, geocoder)
    total_hits += h3; total_queries += t3
    
    print("\n=== FINAL SUMMARY ===")
    # Adjusted score: Count rejected out-of-bounds as 'success' for the system, but for hit rate, we look at valid queries
    valid_queries = t1 + t3
    valid_hits = h1 + h3
    print(f"Valid Location Hit Rate: {valid_hits}/{valid_queries} ({valid_hits/valid_queries*100:.1f}%)")
    print(f"False Positive Rate: {h2}/{t2} ({h2/t2*100:.1f}%)")
