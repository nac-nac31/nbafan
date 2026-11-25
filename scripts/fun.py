"""Eğlenceli istatistikler: takas karnesi, yedekte kalan puanlar, rekabetler, rekorlar, waiver,
pişmanlıklar, draft karnesi, takım kişilikleri ve sakatlık şanssızlığı.

Girdi: build.py'nin ürettiği data + data/daily/<sezon>.json (günlük kadrolar, işlemler, draft) +
data/raw/<sezon>/gamelogs.json (oyuncu maç kayıtları)."""
import datetime, statistics

# fetch.GSTATS sırası
I = {k: i for i, k in enumerate(["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO", "FGM", "FGA", "FTM", "FTA", "MIN"])}
COUNT = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TO"]
CATS = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]
SID = {"PTS": "0", "REB": "6", "AST": "3", "STL": "2", "BLK": "1", "3PM": "17", "FG%": "19", "FT%": "20", "TO": "11"}
SLOTS = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 11: 3}  # PG SG SF PF C G F UTIL×3
BENCH, IR = 12, 13


def gz(line, Z):
    """Tek maçın 9-kategori z değeri (oyuncu z-skoruyla aynı ölçek)."""
    if not line:
        return 0.0
    m, sd = Z["mean"], Z["sd"]
    z = 0.0
    for c in ("PTS", "REB", "AST", "STL", "BLK", "3PM"):
        z += (line[I[c]] - m[c]) / sd[c]
    z -= (line[I["TO"]] - m["TO"]) / sd["TO"]
    z += (line[I["FGM"]] - m["FG%"] * line[I["FGA"]]) / Z["fga"] / Z["sd_fg"]
    z += (line[I["FTM"]] - m["FT%"] * line[I["FTA"]]) / Z["fta"] / Z["sd_ft"]
    return z


def add_lines(acc, line):
    for k, i in I.items():
        acc[k] = acc.get(k, 0) + line[i]


def cats_of(tot):
    out = {c: tot.get(c, 0) for c in COUNT}
    out["FG%"] = tot["FGM"] / tot["FGA"] if tot.get("FGA") else 0
    out["FT%"] = tot["FTM"] / tot["FTA"] if tot.get("FTA") else 0
    return out


def cat_score(a, b):
    w = l = 0
    for c in CATS:
        x, y = a[c], b[c]
        if c == "TO":
            x, y = -x, -y
        if abs(x - y) < 1e-9:
            continue
        if x > y:
            w += 1
        else:
            l += 1
    return w, l


def can_fill(players, elig):
    """players: seçilen oyuncular; elig: pid -> uygun slotlar. Slot kapasitesine göre eşleşme var mı?"""
    cap = dict(SLOTS)
    owner = {s: [] for s in cap}

    def aug(p, seen):
        for s in elig.get(p, ()):
            if s not in cap or s in seen:
                continue
            seen.add(s)
            if len(owner[s]) < cap[s]:
                owner[s].append(p)
                return True
            for q in list(owner[s]):
                if aug(q, seen):
                    owner[s].remove(q)
                    owner[s].append(p)
                    return True
        return False

    return all(aug(p, set()) for p in players)


def best_lineup(cands, elig):
    """cands: [(değer, pid)]. Transversal matroid: değere göre açgözlü seçim optimaldir."""
    chosen = []
    for v, p in sorted(cands, reverse=True):
        if v <= -50:
            break
        if len(chosen) >= sum(SLOTS.values()):
            break
        if can_fill(chosen + [p], elig):
            chosen.append(p)
    return set(chosen)


def fmt_day(ms):
    """Tarih (İstanbul), ISO biçiminde; sayfa dile göre biçimlendirir."""
    if not ms:
        return ""
    d = datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone(datetime.timedelta(hours=3)))
    return d.strftime("%Y-%m-%d")


def line_dict(line):
    return {k: line[i] for k, i in I.items()}


