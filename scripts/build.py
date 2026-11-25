"""Ham ESPN verisinden istatistikleri hesaplar ve site/index.html üretir."""
import collections, datetime, json, os, pathlib, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch import current_season  # noqa: E402

CATS = ["0", "6", "3", "2", "1", "17", "19", "20", "11"]
CN = {"0": "PTS", "6": "REB", "3": "AST", "2": "STL", "1": "BLK", "17": "3PM", "19": "FG%", "20": "FT%", "11": "TO"}
LOWER_IS_BETTER = {"11"}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def cmp(a, b):
    w = l = t = 0
    for c in CATS:
        x, y = a[c], b[c]
        if c in LOWER_IS_BETTER:
            x, y = -x, -y
        w += x > y
        l += x < y
        t += x == y
    return w, l, t


def pct(r):
    return (r[0] + 0.5 * r[2]) / max(1, sum(r))


def is_close(c, x, y):
    if c in ("19", "20"):
        return abs(x - y) < 0.01
    return abs(x - y) <= max(2, 0.05 * max(x, y))


def current_week(M, L, names):
    """Devam eden haftanın maçları: kategori kategori anlık durum."""
    week = L["status"].get("currentMatchupPeriod")
    rows, vals = [], {}
    for m in M["schedule"]:
        if m.get("matchupPeriodId") != week or "home" not in m or "away" not in m:
            continue
        h, a = m["home"], m["away"]
        hs = (h.get("cumulativeScore") or {}).get("scoreByStat") or {}
        as_ = (a.get("cumulativeScore") or {}).get("scoreByStat") or {}
        if not hs or not as_:
            continue
        hv = {c: hs[c]["score"] for c in CATS}
        av = {c: as_[c]["score"] for c in CATS}
        vals[h["teamId"]], vals[a["teamId"]] = hv, av
        W, Lo, T = cmp(hv, av)
        cats = []
        for c in CATS:
            x, y = hv[c], av[c]
            better = (x < y) if c in LOWER_IS_BETTER else (x > y)
            worse = (x > y) if c in LOWER_IS_BETTER else (x < y)
            cats.append({"c": CN[c], "h": x, "a": y, "r": "H" if better else "A" if worse else "T", "close": is_close(c, x, y)})
        rows.append({"home": h["teamId"], "away": a["teamId"], "score": [W, Lo, T], "cats": cats,
                     "closeCount": sum(k["close"] for k in cats)})
    live = {}
    for t, a in vals.items():
        live[t] = sum(cmp(a, b)[0] > cmp(a, b)[1] for u, b in vals.items() if u != t)
    rows.sort(key=lambda r: (abs(r["score"][0] - r["score"][1]), -r["closeCount"]))
    return {"week": week, "matchups": rows, "live": live}


