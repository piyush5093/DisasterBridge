"""
Step 1 + Demand Prediction Model Training
=========================================
Dataset  : DATASETS/district_wise_details.csv  (Kerala Floods 2018)
Output   : ml_engine/models/saved/demand_model.pkl
           ml_engine/data/processed/kerala_processed.csv

Features used:
  - actual_rainfall_in_mm
  - normal_rainfall_in_mm
  - rainfall_excess          (derived)
  - no_of_landslides
  - no_of_camps
  - full_damaged_houses
  - camp_ratio               (derived)
  - damage_per_camp          (derived)

Targets (derived heuristics):
  - food_packets_needed      (camps + 3 meals + 3 days)
  - water_liters_needed      (camps + avg 4 people + 5L/day + 3 days)
  - medical_kits_needed      (fatalities + 10 + damaged_houses + 0.05)
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.multioutput import MultiOutputRegressor

# -- Paths ---------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parents[2]
DATASET_CSV = ROOT / "DATASETS" / "district_wise_details.csv"
PROCESSED   = ROOT / "ml_engine" / "data" / "processed" / "kerala_processed.csv"
MODEL_DIR   = ROOT / "ml_engine" / "models" / "saved"
MODEL_PATH  = MODEL_DIR / "demand_model.pkl"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED.parent.mkdir(parents=True, exist_ok=True)


# -- 1. Load Raw Data ----------------------------------------------------------
def load_data() -> pd.DataFrame:
    print(f"[1/5] Loading dataset: {DATASET_CSV}")
    df = pd.read_csv(DATASET_CSV)
    print(f"      Rows: {len(df)} | Columns: {list(df.columns)}")
    return df


# -- 2. Feature Engineering ----------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    print("[2/5] Engineering features...")

    # Rainfall excess (how much more than normal)
    df["rainfall_excess"] = df["actual_rainfall_in_mm"] - df["normal_rainfall_in_mm"]
    df["rainfall_ratio"]  = df["actual_rainfall_in_mm"] / (df["normal_rainfall_in_mm"] + 1)

    # Camp and damage ratios
    df["camp_ratio"]       = df["no_of_camps"] / (df["full_damaged_houses"] + 1)
    df["damage_per_camp"]  = df["full_damaged_houses"] / (df["no_of_camps"] + 1)

    # Landslide risk flag
    df["high_landslide"]   = (df["no_of_landslides"] > 20).astype(int)

    # -- Derive Target Variables (Resource Demand) -----------------------------
    # Assumption: avg 4 people per camp
    avg_people_per_camp = 4

    # Food: 3 meals/day + 3 days + people in camps
    df["food_packets_needed"] = (
        df["no_of_camps"] * avg_people_per_camp * 3 * 3
    ).astype(int)

    # Water: 5 litres/person/day + 3 days
    df["water_liters_needed"] = (
        df["no_of_camps"] * avg_people_per_camp * 5 * 3
    ).astype(int)

    # Medical kits: fatality-driven + house damage proxy
    df["medical_kits_needed"] = (
        df["fatalities"] * 10 + df["full_damaged_houses"] * 0.05
    ).astype(int)

    # Severity score (0-10): composite of damage signals
    df["severity_score"] = (
        (df["rainfall_ratio"].clip(1, 5) - 1) * 1.5 +
        (df["fatalities"] / df["fatalities"].max()) * 3.0 +
        (df["no_of_landslides"] / (df["no_of_landslides"].max() + 1)) * 2.0 +
        (df["full_damaged_houses"] / df["full_damaged_houses"].max()) * 3.0
    ).clip(0, 10).round(2)

    print(f"      Features added: rainfall_excess, rainfall_ratio, camp_ratio,")
    print(f"                      damage_per_camp, high_landslide")
    print(f"      Targets added : food_packets_needed, water_liters_needed, medical_kits_needed")
    return df


# -- 3. Train Model ------------------------------------------------------------
FEATURES = [
    "actual_rainfall_in_mm",
    "normal_rainfall_in_mm",
    "rainfall_excess",
    "rainfall_ratio",
    "no_of_landslides",
    "no_of_camps",
    "full_damaged_houses",
    "camp_ratio",
    "damage_per_camp",
    "high_landslide",
]

TARGETS = [
    "food_packets_needed",
    "water_liters_needed",
    "medical_kits_needed",
]


def train_model(df: pd.DataFrame):
    print("[3/5] Training RandomForest model...")

    X = df[FEATURES].fillna(0)
    Y = df[TARGETS].fillna(0)

    # Pipeline: scale + multi-output RF
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
    )
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  MultiOutputRegressor(rf)),
    ])

    pipeline.fit(X, Y)

    # Cross-validation (leave-one-out on small dataset)
    from sklearn.model_selection import LeaveOneOut
    loo   = LeaveOneOut()
    preds = {t: [] for t in TARGETS}
    trues = {t: [] for t in TARGETS}

    for train_idx, test_idx in loo.split(X):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        Y_tr, Y_te = Y.iloc[train_idx], Y.iloc[test_idx]
        p = Pipeline([
            ("scaler", StandardScaler()),
            ("model",  MultiOutputRegressor(
                RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
            )),
        ])
        p.fit(X_tr, Y_tr)
        pred = p.predict(X_te)[0]
        for i, t in enumerate(TARGETS):
            preds[t].append(pred[i])
            trues[t].append(Y_te.iloc[0][t])

    print("\n      -- LOO Cross-Validation Results --")
    for t in TARGETS:
        from sklearn.metrics import mean_absolute_error, r2_score
        mae = mean_absolute_error(trues[t], preds[t])
        try:
            r2 = r2_score(trues[t], preds[t])
        except Exception:
            r2 = float("nan")
        print(f"      {t:<28} MAE={mae:>8.1f}   R+={r2:.3f}")

    return pipeline


# -- 4. Save Artefacts ---------------------------------------------------------
def save_model(pipeline, df: pd.DataFrame):
    print(f"\n[4/5] Saving model -> {MODEL_PATH}")

    bundle = {
        "pipeline": pipeline,
        "features": FEATURES,
        "targets":  TARGETS,
        "dataset":  "Kerala Floods 2018 + district_wise_details.csv",
        "trained_on_districts": df["district"].tolist(),
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"      Saved  +  ({MODEL_PATH.stat().st_size / 1024:.1f} KB)")

    df.to_csv(PROCESSED, index=False)
    print(f"      Processed CSV -> {PROCESSED}")


# -- 5. Quick Inference Test ---------------------------------------------------
def test_inference(pipeline):
    print("\n[5/5] Quick inference test...")

    sample = pd.DataFrame([{
        "actual_rainfall_in_mm": 900.0,
        "normal_rainfall_in_mm": 400.0,
        "rainfall_excess":       500.0,
        "rainfall_ratio":        2.25,
        "no_of_landslides":      35,
        "no_of_camps":           800,
        "full_damaged_houses":   1200,
        "camp_ratio":            0.67,
        "damage_per_camp":       1.5,
        "high_landslide":        1,
    }])

    pred = pipeline.predict(sample)[0]
    print("\n      Sample Zone (rainfall=900mm, 800 camps, 1200 damaged houses):")
    print(f"      food_packets_needed  : {int(pred[0]):,}")
    print(f"      water_liters_needed  : {int(pred[1]):,} L")
    print(f"      medical_kits_needed  : {int(pred[2]):,}")


# -- Main ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  AI Disaster Response + Demand Model Training (Step 1)")
    print("=" * 60)

    df       = load_data()
    df       = engineer_features(df)
    pipeline = train_model(df)
    save_model(pipeline, df)
    test_inference(pipeline)

    print("\n" + "=" * 60)
    print("  [OK]  Step 1 Complete!")
    print(f"  Model  : {MODEL_PATH}")
    print(f"  Processed: {PROCESSED}")
    print("=" * 60)
