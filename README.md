# 📄 Tracking Surat Mutasi

Aplikasi web berbasis **Streamlit** untuk melacak status surat mutasi.  
Data langsung diambil dari **Google Sheets** menggunakan **Service Account** (Google API).

---

## 🚀 Fitur
- 🔍 Pencarian surat berdasarkan **Nomor Surat**.
- 📊 Menampilkan **status terakhir** dan **alur proses** surat.
- 🌈 Tampilan log proses berwarna untuk memudahkan identifikasi status.
- 🔄 Tombol **Refresh Data** langsung dari Google Sheets.

---

## 🛠 Persiapan Sebelum Deploy

### 1. **Buat Service Account di Google Cloud**
1. Buka [Google Cloud Console](https://console.cloud.google.com/).
2. Aktifkan **Google Sheets API** dan **Google Drive API**.
3. Buat **Service Account** dan unduh file `.json` credentials.
4. Bagikan Google Sheets kamu ke `client_email` dari service account tersebut dengan akses **Editor**.

---

### 2. **Simpan Credential di Streamlit Secrets**
**⚠️ Penting**: Jangan upload file `.json` ke GitHub karena berisi data sensitif.

1. Buka file `.json` service account di teks editor.
2. Salin semua isinya.
3. Di **Streamlit Cloud**, buka **Settings → Secrets**.
4. Masukkan format berikut:
    ```toml
    gcp_service_account_json = """
    {
      "type": "service_account",
      "project_id": "xxxx",
      "private_key_id": "xxxx",
      "private_key": "-----BEGIN PRIVATE KEY-----\nxxxx\n-----END PRIVATE KEY-----\n",
      "client_email": "xxxx@xxxx.iam.gserviceaccount.com",
      "client_id": "xxxx",
      ...
    }
    """
    ```
5. Simpan.

---

### 3. **Buat File `requirements.txt`**
```txt
streamlit
pandas
gspread
oauth2client
