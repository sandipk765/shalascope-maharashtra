import csv
from pathlib import Path

path = Path(r"c:\Users\userp\Desktop\ShalaScope_Maharashtra\data\extracted\2021-22\enrolment_data_2_Maharashtra_2021-22\127_enr2.csv")
with open(path, encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    print("Columns:", header)

    item_desc_idx = header.index("item_desc") if "item_desc" in header else -1
    item_cd_idx   = header.index("item_cd")   if "item_cd"   in header else -1
    print(f"item_desc col: {item_desc_idx}, item_cd col: {item_cd_idx}")

    missing_count = 0
    sample = []
    for row in reader:
        if item_desc_idx >= 0 and not row[item_desc_idx].strip():
            missing_count += 1
            if len(sample) < 5:
                cd  = row[item_cd_idx]  if item_cd_idx  >= 0 else "N/A"
                desc = row[item_desc_idx] if item_desc_idx >= 0 else "N/A"
                sample.append({"item_cd": cd, "item_desc_blank": repr(desc)})

    print(f"Rows with blank item_desc: {missing_count}")
    print("Samples:", sample)
