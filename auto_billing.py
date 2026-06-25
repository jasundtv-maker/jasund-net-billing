import os, json
from datetime import datetime, timedelta
import pandas as pd, requests, gspread
from google.oauth2.service_account import Credentials

SHEET_ID="1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"
FONNTE_TOKEN=os.getenv("FONNTE_TOKEN")
TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_CREDENTIALS=os.getenv("GOOGLE_CREDENTIALS")
KOLOM=["NAMA","NO WA","ALAMAT","PAKET","HARGA","JATUH TEMPO","STATUS","TANGGAL BAYAR","STATUS AKUN","NO INVOICE","PERIODE","METODE BAYAR","CATATAN"]
LOG_KOLOM=["WAKTU","JENIS","NAMA","NO WA","STATUS","KETERANGAN"]

def tanggal_wib(): return (datetime.utcnow()+timedelta(hours=7)).date()
def waktu_wib(): return datetime.utcnow()+timedelta(hours=7)
def rupiah(x): return f"Rp {int(x):,}".replace(",",".")
def rapikan_wa(n):
    n=str(n).replace(" ","").replace("-","").replace("+","")
    if n.startswith("08"): n="62"+n[1:]
    return n

def client():
    info=json.loads(GOOGLE_CREDENTIALS)
    scope=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=scope))

def sh(): return client().open_by_key(SHEET_ID)
def sheet(): return sh().sheet1

def log_ws():
    try: return sh().worksheet("LOG_NOTIFIKASI")
    except Exception:
        ws=sh().add_worksheet(title="LOG_NOTIFIKASI", rows=1000, cols=10); ws.update([LOG_KOLOM]); return ws

def tambah_log(jenis,nama,no,status,ket):
    try: log_ws().append_row([waktu_wib().strftime("%Y-%m-%d %H:%M:%S"),jenis,str(nama),str(no),status,str(ket)[:400]])
    except Exception as e: print("log gagal",e)

def load_data():
    df=pd.DataFrame(sheet().get_all_records())
    if df.empty: return pd.DataFrame(columns=KOLOM)
    for c in KOLOM:
        if c not in df.columns: df[c]=""
    df["HARGA"]=pd.to_numeric(df["HARGA"], errors="coerce").fillna(0).astype(int)
    df["JATUH TEMPO"]=pd.to_numeric(df["JATUH TEMPO"], errors="coerce").fillna(1).astype(int)
    df["STATUS"]=df["STATUS"].astype(str).str.strip().str.lower().replace({"":"Belum Bayar","belum bayar":"Belum Bayar","lunas":"Lunas","menunggu verifikasi":"Menunggu Verifikasi","nan":"Belum Bayar"})
    return df[KOLOM]

def kirim_fonnte(target,pesan):
    h=requests.post("https://api.fonnte.com/send", headers={"Authorization":FONNTE_TOKEN}, data={"target":target,"message":pesan,"countryCode":"62"}, timeout=30)
    print("Fonnte", h.status_code, h.text[:300]); return h

def kirim_telegram(pesan):
    h=requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":pesan}, timeout=30)
    print("Telegram", h.status_code, h.text[:300]); return h

def pesan_invoice(r):
    return f"""Assalamualaikum Bapak/Ibu {r['NAMA']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini telah terbit.

Periode : {r['PERIODE']}
Paket Internet : {r['PAKET']}
Tagihan : {rupiah(r['HARGA'])}
Jatuh Tempo : Besok tanggal {int(r['JATUH TEMPO'])}

Silakan melakukan pembayaran melalui:
BCA 1831149782 a.n. Aceng Abdul Roup
BRI 4062 0103 3487 530 a.n. Aceng Abdul Roup
DANA 081395440454 a.n. Aceng Abdul Roup

Mohon kirim bukti transfer kepada admin JASUND.NET.
Abaikan pesan ini apabila sudah membayar.

Admin JASUND.NET"""

def main():
    hari=tanggal_wib(); besok=hari+timedelta(days=1)
    print("Tanggal WIB:",hari); print("Cek H-1:",besok.day)
    try: df=load_data()
    except Exception as e:
        msg=f"📡 JASUND.NET AUTO BILLING\n\n❌ Gagal baca Google Sheets:\n{e}"
        print(msg); kirim_telegram(msg); return
    calon=df[(df["JATUH TEMPO"]==besok.day)&(df["STATUS"]=="Belum Bayar")]
    print("Total pelanggan:",len(df)); print("Target H-1:",len(calon))
    if len(calon)==0:
        msg=f"📡 JASUND.NET AUTO BILLING\n\nTanggal cek: {hari}\nInvoice H-1 untuk jatuh tempo: {besok.day}\n\nTidak ada pelanggan H-1 hari ini."
        kirim_telegram(msg); tambah_log("AUTO_H1","-","-","SUKSES","Tidak ada target"); return
    sukses=gagal=0; daftar=""
    for _,r in calon.iterrows():
        no=rapikan_wa(r["NO WA"])
        try:
            h=kirim_fonnte(no, pesan_invoice(r))
            if h.status_code==200:
                sukses+=1; daftar+=f"✅ {r['NAMA']} - {rupiah(r['HARGA'])} - {no}\n"; tambah_log("AUTO_H1_WA",r["NAMA"],no,"SUKSES",h.text)
            else:
                gagal+=1; daftar+=f"❌ {r['NAMA']} - Gagal\n"; tambah_log("AUTO_H1_WA",r["NAMA"],no,"GAGAL",h.text)
        except Exception as e:
            gagal+=1; daftar+=f"❌ {r['NAMA']} - Error\n"; tambah_log("AUTO_H1_WA",r["NAMA"],no,"GAGAL",str(e))
    laporan=f"""📡 JASUND.NET AUTO BILLING H-1

Tanggal cek: {hari}
Invoice H-1 untuk jatuh tempo: {besok.day}

Target: {len(calon)}
✅ Berhasil dikirim: {sukses}
❌ Gagal: {gagal}

Daftar:
{daftar}
"""
    h=kirim_telegram(laporan)
    tambah_log("AUTO_H1_TELEGRAM","ADMIN",TELEGRAM_CHAT_ID,"SUKSES" if h.status_code==200 else "GAGAL",h.text)
    print(laporan)

if __name__=="__main__": main()
