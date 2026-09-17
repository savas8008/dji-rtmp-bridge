# dji-rtmp-bridge

DJI Fly uygulamasının RTMP canlı yayınını bilgisayara alıp hem VLC ile
izlemeyi hem de ileride QGroundControl gibi bir yer kontrol istasyonuna
(GCS) video kaynağı olarak vermeyi sağlayan araç. Tek pencereli bir
arayüzü (`app.py`) var — komut satırına bir şey yazmanıza gerek yok.

## Mimari

```
Telefon (DJI Fly)                Bilgisayar
  RTMP yayını  ───────────►  MediaMTX (:1935 RTMP giriş)
  (hotspot ağı üzerinden)          │
                                   ├──► RTSP (:8554) ──► VLC / QGroundControl
                                   └──► HLS  (:8888) ──► tarayıcıdan hızlı önizleme (opsiyonel)
```

MediaMTX, RTMP girişini **transcode etmeden (remux)** RTSP/HLS olarak
dışarı verir — ekstra gecikme veya CPU yükü eklemez. DJI Fly RTMP
dışında bir protokol desteklemediği, QGroundControl ise RTMP değil RTSP
beklediği için aradaki bu dönüşüm gerekiyor.

## Kullanım (arayüzle)

```powershell
cd d:\github\dji-rtmp-bridge
python app.py
```

(Kalıcı, çift tıklanabilir bir `.exe` istiyorsanız aşağıdaki
**Tek dosyalık .exe olarak paketleme** bölümüne bakın.)

Açılan pencerede:

1. **MediaMTX'i Kur** (yalnızca ilk çalıştırmada görünür) — video
   sunucusunu indirir.
2. **Başlat** — bilgisayarın Mobil Etkin Nokta'sını otomatik açar
   (Windows'un "Mobil Hotspot" özelliği — Ayarlar'daki adı budur), video
   sunucusunu başlatır ve size üç şeyi gösterir:
   - Telefonu bağlayacağınız **Wi-Fi adı ve şifresi**
   - DJI Fly'a gireceğiniz **RTMP adresi** (Kopyala butonuyla panoya
     alınır)
   - İzleme için **RTSP adresi** ve tek tıkla **VLC'de Aç** butonu
3. Telefonu gösterilen Wi-Fi ağına bağlayın.
4. DJI Fly'da: **GO FLY > Transmission (Aktarım) > Live Streaming
   Platforms (Canlı Yayın Platformları) > RTMP** → panodaki adresi
   **RTMP Address** alanına yapıştırın, yayını başlatın.
5. Pencerede "DJI Fly bağlandı, görüntü akıyor" yazısını gördüğünüzde
   **VLC'de Aç**'a tıklayın ya da RTSP adresini QGroundControl'e girin
   (bkz. aşağı).

**Durdur** butonu video sunucusunu kapatır ve isterseniz Mobil Etkin
Nokta'yı da kapatmayı sorar.

> Bit hızı önerisi: 720p30 için 2.5-4 Mbps, 1080p30 için 4.5-6 Mbps;
> hotspot bağlantısı zayıfsa DJI Fly'da düşürün. DJI RC 2 / RC Pro /
> Smart Controller kullanıyorsanız DJI Fly v1.16+'da yayını başlatmak
> için kumandaya mikrofon takılı olması gerekebiliyor.

## QGroundControl'e (veya başka bir GCS'e) Bağlama

**Application Settings (üstteki üç çizgi menü) > General > Video**

- **Video Source**: `RTSP Video Stream`
- **RTSP URL**: arayüzdeki RTSP adresi (örn. `rtsp://192.168.137.1:8554/dji`)
- **Low Latency Mode**: açık — gecikmeyi azaltır (bağlantı zayıfsa
  görüntü kartlanabilir, gerekirse kapatın)

## Tek Dosyalık .exe Olarak Paketleme

Python kurulu olmayan bir bilgisayarda / başka bir kullanıcıda
çalıştırmak için:

```powershell
.\build_exe.ps1
```