def compute(raw):
    L, M = raw["league"], raw["matchups"]
    names = {t["id"]: t["name"].strip() for t in L["teams"]}
    meta = {t["id"]: {"abbrev": t.get("abbrev", ""), "logo": t.get("logo", "")} for t in L["teams"]}
    txc = {t["id"]: t.get("transactionCounter", {}) for t in L["teams"]}
    weeks, opp = collections.defaultdict(dict), collections.defaultdict(dict)
    for m in M["schedule"]:
        if "home" not in m or "away" not in m or m.get("winner") == "UNDECIDED":
            continue
        if m.get("playoffTierType", "NONE") != "NONE":
            continue
        if not m["home"].get("cumulativeScore", {}).get("scoreByStat"):
            continue
        w = m["matchupPeriodId"]
        for s, o in (("home", "away"), ("away", "home")):
            sc = m[s]["cumulativeScore"]["scoreByStat"]
            weeks[w][m[s]["teamId"]] = {c: sc[c]["score"] for c in CATS}
            opp[w][m[s]["teamId"]] = m[o]["teamId"]
    done = sorted(weeks)
    teams = []
    for t in names:
        cat, apc, mrec, weekly, games = [0, 0, 0], [0, 0, 0], [0, 0, 0], [], []
        for w in done:
            a, beat = weeks[w][t], 0
            for u, b in weeks[w].items():
                if u == t:
                    continue
                W, Lo, T = cmp(a, b)
                apc[0] += W; apc[1] += Lo; apc[2] += T
                beat += W > Lo
            o = opp[w][t]
            W, Lo, T = cmp(a, weeks[w][o])
            cat[0] += W; cat[1] += Lo; cat[2] += T
            res = "G" if W > Lo else "M" if Lo > W else "B"
            mrec["GMB".index(res)] += 1
            weekly.append(beat)
            games.append({"w": w, "opp": names[o], "oppId": o, "score": f"{W}-{Lo}" + (f"-{T}" if T else ""), "res": res, "beat": beat})
        tc = txc[t]
        teams.append({
            "id": t, "name": names[t], "abbrev": meta[t]["abbrev"], "logo": meta[t]["logo"], "cat": cat, "catPct": pct(cat), "apPct": pct(apc), "ap": apc,
            "mrec": mrec, "weekly": weekly, "games": games,
            "avg": {CN[c]: sum(weeks[w][t][c] for w in done) / max(1, len(done)) for c in CATS},
            "adds": tc.get("acquisitions", 0), "moves": tc.get("moveToActive", 0), "trades": tc.get("trades", 0),
            "recent": sum(weekly[-2:]) / (11 * max(1, min(2, len(weekly)))),
        })
    for t in teams:
        t["luck"] = t["catPct"] - t["apPct"]
        t["power"] = 0.6 * t["apPct"] + 0.4 * t["recent"]
    for c in CN.values():
        order = sorted(teams, key=lambda t: t["avg"][c], reverse=(c != "TO"))
        for i, t in enumerate(order):
            t.setdefault("rank", {})[c] = i + 1
    beats, steals = [], []
    for t in teams:
        for g in t["games"]:
            ev = {"team": t["name"], "w": g["w"], "opp": g["opp"], "score": g["score"], "beat": g["beat"]}
            if g["res"] == "M" and g["beat"] >= 8:
                beats.append(ev)
            if g["res"] == "G" and g["beat"] <= 3:
                steals.append(ev)
    beats.sort(key=lambda x: (-x["beat"], x["w"]))
    steals.sort(key=lambda x: (x["beat"], x["w"]))
    current = current_week(M, L, names)
    now = datetime.datetime.now(ZoneInfo("Europe/Istanbul"))
    return {
        "current": current,
        "league": L["settings"]["name"], "updated": f"{now.day} {AYLAR[now.month - 1]} {now.year}, {now:%H:%M}",
        "weeks": done, "currentWeek": L["status"].get("currentMatchupPeriod"), "cats": list(CN.values()),
        "teams": teams, "beats": beats, "steals": steals,
    }


POS = {1: "PG", 2: "SG", 3: "SF", 4: "PF", 5: "C"}
INJ = {"OUT": "Sakat", "DAY_TO_DAY": "Belirsiz", "INJURY_RESERVE": "IR", "SUSPENSION": "Ceza"}


W_L15, W_SEASON, W_PROJ = 0.5, 0.3, 0.2  # son 15 gün, sezon, sezon öncesi ESPN projeksiyonu


def blend(parts):
    tot = sum(w for _, w in parts)
    keys = set().union(*[a.keys() for a, _ in parts])
    num = lambda v: v if isinstance(v, (int, float)) else 0
    return {k: sum(num(a.get(k, 0)) * w for a, w in parts) / tot for k in keys}


def player_row(pl, season, on_team):
    stats = {s["id"]: (s.get("averageStats") or {}) for s in pl.get("stats", [])}
    l15, sea, proj = stats.get(f"02{season}", {}), stats.get(f"00{season}", {}), stats.get(f"10{season}", {})
    now = []
    if l15.get("42", 0) >= 3:
        now.append((l15, W_L15))
    if sea.get("42", 0) >= 1:
        now.append((sea, W_SEASON))
    if not now and not proj:
        return None
    parts = now + ([(proj, W_PROJ)] if proj else [])
    mix = blend(parts)
    cur = blend(now) if now else proj
    src = " + ".join(n for n, ok in (("son 15 gün", l15.get("42", 0) >= 3), ("sezon", sea.get("42", 0) >= 1), ("projeksiyon", bool(proj))) if ok)

    def pack(a):
        return {"s": {CN[c]: a.get(c, 0) for c in CATS}, "fga": a.get("14", 0), "fta": a.get("16", 0)}

    gp_now = int((l15 if l15.get("42", 0) >= 3 else sea).get("42", 0))
    mins = (l15 if l15.get("42", 0) >= 3 else sea or proj).get("40", 0)
    return {
        "id": pl["id"], "name": pl["fullName"], "pos": POS.get(pl.get("defaultPositionId"), ""),
        "inj": INJ.get(pl.get("injuryStatus") or "", ""), "team": on_team,
        "owned": round((pl.get("ownership") or {}).get("percentOwned", 0), 1),
        "gp": gp_now, "seasonGp": int(sea.get("42", 0)), "min": round(mins, 1), "src": src,
        "_mix": pack(mix), "_now": pack(cur), "_proj": pack(proj) if proj else None,
    }


