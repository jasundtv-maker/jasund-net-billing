import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests
import urllib.parse

st.set_page_config(
    page_title="JASUND.NET ISP PREMIUM",
    page_icon="📡",
    layout="wide"
)

FILE = "pelanggan.csv"

# =========================
# FUNGSI DASAR
# =========================
def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def load_data():
    if os.path.exists(FILE):
        df = pd.read_csv(FILE, dtype=str)
    else:
        df = pd.DataFrame(columns=[
            "Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"
        ])

    for col in ["Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"]:
        if col not in df.columns:
            df[col] = ""

    df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce").fillna(0).astype(int)
    df["Jatuh Tempo"] = pd.to_numeric(df["Jatuh Tempo"], errors="coerce").fillna(1).astype(int)
    df["No WA"] = df["No WA"].astype(str)
    df["Status"] = df["Status"].replace("", "Belum Bayar").fillna("Belum Bayar")

    return df[["Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"]]

def save_data(df):
    df.to_csv(FILE, index=False)

def rupiah(x):
    return f"Rp {int(x):,}".replace(",", ".")

def rapikan_wa(no):
    no = str(no).replace(" ", "").replace("-", "").replace("+", "")
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
        data={
            "target": target,
            "message": pesan,
            "countryCode": "62"
        },
        timeout=30
    )

def kirim_telegram(token, chat_id, pesan):
    return requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": pesan
        },
        timeout=30
    )

df = load_data()
hari_ini = tanggal_wib()
besok = hari_ini + timedelta(days=1)

total = len(df)
belum = len(df[df["Status"] == "Belum Bayar"]) if total else 0
lunas = len(df[df["Status"] == "Lunas"]) if total else 0
h1 = len(df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")]) if total else 0
total_tagihan = df["Harga"].sum() if total else 0
sudah_lunas = df[df["Status"] == "Lunas"]["Harga"].sum() if total else 0
belum_masuk = df[df["Status"] != "Lunas"]["Harga"].sum() if total else 0

# =========================
# STYLE V4
# =========================
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
    border-right: 1px solid rgba(255,255,255,.12);
}

h1, h2, h3, h4, p, label {
    color: #f8fafc !important;
}