def build_fun(raw, data, daily, logs, Z, seasons=None, cur_season=None):
    if not daily or not Z:
        return None
    days, tx, meta, draft = daily.get("days", {}), daily.get("tx", {}), daily.get("players", {}), daily.get("draft", [])
    teams = {t["id"]: t for t in data["teams"]}
    names = {t["id"]: t["name"] for t in data["teams"]}
    pname = lambda pid: (meta.get(str(pid)) or [str(pid)])[0]
    elig = {int(k): [s for s in v[2] if s in SLOTS] for k, v in meta.items()}
    pvals = {p["id"]: p for p in data["players"]}
    vals = sorted((p["val"] for p in data["players"]), reverse=True)
    repl = vals[min(len(vals) - 1, 12 * 11)] if vals else 0  # ~132. oyuncu: yedek seviyesi
    # skor dönemleri -> hafta ve tarih
    sp_week, week_sps = {}, {}
    for m in raw["matchups"]["schedule"]:
        if "home" in m and m.get("playoffTierType", "NONE") == "NONE":
            for k in (m["home"].get("pointsByScoringPeriod") or {}):
                sp_week[int(k)] = m["matchupPeriodId"]
                week_sps.setdefault(m["matchupPeriodId"], set()).add(int(k))
    sp_date, team_games = {}, {}
    for pt in (raw.get("proschedule") or {}).get("settings", {}).get("proTeams", []):
        for k, gl in (pt.get("proGamesByScoringPeriod") or {}).items():
            team_games.setdefault(pt["id"], set()).add(int(k))
            for g in gl:
                sp_date[int(k)] = min(sp_date.get(int(k), g["date"]), g["date"])
    done_weeks = set(range(1, len(data["weeks"]) + 1))
    latest = max((int(k) for k in days), default=0)
    out = {"repl": round(repl, 2)}

    # ---------- 1) Yedekte kalanlar: optimal kadro vs gerçek ----------
    bench = {t: {"gain": 0.0, "pts": 0, "games": 0, "lost": [], "worst": None, "empty": 0} for t in teams}
    worst_all = []
    wk_act, wk_opt = {}, {}
    for k, day in days.items():
        sp = int(k)
        w = sp_week.get(sp)
        for ts, rows in day.items():
            t = int(ts)
            if t not in bench:
                continue
            act, opt = {}, {}
            cands, lines = [], {}
            for pid, slot, line in rows:
                if not line:
                    continue
                lines[pid] = (slot, line)
                if slot != IR:
                    cands.append((gz(line, Z), pid))
            chosen = best_lineup(cands, elig)
            n_active_played = 0
            for pid, (slot, line) in lines.items():
                if slot not in (BENCH, IR):
                    add_lines(act, line)
                    n_active_played += 1
                if pid in chosen:
                    add_lines(opt, line)
            if w:
                for src, dst in ((act, wk_act), (opt, wk_opt)):
                    acc = dst.setdefault((t, w), {})
                    for kk, v in src.items():
                        acc[kk] = acc.get(kk, 0) + v
            missed = [(gz(lines[p][1], Z), p) for p in chosen if lines[p][0] == BENCH]
            if not missed:
                continue
            g_act = sum(gz(l, Z) for pid, (s, l) in lines.items() if s not in (BENCH, IR))
            g_opt = sum(gz(lines[p][1], Z) for p in chosen)
            b = bench[t]
            b["gain"] += max(0.0, g_opt - g_act)
            b["games"] += len(missed)
            b["pts"] += sum(lines[p][1][I["PTS"]] for _, p in missed)
            v, p = max(missed)
            item = {"team": t, "pid": p, "name": pname(p), "sp": sp, "date": fmt_day(sp_date.get(sp)), "w": w,
                    "val": round(v, 1), "line": line_dict(lines[p][1])}
            worst_all.append(item)
            if not b["worst"] or v > b["worst"]["val"]:
                b["worst"] = item
    # haftalık: yedek yüzünden kaybedilen maçlar
    for t, tm in teams.items():
        for i, g in enumerate(tm["games"]):
            w = g["w"]
            if w not in done_weeks or (t, w) not in wk_act or (g["oppId"], w) not in wk_act:
                continue
            me_a, me_o = cats_of(wk_act[(t, w)]), cats_of(wk_opt[(t, w)])
            opp = cats_of(wk_act[(g["oppId"], w)])
            aw, al = cat_score(me_a, opp)
            ow, ol = cat_score(me_o, opp)
            if g["res"] != "G" and ow > ol and (aw, al) == tuple(int(x) for x in g["score"].split("-")[:2]):
                bench[t]["lost"].append({"w": w, "opp": g["oppId"], "score": g["score"], "opt": f"{ow}-{ol}"})
    out["bench"] = sorted(({"team": t, "gain": round(b["gain"], 1), "pts": int(b["pts"]), "games": b["games"],
                            "lost": b["lost"], "worst": b["worst"]} for t, b in bench.items()), key=lambda x: -x["gain"])
    out["benchWorst"] = sorted(worst_all, key=lambda x: -x["val"])[:5]

    # ---------- işlemler: sahiplik dönemleri ----------
    txs = sorted(tx.values(), key=lambda x: (x["sp"], x.get("date") or 0))
    stints = []  # {pid, team, start, end, how}
    openst = {}
    for p in draft:
        st = {"pid": p[3], "team": p[2], "start": 1, "end": None, "how": "draft", "pick": p[0]}
        stints.append(st)
        openst[(p[3], p[2])] = st
    trades = []
    for x in txs:
        tr_items = [i for i in x["items"] if i[0] == "TRADE"]
        if tr_items:
            trades.append(x)
        for typ, pid, frm, to in sorted(x["items"], key=lambda i: i[0] != "DROP" and i[0] != "TRADE"):
            if frm and (pid, frm) in openst:
                openst.pop((pid, frm))["end"] = x["sp"]
            if typ == "DROP":
                stints.append({"pid": pid, "team": frm, "start": x["sp"], "end": None, "how": "drop", "dropped": True})
            if to:
                st = {"pid": pid, "team": to, "start": x["sp"], "end": None,
                      "how": "trade" if typ == "TRADE" else "waiver" if x["type"] == "WAIVER" else "fa"}
                stints.append(st)
                openst[(pid, to)] = st

    def active_value(pid, team, start, end):
        """Oyuncunun o takımda, aktif kadroda oynadığı maçların değeri (yedek seviyesinin üstü)."""
        val, n, tot = 0.0, 0, {}
        for k, day in days.items():
            sp = int(k)
            if sp < start or (end and sp >= end):
                continue
            for p, slot, line in day.get(str(team), []):
                if p == pid and line and slot not in (BENCH, IR):
                    val += gz(line, Z) - repl
                    n += 1
                    add_lines(tot, line)
        return val, n, tot

    def log_value(pid, start, end=None):
        val, n, tot = 0.0, 0, {}
        for k, line in (logs.get(str(pid)) or {}).items():
            sp = int(k)
            if sp < start or (end and sp >= end):
                continue
            val += gz(line, Z) - repl
            n += 1
            add_lines(tot, line)
        return val, n, tot

    def per_game(tot, n):
        return {c: round(tot.get(c, 0) / n, 1) for c in ("PTS", "REB", "AST", "STL", "BLK", "3PM")} if n else {}

    def owner_now(pid):
        p = pvals.get(pid)
        return p["team"] if p else 0

    # ---------- 2) Waiver kahramanı ----------
    adds = []
    for st in stints:
        if st["how"] in ("waiver", "fa"):
            v, n, tot = active_value(st["pid"], st["team"], st["start"], st["end"])
            if n:
                adds.append({"team": st["team"], "pid": st["pid"], "name": pname(st["pid"]), "sp": st["start"],
                             "date": fmt_day(sp_date.get(st["start"])), "val": round(v, 1), "n": n, "pg": per_game(tot, n),
                             "kept": st["end"] is None})
    adds.sort(key=lambda a: -a["val"])
    by_team = {}
    for a in adds:
        b = by_team.setdefault(a["team"], {"team": a["team"], "val": 0.0, "n": 0, "adds": 0})
        b["val"] += max(0, a["val"]); b["n"] += a["n"]; b["adds"] += 1
    for t in teams:
        by_team.setdefault(t, {"team": t, "val": 0.0, "n": 0, "adds": 0})
    out["waiver"] = {"top": adds[:8], "teams": sorted(({**b, "val": round(b["val"], 1)} for b in by_team.values()), key=lambda b: -b["val"]),
                     "count": sum(1 for x in txs if any(i[0] == "ADD" for i in x["items"]))}

    # ---------- 3) Bırakıp pişman olanlar ----------
    regrets = []
    for st in stints:
        if st["how"] != "drop":
            continue
        v, n, tot = log_value(st["pid"], st["start"] + 1)
        if n >= 3:
            regrets.append({"team": st["team"], "pid": st["pid"], "name": pname(st["pid"]), "sp": st["start"],
                            "date": fmt_day(sp_date.get(st["start"])), "val": round(v, 1), "n": n, "pg": per_game(tot, n),
                            "now": owner_now(st["pid"])})
    regrets.sort(key=lambda r: -r["val"])
    seen = set()
    out["regrets"] = [r for r in regrets if not ((r["pid"], r["team"]) in seen or seen.add((r["pid"], r["team"])))][:8]

    # ---------- 4) Takas karnesi ----------
    trade_cards = []
    for x in trades:
        sides = {}
        for typ, pid, frm, to in x["items"]:
            if typ != "TRADE":
                continue
            sides.setdefault(to, {"team": to, "got": [], "val": 0.0, "now": 0.0})
            sides.setdefault(frm, {"team": frm, "got": [], "val": 0.0, "now": 0.0})
            v, n, tot = active_value(pid, to, x["sp"], None)
            pv = pvals.get(pid, {}).get("val")
            sides[to]["got"].append({"pid": pid, "name": pname(pid), "val": round(v, 1), "n": n,
                                     "rate": round(pv, 1) if pv is not None else None})
            sides[to]["val"] += v
            sides[to]["now"] += (pv or 0) - repl
        if len(sides) < 2:
            continue
        rows = list(sides.values())
        # sonuç: %60 takastan bu yana gerçekleşen, %40 oyuncuların şu anki değeri (kalan sezon)
        for r in rows:
            r["score"] = 0.6 * r["val"] + 0.4 * r["now"] * 10
        tot_abs = sum(abs(r["score"]) for r in rows) or 1
        for r in rows:
            r["net"] = round(r["score"] - max(o["score"] for o in rows if o is not r), 1)
        for r in rows:
            r["grade"] = grade(r["net"] / max(10.0, tot_abs / len(rows)))
            r["val"] = round(r["val"], 1)
            r["now"] = round(r["now"], 1)
            del r["score"]
        rows.sort(key=lambda r: -r["net"])
        trade_cards.append({"sp": x["sp"], "date": fmt_day(sp_date.get(x["sp"]) or x.get("date")), "sides": rows,
                            "gap": rows[0]["net"]})
    trade_cards.sort(key=lambda c: -c["gap"])
    out["trades"] = trade_cards

    # ---------- 5) Draft karnesi ----------
    if draft:
        dv = []
        for pick, rnd, t, pid in draft:
            v, n, tot = log_value(pid, 1)
            p = pvals.get(pid)
            dv.append({"pick": pick, "round": rnd, "team": t, "pid": pid, "name": pname(pid), "val": round(v, 1), "n": n,
                       "pg": per_game(tot, n), "inj": (p or {}).get("inj", "")})
        ranked = sorted(dv, key=lambda d: -d["val"])
        for i, d in enumerate(ranked):
            d["rank"] = i + 1
        exp = [d["val"] for d in ranked]  # k. seçimin beklenen değeri = k. en iyi çıkan oyuncu
        for d in dv:
            d["exp"] = round(exp[d["pick"] - 1], 1) if d["pick"] <= len(exp) else 0
            d["diff"] = round(d["val"] - d["exp"], 1)
        steals = sorted((d for d in dv if d["rank"] <= 60), key=lambda d: -(d["pick"] - d["rank"]))[:5]
        busts = sorted((d for d in dv if d["pick"] <= 48), key=lambda d: -(d["rank"] - d["pick"]))[:5]
        tg = {}
        for d in dv:
            g = tg.setdefault(d["team"], {"team": d["team"], "diff": 0.0, "val": 0.0, "best": None, "worst": None})
            g["diff"] += d["diff"]; g["val"] += d["val"]
            if not g["best"] or d["pick"] - d["rank"] > g["best"]["pick"] - g["best"]["rank"]:
                g["best"] = d
            if d["round"] <= 6 and (not g["worst"] or d["rank"] - d["pick"] > g["worst"]["rank"] - g["worst"]["pick"]):
                g["worst"] = d
        sdv = statistics.pstdev([g["diff"] for g in tg.values()]) or 1
        for g in tg.values():
            g["grade"] = grade(g["diff"] / sdv)
            g["diff"] = round(g["diff"], 1); g["val"] = round(g["val"], 1)
            g["best"] = slim(g["best"]); g["worst"] = slim(g["worst"])
        first = {}
        for d in sorted(dv, key=lambda d: d["pick"]):
            first.setdefault(d["team"], d["pick"])
        out["draft"] = {"teams": sorted(tg.values(), key=lambda g: -g["diff"]), "steals": [slim(d) for d in steals],
                        "busts": [slim(d) for d in busts], "order": first, "rounds": max(d["round"] for d in dv)}

    # ---------- 6) Sakatlık şanssızlığı ----------
    inj = {t: {"team": t, "games": 0, "val": 0.0, "who": {}} for t in teams}
    for k, day in days.items():
        sp = int(k)
        if sp >= latest:  # bugünün maçları bitmemiş olabilir
            continue
        for ts, rows in day.items():
            t = int(ts)
            if t not in inj:
                continue
            for pid, slot, line in rows:
                if line:
                    continue
                pro = (meta.get(str(pid)) or [0, 0])[1]
                if sp not in team_games.get(pro, ()):
                    continue
                p = pvals.get(pid)
                pv = p["val"] if p else None
                if pv is None:
                    gl = logs.get(str(pid)) or {}
                    pv = statistics.mean(gz(l, Z) for l in gl.values()) if gl else repl
                if pv <= repl:
                    continue
                inj[t]["games"] += 1
                inj[t]["val"] += pv - repl
                w = inj[t]["who"].setdefault(pid, [pname(pid), 0])
                w[1] += 1
    out["injury"] = sorted(({"team": t, "games": v["games"], "val": round(v["val"], 1),
                             "who": [{"name": a, "n": b} for a, b in sorted(v["who"].values(), key=lambda x: -x[1])[:3]]}
                            for t, v in inj.items()), key=lambda x: -x["val"])

    # ---------- 7) Rekorlar ----------
    rec = {"week": {}, "game": {}, "day": None}
    allw = []  # (season, w, team-name, owner, cats)
    for y, (Ly, dy) in (seasons or {}).items():
        for t in dy["teams"]:
            for i, wk in enumerate(t.get("_wk") or []):
                allw.append((y, t["games"][i]["w"], t["name"], t["id"] if y == cur_season else None, wk))
    if not allw:
        for t in data["teams"]:
            for i, wk in enumerate(t.get("_wk") or []):
                allw.append((None, t["games"][i]["w"], t["name"], t["id"], wk))
    cur_y = cur_season
    for c in CATS:
        s = SID[c]
        vals_c = [a for a in allw if s in a[4]]
        if not vals_c:
            continue
        hi = max(vals_c, key=lambda a: a[4][s])
        lo = min(vals_c, key=lambda a: a[4][s])
        if c == "TO":
            hi, lo = lo, hi
        rec["week"][c] = {"best": wrec(hi, s, cur_y), "worst": wrec(lo, s, cur_y)}
    best_games = {c: None for c in ("PTS", "REB", "AST", "STL", "BLK", "3PM")}
    best_gz, best_day = None, None
    for k, day in days.items():
        sp = int(k)
        for ts, rows in day.items():
            dtot = 0
            for pid, slot, line in rows:
                if not line or slot in (BENCH, IR):
                    continue
                dtot += line[I["PTS"]]
                for c in best_games:
                    if not best_games[c] or line[I[c]] > best_games[c]["v"]:
                        best_games[c] = {"v": line[I[c]], "pid": pid, "name": pname(pid), "team": int(ts), "sp": sp,
                                         "date": fmt_day(sp_date.get(sp)), "line": line_dict(line)}
                g = gz(line, Z)
                if not best_gz or g > best_gz["val"]:
                    best_gz = {"val": round(g, 1), "pid": pid, "name": pname(pid), "team": int(ts), "sp": sp,
                               "date": fmt_day(sp_date.get(sp)), "line": line_dict(line)}
            if not best_day or dtot > best_day["v"]:
                best_day = {"v": int(dtot), "team": int(ts), "sp": sp, "date": fmt_day(sp_date.get(sp))}
    rec["game"] = best_games
    rec["bestGame"] = best_gz
    rec["day"] = best_day
    out["records"] = rec

    # ---------- 8) Rekabetler ve farklı skorlar ----------
    games_all = []
    for y, (Ly, dy) in (seasons or {"cur": (raw["league"], data)}).items():
        ok = {t["id"]: owner_key_of(t) for t in Ly["teams"]}
        nm = {t["id"]: t["name"] for t in dy["teams"]}
        for t in dy["teams"]:
            for g in t["games"]:
                if t["id"] < g["oppId"]:
                    a, b = (int(x) for x in g["score"].split("-")[:2])
                    games_all.append({"y": y, "w": g["w"], "a": ok.get(t["id"]), "b": ok.get(g["oppId"]),
                                      "an": nm[t["id"]], "bn": nm[g["oppId"]], "s": [a, b],
                                      "ta": t["id"] if y in (cur_season, "cur") else None,
                                      "tb": g["oppId"] if y in (cur_season, "cur") else None})
    blow = sorted(games_all, key=lambda g: (-abs(g["s"][0] - g["s"][1]), -max(g["s"])))[:6]
    close = [g for g in games_all if abs(g["s"][0] - g["s"][1]) <= 1]
    out["blowouts"] = blow
    out["closeCount"] = len(close)
    out["nGames"] = len(games_all)
    pairs = {}
    for g in games_all:
        if not g["a"] or not g["b"]:
            continue
        k = tuple(sorted((g["a"], g["b"])))
        p = pairs.setdefault(k, {"a": k[0], "b": k[1], "w": [0, 0, 0], "cats": [0, 0], "n": 0, "close": 0})
        sa, sb = (g["s"][0], g["s"][1]) if g["a"] == k[0] else (g["s"][1], g["s"][0])
        p["w"][0 if sa > sb else 1 if sb > sa else 2] += 1
        p["cats"][0] += sa; p["cats"][1] += sb
        p["n"] += 1
        p["close"] += abs(sa - sb) <= 1
    riv = sorted(pairs.values(), key=lambda p: (-p["n"], abs(p["cats"][0] - p["cats"][1]) - p["close"] * 2))
    out["rivals"] = riv[:8]
    lopsided = [p for p in pairs.values() if p["n"] >= 2 and (p["w"][0] == 0 or p["w"][1] == 0)]
    out["owned"] = sorted(lopsided, key=lambda p: (-p["n"], -abs(p["cats"][0] - p["cats"][1])))[:5]

    # ---------- 9) Takım kişilikleri ----------
    out["personality"] = personalities(data["teams"])
    out["latest"] = latest
    out["days"] = len(days)
    return out


