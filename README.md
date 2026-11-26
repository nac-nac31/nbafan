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

## Başka lig ekleme (hazırlık)

`python scripts/check_league.py <lig_id>` bir ESPN liginin siteye eklenip eklenemeyeceğini söyler: lig açık mı, özel mi, bulunamadı mı ve ayarları (puanlama türü, kategoriler, kadro slotları, playoff) şu anki motorla uyumlu mu. Çıktı JSON'dur; ileride lig ekleme formu da aynı `inspect()` fonksiyonunu kullanacak.

Motor kategorileri, ters kategorileri (TO), puanlama türünü, takım sayısını, aktif kadro slotlarını ve playoff takım sayısını ligin ESPN ayarlarından okur (`build.py` içindeki `configure`). Desteklenenler: H2H kategori, H2H most categories ve H2H puan (haftalık toplam puan tek kategori FPTS sayılır; kategori profili gizlenir), 8-cat / 9-cat / 11-cat gibi farklı kategori setleri, 2'nin kuvveti olmayan playoff boyutları (üst sıralar bay geçer). Roto ligler henüz yok. Puanlı liglerde eğlence sayfası puanı günlük veriden yaklaşık hesaplar (DD, TD gibi bonuslar yok). Eğlence sayfası günlük verideki 9 kategoriyle sınırlı; ligde DD, 3P% gibi başka kategori varsa orada sayılmaz.

Başka bir ligi denemek için: `ESPN_LEAGUE_ID=<id> python scripts/fetch.py && ESPN_LEAGUE_ID=<id> python scripts/build.py` (ayrı bir klasörde, `data/` bizim ligin verisini tutuyor).

**Siteye başka lig ekleme:** `leagues.json` dosyasına `{"source": "espn" | "sleeper", "id": "<lig no>", "listed": true}` satırı eklenir. Günlük güncellemede `scripts/build_all.py` her ligi kendi klasöründe (`leagues/<kaynak>-<lig no>/`) çeker ve üretir, site `…/nbafan/l/<lig no>/` adresinde yayınlanır. Bir lig hata verirse diğerleri ve bizim lig etkilenmez. `listed: false` olan ligler `l/` listesinde görünmez ve arama motorlarına kapalıdır. Diğer liglere bizim ESPN çerezlerimiz gönderilmez, yani şimdilik yalnızca açık ligler. Yerelde denemek için: `SKIP_LOGOS=1 python scripts/build_all.py [lig no]`.

**Sleeper:** `SLEEPER_LEAGUE_ID=<id> python scripts/fetch_sleeper.py && SEASON=<yıl+1> python scripts/build.py`. Sleeper'ın açık API'si giriş istemez; adaptör ligi, eşleşmeleri, kadroları ve en iyi 200 serbest oyuncuyu ESPN biçimine çevirip `data/raw/<sezon>/` altına yazar (Sleeper'ın "2026" sezonu bizim 2027). Sleeper NBA ligleri puanlıdır. Sleeper günlük kadro ve haftalık NBA takvimi vermediği için eğlence sayfası ve bu haftanın kazanma tahmini yok; oyuncu değeri sezon ortalaması ve Sleeper projeksiyonundan hesaplanır.

**Yahoo:** `scripts/yahoo_auth.py`, `yahoo_api.py`, `yahoo_check.py` hazır, ama Yahoo Fantasy API'si 2026 Temmuz'dan beri onaylı uygulamalara açık (sports.yahoo.com/developer/access/). Onay gelene kadar Yahoo ligleri eklenemez.

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

## Paylaşım, bildirimler ve uygulama

`scripts/extras.py`, `build.py`'den sonra çalışır (motoru değiştirmez):

- **Haftanın hikayesi:** biten haftadan otomatik yazı (TR/EN): en farklı galibiyet, kıl payı maçlar, sürpriz, all-play şampiyonu, şanssız kaybeden, haftanın oyuncusu, seriler, lider ve bu haftanın maçı. Bu hafta sayfasının sonunda; "Görsel olarak paylaş" 1080×1350 bir PNG çizer (telefonda doğrudan WhatsApp'a), "WhatsApp'ta gönder" metni yollar.
- **Bildirimler (ntfy):** `scripts/alerts.py` her güncellemede önceki durumla (`data/alerts_state.json`) karşılaştırır; skor lideri ya da tahmini favori (%57 eşiği) değişince iki takıma, kadrodaki oyuncunun sakatlık durumu değişince o takıma, yeni hafta başlayınca lig kanalına bildirim atar. Kanal adları Takımım sayfasında. Gönderim sadece Actions'ta (`NTFY_ENABLED=1`).
- **Uygulama (PWA):** `static/` ikonları, `manifest.webmanifest` ve `sw.js` (sayfa önce ağdan, 2,5 sn'de gelmezse son kopyadan; logo ve fontlar önbellekten). Telefonda "Ana ekrana ekle".

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
