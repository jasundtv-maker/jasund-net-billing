import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os, requests, urllib.parse

st.set_page_config(page_title="JASUND.NET V3", page_icon="📡", layout="wide")

FILE = "pelanggan.csv"

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def load_data():
    if os.path.exists(FILE):
        df = pd.read_csv(FILE, dtype=str)
    else:
        df = pd.DataFrame(columns=["Nama","No WA","Alamat","Paket","Harga","Jatuh Tempo","Status"])

    for col in ["Nama","No WA","Alamat","Paket","Harga","Jatuh Tempo","Status"]:
        if col not in df.columns:
            df[col] = ""

    df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce").fillna(0).astype(int)
    df["Jatuh Tempo"] = pd.to_numeric(df["Jatuh Tempo"], errors="coerce").fillna(1).astype(int)
    df["No WA"] = df["No WA"].astype(str)
    df["Status"] = df["Status"].replace("", "Belum Bayar").fillna("Belum Bayar")
    return df[["Nama","No WA","Alamat","Paket","Harga","Jatuh Tempo","Status"]]

def save_data(df):
    df.to_csv(FILE, index=False)

def rupiah(x):
    return f"Rp {int(x):,}".replace(",", ".")

def rapikan_wa(no):
    no = str(no).replace(" ","").replace("-","").replace("+","")
    if no.startswith("08"):
        no = "62" + no[1:]
    return no

def pesan_invoice(row):
    return f"""Assalamualaikum Bapak/Ibu {row['Nama']}

Kami informasikan tagihan internet JASUND.NET:

Paket: {row['Paket']}
Tagihan: {rupiah(row['Harga'])}
Jatuh tempo: besok tanggal {int(row['Jatuh Tempo'])}

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

# STYLE WOW
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #020617 0%, #0f172a 45%, #064e3b 100%);
    color: white;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #0f172a);
}
h1, h2, h3, p, label, .stMarkdown, .stText {
    color: #f8fafc !important;
}
.big-title {
    font-size: 44px;
    font-weight: 900;
    background: linear-gradient(90deg,#22c55e,#38bdf8,#a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sub-title {
    font-size: 18px;
    color: #cbd5e1;
}
.card {
    padding: 22px;
    border-radius: 22px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 15px 40px rgba(0,0,0,0.35);
}
.metric-title {
    color: #cbd5e1;
    font-size: 15px;
}
.metric-value {
    color: white;
    font-size: 32px;
    font-weight: 800;
}
.alert-box {
    padding: 18px;
    border-radius: 18px;
    background: rgba(34,197,94,0.15);
    border: 1px solid rgba(34,197,94,0.4);
}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("📡 JASUND.NET")
st.sidebar.caption("Billing RTRW NET Premium")

fonnte_token = st.sidebar.text_input("Token Fonnte", type="password")
telegram_token = st.sidebar.text_input("Token Bot Telegram", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID Telegram", type="password")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard WOW",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💰 Pembayaran",
    "📊 Rekap"
])

st.markdown('<div class="big-title">📡 JASUND.NET BILLING V3</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dashboard Premium Auto Billing RTRW NET</div>', unsafe_allow_html=True)
st.write("")

total = len(df)
belum = len(df[df["Status"] == "Belum Bayar"]) if total else 0
lunas = len(df[df["Status"] == "Lunas"]) if total else 0
h1 = len(df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")]) if total else 0
total_tagihan = df["Harga"].sum() if total else 0
sudah_lunas = df[df["Status"] == "Lunas"]["Harga"].sum() if total else 0
belum_masuk = df[df["Status"] != "Lunas"]["Harga"].sum() if total else 0

if menu == "🏠 Dashboard WOW":
    c1, c2, c3, c4 = st.columns(4)
    data_card = [
        ("👥 Total Pelanggan", total),
        ("⏳ Belum Bayar", belum),
        ("✅ Lunas", lunas),
        ("📨 H-1 Besok", h1),
    ]

    for col, item in zip([c1,c2,c3,c4], data_card):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="metric-title">{item[0]}</div>
                <div class="metric-value">{item[1]}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(f"""<div class="card"><div class="metric-title">💵 Total Tagihan</div><div class="metric-value">{rupiah(total_tagihan)}</div></div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div class="card"><div class="metric-title">🟢 Sudah Masuk</div><div class="metric-value">{rupiah(sudah_lunas)}</div></div>""", unsafe_allow_html=True)
    with c7:
        st.markdown(f"""<div class="card"><div class="metric-title">🔴 Belum Masuk</div><div class="metric-value">{rupiah(belum_masuk)}</div></div>""", unsafe_allow_html=True)

    st.write("")
    st.markdown(f"""
    <div class="alert-box">
    📅 Hari ini WIB: <b>{hari_ini}</b><br>
    📨 Sistem auto billing akan mengecek pelanggan yang jatuh tempo besok tanggal <b>{besok.day}</b>.<br>
    🤖 GitHub Actions akan mengirim invoice otomatis via Fonnte dan laporan ke Telegram.
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if total > 0:
        st.subheader("📋 Pelanggan Jatuh Tempo Besok")
        calon = df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")]
        if len(calon) == 0:
            st.success("Tidak ada pelanggan H-1 untuk besok.")
        else:
            st.dataframe(calon, use_container_width=True)

