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

# --- Fungsi refresh data terbaru ---
def refresh_data(force=False):
    if 'df' not in st.session_state or force:
        raw_data = sheet.get_all_values()
        headers = raw_data[9]        # baris ke-10 jadi header
        rows = raw_data[10:]         # data mulai baris 11
        st.session_state.df = pd.DataFrame(rows, columns=headers)
        st.session_state.last_refresh = pd.Timestamp.now()

# --- Panggil refresh data awal ---
refresh_data(force=False)
df = st.session_state.df

# --- Fungsi bantu ---
def is_filled(val):
    return pd.notna(val) and str(val).strip() != ""

# --- Fungsi log alur ---
def buat_log_df(df):
    log_data = []

    for _, row in df.iterrows():
        no_surat = row.get('No.Surat', '-')
        logs = []

        # --- Step 1 ---
        tanggal_terima = row.get('Tanggal Surat Diterima')
        if is_filled(tanggal_terima):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 1,
                'Nama Tahapan': "Usulan Dokumen Mutasi diterima oleh petugas (Tim Kerja OKH)",
                'Status': 'Proses',
                'Tanggal': tanggal_terima
            })

        # --- Step 2 ---
        disp1 = row.get('Disposisi 1')
        if is_filled(disp1):
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 2,
                'Nama Tahapan': f"Menunggu Disposisi Pimpinan ({disp1})",
                'Status': 'Proses',
                'Tanggal': row.get('Tanggal Disposisi 1')
            })
        else:
            log_data.extend(logs)
            continue

        # --- Step 3 ---
        disp2 = row.get('Disposisi 2')
        if is_filled(disp2):
            if disp2 in ['Diktis', 'GTK']:
                keterangan = f"Dokumen Usul Mutasi sedang proses verifikasi-validasi berkas oleh {disp2}"
            elif disp2 == 'Biro SDM':
                keterangan = "Dokumen Usul Mutasi sudah diterima oleh Biro SDM-Sekretariat Jenderal"
            else:
                keterangan = f"Dokumen Usul Mutasi sedang di proses pada Tim Kepegawaian OKH melalui PIC ({disp2})"
            
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 3,
                'Nama Tahapan': keterangan,
                'Status': 'Proses',
                'Tanggal': row.get('Tanggal Disposisi 2')
            })
        else:
            log_data.extend(logs)
            continue

        # --- Step 4 ---
        disp3 = row.get('Disposisi 3')
        if is_filled(disp3):
            if disp3 in ['Diktis', 'GTK', 'PAI']:
                keterangan = f"Dokumen Usul Mutasi sedang proses verifikasi-validasi berkas oleh {disp3}"
            elif disp3 == 'Biro SDM':
                keterangan = "Dokumen Usul Mutasi sudah diterima oleh Biro SDM-Sekretariat Jenderal"
            elif disp3 == 'Dirjen':
                keterangan = "Menunggu Disposisi/TTE Pimpinan"
            else:
                keterangan = f"Surat Persetujuan Mutasi sedang di proses pada Tim Kepegawaian OKH melalui PIC ({disp3})"
            
            logs.append({
                'Nomor Surat': no_surat,
                'Step': 4,
                'Nama Tahapan': keterangan,
                'Status': 'Proses',
                'Tanggal': row.get('Tanggal Disposisi 3')
            })
        else:
            log_data.extend(logs)
            continue

        # --- Step 5 ---
        disp4 = row.get('Disposisi 4')
        if is_filled(disp4):
            if disp4 == 'Biro SDM':
                keterangan = "Dokumen Usul Mutasi sudah diterima oleh Biro SDM-Sekretariat Jenderal"
            else:
                keterangan = f"Dokumen Usul Mutasi sedang di proses pada Tim Kepegawaian OKH melalui PIC ({disp4})"

            logs.append({
                'Nomor Surat': no_surat,
                'Step': 5,
                'Nama Tahapan': keterangan,
                'Status': 'Proses',
                'Tanggal': row.get('Tanggal Disposisi 4')
            })

        log_data.extend(logs)

    return pd.DataFrame(log_data)

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
        nama_tahapan_lower = str(step['Nama Tahapan']).lower()

        # --- Logika tambahan Biro SDM ---
        if 'biro sdm' in nama_tahapan_lower:
            status_class = "done"
            emoji = "✅"
            status_text = "Selesai"
        else:
            status_class = "done" if step['Status'] not in ["On Progress", "Proses"] else "progress"
            emoji = "✅" if status_class == "done" else "⏳"
            status_text = step['Status']

        html += (
            f"<div class='entry {status_class}'>"
            f"<b>Step {step['Step']}:</b> {step['Nama Tahapan']} {emoji}<br>"
            f"📅 {step['Tanggal']} | Status: {status_text}"
            f"</div>"
        )
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

