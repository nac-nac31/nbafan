"""build.py'den sonra çalışır: haftanın hikayesi, paylaşım görseli verisi, PWA dosyaları ve bildirimler.

Motoru (build.py) değiştirmeden data/stats.json'a "story" ekler, sayfaları yeniden üretir ve
site/ altına manifest, service worker ve ikonları koyar."""
import datetime, json, os, pathlib, shutil, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build  # noqa: E402
import fun  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE_URL = os.environ.get("SITE_URL", "https://nac-nac31.github.io/nbafan/")


def load_raw(season):
    d = ROOT / "data" / "raw" / str(season)
    raw = {}
    for n in ("league", "matchups", "rosters", "freeagents", "proschedule"):
        f = d / f"{n}.json"
        if f.exists():
            raw[n] = json.loads(f.read_text())
    return raw


def sp_weeks(raw):
    out = {}
    for m in (raw.get("matchups") or {}).get("schedule", []):
        if "home" in m:
            for k in (m["home"].get("pointsByScoringPeriod") or {}):
                out[int(k)] = m["matchupPeriodId"]
    return out


def week_players(raw, daily, week, Z):
    """Haftanın oyuncusu (aktif kadroda toplam 9-kat değeri) ve haftanın tek maçı."""
    if not daily or not Z:
        return None, None
    spw = sp_weeks(raw)
    meta = daily.get("players", {})
    tot, best = {}, None
    for k, day in daily.get("days", {}).items():
        if spw.get(int(k)) != week:
            continue
        for ts, rows in day.items():
            for pid, slot, line in rows:
                if not line or slot in (fun.BENCH, fun.IR):
                    continue
                g = fun.gz(line, Z)
                a = tot.setdefault((pid, int(ts)), {"z": 0.0, "n": 0, "line": {}})
                a["z"] += g
                a["n"] += 1
                fun.add_lines(a["line"], line)
                if not best or g > best["z"]:
                    best = {"pid": pid, "team": int(ts), "z": round(g, 1), "name": (meta.get(str(pid)) or [""])[0],
                            "line": fun.line_dict(line)}
    if not tot:
        return None, best
    (pid, t), a = max(tot.items(), key=lambda kv: kv[1]["z"])
    pw = {"pid": pid, "team": t, "z": round(a["z"], 1), "n": a["n"], "name": (meta.get(str(pid)) or [""])[0],
          "pg": {c: round(a["line"].get(c, 0) / a["n"], 1) for c in ("PTS", "REB", "AST", "STL", "BLK", "3PM")}}
    return pw, best


def num(x):
    v = float(x)
    return int(v) if v.is_integer() else v


def fmt(v):
    return f"{v:g}" if isinstance(v, int) or float(v).is_integer() else f"{v:.1f}"


def rec(r):
    return "-".join(str(x) for x in (r if len(r) < 3 or r[2] else r[:2]))


def streak(games):
    if not games:
        return "", 0
    last, n = games[-1]["res"], 0
    for g in reversed(games):
        if g["res"] != last:
            break
        n += 1
    return last, n


def statline(pg, lang):
    lab = {"tr": {"PTS": "sayı", "REB": "ribaund", "AST": "asist", "STL": "top çalma", "BLK": "blok", "3PM": "üçlük"},
           "en": {"PTS": "pts", "REB": "reb", "AST": "ast", "STL": "stl", "BLK": "blk", "3PM": "3pm"}}[lang]
    keep = ["PTS"] + [c for c, m in (("REB", 6), ("AST", 5), ("3PM", 3), ("STL", 2), ("BLK", 2)) if pg.get(c, 0) >= m]
    return ", ".join(f"{pg[c]:g} {lab[c]}" for c in keep[:4])


