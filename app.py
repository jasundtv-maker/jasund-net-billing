import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import requests
import urllib.parse

st.set_page_config(
    page_title="JASUND.NET BILLING",
    page_icon="📡",
    layout="wide"
)

FILE = "pelanggan.csv"

def tanggal_wib():
    return (datetime.utcnow() + timedelta(hours=7)).date()

def load_data():
    if os.path.exists(FILE):
        df = pd.read_csv(FILE, dtype=str)

        for col in ["Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"]:
            if col not in df.columns:
                df[col] = ""

        df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce").fillna(0).astype(int)
        df["Jatuh Tempo"] = pd.to_numeric(df["Jatuh Tempo"], errors="coerce").fillna(1).astype(int)
        df["No WA"] = df["No WA"].astype(str)
        df["Status"] = df["Status"].replace("", "Belum Bayar").fillna("Belum Bayar")

        return df[["Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"]]

    return pd.DataFrame(columns=[
        "Nama", "No WA", "Alamat", "Paket", "Harga", "Jatuh Tempo", "Status"
    ])

def save_data(df):
    df = df.copy()
    df["No WA"] = df["No WA"].astype(str)
    df.to_csv(FILE, index=False)

def format_rupiah(angka):
    return f"Rp {int(angka):,}".replace(",", ".")

def rapikan_nomor_wa(nomor):
    nomor = str(nomor).replace(" ", "").replace("-", "").replace("+", "")
    if nomor.startswith("08"):
        nomor = "62" + nomor[1:]
    return nomor

def buat_pesan_invoice(row):
    return f"""Assalamualaikum Bapak/Ibu {row['Nama']}

Kami informasikan bahwa tagihan internet JASUND.NET untuk bulan ini sudah terbit.

Rincian tagihan:
Nama: {row['Nama']}
Paket: {row['Paket']}
Tagihan: {format_rupiah(row['Harga'])}
Jatuh tempo: besok tanggal {int(row['Jatuh Tempo'])}

Mohon melakukan pembayaran sebelum jatuh tempo agar layanan internet tetap aktif dan lancar.

Terima kasih atas kepercayaan Bapak/Ibu menggunakan layanan JASUND.NET.

Admin JASUND.NET"""

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

st.sidebar.title("⚙️ Setting Notifikasi")
fonnte_token = st.sidebar.text_input("Token Fonnte", type="password")
telegram_token = st.sidebar.text_input("Token Bot Telegram", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID Telegram Admin")

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Tambah Pelanggan",
        "Data Pelanggan",
        "Edit / Hapus Pelanggan",
        "Invoice H-1",
        "Pembayaran",
        "Rekap"
    ]
)

st.title("📡 JASUND.NET BILLING")
st.caption("Aplikasi Billing dan Invoice Otomatis JASUND.NET")

hari_ini = tanggal_wib()
besok = hari_ini + timedelta(days=1)

if menu == "Dashboard":
    st.write("Hari ini WIB:", hari_ini)
    st.write("Besok WIB:", besok)

    total = len(df)
    belum = len(df[df["Status"] == "Belum Bayar"]) if total > 0 else 0
    lunas = len(df[df["Status"] == "Lunas"]) if total > 0 else 0
    h1 = len(df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")]) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Pelanggan", total)
    c2.metric("Belum Bayar", belum)
    c3.metric("Lunas", lunas)
    c4.metric("Jatuh Tempo Besok", h1)

    st.info("Invoice H-1 mengikuti tanggal WIB Indonesia.")

elif menu == "Tambah Pelanggan":
    st.subheader("➕ Tambah Pelanggan")

    with st.form("form_pelanggan"):
        nama = st.text_input("Nama Pelanggan")
        wa = st.text_input("Nomor WhatsApp", placeholder="Contoh: 6281234567890")
        alamat = st.text_area("Alamat")
        paket = st.selectbox("Paket Internet", ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"])
        harga = st.number_input("Harga Bulanan", min_value=0, step=10000)
        jatuh_tempo = st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, step=1)
        simpan = st.form_submit_button("Simpan")

        if simpan:
            if nama == "" or wa == "" or harga == 0:
                st.error("Nama, nomor WhatsApp, dan harga wajib diisi.")
            else:
                baru = pd.DataFrame([{
                    "Nama": nama,
                    "No WA": str(rapikan_nomor_wa(wa)),
                    "Alamat": alamat,
                    "Paket": paket,
                    "Harga": int(harga),
                    "Jatuh Tempo": int(jatuh_tempo),
                    "Status": "Belum Bayar"
                }])
                df_baru = pd.concat([df, baru], ignore_index=True)
                save_data(df_baru)
                st.success("Pelanggan berhasil disimpan.")

elif menu == "Data Pelanggan":
    st.subheader("👥 Data Pelanggan")

    if len(df) == 0:
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

