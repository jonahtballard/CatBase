import requests
import csv
import os

# === Manually set current term ===
SEMESTER = "Fall"
YEAR = 2025

url = 'https://serval.uvm.edu/~rgweb/batch/curr_enroll_fall.txt'
response = requests.get(url)
response.raise_for_status()

lines = response.text.strip().splitlines()
reader = csv.reader(lines)
rows = list(reader)

# Add Semester & Year columns if not present
if "Semester" not in rows[0] and "Year" not in rows[0]:
    rows[0] += ["Semester", "Year"]
    for r in rows[1:]:
        r += [SEMESTER, YEAR]

os.makedirs('data/raw', exist_ok=True)
output_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "uvm_current_sections.csv")
output_path = os.path.abspath(output_path)

with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"✅ Saved data for {SEMESTER} {YEAR} to {output_path}")