def build_story(data, raw, daily, Z):
    W = len(data.get("weeks") or [])
    if not W:
        return None
    T = {t["id"]: t for t in data["teams"]}
    pts = data.get("scoring") == "H2H_POINTS"
    nopp = data.get("nOpp") or len(T) - 1
    nm = lambda i: T[i]["name"]
    power = sorted(T.values(), key=lambda t: -t["power"])
    prank = {t["id"]: i + 1 for i, t in enumerate(power)}
    res = []
    for t in T.values():
        g = next((g for g in t["games"] if g["w"] == W), None)
        if g and t["id"] < g["oppId"]:
            a, b = (num(x) for x in g["score"].split("-")[:2])
            og = next(x for x in T[g["oppId"]]["games"] if x["w"] == W)
            res.append({"a": t["id"], "b": g["oppId"], "s": [a, b], "beat": [g["beat"], og["beat"]]})
    res.sort(key=lambda r: -abs(r["s"][0] - r["s"][1]))
    win = lambda r: (r["a"], r["b"]) if r["s"][0] > r["s"][1] else (r["b"], r["a"]) if r["s"][1] > r["s"][0] else (None, None)
    blow = res[0] if res and res[0]["s"][0] != res[0]["s"][1] else None
    # kıl payı: kategori liginde en fazla 1 kategori, puan liginde kazananın %3'ü kadar fark
    close = [r for r in res if abs(r["s"][0] - r["s"][1]) <= (0.03 * max(r["s"]) if pts else 1)]
    beats = {t: next(g["beat"] for g in T[t]["games"] if g["w"] == W) for t in T}
    king = max(beats, key=beats.get)
    losers = [(beats[l], l, w) for r in res for w, l in [win(r)] if l]
    unlucky = max(losers) if losers else None
    upsets = [(prank[w] - prank[l], w, l, r) for r in res for w, l in [win(r)] if w and prank[w] - prank[l] >= 4]
    upset = max(upsets) if upsets else None
    pw, bg = week_players(raw, daily, W, Z)
    leader = max(T.values(), key=lambda t: (t["catPct"], t["apPct"]))
    if pts:
        leader = max(T.values(), key=lambda t: ((t["mrec"][0] + .5 * t["mrec"][2]) / max(1, sum(t["mrec"])), t["apPct"]))
    streaks = sorted(((n, t, r) for t in T for r, n in [streak(T[t]["games"])] if n >= 3 and r in "GM"), reverse=True)
    cur = data.get("current") or {}
    nxt = None
    ms = [m for m in cur.get("matchups", []) if m.get("proj")]
    if ms and cur.get("week") == W + 1:
        m = min(ms, key=lambda m: abs(m["proj"]["win"] - 0.5))
        nxt = {"a": m["home"], "b": m["away"], "p": round(m["proj"]["win"] * 100)}

    def sc(r, w):
        return f"{fmt(max(r['s']))}-{fmt(min(r['s']))}"

    out = {"tr": [], "en": []}

    def add(tr, en):
        out["tr"].append(tr)
        out["en"].append(en)

    if blow:
        w, l = win(blow)
        add(f"{W}. haftanın en sert sonucu {nm(w)} imzalı: {nm(l)} karşısında {sc(blow, w)}.",
            f"The statement win of week {W} belongs to {nm(w)}: {sc(blow, w)} over {nm(l)}.")
    if close:
        parts_tr = [f"{nm(win(r)[0])} {sc(r, 0)} {nm(win(r)[1])}" if win(r)[0] else f"{nm(r['a'])} ile {nm(r['b'])} {fmt(r['s'][0])}-{fmt(r['s'][1])} berabere" for r in close]
        parts_en = [f"{nm(win(r)[0])} edged {nm(win(r)[1])} {sc(r, 0)}" if win(r)[0] else f"{nm(r['a'])} and {nm(r['b'])} tied {fmt(r['s'][0])}-{fmt(r['s'][1])}" for r in close]
        add(f"Kıl payı biten {'maç' if len(close) == 1 else str(len(close)) + ' maç'}: " + "; ".join(parts_tr) + ".",
            f"{'One' if len(close) == 1 else len(close)} went down to the wire: " + "; ".join(parts_en) + ".")
    if upset:
        d, w, l, r = upset
        add(f"Haftanın sürprizi: güç sıralamasında {prank[w]}. olan {nm(w)}, {prank[l]}. sıradaki {nm(l)} takımını {sc(r, w)} yendi.",
            f"Upset of the week: {nm(w)} (No. {prank[w]} in the power rankings) beat No. {prank[l]} {nm(l)} {sc(r, w)}.")
    add(f"All-play şampiyonu {nm(king)}: bu haftaki istatistikleriyle ligdeki {beats[king]} rakibi yenerdi.",
        f"All-play champ: {nm(king)}, whose numbers would have beaten {beats[king]} of {nopp} teams.")
    if unlucky and unlucky[0] >= max(2, round(nopp * .55)):
        b, l, w = unlucky
        add(f"Şanssızlar köşesi: {nm(l)} ligin {b} takımını yenecek istatistik yaptı ama tam da {nm(w)} ile eşleşti.",
            f"Hard-luck loser: {nm(l)} put up numbers good enough to beat {b} teams, and still ran into {nm(w)}.")
    if pw:
        add(f"Haftanın oyuncusu {pw['name']} ({nm(pw['team'])}): {pw['n']} maçta ortalama {statline(pw['pg'], 'tr')}.",
            f"Player of the week: {pw['name']} ({nm(pw['team'])}), averaging {statline(pw['pg'], 'en')} over {pw['n']} games.")
    if bg and (not pw or bg["pid"] != pw["pid"]):
        add(f"Tek maçta en iyisi {bg['name']}: {statline(bg['line'], 'tr')} ({nm(bg['team'])}).",
            f"Best single game: {bg['name']} with {statline(bg['line'], 'en')} for {nm(bg['team'])}.")
    if streaks:
        n, t, r = streaks[0]
        add(f"{nm(t)} üst üste {n} maçtır {'kazanıyor' if r == 'G' else 'kaybediyor'}.",
            f"{nm(t)} {'has won' if r == 'G' else 'has lost'} {n} straight.")
    if pts:
        add(f"Zirvede {nm(leader['id'])} var: {rec(leader['mrec'])}.", f"{nm(leader['id'])} sits on top at {rec(leader['mrec'])}.")
    else:
        add(f"Zirvede {nm(leader['id'])} var: kategori rekoru {rec(leader['cat'])}.",
            f"{nm(leader['id'])} sits on top with a {rec(leader['cat'])} category record.")
    if nxt:
        add(f"Bu haftanın maçı {nm(nxt['a'])} – {nm(nxt['b'])}: model kazanma ihtimalini %{nxt['p']} – %{100 - nxt['p']} görüyor.",
            f"Game of the week: {nm(nxt['a'])} vs {nm(nxt['b'])}, which the model has at {nxt['p']}% – {100 - nxt['p']}%.")
    return {"week": W, "results": res, "tr": out["tr"], "en": out["en"], "nOpp": nopp, "points": pts,
            "pw": pw, "best": bg, "blow": blow, "king": king, "kingBeat": beats[king], "next": nxt,
            "title": {"tr": f"{W}. hafta özeti", "en": f"Week {W} recap"}}


