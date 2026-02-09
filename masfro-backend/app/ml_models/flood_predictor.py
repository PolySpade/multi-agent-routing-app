# filename: app/ml_models/flood_predictor.py

"""
Flood Prediction Model for MAS-FRO

This module implements a machine learning model (Random Forest Classifier)
for predicting flood risk based on environmental features such as rainfall,
river levels, and elevation data.

The model provides probability estimates for flood occurrence, which are
integrated into the risk scoring system by the HazardAgent.

Author: MAS-FRO Development Team
Date: November 2025
"""
# NOT USED
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class FloodPredictor:
    """
    Random Forest-based flood risk predictor.

    This class implements a machine learning model that predicts the
    probability of flooding based on environmental features. The model
    is trained on historical flood data and can be retrained as new
    data becomes available.

    Features used for prediction:
    - Rainfall accumulation (1h, 3h, 24h)
    - River water level
    - Elevation (meters above sea level)
    - Distance to river (meters)
    - Soil saturation level
    - Historical flood frequency

    Attributes:
        model: RandomForestClassifier instance
        is_trained: Whether the model has been trained
        feature_names: List of feature names in order
        model_path: Path to saved model file

    Example:
        >>> predictor = FloodPredictor()
        >>> predictor.train(training_data, labels)
        >>> risk = predictor.predict_flood_risk(
        ...     rainfall=50.0,
        ...     river_level=3.5,
        ...     elevation=15.0
        ... )
        >>> print(f"Flood probability: {risk:.2%}")
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the FloodPredictor.

        Args:
            model_path: Optional path to saved model file
        """
        # Model configuration
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1  # Use all CPU cores
        )

        self.is_trained = False

        # Feature configuration
        self.feature_names = [
            "rainfall_1h",  # mm
            "rainfall_3h",  # mm
            "rainfall_24h",  # mm
            "river_level",  # meters above normal
            "elevation",  # meters above sea level
            "distance_to_river",  # meters
            "soil_saturation",  # 0-1 scale
            "historical_frequency"  # 0-1 scale (floods per year)
        ]

        # Model persistence
        self.model_path = Path(model_path) if model_path else None

        # Load model if path provided
        if self.model_path and self.model_path.exists():
            self.load_model()

        logger.info("FloodPredictor initialized")

    def train(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        test_size: float = 0.2
    ) -> Dict[str, float]:
        """
        Train the flood prediction model.

        Args:
            features: Feature matrix (n_samples, n_features)
            labels: Binary labels (0 = no flood, 1 = flood)
            test_size: Proportion of data to use for testing

        Returns:
            Dict with training metrics:
                {
                    "accuracy": float,
                    "precision": float,
                    "recall": float,
                    "n_samples": int
                }
        """
        logger.info(f"Training flood predictor on {len(features)} samples")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features,
            labels,
            test_size=test_size,
            random_state=42,
            stratify=labels
        )

        # Train model
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate
        y_pred = self.model.predict(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "n_samples": len(features)
        }

        logger.info(
            f"Model trained - Accuracy: {metrics['accuracy']:.2%}, "
            f"Precision: {metrics['precision']:.2%}, "
            f"Recall: {metrics['recall']:.2%}"
        )

        return metrics

    def predict_flood_risk(
        self,
        rainfall_1h: float,
        rainfall_3h: float = None,
        rainfall_24h: float = None,
        river_level: float = 0.0,
        elevation: float = 20.0,
        distance_to_river: float = 1000.0,
        soil_saturation: float = 0.5,
        historical_frequency: float = 0.1
    ) -> float:
        """
        Predict flood risk probability for given conditions.

        Args:
            rainfall_1h: Rainfall in last 1 hour (mm)
            rainfall_3h: Rainfall in last 3 hours (mm)
            rainfall_24h: Rainfall in last 24 hours (mm)
            river_level: River water level above normal (meters)
            elevation: Elevation above sea level (meters)
            distance_to_river: Distance to nearest river (meters)
            soil_saturation: Soil saturation level (0-1)
            historical_frequency: Historical flood frequency (0-1)

        Returns:
            Flood probability (0-1 scale)
        """
        # Handle missing values with simple imputation
        if rainfall_3h is None:
            rainfall_3h = rainfall_1h * 2.5
        if rainfall_24h is None:
            rainfall_24h = rainfall_1h * 8.0

        # Create feature vector
        features = np.array([[
            rainfall_1h,
            rainfall_3h,
            rainfall_24h,
            river_level,
            elevation,
            distance_to_river,
            soil_saturation,
            historical_frequency
        ]])

        # Predict probability
        if not self.is_trained:
            logger.warning("Model not trained, using heuristic prediction")
            return self._heuristic_prediction(features[0])

        try:
            # Get probability of positive class (flood)
            prob = self.model.predict_proba(features)[0][1]
            return float(prob)

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._heuristic_prediction(features[0])

    def predict_batch(
        self,
        features: np.ndarray
    ) -> np.ndarray:
        """
        Predict flood risk for multiple locations.

        Args:
            features: Feature matrix (n_samples, n_features)

        Returns:
            Array of flood probabilities
        """
        if not self.is_trained:
            logger.warning("Model not trained, using heuristic predictions")
            return np.array([
                self._heuristic_prediction(f) for f in features
            ])

        probabilities = self.model.predict_proba(features)[:, 1]
        return probabilities

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores from trained model.

        Returns:
            Dict mapping feature names to importance scores
        """
        if not self.is_trained:
            logger.warning("Model not trained, no feature importance available")
            return {}

        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances))

    def save_model(self, path: Optional[str] = None) -> bool:
        """
        Save trained model to file.

        Args:
            path: Optional path to save model (uses self.model_path if None)

        Returns:
            True if successful, False otherwise
        """
        save_path = Path(path) if path else self.model_path

        if not save_path:
            logger.error("No save path specified")
            return False

        if not self.is_trained:
            logger.warning("Model not trained, nothing to save")
            return False

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'feature_names': self.feature_names,
                    'is_trained': self.is_trained
                }, f)

            logger.info(f"Model saved to {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def load_model(self, path: Optional[str] = None) -> bool:
        """
        Load trained model from file.

        Args:
            path: Optional path to load model from (uses self.model_path if None)

        Returns:
            True if successful, False otherwise
        """
        load_path = Path(path) if path else self.model_path

        if not load_path or not load_path.exists():
            logger.error(f"Model file not found: {load_path}")
            return False

        try:
            with open(load_path, 'rb') as f:
                data = pickle.load(f)

            self.model = data['model']
            self.feature_names = data['feature_names']
            self.is_trained = data['is_trained']

            logger.info(f"Model loaded from {load_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def _heuristic_prediction(self, features: np.ndarray) -> float:
        """
        Fallback heuristic prediction when model is not trained.

        Uses simple rules based on domain knowledge:
        - High rainfall + low elevation = high risk
        - High river level + close to river = high risk

        Args:
            features: Feature vector

        Returns:
            Estimated flood probability
        """
        rainfall_1h, rainfall_3h, rainfall_24h, river_level, elevation, \
            distance_to_river, soil_saturation, historical_frequency = features

        # Simple heuristic based on key factors
        risk = 0.0

        # Rainfall contribution
        if rainfall_1h > 30:
            risk += 0.3
        elif rainfall_1h > 15:
            risk += 0.15

        # River level contribution
        if river_level > 2.0:
            risk += 0.3
        elif river_level > 1.0:
            risk += 0.15

        # Elevation contribution (inverse)
        if elevation < 10:
            risk += 0.2
        elif elevation < 20:
            risk += 0.1

        # Distance to river contribution
        if distance_to_river < 200:
            risk += 0.1

        # Soil saturation contribution
        risk += soil_saturation * 0.1

        return min(risk, 1.0)


def generate_synthetic_training_data(
    n_samples: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic training data for model development.

    This is a placeholder function for development. In production,
    this would be replaced with actual historical flood data.

    Args:
        n_samples: Number of samples to generate

    Returns:
        Tuple of (features, labels)
    """
    np.random.seed(42)

    features = []
    labels = []

    for _ in range(n_samples):
        # Generate random features
        rainfall_1h = np.random.gamma(2, 10)
        rainfall_3h = rainfall_1h * np.random.uniform(2, 3)
        rainfall_24h = rainfall_3h * np.random.uniform(2, 4)
        river_level = np.random.uniform(-0.5, 5.0)
        elevation = np.random.uniform(5, 50)
        distance_to_river = np.random.uniform(10, 5000)
        soil_saturation = np.random.beta(2, 2)
        historical_frequency = np.random.beta(1, 9)

        # Determine label based on heuristic
        flood = (
            (rainfall_1h > 25 and elevation < 15) or
            (river_level > 2.5 and distance_to_river < 500) or
            (rainfall_24h > 150 and soil_saturation > 0.7)
        )

        features.append([
            rainfall_1h, rainfall_3h, rainfall_24h, river_level,
            elevation, distance_to_river, soil_saturation, historical_frequency
        ])
        labels.append(1 if flood else 0)

    return np.array(features), np.array(labels)