# --- UI Halaman Depan ---
col1, col2 = st.columns([0.7, 4.3])
with col1:
    st.image("assets/kemenag.png", width=70)

with col2:
    st.markdown("""
        <div style="text-align:left; margin-left:0px;">
            <p style="margin:0; font-size:20px; font-weight:bold;">
                KEMENTERIAN AGAMA REPUBLIK INDONESIA
            </p>
            <p style="margin:0; font-size:18px;">
                DIREKTORAT JENDERAL PENDIDIKAN ISLAM
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("""
    <div style="text-align:center; margin-top:40px;">
        <h2 style="color:#2c3e50;">📄 Tracking Surat Mutasi</h2>
        <p style="font-size:16px; color:#34495e; margin-top:20px;">
            Masukkan <b>NIP</b> Anda untuk melakukan pencarian progress <br>
            <strong>Surat Mutasi</strong> di lingkungan Kementerian Agama.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- Input + Button ---
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    nip = st.text_input("Contoh: 198765432019032001", label_visibility="collapsed")
    cari = st.button("🔍 Lacak")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Eksekusi pencarian ---
if nip and cari:
    df_unique = df.drop_duplicates(subset=['No.Surat', 'NIP'], keep='last')
    hasil = df_unique[df_unique['NIP'].astype(str).str.strip().str.lower() == nip.strip().lower()]

    if not hasil.empty:
        row = hasil.iloc[0]

        st.subheader("📌 Hasil Pencarian:")
        st.write(f"**Nomor Surat:** {row.get('No.Surat', '-')}")
        st.write(f"**Nama Ybs:** {row.get('NAMA', '-')}")
        st.write(f"**NIP:** {row.get('NIP', '-')}")
        st.write(f"**Tanggal Surat:** {row.get('Tanggal Surat', '-')}")
        st.write(f"**Perihal:** {row.get('Perihal', '-')}")

        # Buat log timeline hanya dari row ini
        single_row_df = pd.DataFrame([row.to_dict()])
        df_log = buat_log_df(single_row_df)

        # Status terakhir
        status_akhir = df_log.iloc[-1]['Nama Tahapan'] if not df_log.empty else "Belum ada proses"
        st.write(f"**Status Surat Terakhir:** {status_akhir}")

        # Timeline dan tabel log
        if not df_log.empty:
            timeline_tracking(df_log)
            st.markdown("**📋 Tabel Log Tahapan Surat:**")
            st.dataframe(df_log.reset_index(drop=True), use_container_width=True)
        else:
            st.info("Belum ada log alur proses ditemukan.")
    else:
        st.warning("Tidak ditemukan data surat mutasi untuk NIP ini. Silakan verifikasi NIP atau konfirmasi ke unit terkait.")

# --- Footer ---
st.markdown("""
    <div style="text-align: center; font-size: 13px; color: gray;">
        Diberdayakan oleh: <b>Tim Kerja OKH - Sekretariat Direktorat Jenderal Pendidikan Islam</b>
    </div>
""", unsafe_allow_html=True)








































































