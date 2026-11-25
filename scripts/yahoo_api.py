"""Yahoo Fantasy API istemcisi. Kimlik bilgileri ortamdan gelir: YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REFRESH_TOKEN."""
import base64, json, os, urllib.error, urllib.parse, urllib.request

TOKEN = "https://api.login.yahoo.com/oauth2/get_token"
API = "https://fantasysports.yahooapis.com/fantasy/v2/"
_access = None
SCOPE = None


def access_token():
    global _access
    if _access:
        return _access
    cid, secret, ref = (os.environ.get(k) for k in ("YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_REFRESH_TOKEN"))
    if not (cid and secret and ref):
        raise SystemExit("YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET / YAHOO_REFRESH_TOKEN eksik")
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": ref,
                                   "redirect_uri": os.environ.get("YAHOO_REDIRECT_URI", "https://nac-nac31.github.io/nbafan/")}).encode()
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(TOKEN, data=body, headers={"Authorization": f"Basic {basic}",
                                                            "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.load(r)
            _access = tok["access_token"]
            global SCOPE
            SCOPE = tok.get("scope") or tok.get("xoauth_yahoo_guid") and "guid var"
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Yahoo giriş anahtarı reddedildi: HTTP {e.code} {e.read().decode(errors='replace')[:200]}")
    return _access


def get(path):
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(API + path + sep + "format=json", headers={"Authorization": f"Bearer {access_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Yahoo API {path}: HTTP {e.code} {e.read().decode(errors='replace')[:400]}")
