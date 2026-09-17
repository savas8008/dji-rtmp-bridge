# dji-rtmp-bridge

DJI Fly uygulamasının RTMP canlı yayınını bilgisayara alıp hem VLC ile
izlemeyi hem de ileride QGroundControl gibi bir yer kontrol istasyonuna
(GCS) video kaynağı olarak vermeyi sağlayan minimal köprü.

## Mimari

```
Telefon (DJI Fly)                Bilgisayar
  RTMP yayını  ───────────►  MediaMTX (:1935 RTMP giriş)
  (hotspot ağı üzerinden)          │
                                   ├──► RTSP  (:8554)  ──► VLC / QGroundControl
                                   └──► HLS   (:8888)  ──► tarayıcıdan hızlı önizleme (opsiyonel)
```

MediaMTX, RTMP girişini **transcode etmeden (remux)** RTSP/HLS olarak
dışarı verir — bu yüzden ekstra gecikme veya CPU yükü eklemez. DJI Fly
RTMP dışında bir protokol desteklemediği, QGroundControl ise RTMP değil
RTSP beklediği için aradaki bu dönüşüm gerekiyor.

## 1. Bilgisayarda Wi-Fi Hotspot Açma

`Ayarlar > Ağ ve Internet > Mobil hotspot` üzerinden açın ve telefonu bu
ağa bağlayın.

> **Önemli:** Windows'un Mobil Hotspot özelliği, paylaşılacak aktif bir
> internet bağlantısı (Wi-Fi ya da Ethernet) ister. Bilgisayarda hiç
> internet yoksa (örn. sahada, dış mekanda) hotspot açılamayabilir.
> Bu durumda:
> - Bilgisayarı geçici olarak bir Ethernet/Wi-Fi internet kaynağına
>   bağlayıp hotspot'u öyle açın, sonra internet bağlantısını koparsanız
>   hotspot genelde açık kalmaya devam eder, veya
> - `netsh wlan set hostednetwork mode=allow ssid=<isim> key=<sifre>` +
>   `netsh wlan start hostednetwork` ile eski (legacy) sanal Wi-Fi
>   özelliğini deneyin (bazı Wi-Fi adaptörlerinde çalışmayabilir), veya
> - Bilgisayar yerine **telefonun hotspot'unu** açıp bilgisayarı ona
>   bağlayın (bu durumda IP adresi telefonun hotspot IP aralığından
>   olur, aşağıdaki adımlarda ona göre güncelleyin).

Hotspot IP'si genelde `192.168.137.1` olur (`start.ps1` bunu otomatik
bulup ekrana basar).

## 2. MediaMTX'i Kurma ve Başlatma

```powershell
cd d:\github\dji-rtmp-bridge
.\setup.ps1    # MediaMTX'i indirir (bin\mediamtx.exe)
.\start.ps1    # sunucuyu baslatir, RTMP/RTSP URL'lerini ekrana basar
```

`start.ps1` şuna benzer bir çıktı verir:

```
--- DJI Fly icin RTMP adresi (Transmission > Live Streaming Platforms > RTMP) ---
  rtmp://192.168.137.1:1935/dji

--- VLC / QGroundControl icin RTSP adresi ---
  rtsp://192.168.137.1:8554/dji
```

## 3. DJI Fly'da RTMP Yayınını Ayarlama

Uçuş ekranında: **GO FLY > Transmission (Aktarım) > Live Streaming
Platforms (Canlı Yayın Platformları) > RTMP**

- **RTMP Address**: `start.ps1` çıktısındaki tam adres, örn.
  `rtmp://192.168.137.1:1935/dji`
- Çözünürlük/bit hızı: 720p30 için 2.5-4 Mbps, 1080p30 için 4.5-6 Mbps
  önerilir; hotspot bağlantısı zayıfsa düşürün (aşağıdaki Sorun Giderme'ye
  bakın)
- DJI RC 2 / RC Pro / Smart Controller kullanıyorsanız DJI Fly v1.16+'da
  yayını başlatmak için kumandaya mikrofon takılı olması gerekebiliyor

Yayını başlattığınızda MediaMTX konsolunda bir "publish" logu görünmeli.

## 4. VLC ile İzleme (hızlı test)

VLC → **Medya > Ağ Akışını Aç…** → adres kutusuna:

```
rtsp://127.0.0.1:8554/dji
```

(Bilgisayarın kendisinde açıyorsanız `127.0.0.1`, başka bir cihazdan
izliyorsanız hotspot IP'sini kullanın.)

## 5. QGroundControl'e (veya başka bir GCS'e) Bağlama

**Application Settings (üstteki üç çizgi menü) > General > Video**

- **Video Source**: `RTSP Video Stream`
- **RTSP URL**: `rtsp://192.168.137.1:8554/dji` (kendi hotspot IP'nizle)
- **Low Latency Mode**: açık — gecikmeyi azaltır (bağlantı zayıfsa görüntü
  kartlanabilir, gerekirse kapatın)

Fly View ekranına dönünce görüntü düşmeye başlamalı.

## Sorun Giderme

- **Görüntü gelmiyor / bağlantı reddediliyor**: `start.ps1`'i yönetici
  olarak çalıştırıp güvenlik duvarı kurallarının eklendiğinden emin olun
  (Windows, hotspot ağını "genel ağ" sayıp gelen bağlantıları
  engelleyebiliyor).
- **Port zaten kullanımda hatası**: `netstat -ano | findstr "1935 8554"`
  ile 1935/8554 portlarını kimin kullandığını kontrol edin.
- **Görüntü donuyor/takılıyor**: Windows Mobil Hotspot çoğu Wi-Fi
  adaptöründe yalnızca **2.4 GHz** bandını yayınlar; bu bant kalabalıksa
  DJI Fly'da bit hızını düşürün veya hotspot yerine 5 GHz destekleyen bir
  router üzerinden aynı ağa bağlanmayı deneyin.
- **Gecikme yüksek**: MediaMTX transcode yapmadığı için gecikmenin büyük
  kısmı DJI Fly'ın RTMP kodlama/buffer ayarlarından gelir — bit hızını ve
  GOP/keyframe aralığını düşürmek gecikmeyi azaltır. QGroundControl
  tarafında "Low Latency Mode"u açık tutun.

## Notlar

- Bu proje `headtracker-verici` (ESP32 head tracker) ile donanımsal
  olarak ilgisiz, bağımsız bir araçtır.
- MediaMTX kimlik doğrulamasız çalışıyor (`mediamtx.yml`); yalnızca
  izole/güvenilir bir hotspot ağında kullanın, üretim/internet'e açık bir
  ağda **kullanmayın**.
