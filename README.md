Reserve Superleague Website Project

## Updating the fixture list

The "Spiele" tab on `standings.html` is populated from `data/games.json`. To refresh it with the latest fixtures from wfv.at:

```
pip install -r scripts/requirements.txt
python -m playwright install chromium
python scripts/scrape_games.py
```

Commit and push the updated `data/games.json` to publish the changes.
