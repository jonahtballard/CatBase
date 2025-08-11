#!/usr/bin/env python3
"""
Reusable parser for a single RateMyProfessors *professor page* HTML.

Usage (example):
    from rmp_profile_parser import parse_professor_page, load_html

    html = load_html("/path/to/local/ProfessorPage.html")  # or from requests.get(url).text
    data = parse_professor_page(html)
    print(data)

Notes:
- Uses robust "class contains" selectors so it survives RMP's hashed CSS classnames.
- Tries multiple fallbacks and returns None/empty for missing bits instead of crashing.
- You can safely call parse_* helpers individually if you want to customize.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


# -------------------------- small utils --------------------------

def _sel_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    el = soup.select_one(selector)
    if not el:
        return None
    txt = el.get_text(strip=True)
    return txt or None

def _to_float(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except:
        # pull the first number like "4.9 / 5" or "99%"
        m = re.search(r"\d+(?:\.\d+)?", x)
        if m:
            try:
                return float(m.group(0))
            except:
                return None
        return None

def _to_int(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    # extract the first integer in the text
    m = re.search(r"\d+", x.replace(",", ""))
    return int(m.group(0)) if m else None

def load_html(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------- main pieces --------------------------

def parse_canonical_url(soup: BeautifulSoup) -> Optional[str]:
    el = soup.select_one('link[rel="canonical"]')
    return el.get("href") if el and el.get("href") else None

def parse_prof_ids(soup: BeautifulSoup) -> Dict[str, Optional[int]]:
    """
    Try to find:
    - legacyId (integer in /professor/<id>, /compare/professors/<id>, /add/professor-rating/<id>)
    - school legacy id (in /school/<id> or search URL)
    """
    html = str(soup)

    # professor legacyId
    for pat in [
        r"/professor/(\d+)",
        r"/compare/professors/(\d+)",
        r"/add/professor-rating/(\d+)",
    ]:
        m = re.search(pat, html)
        if m:
            prof_id = int(m.group(1))
            break
    else:
        prof_id = None

    # school id
    ms = re.search(r"/school/(\d+)", html) or re.search(r"/search/professors/(\d+)", html)
    school_id = int(ms.group(1)) if ms else None

    return {"professor_legacy_id": prof_id, "school_legacy_id": school_id}

def parse_header_block(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Name, department, school, avg rating, num ratings, would-take-again, difficulty.
    """
    name = _sel_text(soup, '*[class*="NameTitle__NameWrapper"] h1') \
        or _sel_text(soup, '*[class*="HeaderDescription__NameWrapper"]') \
        or _sel_text(soup, '*[class*="MiniStickyHeader__MiniNameWrapper"]')

    # department + school
    department = _sel_text(soup, 'a[class*="TeacherDepartment__StyledDepartmentLink"]') \
        or _sel_text(soup, '*[class*="TeacherTitles__StyledDepartmentName"]')
    school = _sel_text(soup, 'a[href*="/school/"]')

    # avg rating numerator like "4.9"
    avg_rating = _to_float(
        _sel_text(soup, '*[class*="RatingValue__Numerator"]')
    )

    # num ratings in "Overall Quality Based on 53 ratings"
    num_ratings = _to_int(
        _sel_text(soup, '*[class*="RatingValue__NumRatings"]')
    )

    # feedback row: would take again & difficulty
    # Typically layout shows two items with number then label
    feedback_numbers = soup.select('*[class*="TeacherFeedback"] *[class*="FeedbackItem"] *[class*="FeedbackNumber"]')
    feedback_labels  = soup.select('*[class*="TeacherFeedback"] *[class*="FeedbackItem"] *[class*="FeedbackDescription"]')

    would_take_again = None
    difficulty = None
    if feedback_numbers and feedback_labels and len(feedback_numbers) == len(feedback_labels):
        for n_el, l_el in zip(feedback_numbers, feedback_labels):
            n_txt = n_el.get_text(strip=True)
            l_txt = l_el.get_text(strip=True).lower()
            if "would take again" in l_txt:
                would_take_again = _to_float(n_txt)  # typically percent like "99%"
            elif "difficulty" in l_txt:
                difficulty = _to_float(n_txt)

    return {
        "name": name,
        "department": department,
        "school": school,
        "avg_rating": avg_rating,
        "num_ratings": num_ratings,
        "would_take_again_percent": would_take_again,
        "difficulty": difficulty,
    }