elif menu == "➕ Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan")
    with st.form("form"):
        nama = st.text_input("Nama")
        wa = st.text_input("No WhatsApp", placeholder="628xxxxxxxxxx")
        alamat = st.text_area("Alamat")
        paket = st.selectbox("Paket", ["5 Mbps","6 Mbps","7 Mbps","8 Mbps","9 Mbps","10 Mbps","Custom"])
        harga = st.number_input("Harga Bulanan", min_value=0, step=10000)
        jatuh = st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, step=1)
        simpan = st.form_submit_button("Simpan Pelanggan")

    if simpan:
        if nama == "" or wa == "" or harga == 0:
            st.error("Nama, WA, dan harga wajib diisi.")
        else:
            baru = pd.DataFrame([{
                "Nama": nama,
                "No WA": rapikan_wa(wa),
                "Alamat": alamat,
                "Paket": paket,
                "Harga": int(harga),
                "Jatuh Tempo": int(jatuh),
                "Status": "Belum Bayar"
            }])
            df = pd.concat([df, baru], ignore_index=True)
            save_data(df)
            st.success("Pelanggan berhasil ditambahkan.")

elif menu == "👥 Data Pelanggan":
    st.subheader("👥 Data Pelanggan")
    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        cari = st.text_input("Cari pelanggan")
        tampil = df.copy()
        if cari:
            tampil = tampil[tampil.astype(str).apply(lambda r: r.str.contains(cari, case=False).any(), axis=1)]
        st.dataframe(tampil, use_container_width=True)
        st.download_button("⬇️ Download pelanggan.csv", df.to_csv(index=False).encode("utf-8"), "pelanggan.csv", "text/csv")

elif menu == "✏️ Edit / Hapus":
    st.subheader("✏️ Edit / Hapus Pelanggan")
    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == pilih].index[0]

        paket_list = ["5 Mbps","6 Mbps","7 Mbps","8 Mbps","9 Mbps","10 Mbps","Custom"]
        paket_lama = str(df.loc[idx, "Paket"])
        paket_index = paket_list.index(paket_lama) if paket_lama in paket_list else 0

        nama = st.text_input("Nama", value=str(df.loc[idx, "Nama"]))
        wa = st.text_input("No WA", value=str(df.loc[idx, "No WA"]))
        alamat = st.text_area("Alamat", value=str(df.loc[idx, "Alamat"]))
        paket = st.selectbox("Paket", paket_list, index=paket_index)
        harga = st.number_input("Harga", min_value=0, value=int(df.loc[idx, "Harga"]), step=10000)
        jatuh = st.number_input("Jatuh Tempo", min_value=1, max_value=31, value=int(df.loc[idx, "Jatuh Tempo"]))
        status = st.selectbox("Status", ["Belum Bayar","Lunas"], index=0 if df.loc[idx, "Status"] != "Lunas" else 1)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Update Data"):
                df.at[idx, "Nama"] = nama
                df.at[idx, "No WA"] = rapikan_wa(wa)
                df.at[idx, "Alamat"] = alamat
                df.at[idx, "Paket"] = paket
                df.at[idx, "Harga"] = int(harga)
                df.at[idx, "Jatuh Tempo"] = int(jatuh)
                df.at[idx, "Status"] = status
                save_data(df)
                st.success("Data berhasil diupdate.")
                st.rerun()
        with c2:
            yakin = st.checkbox("Yakin hapus pelanggan ini")
            if st.button("🗑️ Hapus"):
                if yakin:
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success("Pelanggan dihapus.")
                    st.rerun()
                else:
                    st.warning("Centang konfirmasi dulu.")

