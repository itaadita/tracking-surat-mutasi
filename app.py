import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Tracking Surat Mutasi", layout="centered")

# --- Autentikasi Google Sheets via Secrets Manager ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Ambil credential dari secrets (disimpan di Streamlit Cloud)
creds_dict = json.loads(st.secrets["gcp_service_account_json"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# --- Buka spreadsheet dan worksheet ---
spreadsheet_id = "1FugGupe8IfGzmvjZsuEkSwGvZTuLqVZG19YKr-RaPbY"
spreadsheet = client.open_by_key(spreadsheet_id)
sheet = spreadsheet.get_worksheet(0)

# --- Header eksplisit ---
expected_headers = [
    'No.', 'No.Surat', 'NAMA', 'Tanggal Surat ', 'Tanggal Surat Diterima',
    'Tanggal Surat Keluar', 'Perihal', 
    'Diteruskan Ke 1', 'Tanggal 1',
    'Dikirim Ke 2', 'Tanggal Kembali 2', 
    'Diteruskan Ke 3', 'Tanggal Kembali 3'
]

# --- Refresh data ---
if 'df' not in st.session_state or st.button("🔄 Refresh Data dari Google Sheets"):
    data = sheet.get_all_records(expected_headers=expected_headers)
    st.session_state.df = pd.DataFrame(data)
    st.session_state.last_refresh = pd.Timestamp.now()

df = st.session_state.df

if 'last_refresh' in st.session_state:
    st.caption(f"📅 Data terakhir diperbarui: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

# --- Fungsi log alur ---
def buat_log_df(df):
    log_data = []
    for _, row in df.iterrows():
        no_surat = row['No.Surat']
        logs = []

        if pd.notna(row['Diteruskan Ke 1']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 1,
                'Nama Tahapan': f"Diteruskan ke: {row['Diteruskan Ke 1']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal 1']
            })

        if pd.notna(row['Dikirim Ke 2']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 2,
                'Nama Tahapan': f"Dikirim ke: {row['Dikirim Ke 2']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal Kembali 2']
            })

        if pd.notna(row['Diteruskan Ke 3']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 3,
                'Nama Tahapan': f"Diteruskan ke: {row['Diteruskan Ke 3']}",
                'Status': 'Selesai',
                'Tanggal': row['Tanggal Kembali 3']
            })

        log_data.extend(logs)
    
    return pd.DataFrame(log_data)

def gabung_log(row):
    logs = []
    if row['Diteruskan Ke 1'] and row['Tanggal 1']:
        logs.append(f"Diteruskan ke {row['Diteruskan Ke 1']} ({row['Tanggal 1']})")
    if row['Dikirim Ke 2']:
        logs.append(f"{row['Dikirim Ke 2']}")
    if row['Tanggal Kembali 2']:
        logs.append(f"Kembali ({row['Tanggal Kembali 2']})")
    if row['Diteruskan Ke 3']:
        logs.append(f"Diteruskan ke {row['Diteruskan Ke 3']}")
    if row['Tanggal Kembali 3']:
        logs.append(f"Kembali ({row['Tanggal Kembali 3']})")
    return logs

df_log = buat_log_df(df)

# --- UI ---
st.title("📄 Tracking Surat Mutasi")

no_surat = st.text_input("Masukkan Nomor Surat untuk Pencarian:")

if no_surat:
    hasil = df[df['No.Surat'].astype(str).str.strip().str.lower() == no_surat.strip().lower()]
    
    if not hasil.empty:
        row = hasil.iloc[0]

        st.subheader("📌 Hasil Pencarian:")
        st.write(f"**Nomor Surat:** {row['No.Surat']}")
        st.write(f"**Nama Ybs:** {row['NAMA']}")
        st.write(f"**Tanggal Surat:** {row['Tanggal Surat ']}")
        st.write(f"**Perihal:** {row['Perihal']}")

        logs_ringkas = gabung_log(row)
        status_akhir = logs_ringkas[-1] if logs_ringkas else "Belum ada proses"
        st.write(f"**Status Surat Terakhir:** {status_akhir}")

        st.markdown("**🧭 Alur Proses Surat (Visual Warna):**", unsafe_allow_html=True)
        log_rows = df_log[df_log['Nomor Surat'].astype(str).str.strip().str.lower() == no_surat.strip().lower()]
        if not log_rows.empty:
            for _, log_row in log_rows.iterrows():
                warna = "#3498db" if log_row['Status'] == "Proses" else "#2ecc71"
                html_log = f"""
                <div style='background-color:{warna}; padding:10px; border-radius:8px; margin-bottom:6px; color:white;'>
                    <b>Step {log_row['Step']}:</b> {log_row['Nama Tahapan']}<br>
                    <i>Tanggal: {log_row['Tanggal']}</i> | Status: {log_row['Status']}
                </div>
                """
                st.markdown(html_log, unsafe_allow_html=True)
        else:
            st.info("Belum ada log alur proses ditemukan.")

        st.markdown("**📋 Tabel Log Tahapan Surat:**")
        st.dataframe(log_rows.reset_index(drop=True), use_container_width=True)

    else:
        st.warning("Nomor Surat tidak ditemukan.")
