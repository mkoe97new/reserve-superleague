"""
Scrapes the Reserve-Superleague friendly-match fixtures from wfv.at and writes
the result to data/games.json, grouped into matchdays ("Spieltage") per the
rules in business_logic/webscraping_games.txt.

Usage:
    python scripts/scrape_games.py

Requires:
    pip install playwright beautifulsoup4 lxml
    python -m playwright install chromium

The source pages sit behind an Anubis JS proof-of-work challenge, so a plain
HTTP client can't reach the real markup - a headless browser is required to
run the challenge script like a normal visitor would.
"""

import json
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SOURCE_URLS = [
    "https://wfv.at/wfv/Bewerb/Freundschaftsspiele/232588?DSG-Reserve-A",
    "https://wfv.at/wfv/Bewerb/Freundschaftsspiele/232589?DSG-Reserve-B",
]

ROUNDS = [
    (1, date(2026, 11, 6), date(2026, 11, 12)),
    (2, date(2026, 11, 13), date(2026, 11, 19)),
    (3, date(2026, 11, 20), date(2026, 11, 26)),
]

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "games.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*\|\s*(\d{2}:\d{2})")
TEAM_TAG_RE = re.compile(r"\b(dsg|res|1b)\b", re.IGNORECASE)


def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        return html


def clean_team_name(name: str) -> str:
    cleaned = TEAM_TAG_RE.sub("", name)
    return re.sub(r"\s+", " ", cleaned).strip()


def round_for_date(game_date: date):
    for round_no, start, end in ROUNDS:
        if start <= game_date <= end:
            return round_no
    return None


def parse_games(html: str):
    soup = BeautifulSoup(html, "lxml")
    games = []

    for row in soup.select("tr.spielplanErgebnisseBody"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue

        date_strong = tds[0].find("strong")
        if not date_strong:
            continue
        match = DATE_RE.search(date_strong.get_text(strip=True))
        if not match:
            continue
        day, month, year, time_str = match.groups()
        game_date = date(int(year), int(month), int(day))

        round_no = round_for_date(game_date)
        if round_no is None:
            continue

        team_links = tds[0].select("div.c1_teams a[href]")
        if len(team_links) < 2:
            continue
        home = clean_team_name(team_links[0].get_text(strip=True))
        away = clean_team_name(team_links[1].get_text(strip=True))

        result_strong = tds[1].find("strong")
        result = result_strong.get_text(strip=True) if result_strong else "-:-"

        games.append({
            "round": round_no,
            "date": game_date.isoformat(),
            "time": time_str,
            "home": home,
            "away": away,
            "result": result if result and result != "-:-" else None,
        })

    return games


def dedupe(games):
    seen = set()
    unique = []
    for game in games:
        key = (game["date"], game["time"], game["home"], game["away"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(game)
    return unique


def main():
    all_games = []
    for url in SOURCE_URLS:
        html = fetch_rendered_html(url)
        all_games.extend(parse_games(html))

    unique_games = dedupe(all_games)
    unique_games.sort(key=lambda g: (g["round"], g["date"], g["time"]))

    rounds = []
    for round_no, _, _ in ROUNDS:
        round_games = [g for g in unique_games if g["round"] == round_no]
        if not round_games:
            continue
        rounds.append({
            "round": round_no,
            "label": f"Spieltag {round_no}",
            "games": [
                {
                    "date": g["date"],
                    "time": g["time"],
                    "home": g["home"],
                    "away": g["away"],
                    "result": g["result"],
                }
                for g in round_games
            ],
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"rounds": rounds}, f, ensure_ascii=False, indent=2)

    total = sum(len(r["games"]) for r in rounds)
    print(f"Wrote {total} game(s) across {len(rounds)} matchday(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
