"""leagues.json'daki her lig için veriyi çeker, siteyi üretir ve site/l/<lig no>/ altına koyar.

Her lig kendi klasöründe çalışır: leagues/<kaynak>-<lig no>/ (data/ ve site/ orada).
Biri hata verirse diğerleri devam eder. Bizim lig bu betiğe dahil değil, ana adreste kalır.

Kullanım:  python scripts/build_all.py            # hepsi
           python scripts/build_all.py 234626984  # yalnızca bu lig
"""
import html, json, os, pathlib, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
NOINDEX = '<meta name="robots" content="noindex">'


def run(cmd, cwd, env, timeout):
    t = time.time()
    p = subprocess.run([sys.executable, str(SCRIPTS / cmd)], cwd=cwd, env=env, timeout=timeout,
                       capture_output=True, text=True)
    tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-4:])
    print(f"  {cmd}: çıkış {p.returncode}, {time.time() - t:.0f} sn\n    " + tail.replace("\n", "\n    "))
    if p.returncode:
        raise RuntimeError(f"{cmd} hata verdi")


def build_one(lg, site_root):
    src, lid = lg["source"], str(lg["id"])
    work = ROOT / "leagues" / f"{src}-{lid}"
    work.mkdir(parents=True, exist_ok=True)
    # Diğer liglere bizim ESPN çerezlerimizi göndermiyoruz: yalnızca açık ligler.
    env = {k: v for k, v in os.environ.items() if k not in ("ESPN_S2", "SWID")}
    if src == "espn":
        env["ESPN_LEAGUE_ID"] = lid
        run("fetch.py", work, env, 1500)
    elif src == "sleeper":
        env["SLEEPER_LEAGUE_ID"] = lid
        run("fetch_sleeper.py", work, env, 600)
        seasons = sorted(p.name for p in (work / "data" / "raw").iterdir() if p.name.isdigit())
        env["SEASON"] = seasons[-1]
    else:
        raise RuntimeError(f"bilinmeyen kaynak: {src}")
    run("build.py", work, env, 900)
    dest = site_root / "l" / lid
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(work / "site", dest)
    if not lg.get("listed", True):
        for f in dest.glob("*.html"):
            f.write_text(f.read_text().replace("<head>", "<head>" + NOINDEX, 1))
    stats = json.loads((work / "data" / "stats.json").read_text())
    return {"id": lid, "source": src, "name": stats.get("league", lid), "teams": len(stats.get("teams", [])),
            "listed": lg.get("listed", True)}


def write_index(site_root, built):
    rows = "".join(f'<li><a href="{b["id"]}/">{html.escape(b["name"])}</a> · {b["source"].upper()} · {b["teams"]} takım</li>'
                   for b in built if b["listed"])
    (site_root / "l").mkdir(parents=True, exist_ok=True)
    (site_root / "l" / "index.html").write_text(
        f'<!doctype html><html lang="tr"><head><meta charset="utf-8">{NOINDEX}'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ligler</title></head>'
        '<body style="font-family:system-ui;background:#0f3d2e;color:#fff;padding:24px">'
        f'<h1>Ligler</h1><ul>{rows or "<li>Henüz listelenen lig yok.</li>"}</ul>'
        '<p><a style="color:#fff" href="../">Ana lig</a></p></body></html>\n')


def main():
    cfg = json.loads((ROOT / "leagues.json").read_text())
    only = set(sys.argv[1:])
    site_root = ROOT / "site"
    built, failed = [], []
    for lg in cfg["leagues"]:
        if only and str(lg["id"]) not in only:
            continue
        print(f"{lg['source']} {lg['id']}:")
        try:
            built.append(build_one(lg, site_root))
        except Exception as e:
            print(f"  ATLANDI: {e}")
            failed.append(str(lg["id"]))
    write_index(site_root, built)
    print(f"{len(built)} lig hazır, {len(failed)} hata" + (f": {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
