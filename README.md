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
- **Playoff/şampiyonluk ihtimali:** `simulate_season` kalan normal sezonu ve playoffları 10.000 kez oynar. Takım gücü kategori başına %50 geçmiş haftalık ortalama (shrink) + %50 güncel kadro projeksiyonu; sezon içi değişim için 200 farklı "güç dünyası" çekilir. ESPN ayarından: 21 hafta, ilk 8 playoff, kategori rekoruna göre sıralama, 1-8/4-5/2-7/3-6, tek haftalık turlar.

## Eğlence sayfası

`scripts/fetch.py` her gün için kadroları (hangi oyuncu hangi slotta) ve o günkü istatistikleri, tüm ekleme/bırakma/takas işlemlerini ve draftı `data/daily/<sezon>.json` dosyasına yazar; biten günler bir daha çekilmez. Oyuncu maç kayıtları her çalışmada `data/raw/<sezon>/gamelogs.json` olarak yenilenir. `scripts/fun.py` bunlardan şunları hesaplar:

- **Yedekte kalanlar:** her gün, oynayan oyunculardan kurala uygun en iyi kadro (açgözlü seçim + slot eşleştirmesi) ile gerçek kadro farkı; en iyi kadroyla kazanılacak maçlar.
- **Waiver / pişmanlık / takas:** oyuncunun aktif kadroda (ya da bırakıldıktan sonra her yerde) ürettiği, yedek seviyesinin (~132. oyuncu) üstündeki maç başı z-değeri toplamı. Takas notu %60 gerçekleşen + %40 kalan sezon değeri.
- **Draft karnesi:** her seçim, o sıradan beklenen değerle (draft edilenler arasında n. en iyi oyuncu) karşılaştırılır.
- **Rekorlar, rekabetler, kişilikler, sakatlık endeksi.**

## Takım logoları

ESPN'in hazır logoları kendiliğinden gelir. Takımların kendi yüklediği resimler ESPN'de giriş yapmayı gerektirdiği için iki yol var:

- Repo ayarlarında `ESPN_S2` ve `SWID` secret'larını eklemek (Settings → Secrets and variables → Actions).
- Resmi repoya `logos/<takım id>.png` olarak eklemek. Elle eklenen resim her zaman önceliklidir.

## Dil

`site/index.html` Türkçe, `site/en.html` İngilizce. İngilizce sayfa `scripts/i18n_en.py` içindeki çevirilerle aynı şablondan üretilir; şablona yeni bir metin eklenince oraya karşılığı da eklenmeli.

## Pazar: takas analizcisi ve waiver radarı

`scripts/market.py` iki şey üretir, arayüzü `templates/market.js`:

- **Waiver radarı:** serbest oyuncular (en çok sahiplenilen 200 + ESPN'de sahipliği en hızlı artan 100) için son 7/15/30 gün ve sezon değerleri. Radar puanı = son değer + sezon ortalamasına göre sıçrama + sahiplik ivmesi. Her oyuncu için, bırakma adayından daha faydalı olduğu takımlar arasında kategori ihtiyacına en çok uyanlar gösterilir; bir takım seçilince o takıma göre kazanç hesaplanır.
- **Takas analizcisi:** `simulate_season` ile aynı model tarayıcıda çalışır. Takas edilen oyuncularla kadro projeksiyonu yeniden hesaplanır, sezon önce/sonra 3.000'er kez aynı rastgele sayılarla oynanır; playoff/şampiyonluk ihtimali ve haftalık kategori sıraları karşılaştırılır. Eşit olmayan takaslarda fazla oyuncu alan takım en düşük değerlisini bırakır, eksik kalan en iyi serbest oyuncuyu alır.
