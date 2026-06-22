import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF

st.set_page_config(page_title="JASUND.NET V8 ISP PRO", page_icon="📡", layout="wide")

SHEET_ID = "1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"

KOLOM = [
    "NAMA", "NO WA", "ALAMAT", "PAKET", "HARGA",
    "JATUH TEMPO", "STATUS", "TANGGAL BAYAR", "CATATAN"
]

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

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
    df["STATUS"] = df["STATUS"].replace("", "Belum Bayar").fillna("Belum Bayar")

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

def pesan_invoice(row):
    return f"""Assalamualaikum Bapak/Ibu {row['NAMA']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini telah terbit.

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

def tombol_wa(no, pesan):
    link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
    st.markdown(
        f'<a href="{link}" target="_blank" class="wa-button">💬 Kirim Manual WhatsApp</a>',
        unsafe_allow_html=True
    )

def kirim_fonnte(token, target, pesan):
    return requests.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": token},
        data={"target": target, "message": pesan, "countryCode": "62"},
        timeout=30
    )

def get_secret(name):
    try:
        return st.secrets[name]
    except:
        return ""

def buat_pdf(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "INVOICE JASUND.NET", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(8)
    pdf.cell(0, 8, f"Nama Pelanggan : {row['NAMA']}", ln=True)
    pdf.cell(0, 8, f"No WhatsApp    : {row['NO WA']}", ln=True)
    pdf.cell(0, 8, f"Alamat         : {row['ALAMAT']}", ln=True)
    pdf.cell(0, 8, f"Paket Internet : {row['PAKET']}", ln=True)
    pdf.cell(0, 8, f"Tagihan        : {rupiah(row['HARGA'])}", ln=True)
    pdf.cell(0, 8, f"Jatuh Tempo    : Tanggal {int(row['JATUH TEMPO'])}", ln=True)
    pdf.cell(0, 8, f"Status         : {row['STATUS']}", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Metode Pembayaran:", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "BCA  : 1831149782 a.n. Aceng Abdul Roup", ln=True)
    pdf.cell(0, 8, "BRI  : 4062 0103 3487 530 a.n. Aceng Abdul Roup", ln=True)
    pdf.cell(0, 8, "DANA : 081395440454 a.n. Aceng Abdul Roup", ln=True)

    pdf.ln(8)
    pdf.multi_cell(0, 8, "Mohon kirimkan bukti transfer kepada admin JASUND.NET. Abaikan invoice ini apabila sudah melakukan pembayaran.")

    return bytes(pdf.output(dest="S"))

FONNTE_TOKEN = get_secret("FONNTE_TOKEN")

df = load_data()
hari_ini = tanggal_wib()
besok = hari_ini + timedelta(days=1)

total = len(df)
belum = len(df[df["STATUS"] == "Belum Bayar"]) if total else 0
lunas = len(df[df["STATUS"] == "Lunas"]) if total else 0
h1 = len(df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]) if total else 0
total_tagihan = df["HARGA"].sum() if total else 0
sudah_lunas = df[df["STATUS"] == "Lunas"]["HARGA"].sum() if total else 0
belum_masuk = df[df["STATUS"] != "Lunas"]["HARGA"].sum() if total else 0
persen_lunas = round((lunas / total) * 100) if total else 0

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
st.sidebar.caption("ISP Billing Premium V8")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💰 Pembayaran",
    "📄 Invoice PDF",
    "📊 Rekap",
    "⚙️ Status Sistem"
])

st.markdown('<div class="main-title">📡 JASUND.NET ISP BILLING V8</div>', unsafe_allow_html=True)
st.write("Google Sheets Database • Auto Billing H-1 • WhatsApp Fonnte • Invoice PDF")

st.markdown(f"""
<div class="running">
🚀 ONLINE | 📅 Hari ini WIB: <b>{hari_ini}</b> | 📨 Auto Billing H-1 tanggal: <b>{besok.day}</b> | ☁️ Database: <b>Google Sheets</b>
</div>
""", unsafe_allow_html=True)

st.write("")

if menu == "🏠 Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("👥 Total Pelanggan", total, "green"),
        ("⏳ Belum Bayar", belum, "red"),
        ("✅ Lunas", lunas, "blue"),
        ("📨 H-1 Besok", h1, "orange"),
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
                "CATATAN": catatan
            }])
            df = pd.concat([df, baru], ignore_index=True)
            save_data(df)
            st.success("Pelanggan berhasil ditambahkan ke Google Sheets.")
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
        status = st.selectbox("Status", ["Belum Bayar", "Lunas", "Menunggu Verifikasi"], index=0)
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
                df.at[idx, "CATATAN"] = catatan
                if status == "Lunas":
                    df.at[idx, "TANGGAL BAYAR"] = str(hari_ini)
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
            st.text_area("Preview Invoice", pesan, height=260, key=f"preview_{i}")

            tombol_wa(no, pesan)

            if FONNTE_TOKEN:
                if st.button(f"🚀 KIRIM FONNTE KE {row['NAMA']}", key=f"fonnte_{i}"):
                    hasil = kirim_fonnte(FONNTE_TOKEN, no, pesan)
                    if hasil.status_code == 200:
                        st.success("Invoice berhasil dikirim.")
                    else:
                        st.error(hasil.text)

elif menu == "💰 Pembayaran":
    st.subheader("💰 Update Pembayaran")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["NAMA"].astype(str).tolist())
        idx = df[df["NAMA"].astype(str) == pilih].index[0]

        st.write("Paket:", df.loc[idx, "PAKET"])
        st.write("Tagihan:", rupiah(df.loc[idx, "HARGA"]))
        st.write("Status Sekarang:", df.loc[idx, "STATUS"])

        bukti = st.file_uploader("Upload Bukti Transfer (opsional)", type=["jpg", "jpeg", "png", "pdf"])
        status_baru = st.selectbox("Status Baru", ["Belum Bayar", "Menunggu Verifikasi", "Lunas"])

        if st.button("💾 SIMPAN PEMBAYARAN"):
            df.at[idx, "STATUS"] = status_baru
            if status_baru == "Lunas":
                df.at[idx, "TANGGAL BAYAR"] = str(hari_ini)
            if bukti:
                df.at[idx, "CATATAN"] = f"Bukti transfer diterima: {bukti.name}"
            save_data(df)
            st.success("Status pembayaran berhasil diperbarui.")
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

elif menu == "⚙️ Status Sistem":
    st.subheader("⚙️ Status Sistem")
    st.markdown(f"""
    <div class="clean-box">
    ✅ Database: Google Sheets<br>
    ✅ Hari ini WIB: {hari_ini}<br>
    ✅ Auto Billing: H-1 saja<br>
    ✅ WhatsApp API: Fonnte<br>
    ✅ Invoice PDF: Aktif<br>
    ✅ Versi: JASUND.NET V8 ISP PREMIUM PRO
    </div>
    """, unsafe_allow_html=True)
