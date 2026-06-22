import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="JASUND.NET V5 GOOGLE SHEETS",
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

Kami informasikan tagihan internet JASUND.NET:

Paket: {row['PAKET']}
Tagihan: {rupiah(row['HARGA'])}
Jatuh tempo: besok tanggal {int(row['JATUH TEMPO'])}

Mohon melakukan pembayaran sebelum jatuh tempo agar layanan internet tetap aktif dan lancar.

Terima kasih.

Admin JASUND.NET"""

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
    radial-gradient(circle at top left, rgba(59,130,246,.35), transparent 35%),
    radial-gradient(circle at top right, rgba(236,72,153,.25), transparent 30%),
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
    background:linear-gradient(90deg,rgba(34,197,94,.22),rgba(56,189,248,.18),rgba(168,85,247,.18));
    border:1px solid rgba(255,255,255,.18);
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
.metric-label{font-size:15px;font-weight:600;}
.metric-value{font-size:34px;font-weight:900;margin-top:8px;}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("📡 JASUND.NET")
st.sidebar.caption("V5 Google Sheets")

fonnte_token = st.sidebar.text_input("Token Fonnte", type="password")
telegram_token = st.sidebar.text_input("Token Bot Telegram", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID Telegram", type="password")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard V5",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💰 Pembayaran",
    "📊 Rekap"
])

st.markdown('<div class="main-title">📡 JASUND.NET BILLING V5</div>', unsafe_allow_html=True)
st.write("Database sudah memakai Google Sheets otomatis")

st.markdown(f"""
<div class="running">
🚀 Status: <b>ONLINE</b> |
📅 Hari ini WIB: <b>{hari_ini}</b> |
📨 Cek H-1 tanggal: <b>{besok.day}</b> |
☁️ Database: <b>Google Sheets</b>
</div>
""", unsafe_allow_html=True)

st.write("")

if menu == "🏠 Dashboard V5":
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
                st.success("Data berhasil diupdate ke Google Sheets.")
                st.rerun()

        with c2:
            yakin = st.checkbox("Saya yakin ingin menghapus pelanggan ini")
            if st.button("🗑️ Hapus Pelanggan"):
                if yakin:
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success("Pelanggan berhasil dihapus dari Google Sheets.")
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

            link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
            st.link_button("Kirim Manual WhatsApp", link)

            if fonnte_token:
                if st.button(f"🚀 Kirim Fonnte ke {row['NAMA']}", key=f"fonnte_{i}"):
                    hasil = kirim_fonnte(fonnte_token, no, pesan)
                    if hasil.status_code == 200:
                        st.success("Invoice berhasil dikirim.")
                    else:
                        st.error(hasil.text)

        if st.button("🚀 Kirim Semua Invoice H-1 via Fonnte"):
            if not fonnte_token:
                st.error("Token Fonnte belum diisi.")
            else:
                sukses, gagal = 0, 0
                for _, row in calon.iterrows():
                    try:
                        h = kirim_fonnte(fonnte_token, rapikan_wa(row["NO WA"]), pesan_invoice(row))
                        if h.status_code == 200:
                            sukses += 1
                        else:
                            gagal += 1
                    except:
                        gagal += 1
                st.success(f"Selesai. Berhasil: {sukses}, Gagal: {gagal}")

        if st.button("🔔 Kirim Laporan Telegram"):
            if not telegram_token or not telegram_chat_id:
                st.error("Token Telegram / Chat ID belum diisi.")
            else:
                h = kirim_telegram(telegram_token, telegram_chat_id, laporan)
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
            st.success("Status pembayaran berhasil diperbarui di Google Sheets.")
            st.rerun()

elif menu == "📊 Rekap":
    st.subheader("📊 Rekap Tagihan")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tagihan", rupiah(total_tagihan))
    c2.metric("Sudah Lunas", rupiah(sudah_lunas))
    c3.metric("Belum Masuk", rupiah(belum_masuk))

    st.dataframe(df, use_container_width=True)
