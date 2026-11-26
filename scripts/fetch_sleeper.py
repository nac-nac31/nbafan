"""Sleeper NBA liginin verisini çeker ve motorun okuduğu ESPN biçimine çevirir (data/raw/<sezon>/).

Kullanım:  SLEEPER_LEAGUE_ID=<id> python scripts/fetch_sleeper.py
Sonra:     python scripts/build.py   (SEASON otomatik; Sleeper 2026 sezonu = ESPN'deki 2027)

Sleeper herkese açık bir API kullanır, giriş gerekmez. Sleeper NBA ligleri puanlıdır (H2H Points).
Günlük kadro verisi olmadığı için eğlence sayfası ve haftalık maç tahmini Sleeper liglerinde yok.
"""
import json, os, pathlib, urllib.request

API = "https://api.sleeper.app/v1/"
# Sleeper istatistik anahtarı -> ESPN istatistik ID'si
STAT = {"pts": 0, "blk": 1, "stl": 2, "ast": 3, "oreb": 4, "dreb": 5, "reb": 6, "to": 11, "fgm": 13, "fga": 14,
        "ftm": 15, "fta": 16, "tpm": 17, "tpa": 18, "dd": 37, "td": 38}
SLOT = {"PG": 0, "SG": 1, "SF": 2, "PF": 3, "C": 4, "G": 5, "F": 6, "UTIL": 11, "BN": 12}
POS = {"PG": 1, "SG": 2, "SF": 3, "PF": 4, "C": 5}
INJ = {"Out": "OUT", "Questionable": "DAY_TO_DAY", "Doubtful": "DAY_TO_DAY", "Sus": "SUSPENSION", "IR": "INJURY_RESERVE"}


