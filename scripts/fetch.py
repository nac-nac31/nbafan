"""ESPN Fantasy Basketball liginden ham veriyi çeker ve data/raw/ altına yazar."""
import datetime, json, os, pathlib, urllib.request

LEAGUE_ID = os.environ.get("ESPN_LEAGUE_ID", "1540046349")
BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/segments/0/leagues/{league}"
VIEWS = {
    "league": ["mSettings", "mTeam", "mStatus"],
    "matchups": ["mMatchupScore", "mMatchup"],
    "transactions": ["mTransactions2"],
    "rosters": ["mRoster"],
}
FA_FILTER = {"players": {"filterStatus": {"value": ["FREEAGENT", "WAIVERS"]}, "limit": 200,
                         "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}


def current_season(today=None):
    today = today or datetime.date.today()
    return today.year + 1 if today.month >= 7 else today.year


def get(season, views, extra_headers=None, query=""):
    url = BASE.format(season=season, league=LEAGUE_ID) + "?" + "&".join(f"view={v}" for v in views) + query
    req = urllib.request.Request(url, headers={"User-Agent": "nbafan-stats", **(extra_headers or {})})
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
    league = json.loads((out / "league.json").read_text())
    sp = league.get("scoringPeriodId") or league.get("status", {}).get("latestScoringPeriod", 1)
    fa = get(season, ["kona_player_info"], {"x-fantasy-filter": json.dumps(FA_FILTER)}, f"&scoringPeriodId={sp}")
    (out / "freeagents.json").write_text(json.dumps(fa, ensure_ascii=False))
    print(f"{season} serbest oyuncular ok: {len(fa.get('players', []))}")
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}?view=proTeamSchedules_wl"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nbafan-stats"}), timeout=60) as r:
        (out / "proschedule.json").write_text(r.read().decode())
    print(f"{season} NBA takvimi ok")
    fetch_history(league)


def fetch_history(league):
    """Geçmiş sezonlar: ESPN çerezleri (ESPN_S2, SWID) gerekir."""
    for y in league.get("status", {}).get("previousSeasons", []):
        out = pathlib.Path("data/raw") / str(y)
        out.mkdir(parents=True, exist_ok=True)
        try:
            for name, views in (("league", VIEWS["league"]), ("matchups", VIEWS["matchups"])):
                d = get(y, views)
                (out / f"{name}.json").write_text(json.dumps(d, ensure_ascii=False))
            print(f"{y} geçmiş sezon ok: {len(d.get('schedule', []))} maç")
        except Exception as e:  # çerez yoksa ya da ESPN izin vermezse
            print(f"{y} geçmiş sezon alınamadı: {e}")


if __name__ == "__main__":
    main()