.main-title {
    font-size: 46px;
    font-weight: 900;
    letter-spacing: 1px;
    background: linear-gradient(90deg, #22c55e, #38bdf8, #a78bfa, #fb7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.sub-title {
    font-size: 17px;
    color:#cbd5e1;
    margin-bottom: 20px;
}

.running {
    padding: 14px 22px;
    border-radius: 18px;
    background: linear-gradient(90deg, rgba(34,197,94,.22), rgba(56,189,248,.18), rgba(168,85,247,.18));
    border: 1px solid rgba(255,255,255,.18);
    box-shadow: 0 0 30px rgba(34,197,94,.18);
}

.card-green {
    background: linear-gradient(135deg,#16a34a,#22c55e);
    padding: 24px;
    border-radius: 24px;
    color:white;
    box-shadow: 0 0 30px rgba(34,197,94,.45);
}

.card-blue {
    background: linear-gradient(135deg,#0284c7,#38bdf8);
    padding: 24px;
    border-radius: 24px;
    color:white;
    box-shadow: 0 0 30px rgba(56,189,248,.45);
}

.card-purple {
    background: linear-gradient(135deg,#7c3aed,#c084fc);
    padding: 24px;
    border-radius: 24px;
    color:white;
    box-shadow: 0 0 30px rgba(192,132,252,.45);
}

.card-orange {
    background: linear-gradient(135deg,#ea580c,#facc15);
    padding: 24px;
    border-radius: 24px;
    color:white;
    box-shadow: 0 0 30px rgba(250,204,21,.42);
}

.card-red {
    background: linear-gradient(135deg,#dc2626,#fb7185);
    padding: 24px;
    border-radius: 24px;
    color:white;
    box-shadow: 0 0 30px rgba(248,113,113,.45);
}

.card-glass {
    padding: 22px;
    border-radius: 24px;
    background: rgba(255,255,255,.09);
    border: 1px solid rgba(255,255,255,.18);
    box-shadow: 0 18px 45px rgba(0,0,0,.35);
}

.metric-label {
    font-size: 15px;
    font-weight: 600;
    opacity: .95;
}

.metric-value {
    font-size: 34px;
    font-weight: 900;
    margin-top: 8px;
}

.small-note {
    font-size: 13px;
    opacity:.9;
}

hr {
    border-color: rgba(255,255,255,.12);
}
</style>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("📡 JASUND.NET")
st.sidebar.caption("ISP Billing Premium V4")

fonnte_token = st.sidebar.text_input("Token Fonnte", type="password")
telegram_token = st.sidebar.text_input("Token Bot Telegram", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID Telegram", type="password")

menu = st.sidebar.radio("Menu", [
    "🏠 Dashboard V4",
    "➕ Tambah Pelanggan",
    "👥 Data Pelanggan",
    "✏️ Edit / Hapus",
    "📨 Invoice H-1",
    "💰 Pembayaran",
    "📊 Rekap"
])

# =========================
# HEADER
# =========================
st.markdown('<div class="main-title">📡 JASUND.NET ISP BILLING V4</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dashboard Premium RTRW NET • Auto Invoice • Fonnte WhatsApp • Telegram Report</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="running">
🚀 Status sistem: <b>ONLINE</b> &nbsp; | &nbsp;
📅 Hari ini WIB: <b>{hari_ini}</b> &nbsp; | &nbsp;
📨 Auto Billing H-1 untuk tanggal: <b>{besok.day}</b> &nbsp; | &nbsp;
🤖 GitHub Actions aktif setiap hari jam 08:00 WIB
</div>
""", unsafe_allow_html=True)

st.write("")

# =========================
# DASHBOARD V4
# =========================
if menu == "🏠 Dashboard V4":
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="card-green">
            <div class="metric-label">👥 Total Pelanggan</div>
            <div class="metric-value">{total}</div>
            <div class="small-note">Semua pelanggan terdaftar</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card-red">
            <div class="metric-label">⏳ Belum Bayar</div>
            <div class="metric-value">{belum}</div>
            <div class="small-note">Perlu ditagih / dipantau</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card-blue">
            <div class="metric-label">✅ Sudah Lunas</div>
            <div class="metric-value">{lunas}</div>
            <div class="small-note">Pembayaran berhasil</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="card-orange">
            <div class="metric-label">📨 H-1 Besok</div>
            <div class="metric-value">{h1}</div>
            <div class="small-note">Akan dikirim invoice</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    c5, c6, c7 = st.columns(3)

    with c5:
        st.markdown(f"""
        <div class="card-purple">
            <div class="metric-label">💵 Total Tagihan</div>
            <div class="metric-value">{rupiah(total_tagihan)}</div>
            <div class="small-note">Potensi pemasukan aktif</div>
        </div>
        """, unsafe_allow_html=True)

    with c6:
        st.markdown(f"""
        <div class="card-green">
            <div class="metric-label">🟢 Uang Masuk</div>
            <div class="metric-value">{rupiah(sudah_lunas)}</div>
            <div class="small-note">Total status lunas</div>
        </div>
        """, unsafe_allow_html=True)

    with c7:
        st.markdown(f"""
        <div class="card-red">
            <div class="metric-label">🔴 Belum Masuk</div>
            <div class="metric-value">{rupiah(belum_masuk)}</div>
            <div class="small-note">Tagihan belum dibayar</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🥧 Status Pembayaran")
        if total > 0:
            status_df = df["Status"].value_counts().reset_index()
            status_df.columns = ["Status", "Jumlah"]
            st.bar_chart(status_df.set_index("Status"))
        else:
            st.info("Belum ada data pelanggan.")

    with col_b:
        st.subheader("📶 Sebaran Paket Internet")
        if total > 0:
            paket_df = df["Paket"].value_counts().reset_index()
            paket_df.columns = ["Paket", "Jumlah"]
            st.bar_chart(paket_df.set_index("Paket"))
        else:
            st.info("Belum ada data paket.")

    st.write("")
    st.markdown("---")

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("📨 Pelanggan Jatuh Tempo Besok")
        calon = df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")] if total else pd.DataFrame()
        if len(calon) == 0:
            st.success("Tidak ada pelanggan H-1 besok.")
        else:
            st.dataframe(calon, use_container_width=True)

    with col_d:
        st.subheader("🏆 Tagihan Terbesar")
        if total > 0:
            top_df = df.sort_values("Harga", ascending=False).head(5)
            st.dataframe(top_df[["Nama", "Paket", "Harga", "Status"]], use_container_width=True)
        else:
            st.info("Belum ada pelanggan.")

# =========================
# TAMBAH
# =========================
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
            st.warning("Jangan lupa download pelanggan.csv lalu update ke GitHub agar Auto Billing membaca data terbaru.")

# =========================
# DATA
# =========================
elif menu == "👥 Data Pelanggan":
    st.subheader("👥 Data Pelanggan")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        cari = st.text_input("Cari nama / alamat / nomor WA")
        tampil = df.copy()

        if cari:
            tampil = tampil[
                tampil.astype(str).apply(
                    lambda row: row.str.contains(cari, case=False).any(),
                    axis=1
                )
            ]

        st.dataframe(tampil, use_container_width=True)

        st.download_button(
            "⬇️ Download pelanggan.csv",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="pelanggan.csv",
            mime="text/csv"
        )

# =========================
# EDIT HAPUS
# =========================
elif menu == "✏️ Edit / Hapus":
    st.subheader("✏️ Edit / Hapus Pelanggan")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == pilih].index[0]

        paket_list = ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"]
        paket_lama = str(df.loc[idx, "Paket"])
        paket_index = paket_list.index(paket_lama) if paket_lama in paket_list else 0

        nama = st.text_input("Nama", value=str(df.loc[idx, "Nama"]))
        wa = st.text_input("No WA", value=str(df.loc[idx, "No WA"]))
        alamat = st.text_area("Alamat", value=str(df.loc[idx, "Alamat"]))
        paket = st.selectbox("Paket", paket_list, index=paket_index)
        harga = st.number_input("Harga", min_value=0, value=int(df.loc[idx, "Harga"]), step=10000)
        jatuh = st.number_input("Jatuh Tempo", min_value=1, max_value=31, value=int(df.loc[idx, "Jatuh Tempo"]))
        status = st.selectbox("Status", ["Belum Bayar", "Lunas"], index=0 if df.loc[idx, "Status"] != "Lunas" else 1)

        col1, col2 = st.columns(2)

        with col1:
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
                st.warning("Download pelanggan.csv lalu update ke GitHub agar Auto Billing memakai data terbaru.")
                st.rerun()

        with col2:
            yakin = st.checkbox("Saya yakin ingin menghapus pelanggan ini")
            if st.button("🗑️ Hapus Pelanggan"):
                if yakin:
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success("Pelanggan berhasil dihapus.")
                    st.warning("Download pelanggan.csv lalu update ke GitHub agar Auto Billing memakai data terbaru.")
                    st.rerun()
                else:
                    st.warning("Centang konfirmasi dulu.")

# =========================
# INVOICE
# =========================
elif menu == "📨 Invoice H-1":
    st.subheader("📨 Invoice H-1")

    calon = df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")] if total else pd.DataFrame()
    st.info(f"Sistem mencari pelanggan jatuh tempo besok tanggal {besok.day} WIB.")

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
            st.write("No WA:", no)
            st.write("Paket:", row["Paket"])
            st.write("Tagihan:", rupiah(row["Harga"]))
            st.text_area("Preview Invoice", pesan, height=220, key=f"preview_{i}")

            link = "https://wa.me/" + no + "?text=" + urllib.parse.quote(pesan)
            st.link_button("Kirim Manual WhatsApp", link)

            if fonnte_token:
                if st.button(f"🚀 Kirim Fonnte ke {row['Nama']}", key=f"fonnte_{i}"):
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
                        h = kirim_fonnte(fonnte_token, rapikan_wa(row["No WA"]), pesan_invoice(row))
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

# =========================
# PEMBAYARAN
# =========================
elif menu == "💰 Pembayaran":
    st.subheader("💰 Update Pembayaran")

    if total == 0:
        st.warning("Belum ada pelanggan.")
    else:
        pilih = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == pilih].index[0]

        st.write("Paket:", df.loc[idx, "Paket"])
        st.write("Tagihan:", rupiah(df.loc[idx, "Harga"]))
        st.write("Status Sekarang:", df.loc[idx, "Status"])

        status_baru = st.selectbox("Status Baru", ["Belum Bayar", "Lunas"])

        if st.button("💾 Simpan Status"):
            df.at[idx, "Status"] = status_baru
            save_data(df)
            st.success("Status pembayaran berhasil diperbarui.")
            st.warning("Download pelanggan.csv lalu update ke GitHub agar Auto Billing memakai data terbaru.")
            st.rerun()

# =========================
# REKAP
# =========================
elif menu == "📊 Rekap":
    st.subheader("📊 Rekap Tagihan")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tagihan", rupiah(total_tagihan))
    c2.metric("Sudah Lunas", rupiah(sudah_lunas))
    c3.metric("Belum Masuk", rupiah(belum_masuk))

    st.write("")
    st.dataframe(df, use_container_width=True)
