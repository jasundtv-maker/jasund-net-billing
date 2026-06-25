import os
import json
from datetime import datetime, timedelta

import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"

FONNTE_TOKEN = os.getenv("FONNTE_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

KOLOM = [
    "NAMA", "NO WA", "ALAMAT", "PAKET", "HARGA",
    "JATUH TEMPO", "STATUS", "TANGGAL BAYAR",
    "STATUS AKUN", "NO INVOICE", "PERIODE",
    "METODE BAYAR", "CATATAN"
]

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def rapikan_wa(nomor):
    nomor = str(nomor).replace(" ", "").replace("-", "").replace("+", "")
    if nomor.startswith("08"):
        nomor = "62" + nomor[1:]
    return nomor

def kirim_telegram(pesan):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat id kosong.")
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan}
    return requests.post(url, data=data, timeout=30)

def kirim_fonnte(target, pesan):
    if not FONNTE_TOKEN:
        print("Fonnte token kosong.")
        return None
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    data = {"target": target, "message": pesan, "countryCode": "62"}
    return requests.post(url, headers=headers, data=data, timeout=30)

def koneksi_sheet():
    if not GOOGLE_CREDENTIALS:
        raise Exception("GOOGLE_CREDENTIALS belum ada di GitHub Secrets.")
    info = json.loads(GOOGLE_CREDENTIALS)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def load_data():
    sheet = koneksi_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame(columns=KOLOM)

    for col in KOLOM:
        if col not in df.columns:
            df[col] = ""

    df["HARGA"] = pd.to_numeric(df["HARGA"], errors="coerce").fillna(0).astype(int)
    df["JATUH TEMPO"] = pd.to_numeric(df["JATUH TEMPO"], errors="coerce").fillna(1).astype(int)
    df["NO WA"] = df["NO WA"].astype(str)

    df["STATUS"] = df["STATUS"].astype(str).str.strip().str.lower()
    df["STATUS"] = df["STATUS"].replace({
        "": "Belum Bayar",
        "belum bayar": "Belum Bayar",
        "lunas": "Lunas",
        "menunggu verifikasi": "Menunggu Verifikasi",
        "nan": "Belum Bayar"
    })

    return df[KOLOM]

def buat_pesan_invoice(row):
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini telah terbit.

Periode : {row['PERIODE']}
Paket Internet : {row['PAKET']}
Tagihan : {rupiah(row['HARGA'])}
Jatuh Tempo : Besok tanggal {int(row['JATUH TEMPO'])}

Silakan melakukan pembayaran melalui:

BCA
1831149782
a.n. Aceng Abdul Roup

BRI
4062 0103 3487 530
a.n. Aceng Abdul Roup

DANA
081395440454
a.n. Aceng Abdul Roup

Setelah melakukan pembayaran, mohon kirimkan bukti transfer kepada admin JASUND.NET.

Pembayaran juga dapat dilakukan langsung ke kantor JASUND.NET.

Abaikan pesan ini apabila Bapak/Ibu telah melakukan pembayaran sebelumnya.

Terima kasih atas kepercayaan Bapak/Ibu menggunakan layanan internet JASUND.NET.

Admin JASUND.NET"""

def main():
    hari_ini = tanggal_wib()
    besok = hari_ini + timedelta(days=1)

    print("Tanggal WIB:", hari_ini)
    print("Cek H-1 untuk tanggal:", besok.day)

    try:
        df = load_data()
    except Exception as e:
        pesan_error = f"📡 JASUND.NET AUTO BILLING\n\n❌ Gagal baca Google Sheets:\n{e}"
        print(pesan_error)
        kirim_telegram(pesan_error)
        return

    if len(df) == 0:
        kirim_telegram("📡 JASUND.NET AUTO BILLING\n\nDatabase Google Sheets kosong.")
        return

    calon = df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]

    print("Total pelanggan:", len(df))
    print("Target H-1:", len(calon))

    if len(calon) == 0:
        kirim_telegram(
            f"📡 JASUND.NET AUTO BILLING\n\n"
            f"Tanggal cek: {hari_ini}\n"
            f"Invoice H-1 untuk jatuh tempo: {besok.day}\n\n"
            f"Tidak ada pelanggan H-1 hari ini."
        )
        return

    sukses = 0
    gagal = 0
    daftar = ""

    for _, row in calon.iterrows():
        nama = row["NAMA"]
        no_wa = rapikan_wa(row["NO WA"])
        pesan = buat_pesan_invoice(row)

        try:
            hasil = kirim_fonnte(no_wa, pesan)
            if hasil is not None and hasil.status_code == 200:
                sukses += 1
                daftar += f"✅ {nama} - {rupiah(row['HARGA'])} - {no_wa}\n"
                print("Berhasil:", nama, no_wa)
            else:
                gagal += 1
                error_text = hasil.text if hasil is not None else "Token Fonnte kosong"
                daftar += f"❌ {nama} - Gagal - {error_text[:80]}\n"
                print("Gagal:", nama, error_text)
        except Exception as e:
            gagal += 1
            daftar += f"❌ {nama} - Error: {str(e)[:80]}\n"
            print("Error:", nama, e)

    laporan = f"""📡 JASUND.NET AUTO BILLING H-1

Tanggal cek: {hari_ini}
Invoice H-1 untuk jatuh tempo: {besok.day}

Target: {len(calon)}
✅ Berhasil dikirim: {sukses}
❌ Gagal: {gagal}

Daftar:
{daftar}
"""

    kirim_telegram(laporan)
    print(laporan)

if __name__ == "__main__":
    main()
