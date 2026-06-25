import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests, urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="JASUND.NET V15 ENTERPRISE ISP", page_icon="📡", layout="wide")

SHEET_ID = "1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"
ADMIN_WA = "6281395440454"

KOLOM = ["NAMA","NO WA","ALAMAT","PAKET","HARGA","JATUH TEMPO","STATUS","TANGGAL BAYAR","STATUS AKUN","NO INVOICE","PERIODE","METODE BAYAR","CATATAN"]
LOG_KOLOM = ["WAKTU","JENIS","NAMA","NO WA","STATUS","KETERANGAN"]
VOUCHER_KOLOM = ["TANGGAL","PENYETOR","TOTAL SETOR","CATATAN"]
PENGELUARAN_KOLOM = ["TANGGAL","KATEGORI","KETERANGAN","JUMLAH"]

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def waktu_wib():
    return datetime.utcnow() + timedelta(hours=7)

def bulan_tahun():
    bulan = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}
    t = tanggal_wib()
    return f"{bulan[t.month]} {t.year}"

def rupiah(x):
    try: return f"Rp {int(x):,}".replace(",", ".")
    except: return "Rp 0"

def rapikan_wa(no):
    no = str(no).replace(" ","").replace("-","").replace("+","")
    if no.startswith("08"): no = "62" + no[1:]
    return no

def get_secret(name):
    try: return st.secrets[name]
    except Exception: return ""

FONNTE_TOKEN = get_secret("FONNTE_TOKEN")
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

def koneksi_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def spreadsheet():
    return koneksi_client().open_by_key(SHEET_ID)

def sheet_by_name(name, headers):
    sh = spreadsheet()
    try:
        ws = sh.worksheet(name)
    except Exception:
        ws = sh.add_worksheet(title=name, rows=1000, cols=max(10, len(headers)))
        ws.update([headers])
    return ws

def main_sheet():
    return spreadsheet().sheet1

def load_main():
    ws = main_sheet()
    df = pd.DataFrame(ws.get_all_records())
    if df.empty: df = pd.DataFrame(columns=KOLOM)
    for c in KOLOM:
        if c not in df.columns: df[c] = ""
    df["HARGA"] = pd.to_numeric(df["HARGA"], errors="coerce").fillna(0).astype(int)
    df["JATUH TEMPO"] = pd.to_numeric(df["JATUH TEMPO"], errors="coerce").fillna(1).astype(int)
    df["NO WA"] = df["NO WA"].astype(str)
    df["STATUS"] = df["STATUS"].astype(str).str.strip().str.lower().replace({
        "":"Belum Bayar","belum bayar":"Belum Bayar","lunas":"Lunas","menunggu verifikasi":"Menunggu Verifikasi","nan":"Belum Bayar"
    })
    df["STATUS AKUN"] = df["STATUS AKUN"].astype(str).str.strip().str.lower().replace({
        "":"Aktif","aktif":"Aktif","menunggak":"Menunggak","suspend":"Suspend","nan":"Aktif"
    })
    df["PERIODE"] = df["PERIODE"].replace("", bulan_tahun()).fillna(bulan_tahun())
    for c in ["TANGGAL BAYAR","NO INVOICE","METODE BAYAR","CATATAN"]:
        df[c] = df[c].fillna("")
    return df[KOLOM]

def save_main(df):
    ws = main_sheet()
    ws.clear()
    ws.update([KOLOM] + df[KOLOM].astype(str).values.tolist())

def load_table(name, headers, money_col=None):
    ws = sheet_by_name(name, headers)
    df = pd.DataFrame(ws.get_all_records())
    if df.empty: df = pd.DataFrame(columns=headers)
    for c in headers:
        if c not in df.columns: df[c] = ""
    if money_col:
        df[money_col] = pd.to_numeric(df[money_col], errors="coerce").fillna(0).astype(int)
    return df[headers]

def save_table(name, headers, df):
    ws = sheet_by_name(name, headers)
    ws.clear()
    ws.update([headers] + df[headers].astype(str).values.tolist())

def tambah_log(jenis, nama, no, status, ket):
    try:
        df = load_table("LOG_NOTIFIKASI", LOG_KOLOM)
        row = pd.DataFrame([{"WAKTU":waktu_wib().strftime("%Y-%m-%d %H:%M:%S"),"JENIS":jenis,"NAMA":nama,"NO WA":no,"STATUS":status,"KETERANGAN":str(ket)[:400]}])
        save_table("LOG_NOTIFIKASI", LOG_KOLOM, pd.concat([df,row], ignore_index=True))
    except Exception as e:
        print("log error", e)