def parse_top_tags(soup: BeautifulSoup) -> List[str]:
    tags = []
    for el in soup.select('*[class*="TeacherTags__TagsContainer"] span[class*="Tag-"]'):
        t = el.get_text(strip=True)
        if t:
            tags.append(t)
    # fallback (older/newer variants)
    if not tags:
        for el in soup.select('span[class*="Tag-"]'):
            t = el.get_text(strip=True)
            if t:
                tags.append(t)
    return tags

def parse_rating_distribution(soup: BeautifulSoup) -> Dict[str, Optional[int]]:
    """
    Reads the sidebar distribution list if present.
    Returns counts per bucket: awesome/great/good/ok/awful (not percentages).
    """
    dist = {"awesome": None, "great": None, "good": None, "ok": None, "awful": None}
    wrapper = soup.select_one('*[class*="RatingDistributionChart__MeterList"]')
    if not wrapper:
        return dist

    # li entries contain a label and a bold number at the end
    for li in wrapper.select('li'):
        label = _sel_text(li, '*[class*="RatingDistributionChart__LabelText"]') or ""
        count_txt = _sel_text(li, 'b') or _sel_text(li, '*[class*="LabelValue"]')
        count = _to_int(count_txt)
        key = label.lower().strip()
        if "awesome" in key:
            dist["awesome"] = count
        elif "great" in key:
            dist["great"] = count
        elif "good" in key:
            dist["good"] = count
        elif key in ("ok", "okay"):
            dist["ok"] = count
        elif "awful" in key:
            dist["awful"] = count
    return dist

