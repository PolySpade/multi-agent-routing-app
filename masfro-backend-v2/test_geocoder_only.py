
import logging
from app.ml_models.location_geocoder import LocationGeocoder
from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(level=logging.INFO)

print("=== Testing LocationGeocoder LLM Fallback ===")

# 1. Init LLM Service
import os
os.environ["LLM_TEXT_MODEL"] = "llama3.2:latest"
llm_service = LLMService(enabled=True)
if not llm_service.is_available():
    print("❌ LLM Service not available. Cannot test fallback.")
    exit()

# 2. Init Geocoder with LLM
geocoder = LocationGeocoder(llm_service=llm_service)

import argparse
import sys

# Argument parsing
parser = argparse.ArgumentParser(description='Test Location Geocoder LLM Fallback')
parser.add_argument('location', nargs='?', default="Corner of Lilac St and General Ordonez", 
                    help='Location name to test geocoding for')
args = parser.parse_args()

# 3. Test Unknown Location
test_loc = args.location
print(f"\n🔍 Searching for location: '{test_loc}'")

# Trigger Geocoding
coords = geocoder.get_coordinates(test_loc)

if coords:
    print(f"✅ FOUND: {coords}")
else:
    print("❌ NOT FOUND")