`dist\DJI-RTMP-Koprusu.exe` üretilir (yanında `hotspot.ps1`,
`mediamtx.yml` ve `bin\` de kopyalanır — **hepsi birlikte aynı klasörde
kalmalı**, sadece exe'yi tek başına taşımak çalışmaz). Bu betik
`pip install pyinstaller` çalıştırır; global Python ortamınıza paket
eklemek istemiyorsanız `python.exe`'yi bir sanal ortamdan (`venv`)
çağıracak şekilde düzenleyin.

## Sorun Giderme

- **"Mobil Etkin Nokta açılamadı"**: Windows'un Mobil Hotspot özelliği,
  paylaşacağı **aktif bir internet/ağ bağlantısı** (Wi-Fi ya da Ethernet)
  ister. Bilgisayarda hiç bağlantı yoksa (sahada, dış mekanda) hotspot
  açılamaz. Bu durumda:
  - Bilgisayarı geçici olarak bir Ethernet/Wi-Fi kaynağına bağlayıp
    hotspot'u öyle açın (bağlantıyı sonra koparsanız hotspot genelde
    açık kalır), veya
  - Bilgisayar yerine **telefonun hotspot'unu** açıp bilgisayarı ona
    bağlayın — bu durumda arayüzdeki otomatik adres bulma çalışmaz,
    telefonun hotspot IP aralığına göre `rtmp://<ip>:1935/dji` adresini
    elle girin (bilgisayarın o ağdaki IP'sini `ipconfig` ile bulun).
- **Görüntü gelmiyor / bağlantı reddediliyor**: Uygulamayı yönetici
  olarak çalıştırmayı deneyin; Windows hotspot ağını "genel ağ" sayıp
  gelen bağlantıları (1935/8554 portları) engelleyebiliyor. Gerekirse
  elle bir güvenlik duvarı kuralı ekleyin:
  `New-NetFirewallRule -DisplayName dji-bridge -Direction Inbound -Protocol TCP -LocalPort 1935,8554 -Action Allow`
- **VLC bulunamadı uyarısı**: VLC kurulu değilse RTSP adresini VLC'ye
  (ya da başka bir oynatıcıya) elle yapıştırabilirsiniz.
- **Görüntü donuyor/takılıyor**: Windows Mobil Hotspot çoğu Wi-Fi
  adaptöründe yalnızca **2.4 GHz** bandını yayınlar; bant kalabalıksa
  DJI Fly'da bit hızını düşürün.
- **Gecikme yüksek**: MediaMTX transcode yapmıyor, gecikmenin büyük kısmı
  DJI Fly'ın kodlama/buffer ayarlarından gelir — bit hızını ve
  GOP/keyframe aralığını düşürmek gecikmeyi azaltır. QGroundControl'de
  "Low Latency Mode"u açık tutun.

## Dosyalar

| Dosya | Görev |
|-------|-------|
| `app.py` | Ana arayüz — hotspot, MediaMTX ve VLC'yi tek pencereden yönetir |
| `hotspot.ps1` | Windows Mobil Etkin Nokta'yı WinRT API'siyle açar/kapatır/bilgi verir (app.py tarafından çağrılır) |
| `mediamtx.yml` | Video sunucusu yapılandırması (RTMP giriş, RTSP/HLS çıkış, yerel API) |
| `setup.ps1` | MediaMTX'i GitHub'dan indirir |
| `start.ps1` | (İleri düzey) Arayüz olmadan, komut satırından MediaMTX'i başlatan eski yöntem |
| `build_exe.ps1` | `app.py`'yi tek dosyalık `.exe`'ye paketler (PyInstaller) |

## Notlar

- Bu proje `headtracker-verici` (ESP32 head tracker) ile donanımsal
  olarak ilgisiz, bağımsız bir araçtır.
- MediaMTX kimlik doğrulamasız çalışıyor; yalnızca izole/güvenilir bir
  hotspot ağında kullanın, üretim/internet'e açık bir ağda
  **kullanmayın**. Yerel API (`:9997`) yalnızca `127.0.0.1`'den erişilebilir.
