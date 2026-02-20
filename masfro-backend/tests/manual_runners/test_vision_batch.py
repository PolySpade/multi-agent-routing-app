
import logging
import sys
import os
from pathlib import Path

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_vision_pipeline():
    print("=== Testing Scout Agent Vision Model (Moondream) ===")
    
    # Initialize LLM Service
    llm = LLMService(vision_model="qwen3-vl:latest")
    
    if not llm.is_available():
        print("❌ LLM Service (Ollama) is not available! Is Ollama running?")
        return

    # Image Directory
    image_dir = Path("app/data/sample_images/flood_levels")
    if not image_dir.exists():
        print(f"❌ Image directory not found: {image_dir}")
        return

    images = list(image_dir.glob("*"))
    print(f"Found {len(images)} images for testing.\n")

    for img_path in images:
        print(f"Processing: {img_path.name}...")
        
        # Analyze
        result = llm.analyze_flood_image(str(img_path))
        
        if result:
            depth = result.get('estimated_depth_m', 'N/A')
            risk = result.get('risk_score', 'N/A')
            passable = result.get('vehicles_passable', [])
            indicators = result.get('visual_indicators', 'No details')
            
            print(f"  ✅ Result:")
            print(f"     - Depth: {depth}m")
            print(f"     - Risk Score: {risk}")
            print(f"     - Passable: {passable}")
            print(f"     - Indicators: {indicators[:100]}...") # Truncate for clean output
        else:
            print("  ❌ Failed to analyze image.")
        
        print("-" * 40)

if __name__ == "__main__":
    test_vision_pipeline()
