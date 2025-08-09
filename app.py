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
    'No.', 'No.Surat', 'NAMA', 'NIP', 'Tanggal Surat ', 'Tanggal Surat Diterima', 
    'Tanggal Surat Keluar', 'Perihal', 
    'Diteruskan Ke 1', 'Tanggal 1',
    'Dikirim Ke 2', 'Tanggal Kembali 2', 
    'Diteruskan Ke 3', 'Tanggal Kembali 3'
]

# --- Refresh data ---
if 'df' not in st.session_state or st.button("🔄 Refresh Data"):
    data = sheet.get_all_records(expected_headers=expected_headers)
    st.session_state.df = pd.DataFrame(data)
    st.session_state.last_refresh = pd.Timestamp.now()

df = st.session_state.df

if 'last_refresh' in st.session_state:
    st.caption(f"📅 Data terakhir diperbarui: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")

# --- Fungsi log ---
def buat_log_df(df):
    log_data = []
    for _, row in df.iterrows():
        no_surat = row['No.Surat']
        logs = []
        if pd.notna(row['Diteruskan Ke 1']):
            logs.append({'Nomor Surat': no_surat, 'Step': 1, 'Nama Tahapan': f"📨 Diteruskan ke: {row['Diteruskan Ke 1']}", 'Status': 'Proses', 'Tanggal': row['Tanggal 1']})
        if pd.notna(row['Dikirim Ke 2']):
            logs.append({'Nomor Surat': no_surat, 'Step': 2, 'Nama Tahapan': f"📤 Dikirim ke: {row['Dikirim Ke 2']}", 'Status': 'Proses', 'Tanggal': row['Tanggal Kembali 2']})
        if pd.notna(row['Diteruskan Ke 3']):
            logs.append({'Nomor Surat': no_surat, 'Step': 3, 'Nama Tahapan': f"✅ Diteruskan ke: {row['Diteruskan Ke 3']}", 'Status': 'Selesai', 'Tanggal': row['Tanggal Kembali 3']})
        log_data.extend(logs)
    return pd.DataFrame(log_data)

df_log = buat_log_df(df)

# --- UI ---
st.title("📄 Tracking Surat Mutasi")
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
        st.write(f"**Perihal:** {row['Perihal']}")

        st.markdown("**🧭 Alur Proses Surat:**", unsafe_allow_html=True)
        log_rows = df_log[df_log['Nomor Surat'] == row['No.Surat']]

        if not log_rows.empty:
            total_steps = 3
            steps_done = log_rows['Step'].max()

            for step_num in range(1, total_steps + 1):
                this_step = log_rows[log_rows['Step'] == step_num]

                # Tentukan warna sesuai aturan
                if step_num <= steps_done:
                    if step_num == 3 and steps_done == 3:
                        warna = "#2ecc71"  # Hijau tahap 3 selesai
                    else:
                        warna = "#3498db"  # Biru
                else:
                    warna = "#95a5a6"  # Abu-abu

                if not this_step.empty:
                    log_row = this_step.iloc[0]
                    html_log = f"""
                    <div style='background-color:{warna}; padding:10px; border-radius:8px; margin-bottom:6px; color:white;'>
                        <b>Step {log_row['Step']}:</b> {log_row['Nama Tahapan']}<br>
                        <i>Tanggal: {log_row['Tanggal']}</i> | Status: {log_row['Status']}
                    </div>
                    """
                else:
                    html_log = f"""
                    <div style='background-color:{warna}; padding:10px; border-radius:8px; margin-bottom:6px; color:white;'>
                        <b>Step {step_num}:</b> Belum ada progres
                    </div>
                    """
                st.markdown(html_log, unsafe_allow_html=True)

            # --- Legenda warna ---
            st.markdown("""
            **Legenda Warna & Ikon:**
            - 📨 <span style='background-color:#3498db; color:white; padding:4px 8px; border-radius:4px;'>Biru</span> = Sedang diproses (Tahap 1 / 2)  
            - ✅ <span style='background-color:#2ecc71; color:white; padding:4px 8px; border-radius:4px;'>Hijau</span> = Selesai diproses (Tahap 3)  
            - <span style='background-color:#95a5a6; color:white; padding:4px 8px; border-radius:4px;'>Abu-abu</span> = Belum diproses
            """, unsafe_allow_html=True)
        else:
            st.info("Belum ada log alur proses ditemukan.")
    else:
        st.warning("NIP tidak ditemukan.")