def build_players(raw, season):
    """Kadrolar + serbest oyuncular, 9-cat z-skoru ile."""
    import statistics
    rows = []
    for t in raw.get("rosters", {}).get("teams", []):
        for e in t.get("roster", {}).get("entries", []):
            r = player_row(e["playerPoolEntry"]["player"], season, t["id"])
            if r:
                r["slot"] = "Yedek" if e.get("lineupSlotId") == 12 else "IR" if e.get("lineupSlotId") == 13 else ""
                rows.append(r)
    for p in raw.get("freeagents", {}).get("players", []):
        r = player_row(p["player"], season, 0)
        if r:
            r["fa"] = p.get("status", "FREEAGENT")
            rows.append(r)
    pool = [r for r in rows if r["gp"] >= 3] or rows
    pool = sorted(pool, key=lambda r: -r["_mix"]["s"]["PTS"])[:220]
    P = [r["_mix"] for r in pool]
    mean = {c: statistics.mean(x["s"][c] for x in P) for c in CN.values()}
    sd = {c: statistics.pstdev(x["s"][c] for x in P) or 1 for c in CN.values()}
    fga = statistics.mean(x["fga"] for x in P) or 1
    fta = statistics.mean(x["fta"] for x in P) or 1
    sd_fg = statistics.pstdev([(x["s"]["FG%"] - mean["FG%"]) * x["fga"] / fga for x in P]) or 1
    sd_ft = statistics.pstdev([(x["s"]["FT%"] - mean["FT%"]) * x["fta"] / fta for x in P]) or 1

    def zs(x):
        z = {}
        for c in CN.values():
            if c == "FG%":
                z[c] = (x["s"][c] - mean[c]) * x["fga"] / fga / sd_fg
            elif c == "FT%":
                z[c] = (x["s"][c] - mean[c]) * x["fta"] / fta / sd_ft
            elif c == "TO":
                z[c] = -(x["s"][c] - mean[c]) / sd[c]
            else:
                z[c] = (x["s"][c] - mean[c]) / sd[c]
        return z

    for r in rows:
        z = zs(r["_mix"])
        r["z"] = {c: round(v, 2) for c, v in z.items()}
        r["val"] = round(sum(z.values()), 2)
        r["valNow"] = round(sum(zs(r["_now"]).values()), 2)
        r["valProj"] = round(sum(zs(r["_proj"]).values()), 2) if r["_proj"] else None
        r["s"] = {c: (round(v, 3) if "%" in c else round(v, 1)) for c, v in r["_now"]["s"].items()}
        del r["_mix"], r["_now"], r["_proj"]
    return sorted(rows, key=lambda r: -r["val"])


def owner_key(team):
    import hashlib
    o = team.get("primaryOwner") or (team.get("owners") or [""])[0] or f"team-{team['id']}"
    return hashlib.sha1(o.encode()).hexdigest()[:10]


def build_history(current_season_id, seasons):
    """seasons: {yıl: (ham lig verisi, compute çıktısı)}. Takımları kullanıcıya göre birleştirir."""
    owners = {}
    for y in sorted(seasons):
        L, data = seasons[y]
        okey = {t["id"]: owner_key(t) for t in L["teams"]}
        final = {t["id"]: t.get("rankCalculatedFinal") or 0 for t in L["teams"]}
        done = y != current_season_id
        for t in data["teams"]:
            k = okey[t["id"]]
            o = owners.setdefault(k, {"key": k, "seasons": [], "mrec": [0, 0, 0], "cat": [0, 0, 0], "ap": [0, 0, 0],
                                      "titles": 0, "h2h": {}})
            o["seasons"].append({"y": y, "name": t["name"], "teamId": t["id"], "final": final[t["id"]] if done else None,
                                 "mrec": t["mrec"], "cat": t["cat"], "apPct": t["apPct"]})
            for f in ("mrec", "cat", "ap"):
                o[f] = [a + b for a, b in zip(o[f], t[f])]
            if done and final[t["id"]] == 1:
                o["titles"] += 1
            for g in t["games"]:
                ok = okey[g["oppId"]]
                h = o["h2h"].setdefault(ok, [0, 0, 0])
                h["GMB".index(g["res"])] += 1
    for o in owners.values():
        o["seasons"].sort(key=lambda s: -s["y"])
        cur = o["seasons"][0]
        o["active"] = cur["y"] == current_season_id
        o["name"] = cur["name"]
        o["teamId"] = cur["teamId"] if o["active"] else None
        o["oldNames"] = sorted({s["name"] for s in o["seasons"][1:]} - {cur["name"]})
        o["nSeasons"] = len(o["seasons"])
        o["apPct"] = pct(o["ap"])
        o["catPct"] = pct(o["cat"])
        finals = [s["final"] for s in o["seasons"] if s["final"]]
        o["best"] = min(finals) if finals else None
    return {"seasons": sorted(seasons), "owners": sorted(owners.values(), key=lambda o: (-o["catPct"]))}