def load_log(): return load_table("LOG_NOTIFIKASI", LOG_KOLOM)
def load_voucher(): return load_table("PEMASUKAN_VOUCHER", VOUCHER_KOLOM, "TOTAL SETOR")
def save_voucher(df): save_table("PEMASUKAN_VOUCHER", VOUCHER_KOLOM, df)
def load_pengeluaran(): return load_table("PENGELUARAN", PENGELUARAN_KOLOM, "JUMLAH")
def save_pengeluaran(df): save_table("PENGELUARAN", PENGELUARAN_KOLOM, df)

def bulan_ini(df, col="TANGGAL"):
    if len(df)==0 or col not in df.columns: return df
    s = pd.to_datetime(df[col], errors="coerce")
    now = waktu_wib()
    return df[(s.dt.month == now.month) & (s.dt.year == now.year)]

def wa_link(no, pesan):
    return "https://wa.me/" + rapikan_wa(no) + "?text=" + urllib.parse.quote(pesan)

def tombol_link(label, link):
    st.markdown(f'<a href="{link}" target="_blank" class="wa-button">{label}</a>', unsafe_allow_html=True)

def kirim_fonnte(target, pesan):
    return requests.post("https://api.fonnte.com/send", headers={"Authorization":FONNTE_TOKEN}, data={"target":target,"message":pesan,"countryCode":"62"}, timeout=30)

def kirim_telegram(pesan):
    return requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":pesan}, timeout=30)

def buat_invoice_no(row):
    return f"JNET-{datetime.now().strftime('%Y%m')}-{str(row['NO WA'])[-4:]}"

def pesan_invoice(row):
    noinv = row["NO INVOICE"] if row["NO INVOICE"] else buat_invoice_no(row)
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini telah terbit.

No Invoice : {noinv}
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

Admin JASUND.NET"""

def pesan_lunas(row):
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Pembayaran internet JASUND.NET telah kami terima.

No Invoice : {row['NO INVOICE']}
Periode : {row['PERIODE']}
Paket : {row['PAKET']}
Nominal : {rupiah(row['HARGA'])}
Status : LUNAS ✅

Terima kasih.
Admin JASUND.NET"""

def clean_text(t):
    return str(t).encode("latin-1","replace").decode("latin-1")

