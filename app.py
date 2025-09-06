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

# --- Header eksplisit (versi baru) ---
#expected_headers = [
    #'No.', 'No.Surat', 'Tanggal Surat', 'Kategori', 'NAMA', 'NIP',
    #'Tanggal Surat Diterima', 'Perihal',
    #'Disposisi 1', 'Tanggal Disposisi 1',
    #'Disposisi 2', 'Tanggal Disposisi 2',
    #'Disposisi 3', 'Tanggal Disposisi 3',
    #'Disposisi 4', 'Tanggal Disposisi 4',
    #'Diteruskan Kepada', 'Status Tindak Lanjut'
#]

# --- Refresh data ---
if 'df' not in st.session_state or st.button("🔄 Refresh Data"):
    data = sheet.get_all_records(head=10) 
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

        # Disposisi 1
        if pd.notna(row['Disposisi 1']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 1,
                'Nama Tahapan': f"Disposisi: {row['Disposisi 1']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal Disposisi 1']
            })

        # Disposisi 2
        if pd.notna(row['Disposisi 2']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 2,
                'Nama Tahapan': f"Disposisi: {row['Disposisi 2']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal Disposisi 2']
            })

        # Disposisi 3
        if pd.notna(row['Disposisi 3']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 3,
                'Nama Tahapan': f"Disposisi: {row['Disposisi 3']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal Disposisi 3']
            })

        # Disposisi 4
        if pd.notna(row['Disposisi 4']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 4,
                'Nama Tahapan': f"Disposisi: {row['Disposisi 4']}",
                'Status': 'Proses',
                'Tanggal': row['Tanggal Disposisi 4']
            })

        # Diteruskan Kepada (final)
        if pd.notna(row['Diteruskan Kepada']):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 5,
                'Nama Tahapan': f"Diteruskan Kepada: {row['Diteruskan Kepada']}",
                'Status': row['Status Tindak Lanjut'],
                'Tanggal': row['Tanggal Surat Diterima']
            })

        log_data.extend(logs)
    
    return pd.DataFrame(log_data)

# --- Fungsi ringkas status ---
def gabung_log(row):
    logs = []
    for i in range(1, 5):
        if row.get(f'Disposisi {i}') and row.get(f'Tanggal Disposisi {i}'):
            logs.append(f"Disposisi {i}: {row[f'Disposisi {i}']} ({row[f'Tanggal Disposisi {i}']})")

    if row.get('Diteruskan Kepada'):
        logs.append(f"Diteruskan Kepada: {row['Diteruskan Kepada']} - Status: {row['Status Tindak Lanjut']}")

    return logs

df_log = buat_log_df(df)

# --- UI ---
st.title("📄 Tracking Surat")

nip = st.text_input("Masukkan NIP untuk Pencarian:")

if nip:
    hasil = df[df['NIP'].astype(str).str.strip().str.lower() == nip.strip().lower()]
    
    if not hasil.empty:
        row = hasil.iloc[0]

        st.subheader("📌 Hasil Pencarian:")
        st.write(f"**Nomor Surat:** {row['No.Surat']}")
        st.write(f"**Nama Ybs:** {row['NAMA']}")
        st.write(f"**NIP:** {row['NIP']}")
        st.write(f"**Tanggal Surat:** {row['Tanggal Surat ']}")
        st.write(f"**Kategori:** {row['Kategori']}")
        st.write(f"**Perihal:** {row['Perihal']}")

        logs_ringkas = gabung_log(row)
        status_akhir = logs_ringkas[-1] if logs_ringkas else "Belum ada proses"
        st.write(f"**Status Surat Terakhir:** {status_akhir}")

        st.markdown("**🧭 Alur Proses Surat (Visual Warna):**", unsafe_allow_html=True)
        log_rows = df_log[df_log['Nomor Surat'] == row['No.Surat']]
        if not log_rows.empty:
            for _, log_row in log_rows.iterrows():
                warna = "#3498db" if log_row['Status'] == "On Progress" or log_row['Status'] == "Proses" else "#2ecc71"
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
        st.warning("NIP tidak ditemukan.")




