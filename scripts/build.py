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
    data = compute(raw)
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
