"""ESPN Fantasy Basketball liginden ham veriyi çeker ve data/raw/ altına yazar."""
import datetime, json, os, pathlib, urllib.request

LEAGUE_ID = os.environ.get("ESPN_LEAGUE_ID", "1540046349")
BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/segments/0/leagues/{league}"
VIEWS = {
    "league": ["mSettings", "mTeam", "mStatus"],
    "matchups": ["mMatchupScore", "mMatchup"],
    "transactions": ["mTransactions2"],
}


def current_season(today=None):
    today = today or datetime.date.today()
    return today.year + 1 if today.month >= 7 else today.year


def get(season, views):
    url = BASE.format(season=season, league=LEAGUE_ID) + "?" + "&".join(f"view={v}" for v in views)
    req = urllib.request.Request(url, headers={"User-Agent": "nbafan-stats"})
    cookies = {k: os.environ.get(k.upper()) for k in ("espn_s2", "swid")}
    if all(cookies.values()):
        req.add_header("Cookie", f"espn_s2={cookies['espn_s2']}; SWID={cookies['swid']}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    season = int(os.environ.get("SEASON") or current_season())
    out = pathlib.Path("data/raw") / str(season)
    out.mkdir(parents=True, exist_ok=True)
    for name, views in VIEWS.items():
        (out / f"{name}.json").write_text(json.dumps(get(season, views), ensure_ascii=False))
        print(f"{season} {name} ok")


if __name__ == "__main__":
    main()
