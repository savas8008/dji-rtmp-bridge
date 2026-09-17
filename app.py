"""DJI Fly RTMP Koprusu - basit masaustu arayuzu.

Tek pencere: Mobil Etkin Nokta'yi acar, MediaMTX'i baslatir, DJI Fly'a
girilecek RTMP adresini ve hotspot Wi-Fi bilgilerini gosterir, DJI Fly
yayina basladiginda bunu algilar ve tek tikla VLC acar. Komut satirina
hicbir sey yazmaya gerek yok.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parent

MEDIAMTX_EXE = ROOT_DIR / "bin" / "mediamtx.exe"
MEDIAMTX_CONFIG = ROOT_DIR / "mediamtx.yml"
HOTSPOT_SCRIPT = ROOT_DIR / "hotspot.ps1"
SETUP_SCRIPT = ROOT_DIR / "setup.ps1"

RTMP_PORT = 1935
RTSP_PORT = 8554
API_URL = "http://127.0.0.1:9997/v3/paths/get/dji"
STREAM_PATH = "dji"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def run_hotspot_action(action: str) -> dict:
    proc = subprocess.run(
        [
            "powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
            "-File", str(HOTSPOT_SCRIPT), "-Action", action,
        ],
        capture_output=True, text=True, timeout=40,
        creationflags=CREATE_NO_WINDOW,
    )
    out = (proc.stdout or "").strip().splitlines()
    if not out:
        return {"ok": False, "error": proc.stderr.strip() or "hotspot.ps1 bos yanit dondu."}
    try:
        return json.loads(out[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": proc.stdout.strip() or proc.stderr.strip()}


def get_hotspot_ip() -> str | None:
    cmd = (
        "(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.IPAddress -like '192.168.137.*' } | "
        "Select-Object -First 1 -ExpandProperty IPAddress)"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, timeout=15,
        creationflags=CREATE_NO_WINDOW,
    )
    ip = (proc.stdout or "").strip()
    return ip or None


def find_vlc() -> str | None:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "VideoLAN" / "VLC" / "vlc.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "VideoLAN" / "VLC" / "vlc.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    which = shutil.which("vlc")
    return which


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DJI Fly RTMP Koprusu")
        self.geometry("640x560")
        self.resizable(False, False)

        self.mediamtx_proc: subprocess.Popen | None = None
        self.poll_stop = threading.Event()
        self.hotspot_ip: str | None = None

        self._build_ui()
        self._log("Hazir. Baslamak icin asagidaki butona tiklayin.")
        if not MEDIAMTX_EXE.exists():
            self._log("UYARI: MediaMTX bulunamadi, ilk once 'Kur' ile indirin.")
            self.install_btn.grid()
        else:
            self.install_btn.grid_remove()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        title = ttk.Label(self, text="DJI Fly Goruntusunu Bilgisayara Al",
                           font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", **pad)

        self.status_var = tk.StringVar(value="Durum: baslatilmadi")
        ttk.Label(self, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=12)

        self.install_btn = ttk.Button(self, text="MediaMTX'i Kur", command=self._on_install)
        self.install_btn.grid(row=2, column=0, columnspan=2, sticky="we", **pad)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="we", **pad)
        self.start_btn = ttk.Button(btn_frame, text="Baslat", command=self._on_start)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.stop_btn = ttk.Button(btn_frame, text="Durdur", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        wifi_box = ttk.LabelFrame(self, text="1) Telefonu bu Wi-Fi agina baglayin")
        wifi_box.grid(row=4, column=0, columnspan=2, sticky="we", **pad)
        self.ssid_var = tk.StringVar(value="—")
        self.pass_var = tk.StringVar(value="—")
        ttk.Label(wifi_box, text="Ag adi (SSID):").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(wifi_box, textvariable=self.ssid_var, state="readonly", width=40).grid(
            row=0, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(wifi_box, text="Sifre:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(wifi_box, textvariable=self.pass_var, state="readonly", width=40).grid(
            row=1, column=1, sticky="w", padx=6, pady=4)

        rtmp_box = ttk.LabelFrame(self, text="2) DJI Fly > Transmission > Live Streaming Platforms > RTMP")
        rtmp_box.grid(row=5, column=0, columnspan=2, sticky="we", **pad)
        self.rtmp_var = tk.StringVar(value="—")
        ttk.Entry(rtmp_box, textvariable=self.rtmp_var, state="readonly", width=48).pack(
            side="left", padx=6, pady=6, fill="x", expand=True)
        ttk.Button(rtmp_box, text="Kopyala", command=lambda: self._copy(self.rtmp_var.get())).pack(
            side="left", padx=6)

        watch_box = ttk.LabelFrame(self, text="3) Goruntuyu izleyin")
        watch_box.grid(row=6, column=0, columnspan=2, sticky="we", **pad)
        self.rtsp_var = tk.StringVar(value="—")
        ttk.Entry(watch_box, textvariable=self.rtsp_var, state="readonly", width=36).pack(
            side="left", padx=6, pady=6, fill="x", expand=True)
        ttk.Button(watch_box, text="VLC'de Ac", command=self._on_open_vlc).pack(side="left", padx=6)
        ttk.Button(watch_box, text="Kopyala", command=lambda: self._copy(self.rtsp_var.get())).pack(
            side="left", padx=(0, 6))

        self.stream_var = tk.StringVar(value="DJI Fly baglantisi bekleniyor...")
        ttk.Label(self, textvariable=self.stream_var, font=("Segoe UI", 10, "bold")).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=12)

        log_box = ttk.LabelFrame(self, text="Kayit")
        log_box.grid(row=8, column=0, columnspan=2, sticky="nsew", **pad)
        self.log_widget = scrolledtext.ScrolledText(log_box, height=10, state="disabled", font=("Consolas", 9))
        self.log_widget.pack(fill="both", expand=True, padx=4, pady=4)

    def _log(self, msg: str):
        def do():
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", f"{time.strftime('%H:%M:%S')}  {msg}\n")
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")
        self.after(0, do)

    def _copy(self, text: str):
        if not text or text == "—":
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._log(f"Panoya kopyalandi: {text}")

    # ---------- Kurulum ----------
    def _on_install(self):
        self.install_btn.configure(state="disabled")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self):
        self._log("MediaMTX indiriliyor...")
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SETUP_SCRIPT)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        for line in proc.stdout:
            self._log(line.rstrip())
        proc.wait()
        if MEDIAMTX_EXE.exists():
            self._log("Kurulum tamamlandi.")
            self.after(0, self.install_btn.grid_remove)
        else:
            self._log("Kurulum basarisiz oldu. bin\\mediamtx.exe olusmadi.")
            self.after(0, lambda: self.install_btn.configure(state="normal"))

    # ---------- Baslat / Durdur ----------
    def _on_start(self):
        if not MEDIAMTX_EXE.exists():
            messagebox.showwarning("Once kurulum gerekli", "Once 'MediaMTX'i Kur' butonuna tiklayin.")
            return
        self.start_btn.configure(state="disabled")
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self):
        self.status_var.set("Durum: Mobil Etkin Nokta kontrol ediliyor...")
        self._log("Mobil Etkin Nokta durumu sorgulaniyor...")
        result = run_hotspot_action("start")
        if not result.get("ok"):
            err = result.get("error", "bilinmeyen hata")
            self._log(f"Mobil Etkin Nokta acilamadi: {err}")
            messagebox.showerror(
                "Mobil Etkin Nokta acilamadi",
                f"{err}\n\nElle acmak icin: Ayarlar > Ag ve Internet > Mobil Etkin Nokta.\n"
                "Ardindan bu pencerede tekrar 'Baslat' deneyin."
            )
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            return

        ssid = result.get("ssid") or "—"
        passphrase = result.get("passphrase") or "—"
        self.after(0, lambda: self.ssid_var.set(ssid))
        self.after(0, lambda: self.pass_var.set(passphrase))
        self._log(f"Mobil Etkin Nokta acik. SSID: {ssid}")

        self._log("Hotspot IP adresi araniyor...")
        ip = None
        for _ in range(10):
            ip = get_hotspot_ip()
            if ip:
                break
            time.sleep(1)
        if not ip:
            self._log("Hotspot IP adresi bulunamadi, 192.168.137.1 varsayilacak.")
            ip = "192.168.137.1"
        self.hotspot_ip = ip

        rtmp_url = f"rtmp://{ip}:{RTMP_PORT}/{STREAM_PATH}"
        rtsp_url = f"rtsp://{ip}:{RTSP_PORT}/{STREAM_PATH}"
        self.after(0, lambda: self.rtmp_var.set(rtmp_url))
        self.after(0, lambda: self.rtsp_var.set(rtsp_url))
        self._log(f"RTMP adresi: {rtmp_url}")

        if self.mediamtx_proc is None or self.mediamtx_proc.poll() is not None:
            self._log("MediaMTX baslatiliyor...")
            self.mediamtx_proc = subprocess.Popen(
                [str(MEDIAMTX_EXE), str(MEDIAMTX_CONFIG)],
                cwd=str(ROOT_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )

        self.after(0, lambda: self.status_var.set(f"Durum: hazir — telefonu '{ssid}' agina baglayin"))
        self.after(0, lambda: self.stop_btn.configure(state="normal"))
        self.after(0, lambda: self.start_btn.configure(state="disabled"))

        self.poll_stop.clear()
        threading.Thread(target=self._poll_stream, daemon=True).start()

    def _poll_stream(self):
        was_ready = False
        while not self.poll_stop.is_set():
            ready = False
            try:
                with urllib.request.urlopen(API_URL, timeout=2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    ready = bool(data.get("ready"))
            except Exception:
                ready = False
            if ready != was_ready:
                if ready:
                    self._log("DJI Fly baglandi, goruntu geliyor.")
                    self.after(0, lambda: self.stream_var.set("Durum: DJI Fly baglaninda goruntu akiyor"))
                else:
                    self._log("DJI Fly yayini durdu / henuz baslamadi.")
                    self.after(0, lambda: self.stream_var.set("DJI Fly baglantisi bekleniyor..."))
                was_ready = ready
            self.poll_stop.wait(2)

    def _on_stop(self):
        self.poll_stop.set()
        if self.mediamtx_proc and self.mediamtx_proc.poll() is None:
            self.mediamtx_proc.terminate()
            self._log("MediaMTX durduruldu.")
        self.mediamtx_proc = None
        self.stop_btn.configure(state="disabled")
        self.start_btn.configure(state="normal")
        self.status_var.set("Durum: durduruldu")
        self.stream_var.set("DJI Fly baglantisi bekleniyor...")

        if messagebox.askyesno("Mobil Etkin Nokta", "Mobil Etkin Nokta'yi da kapatayim mi?"):
            threading.Thread(target=self._stop_hotspot_worker, daemon=True).start()

    def _stop_hotspot_worker(self):
        result = run_hotspot_action("stop")
        if result.get("ok"):
            self._log("Mobil Etkin Nokta kapatildi.")
        else:
            self._log(f"Mobil Etkin Nokta kapatilamadi: {result.get('error')}")

    # ---------- VLC ----------
    def _on_open_vlc(self):
        url = self.rtsp_var.get()
        if not url or url == "—":
            messagebox.showinfo("Once baslatin", "Once 'Baslat' butonuna tiklayip yayini hazirlayin.")
            return
        vlc = find_vlc()
        if not vlc:
            messagebox.showwarning(
                "VLC bulunamadi",
                f"VLC yuklu bulunamadi. Adresi VLC'ye elle yapistirin:\n{url}"
            )
            return
        subprocess.Popen([vlc, url], creationflags=CREATE_NO_WINDOW)
        self._log("VLC acildi.")

    def _on_close(self):
        self.poll_stop.set()
        if self.mediamtx_proc and self.mediamtx_proc.poll() is None:
            self.mediamtx_proc.terminate()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
