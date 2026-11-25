"""Bir ESPN basketbol liginin siteye eklenip eklenemeyeceğini kontrol eder.

Kullanım:
    python scripts/check_league.py <lig_id> [sezon]
    ESPN_S2=... SWID=... python scripts/check_league.py <lig_id>   # özel lig

Çıktı: JSON. `ok` true ise lig şu anki motorla desteklenir; değilse `reason` nedenini söyler.
Başka bir servis (form, sunucu) bu betiği ya da `inspect()` fonksiyonunu çağırarak
lig ekleme isteğini doğrulayabilir.
"""
import datetime, json, os, sys, urllib.error, urllib.request

BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}/segments/0/leagues/{league}"
STAT_NAMES = {"0": "PTS", "1": "BLK", "2": "STL", "3": "AST", "6": "REB", "11": "TO", "13": "FGM", "14": "FGA",
              "15": "FTM", "16": "FTA", "17": "3PM", "18": "3PA", "19": "FG%", "20": "FT%", "21": "3P%",
              "4": "OREB", "5": "DREB", "7": "EJ", "8": "FLAG", "9": "PF", "10": "TECH", "37": "DD", "38": "TD",
              "39": "QD", "40": "MIN", "42": "GS", "44": "GP"}
SLOT_NAMES = {"0": "PG", "1": "SG", "2": "SF", "3": "PF", "4": "C", "5": "G", "6": "F", "7": "SG/SF",
              "8": "G/F", "9": "PF/C", "10": "F/C", "11": "UTIL", "12": "BE", "13": "IR"}
# Şu anki motorun (build.py, fun.py) sabit varsaydığı ayarlar.
ENGINE_CATS = {"0", "6", "3", "2", "1", "17", "19", "20", "11"}
ENGINE_SLOTS = {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "11": 3}


def current_season(today=None):
    today = today or datetime.date.today()
    return today.year + 1 if today.month >= 7 else today.year


def fetch(league_id, season, espn_s2=None, swid=None):
    url = BASE.format(season=season, league=league_id) + "?view=mSettings&view=mTeam&view=mStatus"
    req = urllib.request.Request(url, headers={"User-Agent": "nbafan-stats"})
    if espn_s2 and swid:
        req.add_header("Cookie", f"espn_s2={espn_s2}; SWID={swid}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse_config(league):
    """mSettings yanıtından motorun ihtiyaç duyduğu lig ayarlarını çıkarır."""
    s = league["settings"]
    sc, ro, sch = s["scoringSettings"], s["rosterSettings"], s["scheduleSettings"]
    items = sc.get("scoringItems", [])
    return {
        "name": s.get("name"),
        "size": s.get("size") or len(league.get("teams", [])),
        "scoringType": sc.get("scoringType"),
        "cats": [str(i["statId"]) for i in items],
        "catNames": [STAT_NAMES.get(str(i["statId"]), str(i["statId"])) for i in items],
        "reverseCats": [str(i["statId"]) for i in items if i.get("isReverseItem")],
        "points": {str(i["statId"]): i.get("points") for i in items},
        "slots": {k: v for k, v in ro.get("lineupSlotCounts", {}).items() if v},
        "regularWeeks": sch.get("matchupPeriodCount"),
        "playoffTeams": sch.get("playoffTeamCount"),
        "playoffWeeksPerRound": sch.get("playoffMatchupPeriodLength"),
        "seeding": sch.get("playoffSeedingRule"),
        "isPublic": s.get("isPublic"),
        "previousSeasons": league.get("status", {}).get("previousSeasons", []),
    }


def support(cfg):
    """(destekleniyor mu, eksik/uyumsuz olanlar listesi)"""
    issues = []
    if cfg["scoringType"] != "H2H_CATEGORY":
        issues.append(f"puanlama türü {cfg['scoringType']} (şimdilik sadece H2H kategori)")
    if set(cfg["cats"]) != ENGINE_CATS:
        issues.append("kategoriler 9-cat değil: " + ", ".join(cfg["catNames"]))
    starters = {k: v for k, v in cfg["slots"].items() if k not in ("12", "13")}
    if starters != ENGINE_SLOTS:
        issues.append("kadro slotları farklı: " + ", ".join(f"{SLOT_NAMES.get(k, k)}×{v}" for k, v in starters.items()))
    if cfg["playoffTeams"] not in (2, 4, 6, 8):
        issues.append(f"playoff takım sayısı {cfg['playoffTeams']}")
    return not issues, issues


def inspect(league_id, season=None, espn_s2=None, swid=None):
    season = season or current_season()
    out = {"leagueId": str(league_id), "season": season}
    if not str(league_id).isdigit():
        return {**out, "ok": False, "access": "invalid", "reason": "Lig ID'si sadece rakamlardan oluşmalı."}
    try:
        league = fetch(league_id, season, espn_s2, swid)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {**out, "ok": False, "access": "private",
                    "reason": "Lig özel. Lig yöneticisi ESPN'de ligi herkese açık yapmalı "
                              "(League Settings → Basic Settings → Make League Viewable to Public) "
                              "ya da espn_s2 ve SWID çerezleri verilmeli."}
        if e.code == 404:
            return {**out, "ok": False, "access": "not_found", "reason": "Bu ID ve sezon için lig bulunamadı."}
        return {**out, "ok": False, "access": "error", "reason": f"ESPN hata verdi: HTTP {e.code}"}
    cfg = parse_config(league)
    ok, issues = support(cfg)
    return {**out, "ok": ok, "access": "cookies" if espn_s2 else "public", "config": cfg,
            "reason": None if ok else "Şu an desteklenmiyor: " + "; ".join(issues)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res = inspect(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None,
                  os.environ.get("ESPN_S2"), os.environ.get("SWID"))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res["ok"] else 1)
