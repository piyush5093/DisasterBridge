"""
Step 4 -- Demand Predictor Service
====================================
Loads the trained RandomForest model (demand_model.pkl) from Step 1
and provides resource demand predictions for any DisasterZone.

Usage (imported by zones.py route in Step 5):
    from app.services.demand_predictor import predict_demand, predictor

Public API:
    predictor.predict(zone)          -> DemandEstimate
    predictor.predict_raw(features)  -> DemandEstimate
    predictor.is_ready()             -> bool
"""

import os
import pickle
import warnings
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

warnings.filterwarnings("ignore")

# -- Model path: walk up from this file to find project root ----------------
_THIS_DIR = Path(__file__).resolve().parent

def _find_project_root(start: Path) -> Path:
    """Walk up directory tree until we find ml_engine/ folder."""
    for parent in [start] + list(start.parents):
        if (parent / "ml_engine").exists():
            return parent
    return start.parents[3]  # fallback

_PROJ_ROOT = _find_project_root(_THIS_DIR)
MODEL_PATH = _PROJ_ROOT / "ml_engine" / "models" / "saved" / "demand_model.pkl"


# ---------------------------------------------------------------------------
@dataclass
class DemandEstimate:
    """Resource demand prediction result for one DisasterZone."""

    # Core predictions (from ML model)
    food_packets:   int = 0
    water_liters:   int = 0
    medical_kits:   int = 0

    # Derived / rule-based extras
    shelter_capacity:   int = 0
    rescue_vehicles:    int = 0
    personnel_needed:   int = 0

    # Confidence & metadata
    confidence:         float = 0.0       # 0.0 - 1.0
    method:             str   = "unknown" # "ml_model" | "heuristic" | "fallback"
    model_version:      str   = "1.0"
    input_features:     Dict[str, Any] = field(default_factory=dict)
    warnings:           list  = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "food_packets":      self.food_packets,
            "water_liters":      self.water_liters,
            "medical_kits":      self.medical_kits,
            "shelter_capacity":  self.shelter_capacity,
            "rescue_vehicles":   self.rescue_vehicles,
            "personnel_needed":  self.personnel_needed,
            "confidence":        round(self.confidence, 3),
            "method":            self.method,
            "model_version":     self.model_version,
            "input_features":    self.input_features,
            "warnings":          self.warnings,
        }