def parse_similar_professors(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in soup.select('*[class*="SimilarProfessors"] a[href*="/professor/"]'):
        url = a.get("href") or ""
        name = _sel_text(a, '*[class*="TeacherNameSpan"]') or _sel_text(a, '*[class*="SimilarProfessorListItem"]')
        score = _to_float(_sel_text(a, '*[class*="TeacherScoreSpan"]'))
        m = re.search(r"/professor/(\d+)", url)
        legacy_id = int(m.group(1)) if m else None
        if name:
            out.append({
                "name": name,
                "legacy_id": legacy_id,
                "score": score,
                "url": f"https://www.ratemyprofessors.com{url}" if url.startswith("/") else url or None,
            })
    return out

def _parse_rating_meta(li: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract "For Credit: Yes", "Attendance: Mandatory" ... into a dict.
    """
    meta: Dict[str, Optional[str]] = {}
    for el in li.select('*[class*="CourseMeta"] *[class*="MetaItem"]'):
        txt = el.get_text(" ", strip=True)
        if ":" in txt:
            k, v = [t.strip() for t in txt.split(":", 1)]
            meta[k] = v if v else None
    return meta

def parse_student_ratings(soup: BeautifulSoup, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Parse the ratings list (course, date, quality/difficulty, comment, tags, meta, thumbs).
    """
    results: List[Dict[str, Any]] = []
    ul = soup.select_one('ul#ratingsList') or soup.select_one('*[id*="ratingsList"]')
    if not ul:
        return results

    items = ul.select('li div[class*="Rating__StyledRating"]')
    if not items:
        # fallback: each li might just be a rating item
        items = ul.select('li')

    for li in items:
        course = _sel_text(li, '*[class*="RatingHeader__StyledClass"]')
        date   = _sel_text(li, '*[class*="RatingHeader__RatingTimeStamp"]')

        # quality & difficulty numbers
        q = li.select('*[class*="CardNumRating__CardNumRatingHeader"]')
        n = li.select('*[class*="CardNumRating__CardNumRatingNumber"]')
        quality = None
        difficulty = None
        if q and n and len(q) == len(n):
            for header_el, num_el in zip(q, n):
                htxt = header_el.get_text(strip=True).lower()
                val  = _to_float(num_el.get_text(strip=True))
                if "quality" in htxt:
                    quality = val
                elif "difficulty" in htxt:
                    difficulty = val

        comment = _sel_text(li, '*[class*="Comments__StyledComments"]')

        # rating tags inside a single rating
        rtags: List[str] = []
        for tg in li.select('*[class*="RatingTags"] span[class*="Tag-"]'):
            tt = tg.get_text(strip=True)
            if tt:
                rtags.append(tt)

        # meta (For Credit, Attendance, Grade, etc.)
        meta = _parse_rating_meta(li)

        # thumbs helpful counts (optional)
        thumbs_up = _to_int(_sel_text(li, '#thumbs_up ~ *')) \
            or _to_int(_sel_text(li, '*[id*="thumbs_up"] ~ *'))
        thumbs_down = _to_int(_sel_text(li, '#thumbs_down ~ *')) \
            or _to_int(_sel_text(li, '*[id*="thumbs_down"] ~ *'))

        results.append({
            "course": course,
            "date": date,
            "quality": quality,
            "difficulty": difficulty,
            "comment": comment,
            "tags": rtags,
            "meta": meta,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
        })

        if limit and len(results) >= limit:
            break

    return results

def parse_links(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    rate = None
    compare = None
    rate_a = soup.select_one('a[href*="/add/professor-rating/"]')
    comp_a = soup.select_one('a[href*="/compare/professors/"]')
    if rate_a and rate_a.get("href"):
        h = rate_a.get("href")
        rate = f"https://www.ratemyprofessors.com{h}" if h.startswith("/") else h
    if comp_a and comp_a.get("href"):
        h = comp_a.get("href")
        compare = f"https://www.ratemyprofessors.com{h}" if h.startswith("/") else h
    return {
        "profile_url": parse_canonical_url(soup),
        "rate_url": rate,
        "compare_url": compare,
    }

def parse_relay_json(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Optional: RMP often hydrates data into window.__RELAY_STORE__ or __NEXT_DATA__.
    We sniff basic fields if present. All keys are optional.
    """
    data: Dict[str, Any] = {}
    # __NEXT_DATA__
    nxt = soup.find("script", id="__NEXT_DATA__", type="application/json")
    if nxt and nxt.string:
        try:
            obj = json.loads(nxt.string)
            data["__next_data__"] = obj
        except Exception:
            pass

    # window.__RELAY_STORE__ (requires a JS assignment parse; we extract JSON-ish part)
    for script in soup.find_all("script"):
        if script.string and "window.__RELAY_STORE__" in script.string:
            m = re.search(r"window\.__RELAY_STORE__\s*=\s*(\{.*\});", script.string, flags=re.S)
            if m:
                raw = m.group(1)
                try:
                    # Very rough sanitize: remove trailing semicolon and parse JSON.
                    # The content *should* be valid JSON as shipped by RMP.
                    data["__relay_store__"] = json.loads(raw)
                except Exception:
                    pass
            break
    return data


# -------------------------- public API --------------------------

def parse_professor_page(html: str, ratings_limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Parse a single professor page HTML and return a structured dict of interesting fields.
    """
    soup = BeautifulSoup(html, "html.parser")

    ids = parse_prof_ids(soup)
    header = parse_header_block(soup)
    tags = parse_top_tags(soup)
    dist = parse_rating_distribution(soup)
    similar = parse_similar_professors(soup)
    ratings = parse_student_ratings(soup, limit=ratings_limit)
    links = parse_links(soup)

    # Try to include helpful raw JSON blocks if you want to mine more later (optional)
    relay_bits = parse_relay_json(soup)

    return {
        **ids,
        **header,
        "top_tags": tags,
        "rating_distribution": dist,
        "similar_professors": similar,
        "ratings": ratings,
        "links": links,
        # raw (optional)
        "raw": {
            k: v for k, v in relay_bits.items()
        }
    }


# -------------------------- quick CLI --------------------------

if __name__ == "__main__":
    import argparse, json as _json, sys, pathlib

    p = argparse.ArgumentParser(description="Parse a RateMyProfessors professor page HTML.")
    p.add_argument("html_path", nargs="?", help="Path to a saved professor page HTML")
    p.add_argument("--limit", type=int, default=10, help="Limit number of student ratings parsed (default 10)")
    args = p.parse_args()

    if not args.html_path:
        print("Provide a path to an HTML file, e.g.: python rmp_profile_parser.py '/mnt/data/Professor.html'", file=sys.stderr)
        sys.exit(2)

    html = load_html(args.html_path)
    data = parse_professor_page(html, ratings_limit=args.limit)
    print(_json.dumps(data, indent=2, ensure_ascii=False))
