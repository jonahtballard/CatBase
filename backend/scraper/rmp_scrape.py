#!/usr/bin/env python3
"""
RMP scraper — scroll + click "Show More", match cards, parse profile with global parser, UPSERT to DB.

First time:
  pip install "playwright>=1.47" beautifulsoup4 requests
  python -m playwright install chromium

Run:
  python backend/scraper/rmp_scrape.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext

# use the global parser
from rmp_profile_parser import parse_professor_page

# ======= CONFIG =======
TARGET_SEMESTER = "Fall"
TARGET_YEAR     = 2025
DRY_RUN         = False       # <-- flip to False to write to DB
LIMIT_MATCHES   = None        # stop after N matches; None = all

HEADLESS = True
SLOW_MO_MS = 0

SCHOOL_ID       = 1320
START_URL       = f"https://www.ratemyprofessors.com/search/professors/{SCHOOL_ID}?q=*"

CARD_ANCHOR_SEL = "a.TeacherCard__StyledTeacherCard-syjs0d-0"
NAME_DIV_SEL    = "div.CardName__StyledCardName-sc-1gyrgim-0"

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "university_courses.db"

# HTTP for profile HTML (faster than navigating the same tab)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
# ======================


# ---------- DB ----------
def get_instructors_for_term(semester: str, year: int) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT DISTINCT i.instructor_id, i.name, i.netid, i.email
            FROM instructors i
            JOIN section_instructors si ON si.instructor_id = i.instructor_id
            JOIN sections s ON s.section_id = si.section_id
            JOIN terms t ON t.term_id = s.term_id
            WHERE t.semester = ? AND t.year = ?
            ORDER BY i.name
        """
        rows = conn.execute(sql, (semester, year)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def upsert_rmp(conn: sqlite3.Connection, instructor_id: int, parsed: Dict[str, Any]) -> None:
    """
    Overwrite RMP fields for this instructor on every run.
    If a value isn't present in `parsed`, we store NULL (fresh == empty).
    """
    rmp_id = parsed.get("professor_legacy_id")
    profile_url = (parsed.get("links") or {}).get("profile_url") \
                  or (f"https://www.ratemyprofessors.com/professor/{rmp_id}" if rmp_id else None)

    top_tags_json = json.dumps(parsed.get("top_tags") or [], ensure_ascii=False)
    dist_json = json.dumps(parsed.get("rating_distribution") or {}, ensure_ascii=False)

    conn.execute(
        """
        UPDATE instructors SET
            rmp_id                       = ?,   -- overwrite (can be NULL)
            rmp_url                      = ?,   -- overwrite (can be NULL)
            rmp_avg_rating               = ?,   -- overwrite
            rmp_num_ratings              = ?,   -- overwrite
            rmp_would_take_again         = ?,   -- overwrite
            rmp_difficulty               = ?,   -- overwrite
            rmp_top_tags_json            = ?,   -- overwrite
            rmp_rating_distribution_json = ?,   -- overwrite
            rmp_last_refreshed           = datetime('now')
        WHERE instructor_id = ?
        """,
        (
            rmp_id,
            profile_url,
            parsed.get("avg_rating"),
            parsed.get("num_ratings"),
            parsed.get("would_take_again_percent"),
            parsed.get("difficulty"),
            top_tags_json,
            dist_json,
            instructor_id,
        ),
    )
    conn.commit()


# ---------- Name helpers ----------
def normalize_name(name: str) -> str:
    name = (name or "").strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) >= 2:
            last = parts[0]
            first = parts[1]
            rest = parts[2:] if len(parts) > 2 else []
            name = " ".join([first] + rest + [last])
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\b([A-Za-z])\.\b", r"\1", name)
    return name.strip()

