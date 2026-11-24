"""Test map rendering — checks GeoJSON matching and plotly version."""
import json, re
import pandas as pd
import plotly
from pathlib import Path

ROOT = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra")

print(f"Plotly version: {plotly.__version__}")

# Load GeoJSON
gj_path = ROOT / "assets" / "maharashtra_districts.geojson"
with open(gj_path, encoding="utf-8") as f:
    gj = json.load(f)

def normalize_district(value):
    if value is None: return ""
    value = str(value).strip().lower().replace("&","and")
    value = re.sub(r"\b(district|city)\b","",value)
    value = re.sub(r"[-_]+"," ",value)
    value = re.sub(r"[()]","",value)
    return " ".join(value.split())

# Add dtname_norm to GeoJSON
geojson_norms = []
for feat in gj["features"]:
    props = feat.get("properties", {})
    raw = props.get("dtname", "")
    norm = normalize_district(raw)
    props["dtname_norm"] = norm
    geojson_norms.append(norm)

print(f"\nGeoJSON normalized district names ({len(geojson_norms)}):")
for n in sorted(geojson_norms): print(f"  {n}")

# Load data
hist = pd.read_csv(ROOT / "data/processed/district_year/maharashtra_district_year_shala_score_v1.csv", low_memory=False)
latest = hist[hist["academic_year"] == hist["academic_year"].max()]
map_df = latest[["district","shala_score_v1"]].copy()
map_df["district_norm"] = map_df["district"].astype(str).apply(normalize_district)

print(f"\nData normalized district names ({len(map_df)}):")
for n in sorted(map_df["district_norm"].tolist()): print(f"  {n}")

# Check matches
matched = set(map_df["district_norm"]) & set(geojson_norms)
unmatched_data = set(map_df["district_norm"]) - set(geojson_norms)
unmatched_geo  = set(geojson_norms) - set(map_df["district_norm"])

print(f"\nMatched: {len(matched)}/36")
print(f"Unmatched in data (no GeoJSON): {sorted(unmatched_data)}")
print(f"Unmatched in GeoJSON (no data): {sorted(unmatched_geo)}")