# ---------------- PWA ----------------
def write_pwa(site, data, version):
    static = ROOT / "static"
    for f in static.glob("*"):
        shutil.copy(f, site / f.name)
    name = data.get("league") or "Fantasy"
    for lang, start, fn in (("tr", "./", "manifest.webmanifest"), ("en", "./en.html", "manifest-en.webmanifest")):
        man = {"name": f"{name} · {'Lig Raporu' if lang == 'tr' else 'League Report'}", "short_name": name[:12],
               "lang": lang, "start_url": start, "scope": "./", "display": "standalone",
               "background_color": "#0A130E", "theme_color": "#122A1E",
               "description": "ESPN 9-cat H2H lig istatistikleri" if lang == "tr" else "ESPN 9-cat H2H league stats",
               "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                         {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                         {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
        (site / fn).write_text(json.dumps(man, ensure_ascii=False, indent=1))
    sw = (ROOT / "templates" / "sw.js").read_text().replace("__VERSION__", version)
    (site / "sw.js").write_text(sw)


HEAD_EXTRA = """<link rel="manifest" href="__MAN__"><meta name="theme-color" content="#122A1E">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png"><link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="__SHORT__">
<meta property="og:type" content="website"><meta property="og:title" content="__TITLE__"><meta property="og:description" content="__DESC__">
<meta property="og:image" content="__URL__icon-512.png"><meta property="og:url" content="__URL__"><meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>"""


def page(data, lang):
    html = build.render_page(data, lang)
    st = data.get("story") or {}
    desc = (st.get(lang) or [""])[0]
    extra = (HEAD_EXTRA.replace("__MAN__", "manifest.webmanifest" if lang == "tr" else "manifest-en.webmanifest")
             .replace("__SHORT__", (data.get("league") or "Fantasy")[:12])
             .replace("__TITLE__", build_title(data, lang)).replace("__DESC__", desc.replace('"', "'"))
             .replace("__URL__", SITE_URL))
    html = html.replace("</head>", extra + "</head>", 1)
    js = (ROOT / "templates" / "share.js").read_text()
    return html.replace("</body>", "<script>\n" + js + "\n</script></body>", 1)


def build_title(data, lang):
    st = data.get("story") or {}
    t = (st.get("title") or {}).get(lang, "")
    return f"{data.get('league', '')} · {t}" if t else data.get("league", "")


def main():
    season = int(os.environ.get("SEASON") or build.current_season())
    sp = ROOT / "data" / "stats.json"
    data = json.loads(sp.read_text())
    raw = load_raw(season)
    Z = None
    if raw.get("rosters"):
        if hasattr(build, "configure"):  # lig ayarları (kategoriler / puan) — motorun yeni sürümü
            build.configure(raw["league"])
        build.build_players(raw, season)
        Z = build.ZREF
        if hasattr(fun, "configure"):
            fun.configure(raw["league"], Z)
    dpath = ROOT / "data" / "daily" / f"{season}.json"
    daily = json.loads(dpath.read_text()) if dpath.exists() else None
    data["story"] = build_story(data, raw, daily, Z)
    if data["story"]:
        print("hikaye:", data["story"]["title"]["tr"])
        for s in data["story"]["tr"]:
            print("  ", s)
    try:
        import alerts
        alerts.run(data, raw, daily)  # data["notify"] (kanal adları) burada eklenir
    except Exception as e:  # bildirim hatası siteyi durdurmasın
        import traceback
        traceback.print_exc()
        print("bildirim gönderilemedi:", e)
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    version = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
    write_pwa(site, data, version)
    (site / "index.html").write_text(page(data, "tr"))
    (site / "en.html").write_text(page(data, "en"))
    sp.write_text(json.dumps(data, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
