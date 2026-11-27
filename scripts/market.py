"""Takas analizcisi ve waiver radarı için veriler.

build_market(raw, data, season, zref, cats, cn, lower) iki şey ekler:
- data["radar"]: serbest oyuncuların son 7/15/30 gün ve sezon değerleri, yükseliş eğilimi,
  sahiplik değişimi ve kategorisine en çok uydukları takımlar.
- data["tradeSim"]: tarayıcıda takas sonrası sezonu yeniden simüle etmek için girdiler
  (simulate_season ile aynı model: geçmiş haftalar + kadro projeksiyonu).
"""
import statistics

SPLITS = (("l7", "01"), ("l15", "02"), ("l30", "03"), ("sea", "00"))
RAWK = ("0", "6", "3", "2", "1", "17", "11", "13", "14", "15", "16")
INJ = {"OUT": "Sakat", "DAY_TO_DAY": "Belirsiz", "INJURY_RESERVE": "IR", "SUSPENSION": "Ceza"}  # build.INJ ile aynı
INJ_OUT = ("Sakat", "IR", "Ceza")


def zfun(zref, cats, cn):
    mean, sd = zref["mean"], zref["sd"]

    def zs(a):
        z = {}
        fga, fta = a.get("14", 0), a.get("16", 0)
        for c in cats:
            k, v = cn[c], a.get(c, 0)
            if c == "19":
                z[k] = (v - mean[k]) * fga / zref["fga"] / zref["sd_fg"]
            elif c == "20":
                z[k] = (v - mean[k]) * fta / zref["fta"] / zref["sd_ft"]
            elif c == "11":
                z[k] = -(v - mean[k]) / sd[k]
            else:
                z[k] = (v - mean[k]) / sd[k]
        return z
    return zs


def team_weights(team, cn_vals, n_teams):
    """Takımın zayıf olduğu kategoriler daha ağır; açıkça punt edilen (son sıra) kategori hafif."""
    w = {}
    for c in cn_vals:
        r = team["rank"][c]
        x = 1.0
        if r >= n_teams - 4:
            x += 0.5
        if r <= 3:
            x -= 0.3
        if r == n_teams:
            x = 0.4
        w[c] = x
    return w


def build_radar(raw, data, season, zref, cats, cn, row_fn=None):
    zs = zfun(zref, cats, cn)
    cv = [cn[c] for c in cats]
    seen, players = set(), []
    for src in ("freeagents", "freeagents_hot"):
        for p in (raw.get(src) or {}).get("players", []):
            pl = p["player"]
            if pl["id"] in seen:
                continue
            seen.add(pl["id"])
            players.append((p, pl))
    rows_by_id = {r["id"]: r for r in data.get("players", [])}
    teams = data["teams"]
    n = len(teams)
    weights = {t["id"]: team_weights(t, cv, n) for t in teams}
    # her takımın bırakma adayı: sağlıklı oyuncular arasında en düşük değerli
    worst = {}
    for t in teams:
        mine = [r for r in data["players"] if r["team"] == t["id"] and r.get("slot") != "IR"
                and r["inj"] not in ("Sakat", "IR")]
        if mine:
            worst[t["id"]] = min(mine, key=lambda r: r["val"])
    out = []
    for p, pl in players:
        st = {s["id"]: (s.get("averageStats") or {}) for s in pl.get("stats", [])}
        sp = {k: st.get(f"{code}{season}", {}) for k, code in SPLITS}
        gp = {k: int(v.get("42", 0)) for k, v in sp.items()}
        if gp["l15"] < 2 and gp["l7"] < 2:
            continue
        vals, zz = {}, {}
        for k in sp:
            if gp[k] >= 1:
                z = zs(sp[k])
                zz[k] = z
                vals[k] = round(sum(z.values()), 2)
        base = vals.get("sea") if gp["sea"] >= 5 else vals.get("l30")
        recent = vals.get("l7") if gp["l7"] >= 2 else vals.get("l15")
        trend = round(recent - base, 2) if recent is not None and base is not None else 0.0
        mins = {k: round(sp[k].get("40", 0), 1) for k in sp if gp[k] >= 1}
        own = pl.get("ownership") or {}
        zf = zz.get("l15") if gp["l15"] >= 3 else zz.get("l7") or zz.get("sea")
        if not zf:
            continue
        fits = []
        for t in teams:
            w = weights[t["id"]]
            wm = sum(w.values()) / len(w)
            mine = sum(w[c] * zf[c] for c in cv)
            wr = worst.get(t["id"])
            theirs = sum(w[c] * wr["z"][c] for c in cv) if wr else 0
            match = sum((w[c] - wm) * zf[c] for c in cv)  # oyuncunun profili takımın ihtiyacına ne kadar uyuyor
            if mine - theirs > 0:  # sadece bırakma adayından daha faydalıysa
                fits.append((round(match, 2), round(mine - theirs, 2), t["id"], wr["id"] if wr else None))
        fits.sort(reverse=True)
        r = rows_by_id.get(pl["id"])
        g = None
        if row_fn:  # maç başı ham istatistik: haftalık ve sezonluk etki hesabı için
            pr = row_fn(pl, season, 0)
            g = pr["g"] if pr else None
        out.append({
            "id": pl["id"], "name": pl.get("fullName", ""), "pos": (r or {}).get("pos", ""),
            "inj": INJ.get(pl.get("injuryStatus") or "", ""), "fa": p.get("status", "FREEAGENT"),
            "pro": pl.get("proTeamId"),
            "owned": round(own.get("percentOwned", 0), 1), "chg": round(own.get("percentChange", 0), 2),
            "gp": gp, "v": vals, "min": mins, "trend": trend,
            "z": {c: round(zf[c], 2) for c in cv},
            "fit": [{"t": tid, "m": m, "g": gn, "drop": d} for m, gn, tid, d in fits[:3]],
            "g": g, "val": (r or {}).get("val", vals.get("l15", vals.get("sea", 0))),
        })
    # radar puanı: son haftalardaki değer + yükseliş + sahiplik ivmesi
    for r in out:
        now = r["v"].get("l7") if r["gp"]["l7"] >= 2 else r["v"].get("l15", -9)
        l15 = r["v"].get("l15", now)
        r["score"] = round(0.45 * now + 0.35 * l15 + 0.35 * max(0, r["trend"]) + min(2.0, max(-1.0, r["chg"] * 0.5)), 2)
        if r["inj"] in INJ_OUT:
            r["score"] -= 3
    out.sort(key=lambda r: -r["score"])
    return out[:80]


