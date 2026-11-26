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
    try:  # sahipliği en hızlı artan serbest oyuncular (waiver radarı)
        hot = {"players": {**FA_FILTER["players"], "limit": 100, "sortPercOwned": None,
                           "sortPercChanged": {"sortPriority": 1, "sortAsc": False}}}
        hot["players"].pop("sortPercOwned")
        fh = get(season, ["kona_player_info"], {"x-fantasy-filter": json.dumps(hot)}, f"&scoringPeriodId={sp}")
        (out / "freeagents_hot.json").write_text(json.dumps(fh, ensure_ascii=False))
        print(f"{season} yükselen serbest oyuncular ok: {len(fh.get('players', []))}")
    except Exception as e:
        print(f"{season} yükselen serbest oyuncular alınamadı: {e}")
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}?view=proTeamSchedules_wl"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nbafan-stats"}), timeout=60) as r:
        (out / "proschedule.json").write_text(r.read().decode())
    print(f"{season} NBA takvimi ok")
    try:
        fetch_daily(season, league)
    except Exception as e:  # eğlenceli istatistikler olmadan da site üretilsin
        print(f"{season} günlük veri alınamadı: {e}")
    fetch_history(league)


CACHE_V = 2
# günlük kutu skorlarından saklanan istatistikler (sıra önemli)
GSTATS = ["0", "6", "3", "2", "1", "17", "11", "13", "14", "15", "16", "40"]


def game_line(player, sp, season=None):
    for st in player.get("stats", []):
        if st.get("statSourceId") == 0 and st.get("statSplitTypeId") == 5 and st.get("scoringPeriodId") == sp \
                and (season is None or st.get("seasonId") == season):
            v = st.get("stats") or {}
            if v.get("40", 0) or v.get("14", 0) or v.get("0", 0):
                return [round(v.get(k, 0), 1) for k in GSTATS]
    return None


def fetch_daily(season, league):
    """Her gün için kadro (hangi slotta) + o günkü istatistik, işlemler, draft ve oyuncu maç kayıtları.
    Biten günler data/daily/<sezon>.json içinde saklanır, sadece eksik günler çekilir."""
    path = pathlib.Path("data/daily") / f"{season}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(path.read_text()) if path.exists() else {}
    if cache.get("v") != CACHE_V:  # biçim değişti: her günü yeniden çek
        cache = {"v": CACHE_V}
    days, tx, meta = cache.setdefault("days", {}), cache.setdefault("tx", {}), cache.setdefault("players", {})
    st = league.get("status", {})
    first, latest = st.get("firstScoringPeriod", 1), st.get("latestScoringPeriod", 1)
    if st.get("finalScoringPeriod"):
        latest = min(latest, st["finalScoringPeriod"])
    done = not st.get("isActive", True) or season < current_season()
    n = 0
    for sp in range(first, latest + 1):
        if str(sp) in days and (done or sp < latest - 1):
            continue
        d = get(season, ["mBoxscore", "mTransactions2"], query=f"&scoringPeriodId={sp}")
        day = {}
        for m in d.get("schedule", []):
            for side in ("home", "away"):
                t = m.get(side) or {}
                ents = (t.get("rosterForCurrentScoringPeriod") or {}).get("entries")
                if not ents:
                    continue
                rows = []
                for e in ents:
                    pl = e["playerPoolEntry"]["player"]
                    meta[str(pl["id"])] = [pl.get("fullName", ""), pl.get("proTeamId", 0),
                                           [x for x in pl.get("eligibleSlots", []) if x <= 6 or x == 11],
                                           pl.get("injuryStatus", "")]
                    rows.append([pl["id"], e.get("lineupSlotId"), game_line(pl, sp)])
                day[str(t["teamId"])] = rows
        if day:
            days[str(sp)] = day
        for x in d.get("transactions", []):
            ok = x.get("status") == "EXECUTED" and x.get("type") in ("FREEAGENT", "WAIVER", "TRADE_UPHOLD")
            # onaylanan takasın kabul kaydının durumu boş gelir; içinde yer açmak için yapılan bırakmalar var
            ok = ok or (x.get("type") == "TRADE_ACCEPT" and x.get("status") in (None, "EXECUTED"))
            if not ok:
                continue
            items = [[i["type"], i["playerId"], i.get("fromTeamId", 0), i.get("toTeamId", 0)] for i in x.get("items", [])
                     if i.get("type") in ("ADD", "DROP", "TRADE")]
            if items:
                tx[x["id"]] = {"type": x["type"], "sp": x.get("scoringPeriodId", sp), "date": x.get("proposedDate"),
                               "team": x.get("teamId"), "items": items}
        n += 1
    if "draft" not in cache or not cache["draft"]:
        dd = get(season, ["mDraftDetail"]).get("draftDetail", {})
        cache["draft"] = [[p["overallPickNumber"], p["roundId"], p["teamId"], p["playerId"]] for p in dd.get("picks", [])]
    path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")))
    print(f"{season} günlük veri ok: {n} gün çekildi, toplam {len(days)} gün, {len(tx)} işlem")
    # oyuncu maç kayıtları (bırakılan / takas edilen / draft edilen herkes)
    ids = {p[3] for p in cache["draft"]} | {int(k) for k in meta}
    ids |= {i[1] for x in tx.values() for i in x["items"]}
    logs = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 60):
        f = {"players": {"filterIds": {"value": ids[i:i + 60]},
                         "filterStatsForTopScoringPeriodIds": {"value": 200, "additionalValue": [f"00{season}"]}}}
        d = get(season, ["kona_playercard"], {"x-fantasy-filter": json.dumps(f)})
        for p in d.get("players", []):
            pl = p["player"]
            meta.setdefault(str(pl["id"]), [pl.get("fullName", ""), pl.get("proTeamId", 0),
                                            [x for x in pl.get("eligibleSlots", []) if x <= 6 or x == 11],
                                            pl.get("injuryStatus", "")])
            g = {}
            for s in pl.get("stats", []):
                if s.get("statSplitTypeId") == 5 and s.get("seasonId") == season and s.get("statSourceId") == 0:
                    v = s.get("stats") or {}
                    if v.get("40", 0) or v.get("14", 0):
                        g[str(s["scoringPeriodId"])] = [round(v.get(k, 0), 1) for k in GSTATS]
            logs[str(pl["id"])] = g
    out = pathlib.Path("data/raw") / str(season)
    (out / "gamelogs.json").write_text(json.dumps(logs, separators=(",", ":")))
    path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")))
    print(f"{season} maç kayıtları ok: {len(logs)} oyuncu")


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
            url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{y}?view=proTeamSchedules_wl"
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nbafan-stats"}), timeout=60) as r:
                (out / "proschedule.json").write_text(r.read().decode())
            fetch_daily(y, json.loads((out / "league.json").read_text()))
        except Exception as e:  # çerez yoksa ya da ESPN izin vermezse
            print(f"{y} geçmiş sezon alınamadı: {e}")


if __name__ == "__main__":
    main()
