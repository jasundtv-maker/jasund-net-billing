import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="JASUND.NET V7 ISP PREMIUM",
    page_icon="📡",
    layout="wide"
)

SHEET_ID = "1fDoA-aioZsUvx4aaTcita8ZkYapjR5bdf7ZlbqajFAA"
KOLOM = ["NAMA", "NO WA", "ALAMAT", "PAKET", "HARGA", "JATUH TEMPO", "STATUS"]

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

📦 Paket Internet : {row['PAKET']}
💰 Tagihan : {rupiah(row['HARGA'])}
📅 Jatuh Tempo : Besok tanggal {int(row['JATUH TEMPO'])}

Silakan melakukan pembayaran melalui:

🏦 BCA
1831149782
a.n. Aceng Abdul Roup

🏦 BRI
4062 0103 3487 530
a.n. Aceng Abdul Roup

📱 DANA
081395440454
a.n. Aceng Abdul Roup

Setelah melakukan pembayaran, mohon kirimkan bukti transfer kepada admin JASUND.NET.

Pembayaran juga dapat dilakukan langsung ke kantor JASUND.NET.

⚠️ Abaikan pesan ini apabila Bapak/Ibu telah melakukan pembayaran sebelumnya.

Terima kasih atas kepercayaan Bapak/Ibu menggunakan layanan internet JASUND.NET.

Hormat kami,