elif menu == "Edit / Hapus Pelanggan":
    st.subheader("✏️ Edit / Hapus Pelanggan")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        nama_pilih = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == nama_pilih].index[0]

        paket_list = ["5 Mbps", "6 Mbps", "7 Mbps", "8 Mbps", "9 Mbps", "10 Mbps", "Custom"]
        paket_lama = str(df.loc[idx, "Paket"])
        paket_index = paket_list.index(paket_lama) if paket_lama in paket_list else 0

        nama = st.text_input("Nama", value=str(df.loc[idx, "Nama"]))
        wa = st.text_input("No WA", value=str(df.loc[idx, "No WA"]))
        alamat = st.text_area("Alamat", value=str(df.loc[idx, "Alamat"]))
        paket = st.selectbox("Paket", paket_list, index=paket_index)
        harga = st.number_input("Harga", min_value=0, value=int(df.loc[idx, "Harga"]), step=10000)
        jatuh_tempo = st.number_input("Tanggal Jatuh Tempo", min_value=1, max_value=31, value=int(df.loc[idx, "Jatuh Tempo"]))
        status_lama = str(df.loc[idx, "Status"])
        status = st.selectbox("Status", ["Belum Bayar", "Lunas"], index=0 if status_lama != "Lunas" else 1)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Update Data"):
                df.at[idx, "Nama"] = str(nama)
                df.at[idx, "No WA"] = str(rapikan_nomor_wa(wa))
                df.at[idx, "Alamat"] = str(alamat)
                df.at[idx, "Paket"] = str(paket)
                df.at[idx, "Harga"] = int(harga)
                df.at[idx, "Jatuh Tempo"] = int(jatuh_tempo)
                df.at[idx, "Status"] = str(status)
                save_data(df)
                st.success("Data pelanggan berhasil diperbarui.")
                st.rerun()

        with col2:
            yakin = st.checkbox("Saya yakin ingin menghapus pelanggan ini")
            if st.button("🗑️ Hapus Pelanggan"):
                if yakin:
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success("Pelanggan berhasil dihapus.")
                    st.rerun()
                else:
                    st.warning("Centang konfirmasi dulu sebelum menghapus.")

elif menu == "Invoice H-1":
    st.subheader("📨 Invoice H-1 Otomatis")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        calon = df[(df["Jatuh Tempo"] == besok.day) & (df["Status"] == "Belum Bayar")]

        st.info(f"Sistem mencari pelanggan yang jatuh tempo besok tanggal {besok.day} WIB.")

        if len(calon) == 0:
            st.success("Tidak ada pelanggan jatuh tempo besok.")
        else:
            laporan = "📡 JASUND.NET BILLING\n\nPelanggan jatuh tempo besok:\n\n"

            for i, row in calon.iterrows():
                pesan = buat_pesan_invoice(row)
                no_wa = rapikan_nomor_wa(row["No WA"])
                laporan += f"- {row['Nama']} | {row['Paket']} | {format_rupiah(row['Harga'])} | WA: {no_wa}\n"

                link_manual = "https://wa.me/" + no_wa + "?text=" + urllib.parse.quote(pesan)

                st.markdown("---")
                st.write("Nama:", row["Nama"])
                st.write("No WA:", no_wa)
                st.write("Paket:", row["Paket"])
                st.write("Tagihan:", format_rupiah(row["Harga"]))
                st.text_area("Preview Pesan Invoice", pesan, height=230, key=f"preview_{i}")

                st.link_button("Kirim Manual WhatsApp", link_manual)

                if fonnte_token:
                    if st.button(f"Kirim Fonnte ke {row['Nama']}", key=f"kirim_{i}"):
                        hasil = kirim_fonnte(fonnte_token, no_wa, pesan)
                        if hasil.status_code == 200:
                            st.success(f"Invoice berhasil dikirim ke {row['Nama']}")
                        else:
                            st.error(f"Gagal kirim: {hasil.text}")

            st.markdown("---")

            if st.button("🚀 Kirim Semua Invoice H-1 via Fonnte"):
                if not fonnte_token:
                    st.error("Token Fonnte belum diisi.")
                else:
                    sukses = 0
                    gagal = 0
                    for _, row in calon.iterrows():
                        pesan = buat_pesan_invoice(row)
                        no_wa = rapikan_nomor_wa(row["No WA"])
                        try:
                            hasil = kirim_fonnte(fonnte_token, no_wa, pesan)
                            if hasil.status_code == 200:
                                sukses += 1
                            else:
                                gagal += 1
                        except:
                            gagal += 1
                    st.success(f"Selesai kirim invoice. Berhasil: {sukses}, Gagal: {gagal}")

            if st.button("🔔 Kirim Laporan ke Telegram Admin"):
                if not telegram_token or not telegram_chat_id:
                    st.error("Token Telegram dan Chat ID belum diisi.")
                else:
                    hasil = kirim_telegram(telegram_token, telegram_chat_id, laporan)
                    if hasil.status_code == 200:
                        st.success("Laporan Telegram berhasil dikirim.")
                    else:
                        st.error(f"Gagal Telegram: {hasil.text}")

elif menu == "Pembayaran":
    st.subheader("💰 Update Pembayaran")

    if len(df) == 0:
        st.warning("Belum ada pelanggan.")
    else:
        nama = st.selectbox("Pilih Pelanggan", df["Nama"].astype(str).tolist())
        idx = df[df["Nama"].astype(str) == nama].index[0]

        st.write("Paket:", df.loc[idx, "Paket"])
        st.write("Tagihan:", format_rupiah(df.loc[idx, "Harga"]))
        st.write("Status sekarang:", df.loc[idx, "Status"])

        status_baru = st.selectbox("Status Baru", ["Belum Bayar", "Lunas"])

        if st.button("Simpan Status"):
            df.at[idx, "Status"] = status_baru
            save_data(df)
            st.success("Status pembayaran berhasil diperbarui.")
            st.rerun()

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