elif menu == "📨 Invoice H-1":
    st.subheader("📨 Invoice H-1")
    calon = df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")] if total else pd.DataFrame()
    st.info(f"Mencari pelanggan jatuh tempo besok tanggal {besok.day} WIB.")

    if len(calon) == 0:
        st.success("Tidak ada pelanggan H-1.")
    else:
        laporan = "📡 JASUND.NET BILLING\n\nPelanggan jatuh tempo besok:\n\n"
        for i, row in calon.iterrows():
            pesan = pesan_invoice(row)
            no = rapikan_wa(row["No WA"])
            laporan += f"- {row['Nama']} | {row['Paket']} | {rupiah(row['Harga'])} | WA: {no}\n"

            st.markdown("---")
            st.write("Nama:", row["Nama"])
            st.write("WA:", no)
            st.write("Paket:", row["Paket"])
            st.write("Tagihan:", rupiah(row["Harga"]))
            st.text_area("Preview Invoice", pesan, height=220, key=f"prev{i}")

            link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
            st.link_button("Kirim Manual WhatsApp", link)

            if fonnte_token and st.button(f"Kirim Fonnte ke {row['Nama']}", key=f"fon{i}"):
                hasil = kirim_fonnte(fonnte_token, no, pesan)
                if hasil.status_code == 200:
                    st.success("Berhasil dikirim.")
                else:
                    st.error(hasil.text)

        if st.button("🚀 Kirim Semua via Fonnte"):
            if not fonnte_token:
                st.error("Token Fonnte belum diisi.")
            else:
                sukses, gagal = 0, 0
                for _, row in calon.iterrows():
                    try:
                        h = kirim_fonnte(fonnte_token, rapikan_wa(row["No WA"]), pesan_invoice(row))
                        sukses += 1 if h.status_code == 200 else 0
                        gagal += 0 if h.status_code == 200 else 1
                    except:
                        gagal += 1
                st.success(f"Selesai. Berhasil: {sukses}, Gagal: {gagal}")

        if st.button("🔔 Kirim Laporan Telegram"):
            if not telegram_token or not telegram_chat_id:
                st.error("Token Telegram / Chat ID belum diisi.")
            else:
                h = kirim_telegram(telegram_token, telegram_chat_id, laporan)
                st.success("Laporan Telegram terkirim.") if h.status_code == 200 else st.error(h.text)

elif menu == "💰 Pembayaran":
    st.subheader("💰 Pembayaran")
    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == pilih].index[0]
        st.write("Tagihan:", rupiah(df.loc[idx, "Harga"]))
        status = st.selectbox("Status Baru", ["Belum Bayar","Lunas"])
        if st.button("Simpan Status"):
            df.at[idx, "Status"] = status
            save_data(df)
            st.success("Status pembayaran diperbarui.")
            st.rerun()

elif menu == "📊 Rekap":
    st.subheader("📊 Rekap Tagihan")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tagihan", rupiah(total_tagihan))
    c2.metric("Sudah Lunas", rupiah(sudah_lunas))
    c3.metric("Belum Masuk", rupiah(belum_masuk))
    st.dataframe(df, use_container_width=True)
