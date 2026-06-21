import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import requests
import urllib.parse

st.set_page_config(
    page_title="JASUND.NET BILLING",
    page_icon="📡",
    layout="wide"
)

FILE = "pelanggan.csv"

# =====================
# FUNGSI DATA
# =====================
def load_data():
    if os.path.exists(FILE):
        return pd.read_csv(FILE)
    return pd.DataFrame(columns=[
        "Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"
    ])

def save_data(df):
    df.to_csv(FILE, index=False)

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def rapikan_nomor_wa(nomor):
    nomor = str(nomor).replace(" ", "").replace("-", "")
    if nomor.startswith("08"):
        nomor = "62" + nomor[1:]
    return nomor

def kirim_fonnte(token, target, pesan):
    url = "https://api.fonnte.com/send"
    headers = {"Authorization": token}
    data = {
        "target": target,
        "message": pesan,
        "countryCode": "62"
    }
    return requests.post(url, headers=headers, data=data, timeout=30)

def kirim_telegram(bot_token, chat_id, pesan):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": pesan
    }
    return requests.post(url, data=data, timeout=30)

df = load_data()

# =====================
# SIDEBAR SETTING
# =====================
st.sidebar.title("⚙️ Setting Notifikasi")

fonnte_token = st.sidebar.text_input(
    "Token Fonnte",
    type="password",
    help="Masukkan token Fonnte kang"
)

telegram_token = st.sidebar.text_input(
    "Token Bot Telegram",
    type="password"
)

telegram_chat_id = st.sidebar.text_input(
    "Chat ID Telegram Admin"
)

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Tambah Pelanggan",
        "Data Pelanggan",
        "Invoice H-1",
        "Pembayaran",
        "Rekap"
    ]
)

# =====================
# HEADER
# =====================
st.title("📡 JASUND.NET BILLING")
st.caption("Aplikasi Billing dan Invoice Otomatis JASUND.NET")

# =====================
# DASHBOARD
# =====================
if menu == "Dashboard":
    total = len(df)
    belum = len(df[df["Status"] == "Belum Bayar"]) if total > 0 else 0
    lunas = len(df[df["Status"] == "Lunas"]) if total > 0 else 0

    besok = date.today() + timedelta(days=1)
    h1 = len(df[df["Jatuh Tempo"] == besok.day]) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pelanggan", total)
    c2.metric("Belum Bayar", belum)
    c3.metric("Lunas", lunas)
    c4.metric("Jatuh Tempo Besok", h1)

    st.info("Menu Invoice H-1 akan menampilkan pelanggan yang jatuh tempo besok.")

# =====================
# TAMBAH PELANGGAN
# =====================
elif menu == "Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan")

    with st.form("form_pelanggan"):
        nama = st.text_input("Nama Pelanggan")
        wa = st.text_input("Nomor WhatsApp", placeholder="Contoh: 6281234567890")
        alamat = st.text_area("Alamat")

        paket = st.selectbox(
            "Paket Internet",
            ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"]
        )

        harga = st.number_input("Harga Bulanan", min_value=0, step=10000)

        jatuh_tempo = st.number_input(
            "Tanggal Jatuh Tempo",
            min_value=1,
            max_value=31,
            step=1
        )

        simpan = st.form_submit_button("Simpan")

        if simpan:
            if nama == "" or wa == "" or harga == 0:
                st.error("Nama, nomor WhatsApp, dan harga wajib diisi.")
            else:
                baru = pd.DataFrame([{
                    "Nama": nama,
                    "No WA": rapikan_nomor_wa(wa),
                    "Alamat": alamat,
                    "Paket": paket,
                    "Harga": harga,
                    "Jatuh Tempo": jatuh_tempo,
                    "Status": "Belum Bayar"
                }])

                df_baru = pd.concat([df, baru], ignore_index=True)
                save_data(df_baru)
                st.success("Pelanggan berhasil disimpan.")

# =====================
# DATA PELANGGAN
# =====================
elif menu == "Data Pelanggan":
    st.subheader("👥 Data Pelanggan")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        st.dataframe(df, use_container_width=True)

