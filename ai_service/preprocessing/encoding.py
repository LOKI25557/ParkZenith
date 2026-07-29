"""
Encoding module for ParkZenith Preprocessing Pipeline.
Implements One-Hot Encoding, Label Encoding, and Ordinal Encoding for categorical features.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd

try:
    from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, LabelEncoder
except ImportError:
    OneHotEncoder = OrdinalEncoder = LabelEncoder = None

logger = logging.getLogger(__name__)


class CategoricalEncoder:
    """
    Handles fitting and transforming categorical features.
    """

    def __init__(self, strategy: str = "onehot") -> None:
        self.strategy = strategy.lower().strip()
        self.columns: List[str] = []
        self.encoders: Dict[str, Any] = {}
        self.onehot_encoder: Optional[Any] = None
        self.onehot_feature_names: List[str] = []

    def fit(self, df: pd.DataFrame, columns: List[str]) -> "CategoricalEncoder":
        """
        Fits the encoders on the specified categorical columns.
        """
        if not columns:
            return self

        self.columns = [c for c in columns if c in df.columns]
        if not self.columns:
            return self

        if OneHotEncoder is None:
            raise ImportError("scikit-learn is not installed in the current environment.")

        if self.strategy == "onehot":
            # sparse_output=False is standard for scikit-learn >= 1.2
            self.onehot_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            # Fill NA values as "MISSING" for encoding stability
            df_filled = df[self.columns].fillna("MISSING").astype(str)
            self.onehot_encoder.fit(df_filled)
            # Fetch generated feature names
            self.onehot_feature_names = list(self.onehot_encoder.get_feature_names_out(self.columns))
            logger.info("Fitted OneHotEncoder on columns: %s", self.columns)

        elif self.strategy == "ordinal":
            # OrdinalEncoder supports handling unknown values in newer scikit-learn versions
            self.onehot_encoder = OrdinalEncoder(
                handle_unknown="use_encoded_value", unknown_value=-1
            )
            df_filled = df[self.columns].fillna("MISSING").astype(str)
            self.onehot_encoder.fit(df_filled)
            logger.info("Fitted OrdinalEncoder on columns: %s", self.columns)

        elif self.strategy == "label":
            # We fit a LabelEncoder per column
            for col in self.columns:
                le = LabelEncoder()
                df_filled = df[col].fillna("MISSING").astype(str)
                le.fit(df_filled)
                self.encoders[col] = le
            logger.info("Fitted LabelEncoder on columns: %s", self.columns)

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms categorical columns using the fitted encoder state.
        For One-Hot encoding, drops the original columns and appends the new encoded ones.
        For Label and Ordinal encoding, replaces values in-place or adds new encoded columns.
        """
        if not self.columns:
            return df

        df_encoded = df.copy()
        
        # Verify columns exist
        missing = [c for c in self.columns if c not in df_encoded.columns]
        if missing:
            raise ValueError(f"Categorical columns missing during transform: {missing}")

        if self.strategy == "onehot":
            if self.onehot_encoder is None:
                raise ValueError("Encoder not fitted.")
            df_filled = df_encoded[self.columns].fillna("MISSING").astype(str)
            encoded_arr = self.onehot_encoder.transform(df_filled)
            df_ohe = pd.DataFrame(encoded_arr, columns=self.onehot_feature_names, index=df_encoded.index)
            # Drop original columns and concatenate the OHE DataFrame
            df_encoded = df_encoded.drop(columns=self.columns)
            df_encoded = pd.concat([df_encoded, df_ohe], axis=1)
            logger.info("One-hot encoded columns: %s", self.columns)

        elif self.strategy == "ordinal":
            if self.onehot_encoder is None:
                raise ValueError("Encoder not fitted.")
            df_filled = df_encoded[self.columns].fillna("MISSING").astype(str)
            encoded_arr = self.onehot_encoder.transform(df_filled)
            df_encoded[self.columns] = encoded_arr
            logger.info("Ordinal encoded columns: %s", self.columns)

        elif self.strategy == "label":
            for col in self.columns:
                le = self.encoders.get(col)
                if le is None:
                    raise ValueError(f"LabelEncoder not fitted for column: {col}")
                
                df_filled = df_encoded[col].fillna("MISSING").astype(str)
                # Handle unseen values for LabelEncoder by mapping them to a default class or max class+1
                classes = list(le.classes_)
                # Safe mapping
                unknown_class_idx = len(classes)
                
                def safe_map(val):
                    return le.transform([val])[0] if val in classes else unknown_class_idx

                df_encoded[col] = df_filled.apply(safe_map)
            logger.info("Label encoded columns: %s", self.columns)

        return df_encoded

    def fit_transform(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Fits on columns and transforms DataFrame categorical features.
        """
        self.fit(df, columns)
        return self.transform(df)