def buat_pdf(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    noinv = row["NO INVOICE"] if row["NO INVOICE"] else buat_invoice_no(row)
    pdf.set_fill_color(24,78,138); pdf.rect(0,0,210,28,"F")
    pdf.set_text_color(255,255,255); pdf.set_font("Helvetica","B",20); pdf.cell(0,10,"JASUND.NET",ln=True)
    pdf.set_font("Helvetica","",10); pdf.cell(0,6,"Internet Service Provider & RTRW NET Billing",ln=True)
    pdf.set_xy(138,8); pdf.set_font("Helvetica","B",18); pdf.cell(58,10,"INVOICE",align="R")
    pdf.set_text_color(0,0,0); pdf.ln(20)
    pdf.set_font("Helvetica","B",11); pdf.set_fill_color(58,95,160); pdf.set_text_color(255,255,255)
    pdf.cell(90,8," BILL TO",border=1,fill=True); pdf.set_xy(122,38); pdf.cell(74,8," DETAIL INVOICE",border=1,fill=True)
    pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",10); pdf.set_xy(10,46)
    pdf.multi_cell(90,7,clean_text(f"{row['NAMA']}\n{row['ALAMAT']}\nWA: {row['NO WA']}"),border=1)
    pdf.set_xy(122,46)
    for k,v in [("Tanggal",tanggal_wib()),("Invoice No",noinv),("Periode",row["PERIODE"]),("Jatuh Tempo",f"Tanggal {int(row['JATUH TEMPO'])}"),("Status",row["STATUS"])]:
        pdf.set_x(122); pdf.cell(34,7,clean_text(k),border=1); pdf.cell(40,7,clean_text(v),border=1,ln=True)
    pdf.ln(12); pdf.set_font("Helvetica","B",10); pdf.set_fill_color(58,95,160); pdf.set_text_color(255,255,255)
    pdf.cell(105,8," DESCRIPTION",border=1,fill=True); pdf.cell(25,8," QTY",border=1,fill=True,align="C"); pdf.cell(55,8," AMOUNT",border=1,fill=True,align="C"); pdf.ln()
    pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",10)
    y=pdf.get_y(); pdf.multi_cell(105,10,clean_text(f"Tagihan Internet JASUND.NET\nPaket {row['PAKET']}"),border=1)
    pdf.set_xy(115,y); pdf.cell(25,20,"1",border=1,align="C"); pdf.set_xy(140,y); pdf.cell(55,20,rupiah(row["HARGA"]),border=1,align="R")
    pdf.ln(10); pdf.set_x(115); pdf.cell(35,7,"Subtotal"); pdf.cell(45,7,rupiah(row["HARGA"]),align="R",ln=True)
    pdf.set_x(115); pdf.cell(35,7,"Discount"); pdf.cell(45,7,"-",align="R",ln=True)
    pdf.set_x(115); pdf.set_font("Helvetica","B",11); pdf.cell(35,8,"Grand Total",border="T"); pdf.cell(45,8,rupiah(row["HARGA"]),border="T",align="R",ln=True)
    pdf.ln(8); pdf.set_font("Helvetica","B",11); pdf.set_fill_color(58,95,160); pdf.set_text_color(255,255,255); pdf.cell(95,8," METODE PEMBAYARAN",border=1,fill=True,ln=True)
    pdf.set_text_color(0,0,0); pdf.set_font("Helvetica","",10)
    pdf.multi_cell(95,7,clean_text("BCA  : 1831149782\na.n. Aceng Abdul Roup\n\nBRI  : 4062 0103 3487 530\na.n. Aceng Abdul Roup\n\nDANA : 081395440454\na.n. Aceng Abdul Roup"),border=1)
    pdf.ln(8); pdf.multi_cell(0,7,clean_text("Mohon kirimkan bukti transfer kepada admin JASUND.NET.\nAbaikan invoice ini apabila sudah melakukan pembayaran sebelumnya."))
    pdf.ln(15); pdf.set_x(125); pdf.cell(70,7,"Hormat kami,",ln=True,align="C"); pdf.ln(18); pdf.set_x(125); pdf.set_font("Helvetica","B",11); pdf.cell(70,7,"Admin JASUND.NET",ln=True,align="C")
    return bytes(pdf.output(dest="S"))

def export_excel_bytes(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w: df.to_excel(w, index=False, sheet_name="Pelanggan")
    return out.getvalue()

st.markdown("""
<style>
.stApp{background:radial-gradient(circle at top left,rgba(34,197,94,.28),transparent 32%),radial-gradient(circle at top right,rgba(168,85,247,.35),transparent 32%),linear-gradient(135deg,#020617 0%,#071426 45%,#022c22 100%);color:white}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#020617,#0f172a,#111827)}
h1,h2,h3,h4,p,label{color:#f8fafc!important}
.main-title{font-size:46px;font-weight:900;background:linear-gradient(90deg,#22c55e,#38bdf8,#a78bfa,#fb7185);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.running{padding:14px 22px;border-radius:18px;background:linear-gradient(90deg,rgba(34,197,94,.25),rgba(56,189,248,.20),rgba(168,85,247,.20));border:1px solid rgba(255,255,255,.18);color:white;font-weight:700}
.card{padding:24px;border-radius:24px;color:white;box-shadow:0 0 30px rgba(255,255,255,.25);min-height:135px}
.green{background:linear-gradient(135deg,#16a34a,#22c55e)}.blue{background:linear-gradient(135deg,#0284c7,#38bdf8)}.purple{background:linear-gradient(135deg,#7c3aed,#c084fc)}.orange{background:linear-gradient(135deg,#ea580c,#facc15)}.red{background:linear-gradient(135deg,#dc2626,#fb7185)}.dark{background:linear-gradient(135deg,#334155,#0f172a)}.gold{background:linear-gradient(135deg,#f59e0b,#fde047)}
.metric-label{font-size:15px;font-weight:700}.metric-value{font-size:32px;font-weight:900;margin-top:8px}
.wa-button{display:inline-block;background:linear-gradient(135deg,#25D366,#128C7E);color:white!important;padding:12px 24px;border-radius:14px;text-decoration:none!important;font-weight:900;font-size:16px;box-shadow:0 0 22px rgba(37,211,102,.45);margin-top:8px;margin-bottom:18px}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{background:linear-gradient(135deg,#22c55e,#06b6d4)!important;color:white!important;border:none!important;border-radius:14px!important;font-weight:900!important;padding:10px 22px!important;box-shadow:0 0 18px rgba(34,197,94,.35)!important}
.clean-box{padding:18px;border-radius:18px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:white}
</style>
""", unsafe_allow_html=True)

# LOAD DATA
df = load_main()
df_log = load_log()
df_voucher = load_voucher()
df_pengeluaran = load_pengeluaran()
hari_ini = tanggal_wib(); besok = hari_ini + timedelta(days=1)

total = len(df)
aktif = len(df[df["STATUS AKUN"]=="Aktif"]) if total else 0
suspend = len(df[df["STATUS AKUN"]=="Suspend"]) if total else 0
vip = len(df[df["CATATAN"].astype(str).str.contains("VIP", case=False, na=False)]) if total else 0
lunas = len(df[df["STATUS"]=="Lunas"]) if total else 0
h1 = len(df[(df["JATUH TEMPO"]==besok.day)&(df["STATUS"]=="Belum Bayar")]) if total else 0
hari_ini_jt = len(df[(df["JATUH TEMPO"]==hari_ini.day)&(df["STATUS"]=="Belum Bayar")]) if total else 0
total_tagihan = int(df["HARGA"].sum()) if total else 0
sudah_lunas = int(df[df["STATUS"]=="Lunas"]["HARGA"].sum()) if total else 0
belum_masuk = int(df[df["STATUS"]!="Lunas"]["HARGA"].sum()) if total else 0
persen_lunas = round((lunas/total)*100) if total else 0
v_bulan = bulan_ini(df_voucher); p_bulan = bulan_ini(df_pengeluaran)
pendapatan_voucher = int(v_bulan["TOTAL SETOR"].sum()) if len(v_bulan) else 0
total_pengeluaran = int(p_bulan["JUMLAH"].sum()) if len(p_bulan) else 0
total_pendapatan = sudah_lunas + pendapatan_voucher
laba_bersih = total_pendapatan - total_pengeluaran
lunas_hari_ini_df = df[(df["STATUS"]=="Lunas") & (df["TANGGAL BAYAR"].astype(str)==str(hari_ini))]
omset_hari_ini = int(lunas_hari_ini_df["HARGA"].sum()) if len(lunas_hari_ini_df) else 0
notif_sukses = len(df_log[df_log["STATUS"].astype(str).str.upper().str.contains("SUKSES", na=False)]) if len(df_log) else 0
notif_gagal = len(df_log[df_log["STATUS"].astype(str).str.upper().str.contains("GAGAL", na=False)]) if len(df_log) else 0

st.sidebar.title("📡 JASUND.NET")
st.sidebar.caption("V15 Enterprise ISP")
menu = st.sidebar.radio("Menu", [
    "🌐 Halaman Depan",
    "🏠 Dashboard CEO",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💳 Pembayaran Masuk",
    "✅ Sudah Bayar",
    "🎟️ Pemasukan Voucher",
    "💸 Pengeluaran",
    "📄 Invoice PDF",
    "🔔 Notification Center",
    "📣 WA Blast",
    "📈 Export Excel",
    "📑 Laporan Bulanan",
    "🌐 Portal Pelanggan",
    "⚙️ Status Sistem"
])

st.markdown('<div class="main-title">📡 JASUND.NET V15 ENTERPRISE ISP</div>', unsafe_allow_html=True)
st.write("Landing Page • Daftar Pasang WiFi • Billing • Voucher • Pengeluaran • Laba Bersih • Auto Billing H-1")
st.markdown(f'<div class="running">🚀 ONLINE | 📅 Hari ini WIB: <b>{hari_ini}</b> | 📨 Auto Billing H-1 tanggal: <b>{besok.day}</b> | ☁️ Database: <b>Google Sheets</b></div>', unsafe_allow_html=True)
st.write("")

if menu == "🌐 Halaman Depan":
    st.markdown('<div class="main-title">🌐 PASANG WIFI JASUND.NET</div>', unsafe_allow_html=True)
    st.markdown('<div class="clean-box"><h2>Internet Cepat • Stabil • Ping Rendah</h2><p>Mulai dari <b>Rp120.000/bulan</b>. Pilih paket lalu langsung chat admin.</p></div>', unsafe_allow_html=True)
    st.write("")
    p1,p2,p3 = st.columns(3)
    with p1: st.markdown('<div class="card green"><div class="metric-label">🟢 Paket 5 Mbps</div><div class="metric-value">Rp120.000</div><p>YouTube HD • TikTok • Zoom • Browsing • Game Online Ping Rendah 🎮</p></div>', unsafe_allow_html=True)
    with p2: st.markdown('<div class="card blue"><div class="metric-label">🔵 Paket 10 Mbps</div><div class="metric-value">Rp150.000</div><p>Streaming Full HD • CCTV • Meeting • Game Online Ping Sangat Stabil 🎮</p></div>', unsafe_allow_html=True)
    with p3: st.markdown('<div class="card purple"><div class="metric-label">🟣 Paket Custom</div><div class="metric-value">Konsultasi</div><p>Kantor • Sekolah • Usaha • Warnet • CCTV • kebutuhan khusus.</p></div>', unsafe_allow_html=True)

    st.subheader("📲 Daftar Pasang WiFi")
    with st.form("daftar_pasang"):
        nama = st.text_input("Nama")
        wa = st.text_input("Nomor WhatsApp")
        alamat = st.text_area("Alamat Lengkap")
        paket = st.selectbox("Pilih Paket", ["5 Mbps - Rp120.000/bulan", "10 Mbps - Rp150.000/bulan", "Paket Custom"])
        ok = st.form_submit_button("📲 LANJUT KE WHATSAPP ADMIN")
    if ok:
        if not nama or not wa or not alamat: st.error("Nama, nomor WA, dan alamat wajib diisi.")
        else:
            pesan = f"""Assalamualaikum Admin JASUND.NET.

Saya ingin memasang WiFi JASUND.NET.

Nama : {nama}
Nomor WA : {wa}
Alamat : {alamat}

Paket yang dipilih : {paket}

Mohon informasi biaya pemasangan dan jadwal survei.

Terima kasih."""
            tombol_link("📲 KIRIM KE WHATSAPP ADMIN", wa_link(ADMIN_WA, pesan))

    st.subheader("📍 Cek Jangkauan Area")
    with st.form("cek_area"):
        n = st.text_input("Nama", key="n_area")
        w = st.text_input("Nomor WhatsApp", key="w_area")
        a = st.text_area("Alamat / Patokan / Link Google Maps", key="a_area")
        cek = st.form_submit_button("📍 CEK JANGKAUAN VIA WHATSAPP")
    if cek:
        if not n or not w or not a: st.error("Lengkapi data dulu.")
        else:
            pesan = f"""Assalamualaikum Admin JASUND.NET.

Saya ingin cek jangkauan area untuk pemasangan WiFi.

Nama : {n}
Nomor WA : {w}
Alamat / Lokasi : {a}

Mohon dicek apakah lokasi saya sudah terjangkau jaringan JASUND.NET.

Terima kasih."""
            tombol_link("📍 KIRIM CEK AREA", wa_link(ADMIN_WA, pesan))
    st.subheader("Kenapa memilih JASUND.NET?")
    k1,k2,k3 = st.columns(3)
    k1.info("⚡ Ping rendah untuk game online")
    k2.info("📶 Internet stabil untuk rumah dan UMKM")
    k3.info("💬 Support admin ramah dan cepat")

elif menu == "🏠 Dashboard CEO":
    cards = [
        ("👥 Total Pelanggan", total, "green"),("🟢 Aktif", aktif, "blue"),("⭐ VIP", vip, "gold"),("⛔ Suspend", suspend, "red"),
        ("💵 Total Tagihan", rupiah(total_tagihan), "purple"),("🟢 Uang Masuk", rupiah(sudah_lunas), "green"),("🔴 Belum Masuk", rupiah(belum_masuk), "red"),("📊 Lunas", f"{persen_lunas}%", "blue"),
        ("📨 H-1 Besok", h1, "orange"),("📅 Jatuh Tempo Hari Ini", hari_ini_jt, "purple"),("✅ Notif Sukses", notif_sukses, "green"),("❌ Notif Gagal", notif_gagal, "red"),
        ("🏠 Pendapatan Rumahan", rupiah(sudah_lunas), "green"),("🎟️ Pendapatan Voucher", rupiah(pendapatan_voucher), "orange"),("💸 Pengeluaran", rupiah(total_pengeluaran), "red"),("💵 Laba Bersih", rupiah(laba_bersih), "blue")
    ]
    for i in range(0, len(cards), 4):
        cols = st.columns(4)
        for col, (lab,val,war) in zip(cols, cards[i:i+4]):
            with col: st.markdown(f'<div class="card {war}"><div class="metric-label">{lab}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)
        st.write("")
    st.subheader("🎉 Pelanggan Sudah Bayar Hari Ini")
    if len(lunas_hari_ini_df)==0: st.info("Belum ada pelanggan yang bayar hari ini.")
    else: st.dataframe(lunas_hari_ini_df[["NAMA","PAKET","HARGA","TANGGAL BAYAR","METODE BAYAR"]], use_container_width=True)
    st.subheader("📨 Pelanggan Jatuh Tempo Besok")
    calon = df[(df["JATUH TEMPO"]==besok.day)&(df["STATUS"]=="Belum Bayar")]
    if len(calon)==0: st.success("Tidak ada pelanggan H-1 besok.")
    else: st.dataframe(calon, use_container_width=True)
    st.subheader("✅ Pelanggan Sudah Bayar / Lunas")
    lunas_df = df[df["STATUS"]=="Lunas"]
    if len(lunas_df)==0: st.info("Belum ada pelanggan lunas.")
    else: st.dataframe(lunas_df[["NAMA","NO WA","PAKET","HARGA","TANGGAL BAYAR","METODE BAYAR","CATATAN"]], use_container_width=True)
    c1,c2=st.columns(2)
    with c1:
        st.subheader("📶 Sebaran Paket")
        if total: st.bar_chart(df["PAKET"].value_counts())
    with c2:
        st.subheader("💰 Status Pembayaran")
        if total: st.bar_chart(df["STATUS"].value_counts())

elif menu == "➕ Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan Baru")
    with st.form("tambah"):
        nama=st.text_input("Nama Pelanggan"); wa=st.text_input("Nomor WhatsApp"); alamat=st.text_area("Alamat")
        paket=st.selectbox("Paket", ["5 Mbps","10 Mbps","Custom"])
        harga=st.number_input("Harga Bulanan", min_value=0, value=120000, step=10000)
        jt=st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, step=1)
        cat=st.text_area("Catatan")
        simpan=st.form_submit_button("💾 SIMPAN PELANGGAN")
    if simpan:
        if not nama or not wa or harga<=0: st.error("Nama, WA, dan harga wajib diisi.")
        else:
            baru = pd.DataFrame([{"NAMA":nama,"NO WA":rapikan_wa(wa),"ALAMAT":alamat,"PAKET":paket,"HARGA":int(harga),"JATUH TEMPO":int(jt),"STATUS":"Belum Bayar","TANGGAL BAYAR":"","STATUS AKUN":"Aktif","NO INVOICE":"","PERIODE":bulan_tahun(),"METODE BAYAR":"","CATATAN":cat}])
            save_main(pd.concat([df,baru], ignore_index=True))
            tambah_log("TAMBAH_PELANGGAN", nama, wa, "SUKSES", "Pelanggan baru")
            st.success("Pelanggan berhasil ditambahkan."); st.rerun()

elif menu == "👥 Data Pelanggan":
    st.subheader("👥 Data Pelanggan")
    q=st.text_input("Cari pelanggan")
    show=df.copy()
    if q: show=show[show.astype(str).apply(lambda r: r.str.contains(q, case=False).any(), axis=1)]
    st.dataframe(show, use_container_width=True)

elif menu == "✏️ Edit / Hapus":
    st.subheader("✏️ Edit / Hapus")
    if total==0: st.warning("Belum ada pelanggan.")
    else:
        pilih=st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx=df[df["NAMA"].astype(str)==pilih].index[0]
        nama=st.text_input("Nama", value=str(df.loc[idx,"NAMA"])); wa=st.text_input("WA", value=str(df.loc[idx,"NO WA"]))
        alamat=st.text_area("Alamat", value=str(df.loc[idx,"ALAMAT"]))
        paket=st.selectbox("Paket", ["5 Mbps","10 Mbps","Custom"], index=0)
        harga=st.number_input("Harga", min_value=0, value=int(df.loc[idx,"HARGA"]), step=10000)
        jt=st.number_input("Jatuh Tempo", min_value=1,max_value=31,value=int(df.loc[idx,"JATUH TEMPO"]))
        status=st.selectbox("Status Bayar", ["Belum Bayar","Menunggu Verifikasi","Lunas"], index=["Belum Bayar","Menunggu Verifikasi","Lunas"].index(str(df.loc[idx,"STATUS"])) if str(df.loc[idx,"STATUS"]) in ["Belum Bayar","Menunggu Verifikasi","Lunas"] else 0)
        akun=st.selectbox("Status Akun", ["Aktif","Menunggak","Suspend"], index=["Aktif","Menunggak","Suspend"].index(str(df.loc[idx,"STATUS AKUN"])) if str(df.loc[idx,"STATUS AKUN"]) in ["Aktif","Menunggak","Suspend"] else 0)
        cat=st.text_area("Catatan", value=str(df.loc[idx,"CATATAN"]))
        c1,c2=st.columns(2)
        with c1:
            if st.button("💾 UPDATE"):
                df.at[idx,"NAMA"]=nama; df.at[idx,"NO WA"]=rapikan_wa(wa); df.at[idx,"ALAMAT"]=alamat; df.at[idx,"PAKET"]=paket; df.at[idx,"HARGA"]=int(harga); df.at[idx,"JATUH TEMPO"]=int(jt); df.at[idx,"STATUS"]=status; df.at[idx,"STATUS AKUN"]=akun; df.at[idx,"CATATAN"]=cat
                if status=="Lunas":
                    df.at[idx,"TANGGAL BAYAR"]=str(hari_ini)
                    if not df.at[idx,"NO INVOICE"]: df.at[idx,"NO INVOICE"]=buat_invoice_no(df.loc[idx])
                save_main(df); tambah_log("UPDATE", nama, wa, "SUKSES", f"{status}/{akun}"); st.success("Updated"); st.rerun()
        with c2:
            yakin=st.checkbox("Yakin hapus")
            if st.button("🗑️ HAPUS") and yakin:
                save_main(df.drop(idx).reset_index(drop=True)); tambah_log("HAPUS", pilih, "", "SUKSES", "Dihapus"); st.success("Dihapus"); st.rerun()

elif menu == "📨 Invoice H-1":
    st.subheader("📨 Invoice H-1")
    calon=df[(df["JATUH TEMPO"]==besok.day)&(df["STATUS"]=="Belum Bayar")]
    if len(calon)==0: st.success("Tidak ada pelanggan H-1.")
    for i,row in calon.iterrows():
        no=rapikan_wa(row["NO WA"]); pesan=pesan_invoice(row)
        st.markdown("---"); st.write(row["NAMA"], rupiah(row["HARGA"]), no); st.text_area("Preview", pesan, height=240, key=f"p{i}")
        tombol_link("💬 Kirim Manual WhatsApp", wa_link(no, pesan))
        if st.button(f"🚀 Kirim Fonnte {row['NAMA']}", key=f"k{i}"):
            try:
                h=kirim_fonnte(no,pesan); tambah_log("INVOICE_MANUAL",row["NAMA"],no,"SUKSES" if h.status_code==200 else "GAGAL",h.text); st.write(h.text)
            except Exception as e: st.error(e)

elif menu == "💳 Pembayaran Masuk":
    st.subheader("💳 Pembayaran Masuk")
    if total:
        pilih=st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx=df[df["NAMA"].astype(str)==pilih].index[0]
        metode=st.selectbox("Metode", ["BCA","BRI","DANA","Tunai","Lainnya"])
        cat=st.text_area("Catatan Pembayaran", value=str(df.loc[idx,"CATATAN"]))
        st.write("Tagihan:", rupiah(df.loc[idx,"HARGA"]))
        if st.button("✅ KONFIRMASI LUNAS"):
            if not df.at[idx,"NO INVOICE"]: df.at[idx,"NO INVOICE"]=buat_invoice_no(df.loc[idx])
            df.at[idx,"STATUS"]="Lunas"; df.at[idx,"STATUS AKUN"]="Aktif"; df.at[idx,"TANGGAL BAYAR"]=str(hari_ini); df.at[idx,"METODE BAYAR"]=metode; df.at[idx,"CATATAN"]=cat
            save_main(df)
            try:
                h=kirim_fonnte(rapikan_wa(df.loc[idx,"NO WA"]), pesan_lunas(df.loc[idx])); tambah_log("KONFIRMASI_LUNAS", df.loc[idx,"NAMA"], df.loc[idx,"NO WA"], "SUKSES" if h.status_code==200 else "GAGAL", h.text)
            except Exception as e: tambah_log("KONFIRMASI_LUNAS", df.loc[idx,"NAMA"], df.loc[idx,"NO WA"], "GAGAL", str(e))
            st.success("Status lunas disimpan."); st.rerun()

elif menu == "✅ Sudah Bayar":
    st.subheader("✅ Pelanggan Sudah Bayar")
    lunas_df=df[df["STATUS"]=="Lunas"]
    c1,c2,c3=st.columns(3); c1.metric("Jumlah Lunas", len(lunas_df)); c2.metric("Uang Masuk", rupiah(sudah_lunas)); c3.metric("% Lunas", f"{persen_lunas}%")
    st.dataframe(lunas_df, use_container_width=True)

elif menu == "🎟️ Pemasukan Voucher":
    st.subheader("🎟️ Pemasukan Voucher")
    with st.form("voucher"):
        t=st.date_input("Tanggal", value=hari_ini); penyetor=st.text_input("Penyetor", value="Aceng Abdul Roup"); totalv=st.number_input("Total Setor", min_value=0, step=10000); cat=st.text_area("Catatan"); ok=st.form_submit_button("💾 SIMPAN")
    if ok:
        if totalv<=0: st.error("Total setor harus lebih dari 0.")
        else:
            baru=pd.DataFrame([{"TANGGAL":str(t),"PENYETOR":penyetor,"TOTAL SETOR":int(totalv),"CATATAN":cat}])
            save_voucher(pd.concat([df_voucher,baru], ignore_index=True)); tambah_log("PEMASUKAN_VOUCHER", penyetor, "-", "SUKSES", rupiah(totalv)); st.success("Disimpan"); st.rerun()
    st.metric("Voucher Bulan Ini", rupiah(pendapatan_voucher)); st.dataframe(df_voucher, use_container_width=True)

elif menu == "💸 Pengeluaran":
    st.subheader("💸 Pengeluaran")
    with st.form("pengeluaran"):
        t=st.date_input("Tanggal", value=hari_ini); kategori=st.selectbox("Kategori", ["Bandwidth","Listrik","Peralatan","Transport","Gaji","Sewa","Lain-lain"]); ket=st.text_area("Keterangan"); j=st.number_input("Jumlah", min_value=0, step=10000); ok=st.form_submit_button("💾 SIMPAN")
    if ok:
        if j<=0: st.error("Jumlah harus lebih dari 0.")
        else:
            baru=pd.DataFrame([{"TANGGAL":str(t),"KATEGORI":kategori,"KETERANGAN":ket,"JUMLAH":int(j)}])
            save_pengeluaran(pd.concat([df_pengeluaran,baru], ignore_index=True)); tambah_log("PENGELUARAN", kategori, "-", "SUKSES", rupiah(j)); st.success("Disimpan"); st.rerun()
    st.metric("Pengeluaran Bulan Ini", rupiah(total_pengeluaran)); st.dataframe(df_pengeluaran, use_container_width=True)

elif menu == "📄 Invoice PDF":
    st.subheader("📄 Invoice PDF")
    if total:
        pilih=st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        row=df[df["NAMA"].astype(str)==pilih].iloc[0]
        st.write(row["NAMA"], rupiah(row["HARGA"]), row["STATUS"])
        st.download_button("⬇️ DOWNLOAD INVOICE PDF", data=buat_pdf(row), file_name=f"Invoice_JASUNDNET_{row['NAMA']}.pdf", mime="application/pdf")

elif menu == "🔔 Notification Center":
    st.subheader("🔔 Notification Center")
    st.metric("Total Log", len(df_log))
    st.dataframe(df_log.tail(200).sort_index(ascending=False), use_container_width=True)
    if st.button("🧪 TEST TELEGRAM"):
        try:
            h=kirim_telegram("📡 Test Telegram JASUND.NET V15 berhasil."); tambah_log("TEST_TELEGRAM","ADMIN",TELEGRAM_CHAT_ID,"SUKSES" if h.status_code==200 else "GAGAL",h.text); st.write(h.text)
        except Exception as e: st.error(e)

elif menu == "📣 WA Blast":
    st.subheader("📣 WA Blast")
    target=st.selectbox("Target", ["Semua","Belum Bayar","Lunas"])
    pesan=st.text_area("Pesan")
    target_df = df if target=="Semua" else df[df["STATUS"]==target]
    st.write("Target:", len(target_df))
    if st.button("🚀 KIRIM BLAST") and pesan:
        s=g=0
        for _,r in target_df.iterrows():
            try:
                h=kirim_fonnte(rapikan_wa(r["NO WA"]), pesan)
                if h.status_code==200: s+=1; status="SUKSES"
                else: g+=1; status="GAGAL"
                tambah_log("WA_BLAST",r["NAMA"],r["NO WA"],status,h.text)
            except Exception as e: g+=1; tambah_log("WA_BLAST",r["NAMA"],r["NO WA"],"GAGAL",str(e))
        st.success(f"Selesai. Berhasil {s}, Gagal {g}")

elif menu == "📈 Export Excel":
    st.subheader("📈 Export")
    st.download_button("Download Excel Pelanggan", export_excel_bytes(df), f"JASUNDNET_DATA_{hari_ini}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Download CSV Pelanggan", df.to_csv(index=False).encode("utf-8"), f"JASUNDNET_DATA_{hari_ini}.csv", "text/csv")

elif menu == "📑 Laporan Bulanan":
    st.subheader("📑 Laporan Bulanan")
    st.write("Pendapatan Rumahan:", rupiah(sudah_lunas))
    st.write("Pendapatan Voucher:", rupiah(pendapatan_voucher))
    st.write("Total Pendapatan:", rupiah(total_pendapatan))
    st.write("Pengeluaran:", rupiah(total_pengeluaran))
    st.write("Laba Bersih:", rupiah(laba_bersih))

elif menu == "🌐 Portal Pelanggan":
    st.subheader("🌐 Portal Pelanggan")
    no=st.text_input("Masukkan nomor WA pelanggan")
    if no:
        hasil=df[df["NO WA"].astype(str).apply(rapikan_wa)==rapikan_wa(no)]
        if len(hasil)==0: st.error("Data tidak ditemukan.")
        else:
            r=hasil.iloc[0]
            c1,c2,c3=st.columns(3); c1.metric("Nama", r["NAMA"]); c2.metric("Paket", r["PAKET"]); c3.metric("Tagihan", rupiah(r["HARGA"]))
            st.write("Status:", r["STATUS"]); st.download_button("Download Invoice", buat_pdf(r), f"Invoice_{r['NAMA']}.pdf", "application/pdf")
            tombol_link("💬 Lapor Gangguan ke Admin", wa_link(ADMIN_WA, f"Assalamualaikum Admin JASUND.NET.\nSaya {r['NAMA']} ingin melaporkan gangguan internet.\nAlamat: {r['ALAMAT']}"))

elif menu == "⚙️ Status Sistem":
    st.subheader("⚙️ Status Sistem")
    st.markdown(f"""<div class="clean-box">
    ✅ Versi: JASUND.NET V15 ENTERPRISE ISP<br>
    ✅ Database: Google Sheets<br>
    ✅ Landing Page Pasang WiFi: Aktif<br>
    ✅ Pemasukan Voucher: Aktif<br>
    ✅ Pengeluaran: Aktif<br>
    ✅ Laba Bersih: Aktif<br>
    ✅ Auto Billing H-1: Aktif<br>
    ✅ WhatsApp Fonnte: Aktif<br>
    ✅ Telegram Admin: Aktif<br>
    </div>""", unsafe_allow_html=True)
