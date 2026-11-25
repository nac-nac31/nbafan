"""ntfy ile telefon bildirimleri. Her takımın kanalı <önek>-<takımId>, lig kanalı <önek>-lig.

Önceki çalışmanın durumu data/alerts_state.json'da tutulur; sadece değişiklikler bildirilir:
- bu haftaki maçta tahmini favori ya da skor lideri değişirse (iki takıma)
- kadrodaki bir oyuncunun sakatlık durumu değişirse (o takıma)
- yeni hafta başladığında haftanın hikayesi (lig kanalına)
Gönderim sadece NTFY_ENABLED=1 iken yapılır (GitHub Actions); yerelde sadece yazdırılır."""
import hashlib, json, os, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "alerts_state.json"
SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
SITE = os.environ.get("SITE_URL", "https://nac-nac31.github.io/nbafan/")
INJ_TXT = {"": "sağlıklı", "Sakat": "sakat (oynamayacak)", "Belirsiz": "belirsiz (maç günü kararı)", "IR": "IR'de", "Ceza": "cezalı"}


def prefix(league_id):
    return os.environ.get("NTFY_PREFIX") or "nbafan-" + hashlib.sha1(str(league_id).encode()).hexdigest()[:8]


def send(topic, title, msg, click, tags=None, priority=3):
    body = {"topic": topic, "title": title, "message": msg, "click": click, "tags": tags or [], "priority": priority}
    if os.environ.get("NTFY_ENABLED") != "1":
        print(f"[ntfy kuru] {topic}: {title} | {msg}")
        return
    req = urllib.request.Request(SERVER + "/", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "nbafan-stats"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
        print(f"[ntfy] {topic}: {title}")
    except Exception as e:
        print(f"[ntfy hata] {topic}: {e}")


def snapshot(data):
    cur = data.get("current") or {}
    ms = {}
    for m in cur.get("matchups", []):
        p = (m.get("proj") or {}).get("win")
        ms[f"{m['home']}-{m['away']}"] = {"score": m["score"], "win": p}
    inj = {}
    for p in data.get("players", []):
        if p.get("team"):
            inj[str(p["id"])] = [p["team"], "IR" if p.get("slot") == "IR" and not p.get("inj") else p.get("inj", ""), p["name"]]
    st = data.get("story") or {}
    return {"week": cur.get("week"), "matchups": ms, "inj": inj, "storyWeek": st.get("week")}


def run(data, raw, daily=None):
    lid = (raw.get("league") or {}).get("id") or os.environ.get("ESPN_LEAGUE_ID", "1540046349")
    pre = prefix(lid)
    data["notify"] = {"server": SERVER, "prefix": pre}
    names = {t["id"]: t["name"] for t in data["teams"]}
    now = snapshot(data)
    prev = json.loads(STATE.read_text()) if STATE.exists() else None
    # favori: ancak %57'yi geçince değişmiş sayılır (50 civarında gidip gelen maç her güncellemede bildirim atmasın)
    for k, m in now["matchups"].items():
        o = (prev or {}).get("matchups", {}).get(k) if prev and prev.get("week") == now["week"] else None
        pf = o.get("fav") if o else None
        w = m["win"]
        m["fav"] = pf if w is None or abs(w - 0.5) < 0.07 else (w >= 0.5)
    STATE.write_text(json.dumps(now, ensure_ascii=False, indent=1))
    if not prev:
        print("bildirim: ilk çalışma, durum kaydedildi")
        return
    n = 0
    # 1) maç dönüşleri
    if prev.get("week") == now["week"]:
        for k, m in now["matchups"].items():
            o = prev["matchups"].get(k)
            if not o:
                continue
            h, a = (int(x) for x in k.split("-"))
            s, ps = m["score"], o["score"]
            lead = (s[0] > s[1]) - (s[0] < s[1])
            plead = (ps[0] > ps[1]) - (ps[0] < ps[1])
            fav, pfav = m.get("fav"), o.get("fav")
            sc = f"{s[0]}-{s[1]}" + (f"-{s[2]}" if len(s) > 2 and s[2] else "")
            link = SITE + "#bu-hafta"
            if lead != plead and lead != 0:
                w, l = (h, a) if lead > 0 else (a, h)
                for t, txt in ((w, f"{names[l]} karşısında öne geçtin: {sc}"), (l, f"{names[w]} öne geçti: {sc}")):
                    send(f"{pre}-{t}", "Skor değişti", txt, link, ["basketball"], 4)
                    n += 1
            elif fav is not None and pfav is not None and fav != pfav:
                f, u = (h, a) if fav else (a, h)
                p = round((m["win"] if fav else 1 - m["win"]) * 100)
                for t, txt in ((f, f"Model artık seni favori görüyor: %{p} ({names[u]} maçı, şu an {sc})"),
                               (u, f"Model artık {names[f]} takımını favori görüyor: %{p} (şu an {sc})")):
                    send(f"{pre}-{t}", "Maç tersine döndü", txt, link, ["warning"], 4)
                    n += 1
    # 2) sakatlık değişimleri
    for pid, (team, st, name) in now["inj"].items():
        o = prev.get("inj", {}).get(pid)
        if not o or o[0] != team or o[1] == st:
            continue
        bad = st in ("Sakat", "IR", "Ceza") or (st == "Belirsiz" and o[1] == "")
        title = "Kadronda sakatlık" if bad else "Sakatlık güncellemesi"
        send(f"{pre}-{team}", title, f"{name}: {INJ_TXT.get(o[1], o[1])} → {INJ_TXT.get(st, st)}", SITE + "#takimim",
             ["ambulance"] if bad else ["white_check_mark"], 4 if bad else 3)
        n += 1
    # 3) haftanın hikayesi
    st = data.get("story")
    if st and prev.get("storyWeek") is not None and st["week"] != prev.get("storyWeek"):
        send(f"{pre}-lig", f"{data.get('league', '')} · {st['title']['tr']}", "\n".join(st["tr"][:4]), SITE + "#bu-hafta",
             ["trophy"], 3)
        n += 1
    print(f"bildirim: {n} mesaj")
