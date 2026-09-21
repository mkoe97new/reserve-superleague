"""
Scrapes the Reserve-Superleague friendly-match fixtures from wfv.at and writes
the result to data/games.json, grouped into matchdays ("Spieltage") per the
rules in business_logic/webscraping_games.txt. Also scrapes the goal scorers
of each played match per business_logic/goal_scorers.txt.

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
    # TEMPORARY test round to exercise the goal-scorer scraping against
    # already-played matches - remove once real Nov 2026 results exist.
    (4, date(2026, 8, 29), date(2026, 8, 31)),
]

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "games.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*\|\s*(\d{2}:\d{2})")
TEAM_TAG_RE = re.compile(r"\b(dsg|res|1b)\b", re.IGNORECASE)


def fetch_rendered_html(page, url: str, wait_selector: str) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector(wait_selector, timeout=30000)
    except Exception:
        pass
    return page.content()


def clean_team_name(name: str) -> str:
    cleaned = TEAM_TAG_RE.sub("", name)
    return re.sub(r"\s+", " ", cleaned).strip()


def round_for_date(game_date: date):
    for round_no, start, end in ROUNDS:
        if start <= game_date <= end:
            return round_no
    return None


def scorer_link(tds):
    """Third <td> holds a div.links whose <a href> points to the match report,
    unless it is still a "Vorbericht" (preview), meaning the game hasn't been played."""
    if len(tds) < 3:
        return None
    links_div = tds[2].find("div", class_="links")
    if not links_div:
        return None
    if links_div.find(attrs={"title": "Vorbericht"}):
        return None
    link = links_div.find("a", href=True)
    return link["href"] if link else None


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
            "scorer_link": scorer_link(tds),
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


def club_names(soup):
    """The two clubs sit in the two divs of div.head_2_head_teams, each in a
    <span>, in the same home/away order as the fixture list."""
    head_2_head = soup.find("div", class_="head_2_head_teams")
    if not head_2_head:
        return None, None
    club_divs = head_2_head.find_all("div", recursive=False)
    if len(club_divs) < 2:
        return None, None

    def name_of(div):
        span = div.find("span")
        return clean_team_name(span.get_text(strip=True)) if span else None

    return name_of(club_divs[0]), name_of(club_divs[1])


def scorer_name(cell):
    """A goal cell has exactly two direct <span> children; whichever one
    holds the <a> (its position mirrors depending on the home/away column)
    contains the player name."""
    spans = cell.find_all("span", recursive=False)
    if len(spans) != 2:
        return None
    for span in spans:
        link = span.find("a")
        if link:
            return link.get_text(strip=True)
    return None


def parse_scorers(html: str):
    """Walks div.chronologisch and pairs each goal (football-icon.png) with
    the scorer name in the cell right before it (home club) and right after
    it (away club)."""
    soup = BeautifulSoup(html, "lxml")
    home_club, away_club = club_names(soup)

    chronologisch = soup.find("div", class_="chronologisch")
    if not chronologisch:
        return []

    cells = chronologisch.select("div.game_report_by_events_grid_2 > div")
    if not cells:
        cells = chronologisch.find_all("div", recursive=False)

    scorers = []
    for index, cell in enumerate(cells):
        img = cell.find("img")
        if not img or "football-icon.png" not in (img.get("src") or ""):
            continue

        if index > 0 and home_club:
            name = scorer_name(cells[index - 1])
            if name:
                scorers.append([name, home_club])

        if index < len(cells) - 1 and away_club:
            name = scorer_name(cells[index + 1])
            if name:
                scorers.append([name, away_club])

    return scorers


def attach_scorers(page, games):
    for game in games:
        link = game.pop("scorer_link", None)
        if not link:
            game["scorers"] = []
            continue
        html = fetch_rendered_html(page, link, ".chronologisch")
        game["scorers"] = parse_scorers(html)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        all_games = []
        for url in SOURCE_URLS:
            html = fetch_rendered_html(page, url, "tr.spielplanErgebnisseBody")
            all_games.extend(parse_games(html))

        unique_games = dedupe(all_games)
        unique_games.sort(key=lambda g: (g["round"], g["date"], g["time"]))

        attach_scorers(page, unique_games)

        browser.close()

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
                    "scorers": g["scorers"],
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