def key_name(name: str) -> str:
    s = normalize_name(name).lower()
    s = re.sub(r"[^a-z\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------- Page helpers ----------
async def maybe_dismiss_banners(page: Page):
    import re as _re
    for label in [r"Accept", r"I Accept", r"Agree", r"Continue", r"Got it", r"Okay"]:
        btn = page.get_by_role("button", name=_re.compile(label, _re.I))
        try:
            if await btn.count():
                await btn.first.click(timeout=1200)
                await page.wait_for_timeout(250)
                break
        except:
            pass

async def wait_for_first_cards(page: Page, timeout_ms=25000):
    await page.wait_for_selector(CARD_ANCHOR_SEL, timeout=timeout_ms)

async def get_card_info(page: Page, index: int) -> tuple[str | None, str | None]:
    a = page.locator(CARD_ANCHOR_SEL).nth(index)
    try:
        href = await a.get_attribute("href")
        if not href or not href.startswith("/professor/"):
            return None, None
        name_loc = a.locator(NAME_DIV_SEL)
        if not await name_loc.count():
            name_loc = a.locator("div[class*='CardName__StyledCardName']")
        display = (await name_loc.first.text_content()) if await name_loc.count() else None
        return (display.strip() if display else None), href.strip()
    except:
        return None, None

async def scroll_to_bottom(page: Page):
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    except:
        pass
    await page.keyboard.press("End")

async def click_show_more(page: Page) -> bool:
    import re as _re
    # 1) by role
    loc = page.get_by_role("button", name=_re.compile(r"^Show More$", _re.I))
    try:
        if await loc.count():
            if await loc.first.is_visible():
                await loc.first.scroll_into_view_if_needed()
                try:
                    await loc.first.click(timeout=1500)
                    return True
                except:
                    pass
    except:
        pass
    # 2) by exact text
    try:
        loc2 = page.get_by_text("Show More", exact=True)
        if await loc2.count():
            if await loc2.first.is_visible():
                await loc2.first.scroll_into_view_if_needed()
                try:
                    await loc2.first.click(timeout=1500)
                    return True
                except:
                    pass
    except:
        pass
    # 3) wrapper fallback (your snippet)
    try:
        wrapper = page.locator("div[class*='SearchResultsPage__AddPromptWrapper']")
        btns = wrapper.locator("button")
        if await btns.count():
            for i in range(await btns.count()):
                h = await btns.nth(i).element_handle()
                if h:
                    txt = (await h.text_content() or "").strip().lower()
                    if txt == "show more":
                        try:
                            await h.scroll_into_view_if_needed()
                            await h.click()
                            return True
                        except:
                            try:
                                await page.evaluate("(el)=>el.click()", h)
                                return True
                            except:
                                pass
    except:
        pass
    # 4) last-resort querySelectorAll
    try:
        clicked = await page.evaluate("""
(() => {
  const btns = Array.from(document.querySelectorAll('button'));
  const el = btns.find(b => (b.textContent||'').trim().toLowerCase() === 'show more');
  if (el) { el.scrollIntoView({block:'center'}); el.click(); return true; }
  return false;
})()
        """)
        if clicked:
            return True
    except:
        pass
    return False


# ---------- Profile fetch + parse ----------
def fetch_and_parse_profile(profile_href: str) -> Dict[str, Any]:
    url = f"https://www.ratemyprofessors.com{profile_href}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    html = r.text
    return parse_professor_page(html, ratings_limit=10)  # keep the last 10 comments for now


# ---------- main ----------
@dataclass
class MatchResult:
    instructor_id: int
    db_name: str
    rmp_name: str
    href: str
    parsed: Optional[dict] = None

async def main():
    print(f"Targeting {TARGET_SEMESTER} {TARGET_YEAR} …")
    db_profs = get_instructors_for_term(TARGET_SEMESTER, TARGET_YEAR)
    print(f"Loaded {len(db_profs)} instructors from DB.")

    db_map: dict[str, list[dict[str, Any]]] = {}
    for p in db_profs:
        db_map.setdefault(key_name(p["name"]), []).append(p)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO_MS,
            args=["--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Opening: {START_URL}")
        await page.goto(START_URL, wait_until="domcontentloaded")
        await maybe_dismiss_banners(page)
        await wait_for_first_cards(page)

        seen_ids: set[str] = set()
        matches: list[MatchResult] = []

        last_processed = 0
        stagnant_loops = 0

        # open DB connection once if we plan to write
        conn = sqlite3.connect(DB_PATH) if not DRY_RUN else None
        try:
            while True:
                total = await page.locator(CARD_ANCHOR_SEL).count()

                # process new cards
                for idx in range(last_processed, total):
                    display, href = await get_card_info(page, idx)
                    if not display or not href:
                        continue
                    m = re.search(r"/professor/(\d+)", href)
                    pid = m.group(1) if m else href
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    k = key_name(display)
                    if k in db_map:
                        for p in db_map[k]:
                            mr = MatchResult(
                                instructor_id=p["instructor_id"],
                                db_name=p["name"],
                                rmp_name=display,
                                href=href
                            )
                            try:
                                parsed = fetch_and_parse_profile(href)
                                mr.parsed = parsed
                                print(f"[MATCH] {p['name']} -> https://www.ratemyprofessors.com{href}")
                                print(f"        avg={parsed.get('avg_rating')}  count={parsed.get('num_ratings')}  "
                                      f"wta%={parsed.get('would_take_again_percent')}  diff={parsed.get('difficulty')}  "
                                      f"tags={', '.join((parsed.get('top_tags') or [])[:3])}")
                                if conn is not None:
                                    upsert_rmp(conn, p["instructor_id"], parsed)
                            except Exception as e:
                                print(f"[MATCH] {p['name']} -> {href}  (parse error: {e})")
                            matches.append(mr)
                            if LIMIT_MATCHES and len(matches) >= LIMIT_MATCHES:
                                print(f"Matched {len(matches)} instructor(s). (limit reached)")
                                return

                stagnant_loops = stagnant_loops + 1 if total == last_processed else 0
                last_processed = total

                # load more
                clicked = await click_show_more(page)
                await scroll_to_bottom(page)
                await page.wait_for_timeout(900)

                new_total = await page.locator(CARD_ANCHOR_SEL).count()
                if new_total > total or clicked:
                    stagnant_loops = 0

                if stagnant_loops >= 4:
                    print(f"No more growth after {stagnant_loops} loops. Stopping.")
                    break
        finally:
            if conn is not None:
                conn.close()
            await browser.close()

        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
