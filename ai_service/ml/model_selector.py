"""
Model Selector module for ParkZenith Forecasting.
Trains and compares multiple regression models, returning the best performing one.
"""

import logging
from typing import Dict, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor

from .metrics import evaluate_predictions

logger = logging.getLogger(__name__)


def select_best_model(
    X: Any,
    y: Any,
    test_size: float = 0.2,
    shuffle: bool = False
) -> Tuple[Any, str, Dict[str, Dict[str, float]], Dict[str, float]]:
    """
    Splits the dataset (80% train, 20% test), trains multiple regressors,
    evaluates them, and automatically selects the best model based on RMSE.
    
    Returns:
        (best_model_instance, best_model_name, all_model_metrics, best_model_metrics)
    """
    # 80/20 train/test split. Time-series forecasting should use shuffle=False to prevent lookahead bias.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=shuffle, random_state=42
    )

    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree Regressor": DecisionTreeRegressor(max_depth=10, random_state=42),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=50, max_depth=12, random_state=42, n_jobs=-1),
        "Gradient Boosting Regressor": GradientBoostingRegressor(n_estimators=50, max_depth=5, random_state=42)
    }

    all_metrics = {}
    best_model_name = None
    best_rmse = float("inf")
    best_model = None

    logger.info("Starting model comparison over %d models...", len(models))

    for name, model in models.items():
        try:
            logger.info("Training model: %s...", name)
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            metrics = evaluate_predictions(y_test, y_pred)
            all_metrics[name] = metrics
            
            logger.info(
                "Model: %s - MAE: %.4f, RMSE: %.4f, R2: %.4f, MAPE: %.2f%%, Confidence: %.2f%%",
                name, metrics["mae"], metrics["rmse"], metrics["r2_score"], metrics["mape"], metrics["confidence"]
            )
            
            # Selection based on lowest RMSE
            if metrics["rmse"] < best_rmse:
                best_rmse = metrics["rmse"]
                best_model_name = name
                best_model = model
        except Exception as e:
            logger.error("Failed to train/evaluate model %s: %s", name, str(e))

    if best_model is None:
        raise RuntimeError("No model trained successfully during comparison.")

    logger.info("Model selection completed. Best Model: %s (RMSE: %.4f)", best_model_name, best_rmse)
    return best_model, best_model_name, all_metrics, all_metrics[best_model_name]
