"""Ham ESPN verisinden istatistikleri hesaplar ve site/index.html üretir."""
import collections, datetime, json, os, pathlib, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fetch import current_season  # noqa: E402

CATS = ["0", "6", "3", "2", "1", "17", "19", "20", "11"]
CN = {"0": "PTS", "6": "REB", "3": "AST", "2": "STL", "1": "BLK", "17": "3PM", "19": "FG%", "20": "FT%", "11": "TO"}
LOWER_IS_BETTER = {"11"}
ZREF = None  # build_players oyuncu z-skoru referansı (tek maç değeri için)
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
        cat, apc, mrec, weekly, games, wk = [0, 0, 0], [0, 0, 0], [0, 0, 0], [], [], []
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
            wk.append({c: weeks[w][t][c] for c in CATS})
            games.append({"w": w, "opp": names[o], "oppId": o, "score": f"{W}-{Lo}" + (f"-{T}" if T else ""), "res": res, "beat": beat})
        tc = txc[t]
        teams.append({
            "id": t, "name": names[t], "abbrev": meta[t]["abbrev"], "logo": meta[t]["logo"], "cat": cat, "catPct": pct(cat), "apPct": pct(apc), "ap": apc,
            "mrec": mrec, "weekly": weekly, "games": games, "_wk": wk,
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
        "pro": pl.get("proTeamId"),
        "g": {k: round(mix.get(k, 0), 3) for k in ("0", "6", "3", "2", "1", "17", "11", "13", "14", "15", "16")},
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

    global ZREF
    ZREF = {"mean": mean, "sd": sd, "fga": fga, "fta": fta, "sd_fg": sd_fg, "sd_ft": sd_ft}

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
        if r["team"] == 0:
            del r["g"]
    return sorted(rows, key=lambda r: -r["val"])


def phi(x):
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


ACTIVE_SLOTS = 10  # PG, SG, SF, PF, C, G, F, 3x UTIL


def project_week(raw, data):
    """Devam eden haftanın sonunu tahmin eder: kalan maçlar, günlük 10 kişilik kadro, normal yaklaşım."""
    import math
    M, L, sched = raw["matchups"], raw["league"], raw.get("proschedule")
    cur = data.get("current") or {}
    week = cur.get("week")
    if not sched or not week or not cur.get("matchups"):
        return
    keys = {}
    for m in M["schedule"]:
        if "home" in m:
            keys.setdefault(m["matchupPeriodId"], set()).update(int(k) for k in (m["home"].get("pointsByScoringPeriod") or {}))
    prev = keys.get(week - 1)
    start = (max(prev) + 1) if prev else min(keys.get(week, {1}))
    length = 7 * (L["settings"]["scheduleSettings"].get("matchupPeriodLength") or 1)
    days = range(start, start + length)
    games = {}  # proTeamId -> [scoringPeriod,...] kalan
    for t in sched["settings"]["proTeams"]:
        for sp, gl in (t.get("proGamesByScoringPeriod") or {}).items():
            if int(sp) in days and any(not g.get("statsOfficial") for g in gl):
                games.setdefault(t["id"], []).append(int(sp))
    slots = {}
    for t in raw.get("rosters", {}).get("teams", []):
        for e in t["roster"]["entries"]:
            slots[e["playerId"]] = e.get("lineupSlotId")
    byteam = {}
    for p in data["players"]:
        if p["team"] and slots.get(p["id"]) != 13 and p["inj"] not in ("Sakat", "IR"):
            byteam.setdefault(p["team"], []).append(p)
    mvals = {}
    for m in M["schedule"]:
        if m.get("matchupPeriodId") == week and "home" in m and "away" in m:
            for side in ("home", "away"):
                sc = (m[side].get("cumulativeScore") or {}).get("scoreByStat") or {}
                mvals[m[side]["teamId"]] = {k: v["score"] for k, v in sc.items()}
    proj = {}
    for tid, base in mvals.items():
        rem = {k: 0.0 for k in ("0", "6", "3", "2", "1", "17", "11", "13", "14", "15", "16")}
        var = {k: 0.0 for k in rem}
        n = 0
        per_player = {}
        for d in days:
            playing = [p for p in byteam.get(tid, []) if d in games.get(p["pro"], [])]
            playing.sort(key=lambda p: -p["val"])
            for p in playing[:ACTIVE_SLOTS]:
                n += 1
                per_player[p["id"]] = per_player.get(p["id"], 0) + 1
                for k, v in p["g"].items():
                    rem[k] += v
                    var[k] += max(v, (0.4 * v) ** 2)
        for k in rem:  # model hatası: ortalamalar, dakikalar ve kadro kararları belirsiz
            var[k] += (0.15 * rem[k]) ** 2
        tot = {k: base.get(k, 0) + rem[k] for k in rem}
        mu, sd = {}, {}
        for c in CATS:
            if c == "19":
                fga = tot["14"] or 1
                mu[c], sd[c] = tot["13"] / fga, math.sqrt(var["13"]) / fga
            elif c == "20":
                fta = tot["16"] or 1
                mu[c], sd[c] = tot["15"] / fta, math.sqrt(var["15"]) / fta
            else:
                mu[c], sd[c] = tot[c], math.sqrt(var[c])
        proj[tid] = {"mu": mu, "sd": sd, "games": n, "left": per_player}
    for mt in cur["matchups"]:
        h, a = proj.get(mt["home"]), proj.get(mt["away"])
        if not h or not a:
            continue
        pc = {}
        for c in CATS:
            diff = h["mu"][c] - a["mu"][c]
            if c in LOWER_IS_BETTER:
                diff = -diff
            s = math.sqrt(h["sd"][c] ** 2 + a["sd"][c] ** 2)
            pc[CN[c]] = 1.0 if (s == 0 and diff > 0) else 0.0 if (s == 0 and diff < 0) else 0.5 if s == 0 else phi(diff / s)
        dist = [1.0]  # kazanılan kategori sayısının olasılık dağılımı
        for q in pc.values():
            dist = [(dist[i] if i < len(dist) else 0) * (1 - q) + (dist[i - 1] * q if i >= 1 else 0) for i in range(len(dist) + 1)]
        mt["proj"] = {
            "win": round(sum(dist[5:]), 3), "pc": {k: round(v, 3) for k, v in pc.items()},
            "score": [sum(1 for v in pc.values() if v > 0.5), sum(1 for v in pc.values() if v < 0.5)],
            "games": [h["games"], a["games"]],
            "mu": [{CN[c]: round(h["mu"][c], 3) for c in CATS}, {CN[c]: round(a["mu"][c], 3) for c in CATS}],
        }
    left = {}
    for t in proj.values():
        left.update(t["left"])
    for p in data["players"]:
        if p["team"]:
            p["left"] = left.get(p["id"], 0)
    cur["days"] = [start, start + length - 1]


def simulate_season(raw, data, n_sims=10000):
    """Kalan normal sezonu ve playoffları simüle eder: playoff, final ve şampiyonluk ihtimalleri."""
    import math, random, statistics
    L, M = raw["league"], raw["matchups"]
    ss = L["settings"]["scheduleSettings"]
    reg_weeks = ss.get("matchupPeriodCount", 0)
    n_playoff = ss.get("playoffTeamCount", 0)
    cur = data.get("current") or {}
    cur_week = cur.get("week") or 0
    teams = {t["id"]: t for t in data["teams"]}
    if not reg_weeks or not n_playoff or not teams or not all(t["_wk"] for t in teams.values()):
        return
    ids = list(teams)
    # 1) geçmiş haftalardan kategori ortalaması, kategoriye göre ortak sapma
    hist, pooled = {}, {}
    for c in CATS:
        allv = [w[c] for t in teams.values() for w in t["_wk"]]
        lg = statistics.mean(allv)
        resid = []
        for tid, t in teams.items():
            vals = [w[c] for w in t["_wk"]]
            m = statistics.mean(vals)
            resid += [v - m for v in vals]
            n = len(vals)
            hist.setdefault(tid, {})[c] = (n * m + 3 * lg) / (n + 3)
        pooled[c] = (statistics.pstdev(resid) or abs(lg) * 0.1 or 1) * 1.1
    # 2) kadrodan haftalık beklenti (sakat/IR oyuncular yarım ağırlık), lig ortalamasına ölçekli
    slots = {e["playerId"]: e.get("lineupSlotId") for t in raw.get("rosters", {}).get("teams", []) for e in t["roster"]["entries"]}
    rost = {}
    for tid in ids:
        acc = {k: 0.0 for k in ("0", "6", "3", "2", "1", "17", "11", "13", "14", "15", "16")}
        for p in data["players"]:
            if p["team"] != tid or "g" not in p:
                continue
            wgt = 0.5 if (p["inj"] in ("Sakat", "IR") or slots.get(p["id"]) == 13) else 1.0
            for k in acc:
                acc[k] += p["g"].get(k, 0) * 3.3 * wgt
        r = {c: acc[c] for c in ("0", "6", "3", "2", "1", "17", "11")}
        r["19"] = acc["13"] / acc["14"] if acc["14"] else 0
        r["20"] = acc["15"] / acc["16"] if acc["16"] else 0
        rost[tid] = r
    mu = {}
    for c in CATS:
        hm = statistics.mean(hist[t][c] for t in ids)
        rm = statistics.mean(rost[t][c] for t in ids) or 1
        for t in ids:
            rv = rost[t][c] * (hm / rm) if rost[t][c] else hist[t][c]
            mu.setdefault(t, {})[c] = 0.5 * hist[t][c] + 0.5 * rv

    def pcat(a, b, c):
        d = mu[a][c] - mu[b][c]
        if c in LOWER_IS_BETTER:
            d = -d
        return phi(d / (pooled[c] * math.sqrt(2)))

    # sezonun kalanında takım gücü de değişir (sakatlık, takas, waiver): her "dünya" için güçleri biraz kaydır
    rnd = random.Random(42)
    base_mu = {t: dict(mu[t]) for t in ids}
    worlds = []
    for _ in range(200):
        for t in ids:
            g = rnd.gauss(0, 1)
            for c in CATS:
                sh = pooled[c] * 0.35 * (0.6 * g + 0.8 * rnd.gauss(0, 1))
                mu[t][c] = base_mu[t][c] + (-sh if c in LOWER_IS_BETTER else sh)
        worlds.append({(a, b): [pcat(a, b, c) for c in CATS] for a in ids for b in ids if a != b})
    mu = base_mu
    cur_p = {}
    for mt in cur.get("matchups", []):
        if "proj" in mt:
            ph = [mt["proj"]["pc"][CN[c]] for c in CATS]
            cur_p[(mt["home"], mt["away"])] = ph
    future = [(m["matchupPeriodId"], m["home"]["teamId"], m["away"]["teamId"]) for m in M["schedule"]
              if "home" in m and "away" in m and m.get("playoffTierType", "NONE") == "NONE"
              and cur_week < m["matchupPeriodId"] <= reg_weeks]
    if cur_week and not cur_p:  # tahmin yoksa bu haftayı da modelle oyna
        future += [(m["matchupPeriodId"], m["home"]["teamId"], m["away"]["teamId"]) for m in M["schedule"]
                   if m.get("matchupPeriodId") == cur_week and "home" in m and "away" in m]
    base = {t: list(teams[t]["cat"]) for t in ids}
    rr = rnd.random
    res = {t: {"po": 0, "final": 0, "champ": 0, "seed1": 0, "seedSum": 0, "w": 0.0, "l": 0.0} for t in ids}
    bracket = [1, 8, 4, 5, 2, 7, 3, 6] if n_playoff == 8 else None

    def play(a, b, probs):
        wa = sum(1 for q in probs if rr() < q)
        return wa, len(probs) - wa

    for si in range(n_sims):
        P = worlds[si % len(worlds)]
        rec = {t: base[t][:] for t in ids}
        for (h, a), probs in cur_p.items():
            wh, wa = play(h, a, probs)
            rec[h][0] += wh; rec[h][1] += wa; rec[a][0] += wa; rec[a][1] += wh
        for _, h, a in future:
            wh, wa = play(h, a, P[(h, a)])
            rec[h][0] += wh; rec[h][1] += wa; rec[a][0] += wa; rec[a][1] += wh
        order = sorted(ids, key=lambda t: (-(rec[t][0] + 0.5 * rec[t][2]) / max(1, sum(rec[t])), rr()))
        for i, t in enumerate(order):
            res[t]["w"] += rec[t][0]; res[t]["l"] += rec[t][1]
            if i < n_playoff:
                res[t]["po"] += 1
                res[t]["seedSum"] += i + 1
        res[order[0]]["seed1"] += 1
        seeds = {i + 1: t for i, t in enumerate(order[:n_playoff])}
        field = [seeds[s] for s in (bracket or range(1, n_playoff + 1))]
        rank = {t: i for i, t in enumerate(order)}
        while len(field) > 1:
            nxt = []
            for i in range(0, len(field), 2):
                a, b = field[i], field[i + 1]
                wa, wb = play(a, b, P[(a, b)])
                nxt.append(a if (wa > wb or (wa == wb and rank[a] < rank[b])) else b)
            if len(nxt) == 1:
                res[field[0]]["final"] += 1; res[field[1]]["final"] += 1
            field = nxt
        res[field[0]]["champ"] += 1
    out = {}
    for t, r in res.items():
        out[t] = {"po": round(r["po"] / n_sims, 4), "final": round(r["final"] / n_sims, 4), "champ": round(r["champ"] / n_sims, 4),
                  "seed1": round(r["seed1"] / n_sims, 4), "seed": round(r["seedSum"] / r["po"], 2) if r["po"] else None,
                  "w": round(r["w"] / n_sims, 1), "l": round(r["l"] / n_sims, 1)}
    data["sim"] = {"teams": out, "playoffTeams": n_playoff, "regWeeks": reg_weeks, "sims": n_sims,
                   "seedRule": ss.get("playoffSeedingRule")}


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


def render_page(data, lang):
    import copy
    tpl = pathlib.Path("templates")
    head, body = (tpl / "head.html").read_text(), (tpl / "body.html").read_text()
    if lang == "en":
        from i18n_en import PAIRS, MONTHS, INJ, SLOT
        for tr, en in sorted(PAIRS, key=lambda x: -len(x[0])):
            body = body.replace(tr, en)
        head = head.replace("Lig Raporu", "League Report")
        import re
        body = re.sub(r"%\$\{([^{}]*)\}", r"${\1}%", body)  # %50 -> 50%
        data = copy.deepcopy(data)
        now = datetime.datetime.now(ZoneInfo("Europe/Istanbul"))
        data["updated"] = f"{MONTHS[now.month - 1][:3]} {now.day}, {now.year}, {now:%H:%M}"
        for p in data.get("players", []):
            p["inj"] = INJ.get(p["inj"], p["inj"])
            if p.get("slot"):
                p["slot"] = SLOT.get(p["slot"], p["slot"])
        body = body.replace('href="en.html" hreflang="en"', 'href="./" hreflang="tr"').replace('location.hash">EN<', 'location.hash">TR<')
    body = body.replace("/*__FUN__*/", (tpl / "fun.js").read_text())
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = (
        f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        + head + "</head><body>" + body.replace("__DATA__", payload) + "</body></html>\n"
    )
    return page.replace('<h1 id="lg">Fantasy 26-27</h1>', f'<h1 id="lg">{data["league"]}</h1>')


def main():
    season = int(os.environ.get("SEASON") or current_season())
    raw_dir = pathlib.Path("data/raw") / str(season)
    raw = {n: json.loads((raw_dir / f"{n}.json").read_text()) for n in ("league", "matchups")}
    for n in ("rosters", "freeagents", "proschedule"):
        f = raw_dir / f"{n}.json"
        if f.exists():
            raw[n] = json.loads(f.read_text())
    data = compute(raw)
    data["players"] = build_players(raw, season)
    project_week(raw, data)
    simulate_season(raw, data)
    for tid, r in sorted((data.get("sim") or {}).get("teams", {}).items(), key=lambda x: -x[1]["champ"]):
        print(f"sim {tid}: playoff %{r['po']*100:.0f} şampiyon %{r['champ']*100:.1f} kat {r['w']}-{r['l']}")
    for mt in data.get("current", {}).get("matchups", []):
        if "proj" in mt:
            print(f"tahmin: {mt['home']} - {mt['away']}: %{mt['proj']['win']*100:.0f} ({mt['proj']['games']} maç)")
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
    try:
        import fun
        dpath = pathlib.Path("data/daily") / f"{season}.json"
        gpath = raw_dir / "gamelogs.json"
        daily = json.loads(dpath.read_text()) if dpath.exists() else None
        logs = json.loads(gpath.read_text()) if gpath.exists() else {}
        data["fun"] = fun.build_fun(raw, data, daily, logs, ZREF, seasons, season)
        f = data["fun"] or {}
        for y in sorted(seasons):
            dp, rd = pathlib.Path("data/daily") / f"{y}.json", pathlib.Path("data/raw") / str(y)
            if y == season or not f or not dp.exists() or not (rd / "matchups.json").exists():
                continue
            ry = {n: json.loads((rd / f"{n}.json").read_text()) for n in ("league", "matchups")}
            if (rd / "proschedule.json").exists():
                ry["proschedule"] = json.loads((rd / "proschedule.json").read_text())
            gl = json.loads((rd / "gamelogs.json").read_text()) if (rd / "gamelogs.json").exists() else {}
            fy = fun.build_fun(ry, seasons[y][1], json.loads(dp.read_text()), gl, ZREF, None, y)
            if fy:
                for k in ("blowouts", "rivals", "owned", "closeCount", "nGames"):
                    fy.pop(k, None)
                fy["records"].pop("week", None)
                f.setdefault("past", {})[str(y)] = fy
                print(f"eğlence {y}:", len(fy.get("trades", [])), "takas,", len(fy["waiver"]["top"]), "waiver,", fy["days"], "gün")
        print("eğlence:", len(f.get("bench", [])), "takım yedek,", len((f.get("waiver") or {}).get("top", [])), "waiver,",
              len(f.get("trades", [])), "takas,", len(f.get("regrets", [])), "pişmanlık")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("eğlence hesaplanamadı:", e)
    for y in seasons:
        for t in seasons[y][1]["teams"]:
            t.pop("_wk", None)
    pathlib.Path("data/history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=1))
    print("geçmiş:", len(hist["seasons"]), "sezon,", len(hist["owners"]), "menajer;",
          sum(1 for o in hist["owners"] if o["oldNames"]), "isim değiştirmiş;",
          sum(1 for o in hist["owners"] if o["nSeasons"] == 1 and o["active"]), "ilk sezonunda")
    out = pathlib.Path("site")
    out.mkdir(exist_ok=True)
    if os.environ.get("SKIP_LOGOS") != "1":
        localize_logos(data["teams"], out)
    pathlib.Path("data/stats.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(render_page(data, "tr"))
    (out / "en.html").write_text(render_page(data, "en"))
    print(f"site/index.html yazıldı: {len(data['weeks'])} hafta, {len(data['teams'])} takım")


if __name__ == "__main__":
    main()
