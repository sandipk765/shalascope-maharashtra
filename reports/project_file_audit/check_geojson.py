import json

with open(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\assets\maharashtra_districts.geojson", encoding="utf-8") as f:
    gj = json.load(f)

feats = gj.get("features", [])
print(f"Type: {gj.get('type')}")
print(f"Feature count: {len(feats)}")
if feats:
    props = feats[0].get("properties", {})
    print(f"Property keys: {list(props.keys())}")
    print(f"First feature properties: {props}")
    if len(feats) > 1:
        print(f"Second feature properties: {feats[1].get('properties', {})}")
    # Print all district names from properties
    for i, feat in enumerate(feats[:40]):
        p = feat.get("properties", {})
        # Try common keys
        name = p.get("district") or p.get("NAME_2") or p.get("name") or p.get("DISTRICT") or p.get("district_norm") or list(p.values())[0] if p else f"feat_{i}"
        print(f"  [{i}] {name}")