def owner_key_of(team):
    import hashlib
    o = team.get("primaryOwner") or (team.get("owners") or [""])[0] or f"team-{team['id']}"
    return hashlib.sha1(o.encode()).hexdigest()[:10]


def wrec(a, s, cur_y):
    y, w, name, tid, wk = a
    v = wk[s]
    return {"v": round(v, 4) if s in ("19", "20") else round(v), "y": y, "w": w, "name": name, "team": tid, "cur": y == cur_y}


def slim(d):
    if not d:
        return None
    return {k: d[k] for k in ("pick", "round", "team", "pid", "name", "val", "n", "rank", "pg", "inj") if k in d}


def grade(z):
    for cut, g in ((1.5, "A+"), (1.0, "A"), (0.6, "A-"), (0.3, "B+"), (0.0, "B"), (-0.3, "B-"), (-0.6, "C+"),
                   (-1.0, "C"), (-1.5, "D")):
        if z >= cut:
            return g
    return "F"


PERS = [
    # (anahtar, koşul puanı fonksiyonu)  — sıra: 1 en iyi, 12 en kötü
    ("paint", lambda r, t: 4.5 - (r["REB"] + r["BLK"] + r["FG%"]) / 3),
    ("rain", lambda r, t: 4.0 - (r["3PM"] * 2 + r["PTS"]) / 3),
    ("dime", lambda r, t: 3.5 - (r["AST"] * 2 + r["STL"]) / 3),
    ("thief", lambda r, t: 2.5 - r["STL"]),
    ("line", lambda r, t: 2.5 - r["FT%"]),
    ("puntft", lambda r, t: (r["FT%"] - 10) + (4 - min(r["REB"], r["BLK"], r["FG%"])) * .5 if r["FT%"] >= 10 else -9),
    ("puntto", lambda r, t: (r["TO"] - 10) + (4 - min(r["AST"], r["PTS"])) * .5 if r["TO"] >= 10 else -9),
    ("careful", lambda r, t: (3 - r["TO"]) if r["AST"] >= 8 else -9),
    ("scorer", lambda r, t: 2.5 - r["PTS"]),
    ("balanced", lambda r, t: 2.6 - statistics.pstdev(list(r.values()))),
    ("grinder", lambda r, t: (t["adds"] - t["_addsMed"]) / max(2, t["_addsMed"]) * 1.2 - .4),
    ("loyal", lambda r, t: 1.2 - t["adds"] / max(1, t["_addsMed"]) * 2 if t["adds"] <= t["_addsMed"] / 2 else -9),
    ("rebuild", lambda r, t: (statistics.mean(r.values()) - 8.2)),
]


def personalities(teams):
    """Her takıma kategori profiline göre etiket; birincil etiketler mümkün olduğunca tekil."""
    med = statistics.median([t.get("adds", 0) for t in teams]) or 1
    scores = {}
    for t in teams:
        tt = {**t, "_addsMed": med}
        scores[t["id"]] = {k: f(t["rank"], tt) for k, f in PERS}
    prim, used = {}, set()
    for v, tid, k in sorted(((v, tid, k) for tid, sc in scores.items() for k, v in sc.items()), reverse=True):
        if v <= 0 or tid in prim or k in used:
            continue
        prim[tid] = k
        used.add(k)
    res = {}
    for t in teams:
        sc = scores[t["id"]]
        order = sorted(sc, key=lambda k: -sc[k])
        p = prim.get(t["id"]) or order[0]
        sec = [k for k in order if k != p and sc[k] > 0][:1]
        r = t["rank"]
        res[t["id"]] = {"labels": [p] + sec, "best": sorted(r, key=lambda c: r[c])[:3], "worst": sorted(r, key=lambda c: -r[c])[:2]}
    return res
