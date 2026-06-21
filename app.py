import streamlit as st
import pandas as pd
from datetime import date, timedelta
import urllib.parse
import os

st.set_page_config(
    page_title="JASUND.NET BILLING",
    page_icon="📡",
    layout="wide"
)

FILE = "pelanggan.csv"

# =====================
# LOAD DATA
# =====================
def load_data():
    if os.path.exists(FILE):
        return pd.read_csv(FILE)
    return pd.DataFrame(columns=[
        "Nama",
        "No WA",
        "Alamat",
        "Paket",
        "Harga",
        "Jatuh Tempo",
        "Status"
    ])

def save_data(df):
    df.to_csv(FILE, index=False)

df = load_data()

# =====================
# HEADER
# =====================
st.title("📡 JASUND.NET BILLING")
st.caption("Aplikasi Billing dan Invoice Otomatis JASUND.NET")

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Tambah Pelanggan",
        "Data Pelanggan",
        "Invoice H-1"
    ]
)

# =====================
# DASHBOARD
# =====================
if menu == "Dashboard":

    total = len(df)

    if total > 0:
        belum = len(df[df["Status"] == "Belum Bayar"])
        lunas = len(df[df["Status"] == "Lunas"])
    else:
        belum = 0
        lunas = 0

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Pelanggan", total)
    c2.metric("Belum Bayar", belum)
    c3.metric("Lunas", lunas)

    st.info("Sistem akan menampilkan pelanggan yang jatuh tempo besok pada menu Invoice H-1.")

# =====================
# TAMBAH PELANGGAN
# =====================
elif menu == "Tambah Pelanggan":

    st.subheader("➕ Tambah Pelanggan")

    with st.form("form_pelanggan"):

        nama = st.text_input("Nama Pelanggan")
        wa = st.text_input("Nomor WhatsApp")

        alamat = st.text_area("Alamat")

        paket = st.selectbox(
            "Paket Internet",
            [
                "5 Mbps",
                "6 Mbps",
                "7 Mbps",
                "8 Mbps",
                "9 Mbps",
                "10 Mbps",
                "Custom"
            ]
        )

        harga = st.number_input(
            "Harga Bulanan",
            min_value=0,
            step=10000
        )

        jatuh_tempo = st.number_input(
            "Tanggal Jatuh Tempo",
            min_value=1,
            max_value=31,
            step=1
        )

        simpan = st.form_submit_button("Simpan")

        if simpan:

            baru = pd.DataFrame([{
                "Nama": nama,
                "No WA": wa,
                "Alamat": alamat,
                "Paket": paket,
                "Harga": harga,
                "Jatuh Tempo": jatuh_tempo,
                "Status": "Belum Bayar"
            }])

            df_baru = pd.concat([df, baru], ignore_index=True)

            save_data(df_baru)

            st.success("Pelanggan berhasil disimpan")

# =====================
# DATA PELANGGAN
# =====================
elif menu == "Data Pelanggan":

    st.subheader("👥 Data Pelanggan")

    if len(df) == 0:
        st.warning("Belum ada pelanggan")
    else:
        st.dataframe(df, use_container_width=True)

# =====================
# INVOICE H-1
# =====================
elif menu == "Invoice H-1":

    st.subheader("📨 Invoice H-1")

    if len(df) == 0:

        st.warning("Belum ada pelanggan")

    else:

        besok = date.today() + timedelta(days=1)

        calon = df[
            df["Jatuh Tempo"] == besok.day
        ]

        if len(calon) == 0:

            st.success("Tidak ada pelanggan jatuh tempo besok")

        else:

            for _, row in calon.iterrows():

                pesan = f"""
Assalamualaikum.

Tagihan internet JASUND.NET Anda sebesar Rp {int(row['Harga']):,}

Jatuh tempo besok tanggal {int(row['Jatuh Tempo'])}.

Terima kasih.
"""

                link = (
                    "https://wa.me/"
                    + str(row["No WA"])
                    + "?text="
                    + urllib.parse.quote(pesan)
                )

                st.markdown("---")
                st.write("Nama :", row["Nama"])
                st.write("Paket :", row["Paket"])
                st.write("Tagihan :", f"Rp {int(row['Harga']):,}")

                st.link_button(
                    "Kirim WhatsApp",
                    link
                )
