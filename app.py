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

# --- Refresh data (tanpa tombol) ---
if 'df' not in st.session_state:
    raw_data = sheet.get_all_values()
    
    # baris ke-10 (index 9) jadi header
    headers = raw_data[9]  
    rows = raw_data[10:]   # data mulai baris 11
    
    df = pd.DataFrame(rows, columns=headers)
    st.session_state.df = df
    st.session_state.last_refresh = pd.Timestamp.now()

df = st.session_state.df


# --- Fungsi log alur ---
def buat_log_df(df):
    log_data = []
    for _, row in df.iterrows():
        no_surat = row['No.Surat']
        logs = []

        # Disposisi 1-4
        for i in range(1, 5):
            if pd.notna(row.get(f'Disposisi {i}')):
                logs.append({
                    'Nomor Surat': no_surat,
                    'Step': i,
                    'Nama Tahapan': f"Disposisi: {row[f'Disposisi {i}']}",
                    'Status': 'Proses',
                    'Tanggal': row.get(f'Tanggal Disposisi {i}')
                })

        # Diteruskan Kepada (final)
        if pd.notna(row.get('Diteruskan Kepada')):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 5,
                'Nama Tahapan': f"Diteruskan Kepada: {row['Diteruskan Kepada']}",
                'Status': row.get('Status Tindak Lanjut'),
                'Tanggal': row.get('Tanggal Surat Diterima')
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


# --- Fungsi timeline ala Shopee ---
def timeline_tracking(log_rows):
    st.markdown("""
    <style>
    .timeline {
        border-left: 3px solid #3498db;
        margin-left: 20px;
        padding-left: 20px;
    }
    .entry {
        margin-bottom: 15px;
        position: relative;
    }
    .entry:before {
        content: "●";
        position: absolute;
        left: -23px;
        font-size: 18px;
        color: #3498db;
    }
    .done:before {
        color: #2ecc71;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🧭 Timeline Proses Surat")

    html = "<div class='timeline'>"
    for _, step in log_rows.iterrows():
        status_class = "done" if step['Status'] not in ["On Progress", "Proses"] else "progress"
        emoji = "✅" if status_class == "done" else "⏳"

        html += (
            f"<div class='entry {status_class}'>"
            f"<b>Step {step['Step']}:</b> {step['Nama Tahapan']} {emoji}<br>"
            f"📅 {step['Tanggal']} | Status: {step['Status']}"
            f"</div>"
        )
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


# --- Buat log dataframe ---
df_log = buat_log_df(df)


# UI Halaman Depan---
col1, col2 = st.columns([1,4])

with col1:
    st.image("assets/kemenag.png", width=100)

with col2:
    st.markdown(
        """
        <div style="text-align:left; margin-left:10px;">
            <p style="margin:0; font-size:18px; font-weight:bold;">
                KEMENTERIAN AGAMA REPUBLIK INDONESIA
            </p>
            <p style="margin:0; font-size:16px;">
                DIREKTORAT JENDERAL PENDIDIKAN ISLAM
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Garis tipis sebagai pemisah header ---
st.markdown("<hr style='border:1px solid #000; margin-top:5px; margin-bottom:20px;'>", unsafe_allow_html=True)


# Judul Tracking
st.markdown(
    """
    <div style="text-align:center;">
        <h2 style="color:#2c3e50;">📄 Tracking Surat Mutasi</h2>
        <p style="font-size:16px; color:#34495e;">
            Masukkan <b>NIP</b> Anda untuk melakukan pencarian progress <br>
            <strong>Surat Mutasi</strong> di lingkungan Kementerian Agama.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Input + Button di Tengah ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    col_input, col_btn = st.columns([5,1])
    with col_input:
        nip = st.text_input("Masukkan NIP:", label_visibility="collapsed", 
                            placeholder="Contoh: 198765432019032001")
    with col_btn:
        cari = st.button("🔍 Lacak", use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# --- Eksekusi pencarian ---
if nip and cari:
    hasil = df[df['NIP'].astype(str).str.strip().str.lower() == nip.strip().lower()]
    
    if not hasil.empty:
        row = hasil.iloc[0]

        st.subheader("📌 Hasil Pencarian:")
        st.write(f"**Nomor Surat:** {row['No.Surat']}")
        st.write(f"**Nama Ybs:** {row['NAMA']}")
        st.write(f"**NIP:** {row['NIP']}")
        st.write(f"**Tanggal Surat:** {row['Tanggal Surat']}")
        st.write(f"**Perihal:** {row['Perihal']}")
            
        logs_ringkas = gabung_log(row)
        status_akhir = logs_ringkas[-1] if logs_ringkas else "Belum ada proses"
        st.write(f"**Status Surat Terakhir:** {status_akhir}")

        log_rows = df_log[df_log['Nomor Surat'] == row['No.Surat']]
        if not log_rows.empty:
            timeline_tracking(log_rows)
        else:
            st.info("Belum ada log alur proses ditemukan.")

        st.markdown("**📋 Tabel Log Tahapan Surat:**")
        st.dataframe(log_rows.reset_index(drop=True), use_container_width=True)

    else:
        st.warning("NIP tidak ditemukan.")


# --- Data terakhir diperbarui (dipindah ke bawah) ---
if 'last_refresh' in st.session_state:
    st.markdown(
        f"""
        <div style="text-align: center; font-size: 13px; color: gray; margin-bottom: 5px; margin-top: 15px;">
            📅 Data terakhir diperbarui: {st.session_state.last_refresh.strftime("%Y-%m-%d %H:%M:%S")}
        </div>
        """,
        unsafe_allow_html=True
    )


# --- Footer ---
st.markdown(
    """
    <div style="text-align: center; font-size: 13px; color: gray;">
        Diberdayakan oleh: <b>Tim Kerja OKH</b>
    </div>
    """,
    unsafe_allow_html=True
)










