def localize_logos(teams, out):
    """Logoları siteye kopyalar; ESPN'in özel yüklenen resimleri başka sitelerden doğrudan açılmıyor."""
    import urllib.request
    import shutil
    d = out / "logos"
    d.mkdir(parents=True, exist_ok=True)
    manual = pathlib.Path("logos")  # repoya elle eklenen logolar (ör. logos/10.png) her zaman önceliklidir
    cookie = ""
    if os.environ.get("ESPN_S2") and os.environ.get("SWID"):
        cookie = f"espn_s2={os.environ['ESPN_S2']}; SWID={os.environ['SWID']}"
    for t in teams:
        own = sorted(manual.glob(f"{t['id']}.*")) if manual.is_dir() else []
        if own:
            shutil.copy(own[0], d / own[0].name)
            t["logo"] = f"logos/{own[0].name}"
            print(f"logo (elle eklenen): {t['name']}")
            continue
        url = t.get("logo")
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fantasy.espn.com/"})
            if cookie and "fantasy.espn.com" in url:
                req.add_header("Cookie", cookie)
            with urllib.request.urlopen(req, timeout=30) as r:
                body, ctype = r.read(), r.headers.get("Content-Type", "")
            ext = "svg" if "svg" in ctype or url.endswith(".svg") else "png" if "png" in ctype else "gif" if "gif" in ctype else "webp" if "webp" in ctype else "jpg"
            if len(body) < 50:
                raise ValueError("boş yanıt")
            (d / f"{t['id']}.{ext}").write_bytes(body)
            t["logo"] = f"logos/{t['id']}.{ext}"
            print(f"logo ok: {t['name']} ({ctype}, {len(body)} bayt)")
        except Exception as e:  # logo yoksa kısaltma gösterilir
            print(f"logo alınamadı: {t['name']}: {e}")
            if "mystique" in (url or ""):
                t["logo"] = ""  # özel resim çerezsiz açılmıyor; kısaltma gösterilsin


def main():
    season = int(os.environ.get("SEASON") or current_season())
    raw_dir = pathlib.Path("data/raw") / str(season)
    raw = {n: json.loads((raw_dir / f"{n}.json").read_text()) for n in ("league", "matchups")}
    for n in ("rosters", "freeagents"):
        f = raw_dir / f"{n}.json"
        if f.exists():
            raw[n] = json.loads(f.read_text())
    data = compute(raw)
    data["players"] = build_players(raw, season)
    print(f"oyuncular: {len(data['players'])} ({sum(1 for p in data['players'] if p['team'] == 0)} serbest)")
    seasons = {season: (raw["league"], data)}
    for y in raw["league"].get("status", {}).get("previousSeasons", []):
        d = pathlib.Path("data/raw") / str(y)
        try:
            r = {n: json.loads((d / f"{n}.json").read_text()) for n in ("league", "matchups")}
            seasons[y] = (r["league"], compute(r))
            print(f"{y}: {len(seasons[y][1]['teams'])} takım, {len(seasons[y][1]['weeks'])} hafta")
        except Exception as e:
            print(f"{y} işlenemedi: {e}")
    hist = build_history(season, seasons)
    okey = {t["id"]: owner_key(t) for t in raw["league"]["teams"]}
    for t in data["teams"]:
        t["owner"] = okey[t["id"]]
    data["history"] = hist
    pathlib.Path("data/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=1))
    print("geçmiş:", len(hist["seasons"]), "sezon,", len(hist["owners"]), "menajer;",
          sum(1 for o in hist["owners"] if o["oldNames"]), "isim değiştirmiş;",
          sum(1 for o in hist["owners"] if o["nSeasons"] == 1 and o["active"]), "ilk sezonunda")
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    if os.environ.get("SKIP_LOGOS") != "1":
        localize_logos(data["teams"], out)
    pathlib.Path("data/stats.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tpl = pathlib.Path("templates")
    page = (
        '<!doctype html>\n<html lang="tr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        + (tpl / "head.html").read_text()
        + "</head><body>"
        + (tpl / "body.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
        + "</body></html>\n"
    )
    page = page.replace("<h1 id=\"lg\">Fantasy 26-27</h1>", f"<h1 id=\"lg\">{data['league']}</h1>")
    (out / "index.html").write_text(page)
    print(f"site/index.html yazıldı: {len(data['weeks'])} hafta, {len(data['teams'])} takım")


if __name__ == "__main__":
    main()