def get(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "nbafan-stats"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def per_game(tot):
    gp = tot.get("gp") or 0
    if not gp:
        return {}
    avg = {str(e): tot.get(k, 0) / gp for k, e in STAT.items()}
    avg["42"] = gp
    avg["40"] = tot.get("min", 0) / gp
    return avg


def player_obj(pid, meta, season_tot, proj, espn_season, owned):
    m = meta.get(pid) or {}
    stats = []
    s = per_game(season_tot.get(pid) or {})
    if s:
        stats.append({"id": f"00{espn_season}", "averageStats": s})
    p = proj.get(pid) or {}
    if p.get("gp"):
        stats.append({"id": f"10{espn_season}", "averageStats": per_game(p)})
    pos = (m.get("fantasy_positions") or m.get("position") and [m["position"]] or [""])[0]
    return {"id": int(pid), "fullName": m.get("full_name") or f"{m.get('first_name', '')} {m.get('last_name', '')}".strip() or pid,
            "defaultPositionId": POS.get(pos, 0), "injuryStatus": INJ.get(m.get("injury_status") or "", "ACTIVE"),
            "proTeamId": m.get("team") or 0, "ownership": {"percentOwned": owned}, "stats": stats}


def main():
    lid = os.environ["SLEEPER_LEAGUE_ID"]
    L = get(f"league/{lid}")
    if L.get("sport") != "nba":
        raise SystemExit(f"Bu bir Sleeper NBA ligi değil: {L.get('sport')}")
    state = get("state/nba")
    season = L["season"]
    espn_season = int(season) + 1
    st = L["settings"]
    users = {u["user_id"]: u for u in get(f"league/{lid}/users")}
    rosters = get(f"league/{lid}/rosters")
    meta = get("players/nba")
    season_tot = get(f"stats/nba/regular/{season}")
    cur_week = state.get("week") if L["status"] == "in_season" and state.get("season") == season else 0
    try:
        proj = {}
        if cur_week:
            proj = get(f"projections/nba/regular/{season}/{cur_week}")
    except Exception:
        proj = {}
    out = pathlib.Path("data/raw") / str(espn_season)
    out.mkdir(parents=True, exist_ok=True)

    # --- lig ayarları ve takımlar (ESPN mSettings + mTeam biçimi)
    counts = {}
    for p in L.get("roster_positions") or []:
        k = str(SLOT.get(p, 11))
        counts[k] = counts.get(k, 0) + 1
    counts["13"] = st.get("reserve_slots", 0)
    items = [{"statId": STAT[k], "points": v} for k, v in (L.get("scoring_settings") or {}).items() if k in STAT and v]
    teams = []
    for r in rosters:
        u = users.get(r.get("owner_id")) or {}
        name = ((u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Takım {r['roster_id']}").strip()
        teams.append({"id": r["roster_id"], "name": name, "abbrev": "".join(w[0] for w in name.split()[:3]).upper(),
                      "logo": f"https://sleepercdn.com/avatars/thumbs/{u['avatar']}" if u.get("avatar") else "",
                      "primaryOwner": r.get("owner_id") or f"roster-{r['roster_id']}",
                      "transactionCounter": {}})
    reg_weeks = (st.get("playoff_week_start") or 22) - 1
    league = {
        "id": lid, "seasonId": espn_season, "source": "sleeper",
        "settings": {"name": L.get("name", "Sleeper ligi"), "size": L.get("total_rosters"),
                     "scoringSettings": {"scoringType": "H2H_POINTS", "scoringItems": items},
                     "rosterSettings": {"lineupSlotCounts": counts},
                     "scheduleSettings": {"matchupPeriodCount": reg_weeks, "playoffTeamCount": st.get("playoff_teams"),
                                          "matchupPeriodLength": 1, "playoffSeedingRule": "H2H_RECORD"}},
        "status": {"currentMatchupPeriod": cur_week, "latestScoringPeriod": cur_week, "previousSeasons": [],
                   "isActive": L["status"] == "in_season"},
        "teams": teams,
    }
    (out / "league.json").write_text(json.dumps(league, ensure_ascii=False))

    # --- maçlar (ESPN mMatchup biçimi): oynanmış, devam eden ve gelecek normal sezon haftaları
    sched = []
    for w in range(1, reg_weeks + 1):
        try:
            ms = get(f"league/{lid}/matchups/{w}")
        except Exception:
            break
        if not ms:
            break
        pairs = {}
        for m in ms:
            if m.get("matchup_id") is not None:
                pairs.setdefault(m["matchup_id"], []).append(m)
        for mid, pr in sorted(pairs.items()):
            if len(pr) != 2:
                continue
            h, a = pr
            side = lambda m: {"teamId": m["roster_id"], "totalPoints": m.get("points") or 0,
                              "cumulativeScore": {"scoreByStat": {"0": {"score": m.get("points") or 0}}}}
            done = cur_week and w < cur_week
            hp, ap = h.get("points") or 0, a.get("points") or 0
            winner = ("HOME" if hp > ap else "AWAY" if ap > hp else "TIE") if done else "UNDECIDED"
            sched.append({"id": len(sched) + 1, "matchupPeriodId": w, "playoffTierType": "NONE", "winner": winner,
                          "home": side(h), "away": side(a)})
    (out / "matchups.json").write_text(json.dumps({"schedule": sched}))

    # --- kadrolar ve serbest oyuncular
    rostered = set()
    rteams = []
    for r in rosters:
        starters, reserve = set(r.get("starters") or []), set(r.get("reserve") or [])
        entries = []
        for pid in r.get("players") or []:
            rostered.add(pid)
            slot = 11 if pid in starters else 13 if pid in reserve else 12
            entries.append({"playerId": int(pid), "lineupSlotId": slot,
                            "playerPoolEntry": {"player": player_obj(pid, meta, season_tot, proj, espn_season, 100.0)}})
        rteams.append({"id": r["roster_id"], "roster": {"entries": entries}})
    (out / "rosters.json").write_text(json.dumps({"teams": rteams}))
    pool = sorted((pid for pid, s in season_tot.items() if pid not in rostered and pid.isdigit() and (s or {}).get("gp")),
                  key=lambda pid: -(season_tot[pid].get("pts", 0) / max(1, season_tot[pid].get("gp", 1))))[:200]
    fa = [{"player": player_obj(pid, meta, season_tot, proj, espn_season, 0.0), "status": "FREEAGENT"} for pid in pool]
    (out / "freeagents.json").write_text(json.dumps({"players": fa}))
    print(f"Sleeper {L.get('name')}: {len(teams)} takım, {len(sched)} maç, {len(rostered)} kadrolu oyuncu, {len(fa)} serbest")
    print(f"SEASON={espn_season}")


if __name__ == "__main__":
    main()
