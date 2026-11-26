# Mobil uygulama (Capacitor)

iOS ve Android uygulaması, canlı siteyi (`https://nac-nac31.github.io/nbafan/`) uygulama içinde açar; veri sitedeki gibi günde 4 kez güncellenir, uygulamayı yeniden yayınlamak gerekmez. İnternet yoksa `www/offline.html` gösterilir.

Uygulamaya özel olanlar: telefonun paylaşım ekranı (haftalık görsel doğrudan WhatsApp'a), koyu durum çubuğu, açılış ekranı ve ikonlar (`assets/` kaynaklarından `npm run assets` ile üretilir).

## Derleme

`.github/workflows/mobile.yml`, `mobile/` değişince (ya da elle "Run workflow") çalışır:

- **Android:** test APK'sı üretir, run sayfasında `fantezi-lig-android-apk` olarak indirilir. Telefona kurmak için "bilinmeyen kaynaklardan yükleme" izni gerekir.
- **iOS:** macOS'ta imzasız simülatör derlemesi (sadece derlendiğini kontrol eder).

Yerelde: `cd mobile && npm ci && npx cap sync`, sonra `npx cap open android` (Android Studio) ya da `npx cap open ios` (Xcode, Mac gerekir).

## Mağazaya çıkmak için

1. **Google Play:** Play Console hesabı (tek sefer 25$). Yükleme anahtarı (keystore) üretilip GitHub secret olarak eklenir; workflow'a imzalı AAB adımı eklenir.
2. **App Store:** Apple Developer hesabı (yıllık 99$). Sertifika ve provisioning profile (ya da App Store Connect API anahtarı) GitHub secret olarak eklenir; workflow'a imzalı IPA ve TestFlight yükleme adımı eklenir.
3. **Gizlilik politikası sayfası:** iki mağaza da istiyor (sitede basit bir sayfa yeterli).
4. **Gerçek push bildirimi:** Android için Firebase projesi (`google-services.json`), iOS için APNs anahtarı; `@capacitor/push-notifications` eklenir ve şu anki ntfy bildirimleri uygulama bildirimine taşınır. Apple, siteyi sadece paketleyen uygulamaları reddedebildiği için (madde 4.2) push ve paylaşım gibi doğal özellikler başvuruda önemli.