def trade_inputs(raw, data, cats, cn, lower):
    """simulate_season ile aynı girdiler; tarayıcı kadro değişince güçleri yeniden hesaplar."""
    L, M = raw["league"], raw["matchups"]
    ss = L["settings"]["scheduleSettings"]
    reg_weeks, n_playoff = ss.get("matchupPeriodCount", 0), ss.get("playoffTeamCount", 0)
    teams = {t["id"]: t for t in data["teams"]}
    if not reg_weeks or not n_playoff or not teams or not all(t.get("_wk") for t in teams.values()):
        return None
    cur = data.get("current") or {}
    cur_week = cur.get("week") or 0
    hist, pooled = {}, {}
    for c in cats:
        allv = [w[c] for t in teams.values() for w in t["_wk"]]
        lg = statistics.mean(allv)
        resid = []
        for tid, t in teams.items():
            vals = [w[c] for w in t["_wk"]]
            m = statistics.mean(vals)
            resid += [v - m for v in vals]
            hist.setdefault(tid, {})[cn[c]] = round((len(vals) * m + 3 * lg) / (len(vals) + 3), 5)
        pooled[cn[c]] = round((statistics.pstdev(resid) or abs(lg) * 0.1 or 1) * 1.1, 5)
    slots = {e["playerId"]: e.get("lineupSlotId") for t in raw.get("rosters", {}).get("teams", []) for e in t["roster"]["entries"]}
    half = [p["id"] for p in data["players"] if p["team"] and (p["inj"] in ("Sakat", "IR") or slots.get(p["id"]) == 13)]
    cur_p = []
    for mt in cur.get("matchups", []):
        if "proj" in mt:
            cur_p.append([mt["home"], mt["away"], [mt["proj"]["pc"][cn[c]] for c in cats]])
    future = [[m["home"]["teamId"], m["away"]["teamId"]] for m in M["schedule"]
              if "home" in m and "away" in m and m.get("playoffTierType", "NONE") == "NONE"
              and cur_week < m["matchupPeriodId"] <= reg_weeks]
    if cur_week and not cur_p:
        future += [[m["home"]["teamId"], m["away"]["teamId"]] for m in M["schedule"]
                   if m.get("matchupPeriodId") == cur_week and "home" in m and "away" in m]
    # kategori kodu -> ham istatistik anahtarı (yüzdeler isabet/deneme ile)
    keymap = {cn[c]: (["13", "14"] if c == "19" else ["15", "16"] if c == "20" else [c]) for c in cats}
    return {"hist": hist, "pooled": pooled, "half": half, "curP": cur_p, "future": future,
            "base": {tid: list(t["cat"]) for tid, t in teams.items()}, "playoffTeams": n_playoff,
            "lower": [cn[c] for c in cats if c in lower], "keys": keymap, "perWeek": 3.3}


def best_free_agents(raw, data, season, row_fn, n=8):
    """Eşit olmayan takaslarda boşalan yere alınacak en iyi sağlıklı serbest oyuncular (maç başı ham istatistikle)."""
    raws = {p["player"]["id"]: p["player"] for src in ("freeagents", "freeagents_hot") for p in (raw.get(src) or {}).get("players", [])}
    out = []
    for r in data["players"]:
        if r["team"] or r["gp"] < 3 or r["inj"] in ("Sakat", "IR") or r["id"] not in raws:
            continue
        row = row_fn(raws[r["id"]], season, 0)
        if row:
            out.append({"id": r["id"], "name": r["name"], "val": r["val"], "g": row["g"]})
        if len(out) >= n:
            break
    return out


def build_market(raw, data, season, zref, cats, cn, lower, row_fn=None):
    if zref:
        data["radar"] = build_radar(raw, data, season, zref, cats, cn, row_fn)
    ti = trade_inputs(raw, data, cats, cn, lower)
    if ti:
        ti["fa"] = best_free_agents(raw, data, season, row_fn) if row_fn else []
        data["tradeSim"] = ti
