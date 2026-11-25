"""Yahoo Fantasy API için bir kerelik giriş: uzun ömürlü yenileme anahtarı (refresh token) üretir.

Kendi bilgisayarında çalıştır (Python 3.10+, ek paket gerekmez):
    python scripts/yahoo_auth.py

Client ID ve Client Secret'ı sorar (ekrana yazılmaz), tarayıcıda Yahoo giriş sayfasını açar.
"Agree" deyince Yahoo seni siteye yönlendirir; adres çubuğundaki `code=` değerini buraya yapıştır.
Sonunda çıkan YAHOO_REFRESH_TOKEN'ı GitHub'da Settings → Secrets and variables → Actions'a ekle
(YAHOO_CLIENT_ID ve YAHOO_CLIENT_SECRET ile birlikte). Bu değerleri sohbete veya koda yazma.
"""
import base64, getpass, json, os, urllib.error, urllib.parse, urllib.request, webbrowser

AUTH = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN = "https://api.login.yahoo.com/oauth2/get_token"
REDIRECT = os.environ.get("YAHOO_REDIRECT_URI", "https://nac-nac31.github.io/nbafan/")


def token_request(cid, secret, **fields):
    body = urllib.parse.urlencode({"redirect_uri": REDIRECT, **fields}).encode()
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(TOKEN, data=body, headers={
        "Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    cid = os.environ.get("YAHOO_CLIENT_ID") or input("Client ID: ").strip()
    secret = os.environ.get("YAHOO_CLIENT_SECRET") or getpass.getpass("Client Secret (ekrana yazılmaz): ").strip()
    url = AUTH + "?" + urllib.parse.urlencode({"client_id": cid, "redirect_uri": REDIRECT, "response_type": "code"})
    print("\nTarayıcıda açılıyor (açılmazsa bu adresi kopyala):\n" + url + "\n")
    webbrowser.open(url)
    got = input("Yönlendirilen sayfanın adresini ya da sadece code değerini yapıştır: ").strip()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(got).query).get("code", [got])[0]
    try:
        tok = token_request(cid, secret, grant_type="authorization_code", code=code)
    except urllib.error.HTTPError as e:
        print(f"\nYahoo hata verdi (HTTP {e.code}): {e.read().decode(errors='replace')[:300]}")
        print("Kod tek kullanımlık ve birkaç dakikada geçersiz olur: betiği yeniden çalıştırıp yeni kodu hemen yapıştır.")
        print("Redirect URI Yahoo uygulamasındakiyle birebir aynı olmalı: " + REDIRECT)
        raise SystemExit(1)
    except urllib.error.URLError as e:
        print(f"\nBağlantı hatası: {e.reason}")
        if "CERTIFICATE" in str(e.reason):
            print("Mac'te Python sertifikaları eksik. Finder > Uygulamalar > Python 3.x > 'Install Certificates.command' çift tıkla, sonra tekrar dene.")
        raise SystemExit(1)
    print("\nTamam. GitHub'a secret olarak ekle:\n")
    print("YAHOO_REFRESH_TOKEN =", tok["refresh_token"])
    print("\n(YAHOO_CLIENT_ID ve YAHOO_CLIENT_SECRET'ı da ekle.)")


if __name__ == "__main__":
    main()
