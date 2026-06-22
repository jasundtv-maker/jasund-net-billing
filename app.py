import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF

st.set_page_config(
    page_title="JASUND.NET V9 ISP PRO MAX",
    page_icon="📡",
    layout="wide"
)

SHEET_ID = "1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"

KOLOM = [
    "NAMA", "NO WA", "ALAMAT", "PAKET", "HARGA",
    "JATUH TEMPO", "STATUS", "TANGGAL BAYAR",
    "STATUS AKUN", "NO INVOICE", "PERIODE",
    "METODE BAYAR", "CATATAN"
]

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def bulan_tahun():
    return tanggal_wib().strftime("%B %Y")

def koneksi_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def load_data():
    sheet = koneksi_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        df = pd.DataFrame(columns=KOLOM)

    for col in KOLOM:
        if col not in df.columns:
            df[col] = ""

    df["HARGA"] = pd.to_numeric(df["HARGA"], errors="coerce").fillna(0).astype(int)
    df["JATUH TEMPO"] = pd.to_numeric(df["JATUH TEMPO"], errors="coerce").fillna(1).astype(int)
    df["NO WA"] = df["NO WA"].astype(str)
    df["STATUS"] = df["STATUS"].astype(str).str.strip().str.lower()
    df["STATUS"] = df["STATUS"].replace({
    "belum bayar": "Belum Bayar",
    "lunas": "Lunas",
    "menunggu verifikasi": "Menunggu Verifikasi"
})
    df["STATUS AKUN"] = df["STATUS AKUN"].replace("", "Aktif").fillna("Aktif")
    df["PERIODE"] = df["PERIODE"].replace("", bulan_tahun()).fillna(bulan_tahun())

    return df[KOLOM]

def save_data(df):
    sheet = koneksi_sheet()
    df = df[KOLOM].copy()
    data = [KOLOM] + df.astype(str).values.tolist()
    sheet.clear()
    sheet.update(data)

def rupiah(x):
    return f"Rp {int(x):,}".replace(",", ".")

def rapikan_wa(no):
    no = str(no).replace(" ", "").replace("-", "").replace("+", "")
    if no.startswith("08"):
        no = "62" + no[1:]
    return no

def buat_invoice_no(row):
    wa = str(row["NO WA"])[-4:]
    return f"JNET-{datetime.now().strftime('%Y%m')}-{wa}"

def get_secret(name):
    try:
        return st.secrets[name]
    except:
        return ""

FONNTE_TOKEN = get_secret("FONNTE_TOKEN")

def kirim_fonnte(token, target, pesan):
    return requests.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": token},
        data={"target": target, "message": pesan, "countryCode": "62"},
        timeout=30
    )

def pesan_invoice(row):
    no_invoice = row["NO INVOICE"] if row["NO INVOICE"] else buat_invoice_no(row)
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini telah terbit.

No Invoice : {no_invoice}
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

Hormat kami,
Admin JASUND.NET
"""

def pesan_lunas(row):
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Terima kasih.

Pembayaran internet JASUND.NET telah kami terima.

No Invoice : {row['NO INVOICE']}
Periode : {row['PERIODE']}
Paket : {row['PAKET']}
Nominal : {rupiah(row['HARGA'])}
Status : LUNAS ✅

Semoga layanan internet JASUND.NET tetap lancar dan bermanfaat.

Admin JASUND.NET
"""

def tombol_wa(no, pesan, teks="💬 Kirim Manual WhatsApp"):
    link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
    st.markdown(
        f'<a href="{link}" target="_blank" class="wa-button">{teks}</a>',
        unsafe_allow_html=True
    )

def clean_text(text):
    return str(text).encode("latin-1", "replace").decode("latin-1")