Admin JASUND.NET
"""


def tombol_wa(no, pesan, teks="💬 Kirim Manual WhatsApp"):
    link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
    st.markdown(
        f"""
        <a href="{link}" target="_blank" class="wa-button">
            {teks}
        </a>
        """,
        unsafe_allow_html=True
    )

def get_secret(name):
    try:
        return st.secrets[name]
    except:
        return ""

def kirim_fonnte(token, target, pesan):
    return requests.post(
        "https://api.fonnte.com/send",
        headers={"Authorization": token},
        data={"target": target, "message": pesan, "countryCode": "62"},
        timeout=30
    )

def kirim_telegram(token, chat_id, pesan):
    return requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": pesan},
        timeout=30
    )

FONNTE_TOKEN = get_secret("FONNTE_TOKEN")
TELEGRAM_BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_secret("TELEGRAM_CHAT_ID")

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

st.markdown("""
<style>
.stApp {
    background:
    radial-gradient(circle at top left, rgba(34,197,94,.25), transparent 32%),
    radial-gradient(circle at top right, rgba(168,85,247,.30), transparent 32%),
    linear-gradient(135deg, #020617 0%, #071426 45%, #022c22 100%);
    color:white;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a, #111827);
}

h1,h2,h3,h4,p,label {
    color:#f8fafc !important;
}

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

.card-green,.card-blue,.card-purple,.card-orange,.card-red {
    padding:24px;
    border-radius:24px;
    color:white;
    box-shadow:0 0 30px rgba(255,255,255,.25);
}

.card-green{background:linear-gradient(135deg,#16a34a,#22c55e);}
.card-blue{background:linear-gradient(135deg,#0284c7,#38bdf8);}
.card-purple{background:linear-gradient(135deg,#7c3aed,#c084fc);}
.card-orange{background:linear-gradient(135deg,#ea580c,#facc15);}
.card-red{background:linear-gradient(135deg,#dc2626,#fb7185);}

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

.wa-button:hover {
    background:linear-gradient(135deg,#16a34a,#059669);
    color:white !important;
    transform:scale(1.03);
}

.stButton > button {
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
st.sidebar.caption("ISP Billing Premium V7")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💰 Pembayaran",
    "📊 Rekap",
    "⚙️ Status Sistem"
])

st.markdown('<div class="main-title">📡 JASUND.NET ISP BILLING V7</div>', unsafe_allow_html=True)
st.write("Google Sheets Database • Auto Billing • WhatsApp Fonnte • Telegram Report")

st.markdown(f"""
<div class="running">
🚀 ONLINE | 📅 Hari ini WIB: <b>{hari_ini}</b> | 📨 Cek H-1 tanggal: <b>{besok.day}</b> | ☁️ Database: <b>Google Sheets</b>
</div>
""", unsafe_allow_html=True)

st.write("")

if menu == "🏠 Dashboard":
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f'<div class="card-green"><div class="metric-label">👥 Total Pelanggan</div><div class="metric-value">{total}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card-red"><div class="metric-label">⏳ Belum Bayar</div><div class="metric-value">{belum}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card-blue"><div class="metric-label">✅ Lunas</div><div class="metric-value">{lunas}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="card-orange"><div class="metric-label">📨 H-1 Besok</div><div class="metric-value">{h1}</div></div>', unsafe_allow_html=True)

    st.write("")

    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(f'<div class="card-purple"><div class="metric-label">💵 Total Tagihan</div><div class="metric-value">{rupiah(total_tagihan)}</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="card-green"><div class="metric-label">🟢 Uang Masuk</div><div class="metric-value">{rupiah(sudah_lunas)}</div></div>', unsafe_allow_html=True)
    with c7:
        st.markdown(f'<div class="card-red"><div class="metric-label">🔴 Belum Masuk</div><div class="metric-value">{rupiah(belum_masuk)}</div></div>', unsafe_allow_html=True)

    st.write("")
    st.subheader("📨 Pelanggan Jatuh Tempo Besok")
    calon = df[(df["JATUH TEMPO"] == besok.day) & (df["STATUS"] == "Belum Bayar")]
    if len(calon) == 0:
        st.success("Tidak ada pelanggan H-1 besok.")
    else:
        st.dataframe(calon, use_container_width=True)

    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📶 Sebaran Paket")
        if total:
            st.bar_chart(df["PAKET"].value_counts())
        else:
            st.info("Belum ada data.")

    with col2:
        st.subheader("💰 Status Pembayaran")
        if total:
            st.bar_chart(df["STATUS"].value_counts())
        else:
            st.info("Belum ada data.")

elif menu == "➕ Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan Baru")

    with st.form("form_tambah"):
        nama = st.text_input("Nama Pelanggan")
        wa = st.text_input("Nomor WhatsApp", placeholder="628xxxxxxxxxx")
        alamat = st.text_area("Alamat")
        paket = st.selectbox("Paket Internet", ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"])
        harga = st.number_input("Harga Bulanan", min_value=0, step=10000)
        jatuh = st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, step=1)
        simpan = st.form_submit_button("💾 Simpan Pelanggan")

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
                "STATUS": "Belum Bayar"
            }])
            df = pd.concat([df, baru], ignore_index=True)
            save_data(df)
            st.success("Pelanggan berhasil ditambahkan ke Google Sheets.")
            st.rerun()

elif menu == "👥 Data Pelanggan":
    st.subheader("👥 Data Pelanggan")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        cari = st.text_input("Cari pelanggan")
        tampil = df.copy()

        if cari:
            tampil = tampil[
                tampil.astype(str).apply(
                    lambda row: row.str.contains(cari, case=False).any(),
                    axis=1
                )
            ]

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
        status = st.selectbox("Status", ["Belum Bayar", "Lunas"], index=0 if str(df.loc[idx, "STATUS"]) != "Lunas" else 1)

        c1, c2 = st.columns(2)

        with c1:
            if st.button("💾 Update Data"):
                df.at[idx, "NAMA"] = nama
                df.at[idx, "NO WA"] = rapikan_wa(wa)
                df.at[idx, "ALAMAT"] = alamat
                df.at[idx, "PAKET"] = paket
                df.at[idx, "HARGA"] = int(harga)
                df.at[idx, "JATUH TEMPO"] = int(jatuh)
                df.at[idx, "STATUS"] = status
                save_data(df)
                st.success("Data berhasil diupdate.")
                st.rerun()

        with c2:
            yakin = st.checkbox("Saya yakin ingin menghapus pelanggan ini")
            if st.button("🗑️ Hapus Pelanggan"):
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
    st.info(f"Sistem mencari pelanggan jatuh tempo besok tanggal {besok.day} WIB.")

    if len(calon) == 0:
        st.success("Tidak ada pelanggan H-1.")
    else:
        laporan = "📡 JASUND.NET BILLING\n\nPelanggan jatuh tempo besok:\n\n"

        for i, row in calon.iterrows():
            pesan = pesan_invoice(row)
            no = rapikan_wa(row["NO WA"])
            laporan += f"- {row['NAMA']} | {row['PAKET']} | {rupiah(row['HARGA'])} | WA: {no}\n"

            st.markdown("---")
            st.write("Nama:", row["NAMA"])
            st.write("No WA:", no)
            st.write("Paket:", row["PAKET"])
            st.write("Tagihan:", rupiah(row["HARGA"]))
            st.text_area("Preview Invoice", pesan, height=220, key=f"preview_{i}")

            tombol_wa(no, pesan)

            if FONNTE_TOKEN:
                if st.button(f"🚀 Kirim Fonnte ke {row['NAMA']}", key=f"fonnte_{i}"):
                    hasil = kirim_fonnte(FONNTE_TOKEN, no, pesan)
                    if hasil.status_code == 200:
                        st.success("Invoice berhasil dikirim.")
                    else:
                        st.error(hasil.text)
            else:
                st.info("Auto WhatsApp tetap berjalan lewat GitHub Actions setiap hari.")

        if st.button("🔔 Kirim Laporan Telegram"):
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                st.info("Auto Telegram tetap berjalan lewat GitHub Actions.")
            else:
                h = kirim_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, laporan)
                if h.status_code == 200:
                    st.success("Laporan Telegram terkirim.")
                else:
                    st.error(h.text)

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

        status_baru = st.selectbox("Status Baru", ["Belum Bayar", "Lunas"])

        if st.button("💾 Simpan Status"):
            df.at[idx, "STATUS"] = status_baru
            save_data(df)
            st.success("Status pembayaran berhasil diperbarui.")
            st.rerun()

elif menu == "📊 Rekap":
    st.subheader("📊 Rekap Tagihan")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tagihan", rupiah(total_tagihan))
    c2.metric("Sudah Lunas", rupiah(sudah_lunas))
    c3.metric("Belum Masuk", rupiah(belum_masuk))

    st.dataframe(df, use_container_width=True)

elif menu == "⚙️ Status Sistem":
    st.subheader("⚙️ Status Sistem")

    st.markdown(f"""
    <div class="clean-box">
    ✅ Database: Google Sheets<br>
    ✅ Hari ini WIB: {hari_ini}<br>
    ✅ Auto Billing: GitHub Actions jam 08:00 WIB<br>
    ✅ WhatsApp API: Fonnte<br>
    ✅ Telegram Report: Aktif<br>
    ✅ Versi: JASUND.NET V7 ISP PREMIUM
    </div>
    """, unsafe_allow_html=True)
