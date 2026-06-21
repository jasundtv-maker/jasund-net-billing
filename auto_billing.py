import pandas as pd
from datetime import datetime, timedelta
import requests
import os

FILE = "pelanggan.csv"

FONNTE_TOKEN = os.getenv("FONNTE_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def rapikan_nomor_wa(nomor):
    nomor = str(nomor).replace(" ", "").replace("-", "").replace("+", "")
    if nomor.startswith("08"):
        nomor = "62" + nomor[1:]
    return nomor

def buat_pesan_invoice(row):
    return f"""Assalamualaikum Bapak/Ibu {row['Nama']}

Kami informasikan tagihan internet JASUND.NET:

Paket: {row['Paket']}
Tagihan: {format_rupiah(row['Harga'])}
Jatuh tempo: besok tanggal {int(row['Jatuh Tempo'])}

Mohon melakukan pembayaran sebelum jatuh tempo agar layanan internet tetap aktif dan lancar.

Terima kasih.

Admin JASUND.NET"""

def kirim_fonnte(target, pesan):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {
        "target": target,
        "message": pesan,
        "countryCode": "62"
    }
    return requests.post(url, headers=headers, data=data, timeout=30)

def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan
    }
    return requests.post(url, data=data, timeout=30)

def main():
    if not os.path.exists(FILE):
        kirim_telegram("📡 JASUND.NET\n\nFile pelanggan.csv belum ada di repository.")
        return

    df = pd.read_csv(FILE, dtype=str)

    df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce").fillna(0).astype(int)
    df["Jatuh Tempo"] = pd.to_numeric(df["Jatuh Tempo"], errors="coerce").fillna(1).astype(int)

    hari_ini = tanggal_wib()
    besok = hari_ini + timedelta(days=1)

    calon = df[
        (df["Jatuh Tempo"] == besok.day) &
        (df["Status"] == "Belum Bayar")
    ]

    if len(calon) == 0:
        kirim_telegram(f"📡 JASUND.NET\n\nTidak ada invoice H-1 untuk tanggal {besok.day}.")
        return

    sukses = 0
    gagal = 0
    daftar = ""

    for _, row in calon.iterrows():
        no_wa = rapikan_nomor_wa(row["No WA"])
        pesan = buat_pesan_invoice(row)

        try:
            hasil = kirim_fonnte(no_wa, pesan)
            if hasil.status_code == 200:
                sukses += 1
                daftar += f"✅ {row['Nama']} - {format_rupiah(row['Harga'])}\n"
            else:
                gagal += 1
                daftar += f"❌ {row['Nama']} - Gagal\n"
        except:
            gagal += 1
            daftar += f"❌ {row['Nama']} - Error\n"

    laporan = f"""📡 JASUND.NET AUTO BILLING

Tanggal cek: {hari_ini}
Invoice H-1 untuk jatuh tempo: {besok.day}

Berhasil dikirim: {sukses}
Gagal: {gagal}

Daftar:
{daftar}
"""

    kirim_telegram(laporan)

if __name__ == "__main__":
    main()