# ---------------------------------------------------------------------------
class DemandPredictor:
    """
    Singleton service wrapping the trained RandomForest pipeline.
    Falls back to rule-based heuristics if the model is not available.
    """

    def __init__(self):
        self._pipeline    = None
        self._features    = []
        self._targets     = []
        self._loaded      = False
        self._load_error  = None
        self._load_model()

    # -- Model loading -------------------------------------------------------
    def _load_model(self):
        try:
            if not MODEL_PATH.exists():
                self._load_error = f"Model not found at {MODEL_PATH}"
                return

            with open(MODEL_PATH, "rb") as f:
                bundle = pickle.load(f)

            self._pipeline  = bundle["pipeline"]
            self._features  = bundle["features"]
            self._targets   = bundle["targets"]
            self._loaded    = True
            print(f"[DemandPredictor] Model loaded from {MODEL_PATH.name}")
            print(f"[DemandPredictor] Features : {self._features}")
            print(f"[DemandPredictor] Targets  : {self._targets}")

        except Exception as e:
            self._load_error = str(e)
            print(f"[DemandPredictor] WARNING: Could not load model: {e}")
            print(f"[DemandPredictor] Falling back to heuristic mode.")

    def is_ready(self) -> bool:
        return self._loaded and self._pipeline is not None

    # -- Feature extraction from a DisasterZone ORM object ------------------
    def _zone_to_features(self, zone) -> Dict[str, float]:
        """
        Extract ML features from a DisasterZone DB object.
        Uses zone fields + sensible defaults for missing data.
        """
        # Rainfall proxies: use severity_score as stand-in when real rain data absent
        base_rain_mm    = zone.severity_score * 100.0     # 0-1000mm proxy
        normal_rain_mm  = 400.0                            # India avg ~400mm/event
        rainfall_excess = base_rain_mm - normal_rain_mm
        rainfall_ratio  = base_rain_mm / (normal_rain_mm + 1)

        # Camp count proxy: population_affected / 4 people per camp
        pop_affected    = max(zone.population_affected or 0, 1)
        est_camps       = max(pop_affected // 4, 1)

        # Damaged houses proxy: 15% of affected population for floods
        disaster_type   = (zone.disaster_type or "flood").lower()
        damage_factor   = {"flood": 0.15, "earthquake": 0.30, "cyclone": 0.20,
                           "landslide": 0.25, "drought": 0.05}.get(disaster_type, 0.15)
        est_damaged_houses = int(pop_affected * damage_factor)

        # Landslide proxy: vulnerability_index + disaster type
        est_landslides  = 0
        if disaster_type in ("flood", "landslide"):
            est_landslides = int((zone.vulnerability_index or 0) * 50)

        camp_ratio      = est_camps / (est_damaged_houses + 1)
        damage_per_camp = est_damaged_houses / (est_camps + 1)
        high_landslide  = 1 if est_landslides > 20 else 0

        return {
            "actual_rainfall_in_mm": round(base_rain_mm, 2),
            "normal_rainfall_in_mm": round(normal_rain_mm, 2),
            "rainfall_excess":       round(rainfall_excess, 2),
            "rainfall_ratio":        round(rainfall_ratio, 4),
            "no_of_landslides":      est_landslides,
            "no_of_camps":           est_camps,
            "full_damaged_houses":   est_damaged_houses,
            "camp_ratio":            round(camp_ratio, 4),
            "damage_per_camp":       round(damage_per_camp, 4),
            "high_landslide":        high_landslide,
        }

    # -- ML prediction -------------------------------------------------------
    def _ml_predict(self, features: Dict[str, float]) -> tuple:
        """Run model inference. Returns (food, water, medical) raw floats."""
        import pandas as pd
        row = pd.DataFrame([{k: features.get(k, 0.0) for k in self._features}])
        pred = self._pipeline.predict(row)[0]
        food    = max(0, int(pred[self._targets.index("food_packets_needed")]))
        water   = max(0, int(pred[self._targets.index("water_liters_needed")]))
        medical = max(0, int(pred[self._targets.index("medical_kits_needed")]))
        return food, water, medical

    # -- Heuristic fallback --------------------------------------------------
    def _heuristic_predict(self, zone) -> tuple:
        """
        Rule-based demand estimate when model is unavailable.
        Based on WHO/NDMA disaster response guidelines.
        """
        pop = max(zone.population_affected or 0, 100)
        days = 3  # initial 3-day supply window

        food    = pop * 3 * days                       # 3 meals/day
        water   = pop * 5 * days                       # 5L/person/day
        medical = max(50, int(pop * 0.05))             # 5% need medical kits

        # Scale by severity
        scale = {"critical": 1.5, "high": 1.2, "medium": 1.0, "low": 0.7}
        s = scale.get((zone.severity or "medium").lower(), 1.0)
        return int(food * s), int(water * s), int(medical * s)

    # -- Derived estimates ---------------------------------------------------
    def _derive_extra(self, zone, food: int, water: int) -> tuple:
        """Shelter, vehicles, personnel — derived from core estimates."""
        pop = max(zone.population_affected or 0, 1)

        # Shelter: 60% of affected pop needs temporary shelter
        shelter = int(pop * 0.60)

        # Rescue vehicles: 1 per 200 people, minimum 2
        vehicles = max(2, math.ceil(pop / 200))

        # Personnel: 1 per 50 people + 1 team lead per 10 staff
        base_staff  = math.ceil(pop / 50)
        team_leads  = math.ceil(base_staff / 10)
        personnel   = base_staff + team_leads

        return shelter, vehicles, personnel

    # -- Confidence score ----------------------------------------------------
    def _confidence(self, zone) -> float:
        """
        Estimate prediction confidence based on data quality.
        Higher score if zone has real population data and known source.
        """
        score = 0.5  # base

        if zone.population_affected and zone.population_affected > 0:
            score += 0.2
        if zone.severity_score and zone.severity_score > 0:
            score += 0.1
        if zone.source in ("kerala_dataset_2018", "chennai_kml_2015"):
            score += 0.15   # real dataset zones
        if zone.vulnerability_index and zone.vulnerability_index > 0:
            score += 0.05

        return round(min(1.0, score), 3)

    # -- Main predict API ----------------------------------------------------
    def predict(self, zone) -> DemandEstimate:
        """
        Predict resource demand for a DisasterZone ORM object.
        Uses ML model if loaded, falls back to heuristics.
        """
        warns = []
        features = self._zone_to_features(zone)

        if self.is_ready():
            try:
                food, water, medical = self._ml_predict(features)
                method = "ml_model"
            except Exception as e:
                warns.append(f"ML inference failed: {e}. Using heuristic.")
                food, water, medical = self._heuristic_predict(zone)
                method = "heuristic"
        else:
            food, water, medical = self._heuristic_predict(zone)
            method = "heuristic"
            if self._load_error:
                warns.append(f"Model unavailable: {self._load_error}")

        # Vulnerability adjustment: boost medical by vuln index
        vuln = zone.vulnerability_index or 0.0
        medical = int(medical * (1.0 + vuln * 0.5))

        shelter, vehicles, personnel = self._derive_extra(zone, food, water)
        confidence = self._confidence(zone)

        return DemandEstimate(
            food_packets      = food,
            water_liters      = water,
            medical_kits      = medical,
            shelter_capacity  = shelter,
            rescue_vehicles   = vehicles,
            personnel_needed  = personnel,
            confidence        = confidence,
            method            = method,
            model_version     = "1.0",
            input_features    = features,
            warnings          = warns,
        )

    def predict_raw(self, features: Dict[str, float]) -> DemandEstimate:
        """
        Predict from raw feature dict (for testing / API direct calls).
        """
        warns = []
        if self.is_ready():
            try:
                food, water, medical = self._ml_predict(features)
                method = "ml_model"
            except Exception as e:
                warns.append(str(e))
                food = water = medical = 0
                method = "error"
        else:
            food = water = medical = 0
            method = "fallback"
            warns.append("Model not loaded")

        return DemandEstimate(
            food_packets   = food,
            water_liters   = water,
            medical_kits   = medical,
            confidence     = 0.5 if self.is_ready() else 0.0,
            method         = method,
            input_features = features,
            warnings       = warns,
        )


# -- Singleton instance (imported by routes) ---------------------------------
predictor = DemandPredictor()


# -- Convenience function ----------------------------------------------------
def predict_demand(zone) -> Dict[str, Any]:
    """
    Shortcut: predict demand for a zone and return as plain dict.
    Used directly in FastAPI route handlers.
    """
    estimate = predictor.predict(zone)
    return estimate.to_dict()
