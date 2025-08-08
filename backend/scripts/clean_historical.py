import os
import re
import pandas as pd
import numpy as np

# === Paths ===
RAW_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "raw"))
PROCESSED_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "processed"))
os.makedirs(PROCESSED_DIR, exist_ok=True)

STANDARD_ORDER = [
    "Subj", "Number", "Title", "Comp Numb",
    "Lec Lab", "Credits", "Start Time", "End Time", "Days",
    "Bldg", "Room", "Location",
    "Instructor", "NetId", "Email",
    "Max Enrollment", "Current Enrollment",
    "Semester", "Year"
]

def nullify(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    return np.nan if s == "" or s.lower() in {"nan", "none", "null"} else s

def to_hhmm(s):
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    if s == "" or s.upper() == "TBA":
        return np.nan
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        return np.nan
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return np.nan
    return f"{hh:02d}:{mm:02d}"

def normalize_days(day_str):
    day_str = str(day_str).strip() if not pd.isna(day_str) else ""
    if not day_str:
        return np.nan
    return ''.join(day_str.split())

def normalize_credits(credit_str):
    if pd.isna(credit_str):
        return np.nan
    s = str(credit_str).strip()
    s = re.sub(r"\bto\b", "-", s)
    s = s.replace(" or ", "/")
    return s if s else np.nan

def combine_location(bldg, room):
    b = nullify(bldg)
    r = nullify(room)
    if pd.isna(b) and pd.isna(r):
        return np.nan
    if not pd.isna(b) and not pd.isna(r):
        return f"{str(b).upper()} {str(r).upper()}"
    return str(b).upper() if not pd.isna(b) else str(r).upper()

def parse_term_from_filename(name):
    """
    Expect patterns like: uvm_fall_1997.csv, uvm_spring_2005.csv, etc.
    Returns (Semester, Year) or (NA, NA) if not found.
    """
    m = re.search(r"(fall|spring|summer|winter)[_\-]?(\d{4})", name, re.IGNORECASE)
    if m:
        sem = m.group(1).title()
        yr = int(m.group(2))
        return sem, yr
    m2 = re.search(r"(\d{4})[^\d]*(fall|spring|summer|winter)", name, re.IGNORECASE)
    if m2:
        sem = m2.group(2).title()
        yr = int(m2.group(1))
        return sem, yr
    return pd.NA, pd.NA

def standardize_columns(df):
    # Rename common variants
    rename_map = {}
    for col in df.columns:
        low = col.strip().lower()
        if low == "dept":
            rename_map[col] = "Subj"
        elif low in {"#", "course", "course #", "course number"}:
            rename_map[col] = "Number"
        elif low in {"leclab", "lec/lab", "lec lab"}:
            rename_map[col] = "Lec Lab"
        elif low == "comp numb":
            rename_map[col] = "Comp Numb"
        elif low == "max enrollment":
            rename_map[col] = "Max Enrollment"
        elif low == "current enrollment":
            rename_map[col] = "Current Enrollment"
    return df.rename(columns=rename_map)

def clean_dataframe(df, filename):
    df = standardize_columns(df)

    # Drop unwanted columns
    columns_to_drop = [
        "Sec", "Ptrm", "Attr", "Camp Code", "Coll Code",
        "True Max", "GP Ind", "Fees", "XListings"
    ]
    df = df.drop(columns=[c for c in columns_to_drop if c in df.columns], errors="ignore")

    # Normalize text-ish columns
    for c in ["Subj","Number","Title","Comp Numb","Lec Lab","Instructor","NetId","Email","Bldg","Room","Days","Credits"]:
        if c in df.columns:
            df[c] = df[c].map(nullify)

    # Add missing instructor contact columns
    for c in ["Email", "NetId"]:
        if c not in df.columns:
            df[c] = pd.NA

    # Days/Credits/Times
    if "Days" in df.columns:
        df["Days"] = df["Days"].map(normalize_days)
    if "Credits" in df.columns:
        df["Credits"] = df["Credits"].map(normalize_credits)

    df["Start Time"] = df.get("Start Time", pd.Series([np.nan]*len(df))).map(to_hhmm)
    df["End Time"]   = df.get("End Time",   pd.Series([np.nan]*len(df))).map(to_hhmm)

    # Location
    df["Bldg"] = df.get("Bldg", "").map(lambda x: np.nan if pd.isna(nullify(x)) else str(x).strip().upper())
    df["Room"] = df.get("Room", "").map(lambda x: np.nan if pd.isna(nullify(x)) else str(x).strip().upper())
    df["Location"] = [combine_location(b, r) for b, r in zip(df["Bldg"], df["Room"])]

    # Numeric coercions (nullable Int64)
    for c in ["Max Enrollment", "Current Enrollment", "Year"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Derive Semester/Year from filename if missing/empty
    sem, yr = parse_term_from_filename(filename)
    if "Semester" not in df.columns or df["Semester"].isna().all():
        df["Semester"] = pd.Series([sem]*len(df), dtype="string")
    else:
        df["Semester"] = df["Semester"].astype("string")

    if "Year" not in df.columns or df["Year"].isna().all():
        df["Year"] = pd.Series([yr]*len(df), dtype="Int64")
    else:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    # Ensure all STANDARD_ORDER columns exist
    for col in STANDARD_ORDER:
        if col not in df.columns:
            df[col] = pd.NA

    # Final ordering
    df = df[STANDARD_ORDER]
    return df

# === Process files ===
for filename in os.listdir(RAW_DIR):
    if not filename.lower().endswith(".csv"):
        continue
    if filename == "uvm_current_sections.csv":
        continue

    input_path = os.path.join(RAW_DIR, filename)
    output_path = os.path.join(PROCESSED_DIR, filename.replace(".csv", "_cleaned.csv"))

    try:
        print(f"🔧 Cleaning {filename}...")
        df = pd.read_csv(input_path, dtype=str, on_bad_lines="skip")
        cleaned_df = clean_dataframe(df, filename)
        cleaned_df.to_csv(output_path, index=False)
        print(f"✅ Saved DB-ready file to {output_path}")
    except Exception as e:
        print(f"❌ Failed to process {filename}: {e}")
