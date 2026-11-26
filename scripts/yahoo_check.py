"""Yahoo bağlantı testi: anahtar çalışıyor mu, hesabın NBA ligleri neler. Gizli değer yazdırmaz."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import yahoo_api as y

y.access_token()
print("Yahoo girişi: TAMAM", "| izinler:", y.SCOPE or "?")
g = y.get("game/nba")["fantasy_content"]["game"][0]
print("NBA oyunu:", g.get("game_key"), g.get("season"))
u = y.get("users;use_login=1/games;game_keys=nba/leagues")
try:
    games = u["fantasy_content"]["users"]["0"]["user"][1]["games"]
    n = 0
    for k, v in games.items():
        if k == "count":
            continue
        leagues = v["game"][1].get("leagues", {})
        for lk, lv in leagues.items():
            if lk == "count":
                continue
            L = lv["league"][0]
            n += 1
            print("Lig:", L.get("league_key"), "|", L.get("name"), "|", L.get("scoring_type"), "|", L.get("num_teams"), "takım")
    print("Hesaptaki NBA ligi sayısı:", n)
except Exception as e:
    print("Lig listesi okunamadı:", e, json.dumps(u)[:300])
