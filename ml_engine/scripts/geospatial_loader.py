"""
Step 2 -- Geospatial Loader
============================
Input  : DATASETS/46d6c279-ae09-43a8-8691-7a5386f69e3a.kml  (Chennai Floods 2015)
Output : ml_engine/data/processed/chennai_flood_zones.csv
         ml_engine/data/processed/chennai_zone_clusters.csv  (clustered into zones)

What this script does:
  1. Parses the KML file (7,894 road segments, 7,884 flooded)
  2. Extracts flooded road coordinates (lat, lon midpoints)
  3. Clusters nearby flooded segments into DisasterZone polygons
     using DBSCAN spatial clustering
  4. Computes zone center (lat, lon) and bounding box
  5. Saves processed CSVs ready for DB seeding (Step 4)
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import DBSCAN

# -- Paths -------------------------------------------------------------------
ROOT      = Path(__file__).resolve().parents[2]
KML_PATH  = ROOT / "DATASETS" / "46d6c279-ae09-43a8-8691-7a5386f69e3a.kml"
OUT_DIR   = ROOT / "ml_engine" / "data" / "processed"
SEGS_CSV  = OUT_DIR / "chennai_flood_segments.csv"
ZONES_CSV = OUT_DIR / "chennai_flood_zones.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


# -- 1. Parse KML ------------------------------------------------------------
def parse_kml(kml_path: Path) -> pd.DataFrame:
    print(f"[1/5] Parsing KML: {kml_path.name}")
    tree = ET.parse(kml_path)
    root = tree.getroot()

    records = []
    placemarks = root.findall(".//kml:Placemark", KML_NS)
    print(f"      Total placemarks : {len(placemarks)}")

    for pm in placemarks:
        schema = pm.find(".//kml:SchemaData", KML_NS)
        if schema is None:
            continue

        attrs = {
            sd.get("name"): sd.text
            for sd in schema.findall("kml:SimpleData", KML_NS)
        }

        is_flooded = int(attrs.get("is_flooded", 0))
        if not is_flooded:
            continue  # skip non-flooded segments

        road_class = attrs.get("class", "unknown")
        road_type  = attrs.get("type", "unknown")
        osm_id     = attrs.get("osm_id", "")
        length_km  = float(attrs.get("length", 0) or 0)

        # Extract coordinate pairs from LineString
        coords_el = pm.find(".//kml:coordinates", KML_NS)
        if coords_el is None or not coords_el.text:
            continue

        coord_pairs = coords_el.text.strip().split()
        lons, lats = [], []
        for pair in coord_pairs:
            parts = pair.split(",")
            if len(parts) >= 2:
                try:
                    lons.append(float(parts[0]))
                    lats.append(float(parts[1]))
                except ValueError:
                    continue

        if not lats:
            continue

        # Use midpoint of segment
        mid_lat = sum(lats) / len(lats)
        mid_lon = sum(lons) / len(lons)

        records.append({
            "osm_id":     osm_id,
            "road_class": road_class,
            "road_type":  road_type,
            "is_flooded": is_flooded,
            "length_km":  length_km,
            "lat":        round(mid_lat, 6),
            "lon":        round(mid_lon, 6),
            "n_points":   len(lats),
        })

    df = pd.DataFrame(records)
    print(f"      Flooded segments : {len(df)}")
    road_types = sorted([str(x) for x in df['road_class'].unique()])
    print(f"      Road types       : {road_types}")
    print(f"      Lat range        : {df['lat'].min():.4f} -- {df['lat'].max():.4f}")
    print(f"      Lon range        : {df['lon'].min():.4f} -- {df['lon'].max():.4f}")
    return df


# -- 2. Spatial Clustering (DBSCAN) ------------------------------------------
def cluster_into_zones(df: pd.DataFrame, eps_km: float = 1.5, min_samples: int = 10) -> pd.DataFrame:
    """
    Group nearby flooded road segments into disaster zones.
    eps_km  : max distance between points in same cluster (km)
    min_samples : min segments to form a zone
    """
    print(f"\n[2/5] Clustering segments into zones (eps={eps_km}km, min={min_samples})...")

    # Convert lat/lon to radians for haversine metric
    coords_rad = np.radians(df[["lat", "lon"]].values)
    earth_radius_km = 6371.0
    eps_rad = eps_km / earth_radius_km

    db = DBSCAN(eps=eps_rad, min_samples=min_samples, algorithm="ball_tree", metric="haversine")
    df = df.copy()
    df["cluster"] = db.fit_predict(coords_rad)

    n_zones  = df[df["cluster"] >= 0]["cluster"].nunique()
    n_noise  = (df["cluster"] == -1).sum()
    print(f"      Zones found      : {n_zones}")
    print(f"      Noise segments   : {n_noise}")
    return df


# -- 3. Build Zone Summary ---------------------------------------------------
def build_zone_summary(df: pd.DataFrame) -> pd.DataFrame:
    print(f"\n[3/5] Building zone summary...")

    zone_rows = []
    valid = df[df["cluster"] >= 0]

    for cluster_id, grp in valid.groupby("cluster"):
        center_lat = grp["lat"].mean()
        center_lon = grp["lon"].mean()
        bbox_n     = grp["lat"].max()
        bbox_s     = grp["lat"].min()
        bbox_e     = grp["lon"].max()
        bbox_w     = grp["lon"].min()

        # Approximate area from bounding box
        lat_km  = (bbox_n - bbox_s) * 111.0
        lon_km  = (bbox_e - bbox_w) * 111.0 * abs(np.cos(np.radians(center_lat)))
        area_sq_km = round(lat_km * lon_km, 2)

        # Road type breakdown
        main_class = grp["road_class"].value_counts().idxmax()

        # Severity based on cluster size + area
        n_segs = len(grp)
        if n_segs > 500 or area_sq_km > 20:
            severity = "critical"
            severity_score = 9.0
        elif n_segs > 200 or area_sq_km > 10:
            severity = "high"
            severity_score = 7.5
        elif n_segs > 50 or area_sq_km > 3:
            severity = "medium"
            severity_score = 5.5
        else:
            severity = "low"
            severity_score = 3.0

        zone_rows.append({
            "zone_id":          cluster_id,
            "name":             f"Chennai Flood Zone {cluster_id + 1}",
            "state":            "Tamil Nadu",
            "district":         "Chennai",
            "center_lat":       round(center_lat, 6),
            "center_lon":       round(center_lon, 6),
            "area_sq_km":       area_sq_km,
            "n_segments":       n_segs,
            "dominant_road":    main_class,
            "severity":         severity,
            "severity_score":   severity_score,
            "disaster_type":    "flood",
            "source":           "chennai_kml_2015",
            "description":      (
                f"Chennai Floods 2015 -- {n_segs} flooded road segments, "
                f"area ~{area_sq_km} sq km, dominant road type: {main_class}."
            ),
        })

    zones_df = pd.DataFrame(zone_rows).sort_values("severity_score", ascending=False).reset_index(drop=True)
    print(f"      Total zones      : {len(zones_df)}")
    print(f"      Severity breakdown:")
    for sev, cnt in zones_df["severity"].value_counts().items():
        print(f"        {sev:<10} : {cnt}")
    return zones_df


# -- 4. Save Outputs ---------------------------------------------------------
def save_outputs(segs_df: pd.DataFrame, zones_df: pd.DataFrame):
    print(f"\n[4/5] Saving outputs...")
    segs_df.to_csv(SEGS_CSV, index=False)
    zones_df.to_csv(ZONES_CSV, index=False)
    print(f"      Segments CSV  -> {SEGS_CSV}  ({len(segs_df)} rows)")
    print(f"      Zones CSV     -> {ZONES_CSV}  ({len(zones_df)} rows)")


# -- 5. Preview --------------------------------------------------------------
def preview(zones_df: pd.DataFrame):
    print(f"\n[5/5] Top 5 Flood Zones:")
    print("-" * 75)
    cols = ["name", "center_lat", "center_lon", "area_sq_km", "n_segments", "severity"]
    print(zones_df[cols].head(5).to_string(index=False))
    print("-" * 75)


# -- Main --------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  AI Disaster Response -- Geospatial Loader (Step 2)")
    print("=" * 60)

    segs_df  = parse_kml(KML_PATH)
    segs_df  = cluster_into_zones(segs_df, eps_km=1.5, min_samples=10)
    zones_df = build_zone_summary(segs_df)
    save_outputs(segs_df, zones_df)
    preview(zones_df)

    print("\n" + "=" * 60)
    print("  [OK] Step 2 Complete!")
    print(f"  Zones : {ZONES_CSV}")
    print(f"  Segs  : {SEGS_CSV}")
    print("=" * 60)
