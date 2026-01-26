"""
Pickle Model Compatibility Fixer

Attempts to load pickle files using different methods and protocols.
"""

import pickle
import pickletools
from pathlib import Path
import sys

def analyze_pickle_file(pickle_path: Path):
    """Analyze pickle file structure."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {pickle_path.name}")
    print(f"{'='*60}")

    try:
        with open(pickle_path, 'rb') as f:
            # Read first 20 bytes
            first_bytes = f.read(20)
            print(f"First 20 bytes (hex): {first_bytes.hex()}")
            print(f"First 20 bytes (raw): {first_bytes}")

            # Try to identify pickle protocol
            f.seek(0)
            try:
                pickletools.dis(f, annotate=1)
            except Exception as e:
                print(f"Pickletools analysis failed: {e}")

    except Exception as e:
        print(f"Error reading file: {e}")

def try_loading_methods(pickle_path: Path):
    """Try different methods to load the pickle file."""
    print(f"\n{'='*60}")
    print(f"Testing loading methods for: {pickle_path.name}")
    print(f"{'='*60}\n")

    methods = []

    # Method 1: Standard pickle load
    print("Method 1: Standard pickle.load()")
    try:
        with open(pickle_path, 'rb') as f:
            model = pickle.load(f)
        print("  [SUCCESS] Loaded with standard pickle.load()")
        methods.append(("standard", model))
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")

    # Method 2: Protocol 4
    print("\nMethod 2: pickle.load() with protocol 4")
    try:
        with open(pickle_path, 'rb') as f:
            model = pickle.load(f, encoding='bytes')
        print("  [SUCCESS] Loaded with encoding='bytes'")
        methods.append(("protocol4", model))
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")

    # Method 3: Try with different protocols
    for protocol in [0, 1, 2, 3, 4, 5]:
        print(f"\nMethod 3.{protocol}: Attempt with pickle protocol {protocol}")
        try:
            with open(pickle_path, 'rb') as f:
                # This won't change how we load, but let's try
                model = pickle.load(f)
            print(f"  [SUCCESS] Loaded (protocol check passed)")
            methods.append((f"protocol_{protocol}", model))
            break
        except Exception as e:
            print(f"  [FAIL] {type(e).__name__}: {e}")

    # Method 4: Try joblib (sklearn models are often saved with joblib)
    print("\nMethod 4: Try with joblib")
    try:
        import joblib
        model = joblib.load(pickle_path)
        print("  [SUCCESS] Loaded with joblib!")
        methods.append(("joblib", model))
    except ImportError:
        print("  [SKIP] joblib not installed (run: uv add joblib)")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")

    # Method 5: Try dill (extended pickling)
    print("\nMethod 5: Try with dill")
    try:
        import dill
        with open(pickle_path, 'rb') as f:
            model = dill.load(f)
        print("  [SUCCESS] Loaded with dill!")
        methods.append(("dill", model))
    except ImportError:
        print("  [SKIP] dill not installed (run: uv add dill)")
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    if methods:
        print(f"Successfully loaded with {len(methods)} method(s):")
        for method_name, model in methods:
            print(f"  - {method_name}: {type(model)}")
        return methods[0][1]  # Return first successful model
    else:
        print("Could not load with any method!")
        print("\nRecommendations:")
        print("  1. Check if models were saved with joblib (run: uv add joblib)")
        print("  2. Check Python version compatibility")
        print("  3. Verify sklearn version used to train models")
        print("  4. Re-save models with current environment")
        return None

def main():
    """Run pickle diagnostics."""
    models_dir = Path(__file__).parent / "new_models"

    print("="*60)
    print("Pickle Model Compatibility Diagnostic")
    print("="*60)
    print(f"\nPython version: {sys.version}")
    print(f"Pickle protocol supported: {pickle.HIGHEST_PROTOCOL}")

    # Test flood classifier
    flood_path = models_dir / "flood_classifier.pkl"
    if flood_path.exists():
        print("\n" + "="*60)
        print("FLOOD CLASSIFIER")
        print("="*60)
        analyze_pickle_file(flood_path)
        flood_model = try_loading_methods(flood_path)

        if flood_model:
            print("\n[SUCCESS] Flood classifier loaded!")
            print("Testing prediction...")
            try:
                test_result = flood_model.predict(["Baha sa Marikina"])
                print(f"Test prediction: {test_result}")
            except Exception as e:
                print(f"Prediction failed: {e}")

    # Test severity classifier
    severity_path = models_dir / "severity_classifier.pkl"
    if severity_path.exists():
        print("\n" + "="*60)
        print("SEVERITY CLASSIFIER")
        print("="*60)
        analyze_pickle_file(severity_path)
        severity_model = try_loading_methods(severity_path)

        if severity_model:
            print("\n[SUCCESS] Severity classifier loaded!")
            print("Testing prediction...")
            try:
                test_result = severity_model.predict(["Tuhod level baha"])
                print(f"Test prediction: {test_result}")
            except Exception as e:
                print(f"Prediction failed: {e}")

if __name__ == "__main__":
    main()