# =====================
# INVOICE H-1
# =====================
elif menu == "Invoice H-1":
    st.subheader("📨 Invoice H-1 Otomatis")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        besok = date.today() + timedelta(days=1)

        calon = df[
            (df["Jatuh Tempo"] == besok.day) &
            (df["Status"] == "Belum Bayar")
        ]

        st.info(f"Sistem mencari pelanggan yang jatuh tempo besok tanggal {besok.day}.")

        if len(calon) == 0:
            st.success("Tidak ada pelanggan yang jatuh tempo besok.")
        else:
            st.write(f"Jumlah pelanggan H-1: **{len(calon)} orang**")

            laporan_telegram = "📡 JASUND.NET BILLING\n\nPelanggan jatuh tempo besok:\n\n"

            for i, row in calon.iterrows():
                pesan = f"""Assalamualaikum Bapak/Ibu {row['Nama']}

Kami informasikan tagihan internet JASUND.NET:

Paket: {row['Paket']}
Tagihan: {format_rupiah(row['Harga'])}
Jatuh tempo: besok tanggal {int(row['Jatuh Tempo'])}

Mohon melakukan pembayaran sebelum jatuh tempo.
Terima kasih.

Admin JASUND.NET"""

                no_wa = rapikan_nomor_wa(row["No WA"])

                laporan_telegram += f"- {row['Nama']} | {row['Paket']} | {format_rupiah(row['Harga'])} | WA: {no_wa}\n"

                link_manual = "https://wa.me/" + no_wa + "?text=" + urllib.parse.quote(pesan)

                st.markdown("---")
                st.write("Nama:", row["Nama"])
                st.write("Nomor WA:", no_wa)
                st.write("Paket:", row["Paket"])
                st.write("Tagihan:", format_rupiah(row["Harga"]))

                st.link_button("Kirim Manual WhatsApp", link_manual)

                if fonnte_token:
                    if st.button(f"Kirim Fonnte ke {row['Nama']}", key=f"fonnte_{i}"):
                        try:
                            hasil = kirim_fonnte(fonnte_token, no_wa, pesan)
                            if hasil.status_code == 200:
                                st.success(f"Invoice berhasil dikirim ke {row['Nama']}")
                            else:
                                st.error(f"Gagal kirim: {hasil.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")

            st.markdown("---")

            if st.button("🚀 Kirim Semua Invoice H-1 via Fonnte"):
                if not fonnte_token:
                    st.error("Token Fonnte belum diisi di sidebar.")
                else:
                    sukses = 0
                    gagal = 0

                    for _, row in calon.iterrows():
                        pesan = f"""Assalamualaikum Bapak/Ibu {row['Nama']}

Kami informasikan tagihan internet JASUND.NET:

Paket: {row['Paket']}
Tagihan: {format_rupiah(row['Harga'])}
Jatuh tempo: besok tanggal {int(row['Jatuh Tempo'])}

Mohon melakukan pembayaran sebelum jatuh tempo.
Terima kasih.

Admin JASUND.NET"""

                        no_wa = rapikan_nomor_wa(row["No WA"])

                        try:
                            hasil = kirim_fonnte(fonnte_token, no_wa, pesan)
                            if hasil.status_code == 200:
                                sukses += 1
                            else:
                                gagal += 1
                        except:
                            gagal += 1

                    st.success(f"Selesai. Berhasil: {sukses}, Gagal: {gagal}")

            if st.button("🔔 Kirim Laporan ke Telegram Admin"):
                if not telegram_token or not telegram_chat_id:
                    st.error("Token Telegram dan Chat ID belum diisi.")
                else:
                    try:
                        hasil = kirim_telegram(
                            telegram_token,
                            telegram_chat_id,
                            laporan_telegram
                        )

                        if hasil.status_code == 200:
                            st.success("Laporan Telegram berhasil dikirim.")
                        else:
                            st.error(f"Gagal kirim Telegram: {hasil.text}")
                    except Exception as e:
                        st.error(f"Error Telegram: {e}")

# =====================
# PEMBAYARAN
# =====================
elif menu == "Pembayaran":
    st.subheader("💰 Update Pembayaran")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        nama = st.selectbox("Pilih Pelanggan", df["Nama"].tolist())
        idx = df[df["Nama"] == nama].index[0]

        st.write("Paket:", df.loc[idx, "Paket"])
        st.write("Tagihan:", format_rupiah(df.loc[idx, "Harga"]))
        st.write("Status sekarang:", df.loc[idx, "Status"])

        status_baru = st.selectbox("Status Baru", ["Belum Bayar", "Lunas"])

        if st.button("Simpan Status"):
            df.loc[idx, "Status"] = status_baru
            save_data(df)
            st.success("Status berhasil diperbarui.")

# =====================
# REKAP
# =====================
elif menu == "Rekap":
    st.subheader("📊 Rekap Tagihan")

    if len(df) == 0:
        st.warning("Belum ada data.")
    else:
        total_tagihan = df["Harga"].sum()
        total_lunas = df[df["Status"] == "Lunas"]["Harga"].sum()
        total_belum = df[df["Status"] != "Lunas"]["Harga"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Tagihan", format_rupiah(total_tagihan))
        c2.metric("Sudah Lunas", format_rupiah(total_lunas))
        c3.metric("Belum Masuk", format_rupiah(total_belum))

        st.dataframe(df, use_container_width=True)
