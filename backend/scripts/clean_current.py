import os
import re
import pandas as pd
import numpy as np

# === Paths ===
RAW_PATH = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "raw", "uvm_current_sections.csv"))
PROCESSED_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "processed"))
PROCESSED_PATH = os.path.join(PROCESSED_DIR, "uvm_current_sections_cleaned.csv")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# === Helper: standard column names for DB ===
STANDARD_ORDER = [
    "Subj", "Number", "Title", "Comp Numb",
    "Lec Lab", "Credits", "Start Time", "End Time", "Days",
    "Bldg", "Room", "Location",
    "Instructor", "NetId", "Email",
    "Max Enrollment", "Current Enrollment",
    "Semester", "Year"
]

def nullify(val):
    """Convert placeholder NAN-ish strings/empties to real NaN."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    return np.nan if s == "" or s.lower() in {"nan", "none", "null"} else s

def to_hhmm(s):
    """Return 'HH:MM' or NaN. Treat TBA/blank as NaN."""
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    if s == "" or s.upper() == "TBA":
        return np.nan
    # Accept 'H:MM', 'HH:MM'
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        return np.nan
    hh = int(m.group(1))
    mm = int(m.group(2))
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

def coerce_int(val):
    """Return pandas NA-aware integer (Int64) from messy input."""
    s = nullify(val)
    if pd.isna(s):
        return pd.NA
    try:
        return int(str(s).strip())
    except:
        return pd.PA

# === Load CSV ===
df = pd.read_csv(RAW_PATH, dtype=str)  # read everything as str first

# === Rename/standardize common columns ===
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
    else:
        # keep original
        pass

df = df.rename(columns=rename_map)

# === Drop unwanted columns if present ===
columns_to_drop = [
    "Sec", "Ptrm", "Attr", "Camp Code", "Coll Code",
    "True Max", "GP Ind", "Fees", "XListings"
]
df = df.drop(columns=[c for c in columns_to_drop if c in df.columns], errors="ignore")

# === Null/trim normalize select text columns ===
for c in ["Subj","Number","Title","Comp Numb","Lec Lab","Instructor","NetId","Email","Bldg","Room","Days","Credits"]:
    if c in df.columns:
        df[c] = df[c].map(nullify)

# === Normalize days/credits/times ===
if "Days" in df.columns:
    df["Days"] = df["Days"].map(normalize_days)

if "Credits" in df.columns:
    df["Credits"] = df["Credits"].map(normalize_credits)

df["Start Time"] = df.get("Start Time", pd.Series([np.nan]*len(df))).map(to_hhmm)
df["End Time"]   = df.get("End Time",   pd.Series([np.nan]*len(df))).map(to_hhmm)

# === Uppercase building/room and compute Location ===
df["Bldg"] = df.get("Bldg", "").map(lambda x: np.nan if pd.isna(nullify(x)) else str(x).strip().upper())
df["Room"] = df.get("Room", "").map(lambda x: np.nan if pd.isna(nullify(x)) else str(x).strip().upper())
df["Location"] = [combine_location(b, r) for b, r in zip(df["Bldg"], df["Room"])]

# === Ensure numeric columns as strings or nullable ints ===
# Keep CRN (Comp Numb) as string for leading zeros safety
for c in ["Max Enrollment", "Current Enrollment", "Year"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

# Semester/Year might be missing in the current file; add if absent
if "Semester" not in df.columns:
    df["Semester"] = pd.Series([pd.NA]*len(df), dtype="string")
else:
    df["Semester"] = df["Semester"].map(lambda x: nullify(x) if not pd.isna(x) else pd.NA).astype("string")

if "Year" not in df.columns:
    df["Year"] = pd.Series([pd.NA]*len(df), dtype="Int64")

# === Final column order & fill any missing columns with NA ===
for col in STANDARD_ORDER:
    if col not in df.columns:
        df[col] = pd.NA

df = df[STANDARD_ORDER]

# === Save ===
# Times remain as text 'HH:MM' or blank (NULL). Perfect for CSV→DB.
df.to_csv(PROCESSED_PATH, index=False)
print(f"✅ Cleaned, DB-ready data saved to {PROCESSED_PATH}")