def buat_pdf(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    no_invoice = row["NO INVOICE"] if row["NO INVOICE"] else buat_invoice_no(row)

    pdf.set_fill_color(24, 78, 138)
    pdf.rect(0, 0, 210, 28, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "JASUND.NET", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Internet Service Provider & RTRW NET Billing", ln=True)

    pdf.set_xy(138, 8)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(58, 10, "INVOICE", align="R")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(58, 95, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(90, 8, " BILL TO", border=1, fill=True)

    pdf.set_xy(122, 38)
    pdf.cell(74, 8, " DETAIL INVOICE", border=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)

    pdf.set_xy(10, 46)
    pdf.multi_cell(
        90, 7,
        clean_text(f"{row['NAMA']}\n{row['ALAMAT']}\nWA: {row['NO WA']}"),
        border=1
    )

    pdf.set_xy(122, 46)
    details = [
        ("Tanggal", str(tanggal_wib())),
        ("Invoice No", no_invoice),
        ("Periode", str(row["PERIODE"])),
        ("Jatuh Tempo", f"Tanggal {int(row['JATUH TEMPO'])}"),
        ("Status", str(row["STATUS"])),
    ]

    for k, v in details:
        pdf.set_x(122)
        pdf.cell(34, 7, k, border=1)
        pdf.cell(40, 7, clean_text(v), border=1, ln=True)

    pdf.ln(12)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(58, 95, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(105, 8, " DESCRIPTION", border=1, fill=True)
    pdf.cell(25, 8, " QTY", border=1, fill=True, align="C")
    pdf.cell(55, 8, " AMOUNT", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    desc = f"Tagihan Internet JASUND.NET\nPaket {row['PAKET']}"
    y_start = pdf.get_y()
    pdf.multi_cell(105, 10, clean_text(desc), border=1)

    y_after = pdf.get_y()
    pdf.set_xy(115, y_start)
    pdf.cell(25, 20, "1", border=1, align="C")
    pdf.set_xy(140, y_start)
    pdf.cell(55, 20, rupiah(row["HARGA"]), border=1, align="R")

    pdf.ln(8)

    pdf.set_x(115)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(35, 7, "Subtotal")
    pdf.cell(45, 7, rupiah(row["HARGA"]), align="R", ln=True)

    pdf.set_x(115)
    pdf.cell(35, 7, "Discount")
    pdf.cell(45, 7, "-", align="R", ln=True)

    pdf.set_x(115)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(35, 8, "Grand Total", border="T")
    pdf.cell(45, 8, rupiah(row["HARGA"]), border="T", align="R", ln=True)

    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(58, 95, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(95, 8, " METODE PEMBAYARAN", border=1, fill=True, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        95, 7,
        clean_text(
            "BCA  : 1831149782\n"
            "a.n. Aceng Abdul Roup\n\n"
            "BRI  : 4062 0103 3487 530\n"
            "a.n. Aceng Abdul Roup\n\n"
            "DANA : 081395440454\n"
            "a.n. Aceng Abdul Roup"
        ),
        border=1
    )

    pdf.ln(7)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "CATATAN:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 7,
        clean_text(
            "Mohon kirimkan bukti transfer kepada admin JASUND.NET.\n"
            "Pembayaran juga dapat dilakukan langsung ke kantor JASUND.NET.\n"
            "Abaikan invoice ini apabila sudah melakukan pembayaran sebelumnya."
        )
    )

    pdf.ln(12)
    pdf.set_x(125)
    pdf.cell(70, 7, "Hormat kami,", ln=True, align="C")
    pdf.ln(18)
    pdf.set_x(125)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(70, 7, "Admin JASUND.NET", ln=True, align="C")

    pdf.set_y(-22)
    pdf.set_fill_color(24, 78, 138)
    pdf.rect(0, 282, 210, 12, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 8, "JASUND.NET - Internet Service Provider | Billing RTRW NET", align="C")

    return bytes(pdf.output(dest="S"))

# DATA
df = load_data()
hari_ini = tanggal_wib()
besok = hari_ini + timedelta(days=1)

total = len(df)
belum = len(df[df["STATUS"] == "Belum Bayar"]) if total else 0
lunas = len(df[df["STATUS"] == "Lunas"]) if total else 0
menunggu = len(df[df["STATUS"] == "Menunggu Verifikasi"]) if total else 0
aktif = len(df[df["STATUS AKUN"] == "Aktif"]) if total else 0
suspend = len(df[df["STATUS AKUN"] == "Suspend"]) if total else 0
menunggak = len(df[df["STATUS AKUN"] == "Menunggak"]) if total else 0
h1 = len(df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]) if total else 0
hari_ini_jt = len(df[(df["JATUH TEMPO"] == hari_ini.day) & (df["STATUS"] == "Belum Bayar")]) if total else 0
total_tagihan = df["HARGA"].sum() if total else 0
sudah_lunas = df[df["STATUS"] == "Lunas"]["HARGA"].sum() if total else 0
belum_masuk = df[df["STATUS"] != "Lunas"]["HARGA"].sum() if total else 0
persen_lunas = round((lunas / total) * 100) if total else 0

# STYLE
st.markdown("""
<style>
.stApp {
    background:
    radial-gradient(circle at top left, rgba(34,197,94,.28), transparent 32%),
    radial-gradient(circle at top right, rgba(168,85,247,.35), transparent 32%),
    linear-gradient(135deg, #020617 0%, #071426 45%, #022c22 100%);
    color:white;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a, #111827);
}
h1,h2,h3,h4,p,label {color:#f8fafc !important;}
.main-title {
    font-size:46px;
    font-weight:900;
    background:linear-gradient(90deg,#22c55e,#38bdf8,#a78bfa,#fb7185);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}
.running {
    padding:14px 22px;
    border-radius:18px;
    background:linear-gradient(90deg,rgba(34,197,94,.25),rgba(56,189,248,.20),rgba(168,85,247,.20));
    border:1px solid rgba(255,255,255,.18);
    color:white;
    font-weight:700;
}
.card {
    padding:24px;
    border-radius:24px;
    color:white;
    box-shadow:0 0 30px rgba(255,255,255,.25);
}
.green{background:linear-gradient(135deg,#16a34a,#22c55e);}
.blue{background:linear-gradient(135deg,#0284c7,#38bdf8);}
.purple{background:linear-gradient(135deg,#7c3aed,#c084fc);}
.orange{background:linear-gradient(135deg,#ea580c,#facc15);}
.red{background:linear-gradient(135deg,#dc2626,#fb7185);}
.dark{background:linear-gradient(135deg,#334155,#0f172a);}
.metric-label{font-size:15px;font-weight:700;}
.metric-value{font-size:34px;font-weight:900;margin-top:8px;}
.wa-button {
    display:inline-block;
    background:linear-gradient(135deg,#25D366,#128C7E);
    color:white !important;
    padding:12px 24px;
    border-radius:14px;
    text-decoration:none !important;
    font-weight:900;
    font-size:16px;
    box-shadow:0 0 22px rgba(37,211,102,.45);
    margin-top:8px;
    margin-bottom:18px;
}
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background:linear-gradient(135deg,#22c55e,#06b6d4) !important;
    color:white !important;
    border:none !important;
    border-radius:14px !important;
    font-weight:900 !important;
    padding:10px 22px !important;
    box-shadow:0 0 18px rgba(34,197,94,.35) !important;
}
.clean-box{
    padding:18px;
    border-radius:18px;
    background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.15);
    color:white;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("📡 JASUND.NET")
st.sidebar.caption("ISP Billing V9 Pro Max")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard CEO",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💳 Pembayaran Masuk",
    "📄 Invoice PDF",
    "📊 Rekap",
    "⚙️ Status Sistem"
])

st.markdown('<div class="main-title">📡 JASUND.NET ISP BILLING V9 PRO MAX</div>', unsafe_allow_html=True)
st.write("Dashboard CEO • Google Sheets • Auto Billing H-1 • Invoice Pro • Pembayaran Lunas")

st.markdown(f"""
<div class="running">
🚀 ONLINE | 📅 Hari ini WIB: <b>{hari_ini}</b> | 📨 Auto Billing H-1 tanggal: <b>{besok.day}</b> | ☁️ Database: <b>Google Sheets</b>
</div>
""", unsafe_allow_html=True)

st.write("")

if menu == "🏠 Dashboard CEO":
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("👥 Total Pelanggan", total, "green"),
        ("🟢 Aktif", aktif, "blue"),
        ("⚠️ Menunggak", menunggak, "orange"),
        ("⛔ Suspend", suspend, "red"),
    ]
    for col, (label, val, warna) in zip([c1,c2,c3,c4], cards):
        with col:
            st.markdown(f'<div class="card {warna}"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    st.write("")

    c5, c6, c7, c8 = st.columns(4)
    cards2 = [
        ("💵 Total Tagihan", rupiah(total_tagihan), "purple"),
        ("🟢 Uang Masuk", rupiah(sudah_lunas), "green"),
        ("🔴 Belum Masuk", rupiah(belum_masuk), "red"),
        ("📊 Lunas", f"{persen_lunas}%", "blue"),
    ]
    for col, (label, val, warna) in zip([c5,c6,c7,c8], cards2):
        with col:
            st.markdown(f'<div class="card {warna}"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    st.write("")

    c9, c10, c11, c12 = st.columns(4)
    cards3 = [
        ("📨 H-1 Besok", h1, "orange"),
        ("📅 Jatuh Tempo Hari Ini", hari_ini_jt, "purple"),
        ("⏳ Belum Bayar", belum, "red"),
        ("🧾 Menunggu Verifikasi", menunggu, "dark"),
    ]
    for col, (label, val, warna) in zip([c9,c10,c11,c12], cards3):
        with col:
            st.markdown(f'<div class="card {warna}"><div class="metric-label">{label}</div><div class="metric-value">{val}</div></div>', unsafe_allow_html=True)

    st.write("")
    st.subheader("📨 Pelanggan Jatuh Tempo Besok")
    calon = df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]
    if len(calon) == 0:
        st.success("Tidak ada pelanggan H-1 besok.")
    else:
        st.dataframe(calon, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📶 Sebaran Paket")
        if total:
            st.bar_chart(df["PAKET"].value_counts())
    with col2:
        st.subheader("💰 Status Pembayaran")
        if total:
            st.bar_chart(df["STATUS"].value_counts())

elif menu == "➕ Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan Baru")

    with st.form("form_tambah"):
        nama = st.text_input("Nama Pelanggan")
        wa = st.text_input("Nomor WhatsApp", placeholder="628xxxxxxxxxx")
        alamat = st.text_area("Alamat")
        paket = st.selectbox("Paket Internet", ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"])
        harga = st.number_input("Harga Bulanan", min_value=0, step=10000)
        jatuh = st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, step=1)
        catatan = st.text_area("Catatan")
        simpan = st.form_submit_button("💾 SIMPAN PELANGGAN")

    if simpan:
        if nama == "" or wa == "" or harga == 0:
            st.error("Nama, WA, dan harga wajib diisi.")
        else:
            baru = pd.DataFrame([{
                "NAMA": nama,
                "NO WA": rapikan_wa(wa),
                "ALAMAT": alamat,
                "PAKET": paket,
                "HARGA": int(harga),
                "JATUH TEMPO": int(jatuh),
                "STATUS": "Belum Bayar",
                "TANGGAL BAYAR": "",
                "STATUS AKUN": "Aktif",
                "NO INVOICE": "",
                "PERIODE": bulan_tahun(),
                "METODE BAYAR": "",
                "CATATAN": catatan
            }])
            df = pd.concat([df, baru], ignore_index=True)
            save_data(df)
            st.success("Pelanggan berhasil ditambahkan.")
            st.rerun()

elif menu == "👥 Data Pelanggan":
    st.subheader("👥 Data Pelanggan")
    cari = st.text_input("Cari pelanggan")
    tampil = df.copy()
    if cari:
        tampil = tampil[tampil.astype(str).apply(lambda row: row.str.contains(cari, case=False).any(), axis=1)]
    st.dataframe(tampil, use_container_width=True)

elif menu == "✏️ Edit / Hapus":
    st.subheader("✏️ Edit / Hapus Pelanggan")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx = df[df["NAMA"].astype(str) == pilih].index[0]

        paket_list = ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"]
        paket_lama = str(df.loc[idx, "PAKET"])
        paket_index = paket_list.index(paket_lama) if paket_lama in paket_list else 0

        nama = st.text_input("Nama", value=str(df.loc[idx, "NAMA"]))
        wa = st.text_input("No WA", value=str(df.loc[idx, "NO WA"]))
        alamat = st.text_area("Alamat", value=str(df.loc[idx, "ALAMAT"]))
        paket = st.selectbox("Paket", paket_list, index=paket_index)
        harga = st.number_input("Harga", min_value=0, value=int(df.loc[idx, "HARGA"]), step=10000)
        jatuh = st.number_input("Jatuh Tempo", min_value=1, max_value=31, value=int(df.loc[idx, "JATUH TEMPO"]))
        status = st.selectbox("Status Bayar", ["Belum Bayar", "Menunggu Verifikasi", "Lunas"], index=0)
        status_akun = st.selectbox("Status Akun", ["Aktif", "Menunggak", "Suspend"], index=0)
        periode = st.text_input("Periode", value=str(df.loc[idx, "PERIODE"]))
        catatan = st.text_area("Catatan", value=str(df.loc[idx, "CATATAN"]))

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 UPDATE DATA"):
                df.at[idx, "NAMA"] = nama
                df.at[idx, "NO WA"] = rapikan_wa(wa)
                df.at[idx, "ALAMAT"] = alamat
                df.at[idx, "PAKET"] = paket
                df.at[idx, "HARGA"] = int(harga)
                df.at[idx, "JATUH TEMPO"] = int(jatuh)
                df.at[idx, "STATUS"] = status
                df.at[idx, "STATUS AKUN"] = status_akun
                df.at[idx, "PERIODE"] = periode
                df.at[idx, "CATATAN"] = catatan
                if status == "Lunas":
                    df.at[idx, "TANGGAL BAYAR"] = str(hari_ini)
                    if not df.at[idx, "NO INVOICE"]:
                        df.at[idx, "NO INVOICE"] = buat_invoice_no(df.loc[idx])
                save_data(df)
                st.success("Data berhasil diupdate.")
                st.rerun()

        with col2:
            yakin = st.checkbox("Saya yakin ingin menghapus pelanggan ini")
            if st.button("🗑️ HAPUS PELANGGAN"):
                if yakin:
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success("Pelanggan berhasil dihapus.")
                    st.rerun()
                else:
                    st.warning("Centang konfirmasi dulu.")

elif menu == "📨 Invoice H-1":
    st.subheader("📨 Invoice H-1")

    calon = df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]
    st.info(f"Sistem mencari pelanggan jatuh tempo besok tanggal {besok.day} WIB. Notifikasi otomatis cukup H-1.")

    if len(calon) == 0:
        st.success("Tidak ada pelanggan H-1.")
    else:
        for i, row in calon.iterrows():
            pesan = pesan_invoice(row)
            no = rapikan_wa(row["NO WA"])

            st.markdown("---")
            st.write("Nama:", row["NAMA"])
            st.write("No WA:", no)
            st.write("Paket:", row["PAKET"])
            st.write("Tagihan:", rupiah(row["HARGA"]))
            st.text_area("Preview Invoice", pesan, height=280, key=f"preview_{i}")

            tombol_wa(no, pesan)

            if FONNTE_TOKEN:
                if st.button(f"🚀 KIRIM FONNTE KE {row['NAMA']}", key=f"fonnte_{i}"):
                    hasil = kirim_fonnte(FONNTE_TOKEN, no, pesan)
                    if hasil.status_code == 200:
                        st.success("Invoice berhasil dikirim.")
                    else:
                        st.error(hasil.text)

elif menu == "💳 Pembayaran Masuk":
    st.subheader("💳 Pembayaran Masuk")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx = df[df["NAMA"].astype(str) == pilih].index[0]

        row = df.loc[idx]
        st.write("Tagihan:", rupiah(row["HARGA"]))
        st.write("Status Sekarang:", row["STATUS"])

        metode = st.selectbox("Metode Bayar", ["BCA", "BRI", "DANA", "Tunai", "Lainnya"])
        catatan = st.text_area("Catatan Pembayaran", value=str(row["CATATAN"]))

        if st.button("✅ KONFIRMASI LUNAS"):
            if not df.at[idx, "NO INVOICE"]:
                df.at[idx, "NO INVOICE"] = buat_invoice_no(df.loc[idx])

            df.at[idx, "STATUS"] = "Lunas"
            df.at[idx, "STATUS AKUN"] = "Aktif"
            df.at[idx, "TANGGAL BAYAR"] = str(hari_ini)
            df.at[idx, "METODE BAYAR"] = metode
            df.at[idx, "CATATAN"] = catatan

            save_data(df)

            no = rapikan_wa(df.loc[idx, "NO WA"])
            pesan = pesan_lunas(df.loc[idx])

            if FONNTE_TOKEN:
                try:
                    kirim_fonnte(FONNTE_TOKEN, no, pesan)
                    st.success("Status lunas disimpan dan WA konfirmasi terkirim.")
                except:
                    st.success("Status lunas disimpan. WA konfirmasi gagal dikirim.")
            else:
                tombol_wa(no, pesan, "💬 Kirim WA Konfirmasi Lunas")

            st.rerun()

elif menu == "📄 Invoice PDF":
    st.subheader("📄 Download Invoice PDF")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx = df[df["NAMA"].astype(str) == pilih].index[0]
        row = df.loc[idx]

        st.write("Nama:", row["NAMA"])
        st.write("Tagihan:", rupiah(row["HARGA"]))
        st.write("Status:", row["STATUS"])

        pdf_bytes = buat_pdf(row)

        st.download_button(
            "⬇️ DOWNLOAD INVOICE PDF",
            data=pdf_bytes,
            file_name=f"Invoice_JASUNDNET_{row['NAMA']}.pdf",
            mime="application/pdf"
        )

elif menu == "📊 Rekap":
    st.subheader("📊 Rekap Tagihan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tagihan", rupiah(total_tagihan))
    c2.metric("Sudah Lunas", rupiah(sudah_lunas))
    c3.metric("Belum Masuk", rupiah(belum_masuk))
    c4.metric("Persentase Lunas", f"{persen_lunas}%")
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "⬇️ Export CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="rekap_jasund_net.csv",
        mime="text/csv"
    )

elif menu == "⚙️ Status Sistem":
    st.subheader("⚙️ Status Sistem")
    st.markdown(f"""
    <div class="clean-box">
    ✅ Database: Google Sheets<br>
    ✅ Hari ini WIB: {hari_ini}<br>
    ✅ Auto Billing: H-1 saja<br>
    ✅ WhatsApp API: Fonnte<br>
    ✅ Invoice PDF: Aktif<br>
    ✅ Konfirmasi Lunas: Aktif<br>
    ✅ Versi: JASUND.NET V9 ISP PREMIUM PRO MAX
    </div>
    """, unsafe_allow_html=True)
