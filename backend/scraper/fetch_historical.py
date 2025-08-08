import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# === CONFIG ===
BASE_URL = "https://serval.uvm.edu/~rgweb/batch/enrollment/"
ENROLLMENT_TAB_URL = urljoin(BASE_URL, "enrollment_tab.html")
CURRENT_FALL_URL = "https://serval.uvm.edu/~rgweb/batch/curr_enroll_fall.txt"

RAW_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "raw"))
CURRENT_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "data", "current"))

# === ENSURE OUTPUT DIRECTORIES EXIST ===
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CURRENT_DIR, exist_ok=True)

def get_soup(url):
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")

def slugify_term(term):
    return re.sub(r"[^\w]+", "_", term.strip().lower())

def scrape_and_download_historical():
    print("📚 Fetching historical enrollment page...")
    soup = get_soup(ENROLLMENT_TAB_URL)

    links = soup.find_all("a", href=re.compile(r"^curr_enroll_\d{6}\.html$"))
    print(f"Found {len(links)} term links.")

    for a_tag in links:
        term_name = a_tag.get_text().strip()  # e.g., "Spring 2010"
        term_page_url = urljoin(BASE_URL, a_tag['href'])

        print(f"\n🔍 Processing: {term_name} -> {term_page_url}")
        try:
            term_soup = get_soup(term_page_url)
            txt_link = term_soup.find("a", string=lambda s: s and "comma-delimited format" in s.lower())

            if txt_link:
                txt_href = txt_link['href']
                txt_url = txt_href if txt_href.startswith("http") else urljoin(BASE_URL, txt_href)

                filename = f"uvm_{slugify_term(term_name)}.csv"
                filepath = os.path.join(RAW_DIR, filename)

                print(f"⬇️  Downloading {txt_url} -> {filepath}")
                txt_response = requests.get(txt_url)
                txt_response.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(txt_response.content)
            else:
                print(f"⚠️ No .txt link found on: {term_page_url}")

        except Exception as e:
            print(f"❌ Error processing {term_page_url}: {e}")

    print("\n✅ Historical course files saved to data/raw.")

def download_current_fall():
    filename = "uvm_current_sections.csv"
    filepath = os.path.join(CURRENT_DIR, filename)

    try:
        print(f"\n🌐 Downloading current fall data: {CURRENT_FALL_URL}")
        response = requests.get(CURRENT_FALL_URL)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"✅ Saved to {filepath}")
    except Exception as e:
        print(f"❌ Failed to download current fall data: {e}")

if __name__ == "__main__":
    scrape_and_download_historical()
    download_current_fall()
