# nbafan

ESPN Fantasy Basketball ligi (9-cat H2H) için otomatik istatistik sitesi: power rankings, şans endeksi, haftalık all-play, kötü talih ve soygun maçları, kategori profili, menajer ödülleri.

## Nasıl çalışır

- `scripts/fetch.py` ESPN'in API'sinden ligin ham verisini `data/raw/<sezon>/` altına çeker.
- `scripts/build.py` istatistikleri hesaplar, `data/stats.json` ve `site/index.html` üretir.
- `.github/workflows/update.yml` bunu günde dört kez (TSİ 09:00, 15:00, 21:00, 01:00) çalıştırır ve siteyi GitHub Pages'e yayınlar.

Yerelde çalıştırmak için (Python 3.10+, ek paket gerekmez):

```
python scripts/fetch.py
python scripts/build.py
```

## Ayarlar

- `ESPN_LEAGUE_ID`: lig ID'si (varsayılan 1540046349).
- `SEASON`: sezon (ESPN'de 2026-27 sezonu `2027`). Boş bırakılırsa tarihten hesaplanır.
- `ESPN_S2` ve `SWID`: sadece özel lig ya da geçmiş sezonlar için gerekir. Repo ayarlarında Secrets olarak eklenir, koda yazılmaz.

## İstatistiklerin tanımları

- **All-play:** Takım her hafta diğer 11 takımın hepsiyle oynasaydı kazanacağı kategori oranı.
- **Şans endeksi:** Gerçek kategori kazanma oranı eksi all-play oranı.
- **Power ranking:** %60 sezon all-play + %40 son iki haftanın all-play maç galibiyet oranı.

## Takım logoları

ESPN'in hazır logoları kendiliğinden gelir. Takımların kendi yüklediği resimler ESPN'de giriş yapmayı gerektirdiği için iki yol var:

- Repo ayarlarında `ESPN_S2` ve `SWID` secret'larını eklemek (Settings → Secrets and variables → Actions).
- Resmi repoya `logos/<takım id>.png` olarak eklemek. Elle eklenen resim her zaman önceliklidir.
