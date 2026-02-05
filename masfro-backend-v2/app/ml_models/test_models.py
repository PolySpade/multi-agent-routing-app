"""
Model Diagnostic Script

Tests if the ML models in new_models/ are properly formatted and loadable.
"""

import pickle
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pickle_model(model_path: Path, model_name: str):
    """Test if a pickle file can be loaded."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Path: {model_path}")
    print(f"Exists: {model_path.exists()}")

    if not model_path.exists():
        print("[X] File not found!")
        return False

    print(f"Size: {model_path.stat().st_size:,} bytes")

    try:
        with open(model_path, 'rb') as f:
            # Read first few bytes
            first_bytes = f.read(10)
            print(f"First bytes (hex): {first_bytes.hex()}")

            # Try to load
            f.seek(0)
            model = pickle.load(f)

            print(f"[OK] Successfully loaded!")
            print(f"Type: {type(model)}")

            # Check if it's a sklearn model
            if hasattr(model, 'predict'):
                print(f"[OK] Has predict() method")

            if hasattr(model, 'predict_proba'):
                print(f"[OK] Has predict_proba() method")

            # Try a test prediction
            try:
                test_text = "Baha sa Marikina"
                prediction = model.predict([test_text])
                print(f"[OK] Test prediction: {prediction}")

                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba([test_text])
                    print(f"[OK] Test probabilities: {proba}")

            except Exception as e:
                print(f"[WARN] Prediction failed: {e}")

            return True

    except Exception as e:
        print(f"[X] Failed to load: {e}")
        return False

def test_spacy_model(model_path: Path, model_name: str):
    """Test if a spaCy model can be loaded."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Path: {model_path}")
    print(f"Exists: {model_path.exists()}")

    if not model_path.exists():
        print("[X] Directory not found!")
        return False

    # Check for required files
    required_files = ['meta.json', 'config.cfg']
    for file in required_files:
        file_path = model_path / file
        exists = file_path.exists()
        print(f"  {file}: {'[OK]' if exists else '[X]'}")

    try:
        import spacy
        print(f"spaCy version: {spacy.__version__}")

        nlp = spacy.load(str(model_path))
        print(f"[OK] Successfully loaded!")
        print(f"Language: {nlp.lang}")
        print(f"Pipeline: {nlp.pipe_names}")

        # Test NER
        test_text = "Baha sa Nangka, Marikina City"
        doc = nlp(test_text)

        print(f"[OK] Processed test text")
        print(f"Entities found: {len(doc.ents)}")
        for ent in doc.ents:
            print(f"  - {ent.text} ({ent.label_})")

        return True

    except ImportError:
        print("[X] spaCy not installed")
        return False
    except Exception as e:
        print("[X] Failed to load: {e}")
        return False

def main():
    """Run all model tests."""
    print("="*60)
    print("MAS-FRO Model Diagnostic Tool")
    print("="*60)

    models_dir = Path(__file__).parent / "new_models"
    print(f"\nModels directory: {models_dir}")
    print(f"Directory exists: {models_dir.exists()}")

    if not models_dir.exists():
        print("[X] Models directory not found!")
        return

    # List all files
    print("\nContents of new_models/:")
    for item in models_dir.iterdir():
        if item.is_file():
            print(f"  [FILE] {item.name} ({item.stat().st_size:,} bytes)")
        else:
            print(f"  [DIR]  {item.name}/")

    # Test each model
    results = {}

    # Test flood classifier
    flood_model_path = models_dir / "flood_classifier.pkl"
    results['flood_classifier'] = test_pickle_model(
        flood_model_path,
        "Flood Classifier"
    )

    # Test severity classifier
    severity_model_path = models_dir / "severity_classifier.pkl"
    results['severity_classifier'] = test_pickle_model(
        severity_model_path,
        "Severity Classifier"
    )

    # Test location extraction model
    location_model_path = models_dir / "location_extract"
    results['location_model'] = test_spacy_model(
        location_model_path,
        "Location Extraction Model (spaCy)"
    )

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for model_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{model_name:30s} {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} models loaded successfully")

    if passed < total:
        print("\n[WARNING] Some models failed to load!")
        print("Possible issues:")
        print("  1. Pickle files may be corrupted")
        print("  2. Models may have been saved with incompatible Python/library versions")
        print("  3. spaCy may not be installed (run: uv add spacy)")
        print("\nThe NLP processor will use fallback methods for failed models.")

if __name__ == "__main__":
    main()
