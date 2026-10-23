# Penjelasan Mendalam 4 Berkas Utama Sistem DBlast
*(Bedah Fungsi, Arsitektur, & Potongan Kode Penting)*

Dokumen ini membedah secara rinci 4 berkas inti pembangun sistem otomatisasi **DBlast (Dashboard Blasting)**:
1. **`dblast_client.py`** (Antarmuka Pengguna & Pengirim Antrian)
2. **`dblast_engine.py`** (Mesin Eksekusi, Pembuat Laporan, & Pengirim Email)
3. **`dags/dblast_dag.py`** (Definisi Orkestrasi & Jadwal Airflow)
4. **`docker-compose.yaml`** (Infrastruktur Kontainer & Manajemen Lingkungan)

---

## 1. File 1: `dblast_client.py`

### A. Fungsi Utama Berkas
Berkas ini bertindak sebagai **antarmuka sisi klien (*Client Interface*)**. Script ini dikompilasi menjadi `dblast_client.exe` agar pengguna awam dapat memasukkan parameter laporan yang diinginkan tanpa harus membuka kode pemrograman. Tugas utamanya adalah mengumpulkan input pengguna, memvalidasi data, membungkusnya menjadi satu record tugas berstatus `PENDING`, dan mengirimkannya ke tabel antrian Google BigQuery.

---

### B. Bedah Potongan Kode Penting

#### 1. Inisialisasi dan Konfigurasi Target BigQuery
```python
PROJECT_ID = "project-raka-485012" 
TABLE_ID = "project-raka-485012.dblast_data.dblast_queue"
```
* **Fungsi kode**: Menentukan alamat tujuan penyimpanan antrian tugas di Google Cloud BigQuery. Variabel ini mengarahkan data ke project dan tabel `dblast_queue` yang benar.

#### 2. Validasi Pilihan Output Pengguna
```python
output_option = input("[*] Enter Output Option (1-9) : ").strip()
if output_option not in [str(i) for i in range(1, 10)]:
    print("\n[ERROR] Invalid option! Program terminated.")
    return
```
* **Fungsi kode**: Memastikan pengguna hanya memasukkan angka 1 sampai 9. Jika pengguna memasukkan huruf atau angka lain di luar menu, program langsung berhenti secara aman untuk mencegah data korup masuk ke antrian.

#### 3. Loop Dinamis Pengumpulan Parameter Filter Dashboard
```python
filter_params = {}
filter_counter = 1
while True:
    f_name = input(f"[{filter_counter}] Enter Parameter Filter Name  : ").strip()
    if not f_name:
        break 
    f_val = input(f"[{filter_counter}] Enter Parameter Filter Value : ").strip()
    filter_params[f_name] = f_val
    filter_counter += 1
```
* **Fungsi kode**: Memungkinkan pengguna memasukkan lebih dari satu filter Tableau secara fleksibel (misal filter `Region = West`, `Year = 2024`). Saat pengguna menekan **ENTER** tanpa mengetik nama filter, perulangan berhenti dan filter disimpan dalam bentuk dictionary Python.

#### 4. Pembungkusan Data Antrian (*Task Packaging*)
```python
row_to_insert = [{
    "id": str(uuid.uuid4()),
    "output_option": output_option,
    "report_key": report_key,
    "workbook_url": workbook_url,
    "local_file_path": local_file_path,
    "custom_tableau_name": custom_tableau_name,
    "custom_local_name": custom_local_name,
    "filter_params": json.dumps(filter_params),
    "email_to": email_to,
    "email_cc": email_cc,
    "email_bcc": email_bcc,
    "email_subject": email_subject,
    "status": "PENDING",
    "created_at": datetime.now(timezone.utc).isoformat()
}]
```
* **Fungsi kode**:
  * `uuid.uuid4()`: Menghasilkan ID acak unik sepanjang 36 karakter (contoh: `3edfb27d-345e-4447-...`) sebagai identitas utama tugas.
  * `status: "PENDING"`: Menandai bahwa tugas ini baru dan belum pernah dieksekusi.
  * `created_at`: Mencatat waktu pembuatan dalam zona UTC untuk pengurutan kronologis.

#### 5. Pengiriman Data ke BigQuery Menggunakan Load Job
```python
job_config = bigquery.LoadJobConfig(
    write_disposition=bigquery.WriteDisposition.WRITE_APPEND
)
load_job = client.load_table_from_json(row_to_insert, TABLE_ID, job_config=job_config)
load_job.result()
```
* **Fungsi kode**: Mengirim data antrian ke BigQuery dengan metode **Load Job Append**. Metode ini dipilih karena **100% gratis dan diizinkan pada akun Google BigQuery Free Tier (Sandbox)**, berbeda dengan metode streaming insert yang mewajibkan kartu kredit/billing aktif.

---

## 2. File 2: `dblast_engine.py`

### A. Fungsi Utama Berkas
Berkas ini adalah **mesin pemroses utama (*Worker Backend Engine*)**. Dipanggil otomatis oleh Airflow setiap 7 menit, berkas ini bertugas membaca antrian yang belum selesai, mengunduh grafik visual dari Tableau, membuat file Excel dan PDF, menyusun email HTML, mengirimkannya via Gmail SMTP, dan mengunci tugas agar tidak dikirim ganda.

---

### B. Bedah Potongan Kode Penting

#### 1. Mekanisme Otomatis Deteksi Kredensial Google Cloud
```python
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _adc_file = os.path.join(_script_dir, ".gcloud_adc.json")
    if os.path.exists(_adc_file):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _adc_file
```
* **Fungsi kode**: Memastikan script dapat mengakses BigQuery baik saat dijalankan di Windows maupun di dalam kontainer Docker. Jika sistem belum memiliki variabel path kredensial, script otomatis mengarahkannya ke file `.gcloud_adc.json`.

#### 2. Sistem Proteksi Idempotensi (Mencegah Email Dobel di Akun Free Tier)
```python
PROCESSED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_tasks.txt")

def get_processed_tasks():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_task_as_processed(task_id):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{task_id}\n")
```
* **Fungsi kode**: Mengelola file lokal `processed_tasks.txt`. Fungsi `get_processed_tasks()` membaca daftar ID yang sudah sukses, sedangkan `mark_task_as_processed()` mencatat ID baru segera setelah email sukses terkirim.

#### 3. Pengambilan Antrian dan Pengecekan Duplikasi
```python
query = f"""
    SELECT * FROM `{TABLE_ID}`
    WHERE status = 'PENDING'
    ORDER BY created_at ASC
"""
...
for row in pending_tasks:
    if str(row.id) in processed_tasks:
        print(f"[SYSTEM] Task ID {row.id} already processed. Skipping.")
        continue
```
* **Fungsi kode**: Mengambil semua tugas berstatus `PENDING` dari BigQuery dari yang paling lama. Sebelum diproses, script mencocokkan ID dengan daftar log lokal. Jika ID sudah ada, tugas langsung dilewati (*continue/skip*).

#### 4. Ekstraksi Visual Gambar & Dokumen PDF dari Tableau
```python
base_url = f"https://public.tableau.com/views/{workbook_url}"
params = {"?:showVizHome": "no", "&:resolution": "high"}
params.update(filter_params)

response_img = requests.get(f"{base_url}.png", params=params)
response_pdf = requests.get(f"{base_url}.pdf", params=params)
```
* **Fungsi kode**: Memanfaatkan kemampuan render Tableau Server/Public via URL. Dengan menambahkan akhiran `.png` atau `.pdf` beserta parameter filter, Tableau akan langsung merender dan mengembalikan data biner gambar atau dokumen PDF secara instan tanpa perlu membuka browser.

#### 5. Pembuatan File Excel & Penyisipan Gambar Visual Menggunakan Pillow
```python
img_stream = BytesIO(img_data)
wb = openpyxl.Workbook()
sheet = wb.active
sheet.title = "Dashboard Report"
sheet['B2'] = f"Report: {sheet_name}"
...
img_xl = Image(img_stream)
sheet.add_image(img_xl, f'B{row_idx + 1}') 
```
* **Fungsi kode**: Menggunakan pustaka `openpyxl` dan `Pillow` untuk membuat spreadsheet baru di memori RAM (`BytesIO`), menulis judul serta parameter filter di baris atas, dan menyematkan objek gambar dashboard Tableau tepat di bawah teks laporan.

#### 6. Komposisi Email HTML Multipart dengan Gambar Tertanam (CID)
```python
msg_main = EmailMessage()
msg_main['Subject'] = row.email_subject
msg_main['From'] = SENDER_EMAIL
msg_main['To'] = row.email_to
...
msg_main.add_attachment(img_data, maintype='image', subtype='png', cid="<dashboard_image>", filename=f"{base_filename}.png")
```
* **Fungsi kode**: Menyusun email multipart berformat HTML. Parameter `cid="<dashboard_image>"` (*Content-ID*) berfungsi menghubungkan data biner gambar langsung ke tag `<img src="cid:dashboard_image">` di dalam badan email, sehingga gambar dashboard langsung tampil visual saat email dibuka oleh penerima.

#### 7. Pengiriman Email via Protokol SMTP SSL
```python
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(SENDER_EMAIL, APP_PASSWORD)
    smtp.send_message(msg_main)
    smtp.send_message(msg_notif)
```
* **Fungsi kode**: Membuka saluran komunikasi aman terenkripsi SSL ke server Google (port 465), melakukan login menggunakan Gmail App Password, lalu mengirimkan email laporan utama ke penerima dan email notifikasi konfirmasi pendaftaran ke PIC.

#### 8. Penanganan Status Selesai Dual-Layer (Aman untuk Free Tier & Billing)
```python
# Lapisan 1: Kunci lokal
mark_task_as_processed(str(row.id))

# Lapisan 2: Update database BigQuery
try:
    update_query = f"UPDATE `{TABLE_ID}` SET status = 'DONE' WHERE id = '{row.id}'"
    client.query(update_query).result()
except Exception as update_err:
    if "DML queries are not allowed in the free tier" in str(update_err):
        print("[SKIPPED] (Free Tier restriction: Cannot UPDATE to 'DONE', but Email was sent!)")
    else:
        raise update_err
```
* **Fungsi kode**: Lapisan 1 langsung mengunci ID di file lokal agar aman dari duplikasi. Lapisan 2 mencoba melakukan query SQL `UPDATE`. Pada akun Free Tier, error DML ditangkap dan dilewati secara halus. Saat akun beralih ke Billing, perintah ini otomatis mengubah status di BigQuery menjadi `DONE`.

---

## 3. File 3: `dags/dblast_dag.py`

### A. Fungsi Utama Berkas
Berkas ini adalah **skrip orkestrasi Apache Airflow**. Berkas ini mendefinisikan jadwal, aturan retry, dependensi, serta perintah sistem yang harus dieksekusi secara otomatis dan berkala. Berkas inilah yang membuat sistem DBlast dapat berjalan otomatis tanpa perlu ada orang yang menekan tombol *run* setiap saat.

---

### B. Bedah Potongan Kode Penting

#### 1. Pengaturan Argumen Default Pipeline
```python
default_args = {
    'owner': 'raka_arrayan',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}
```
* **Fungsi kode**:
  * `'owner'`: Menamai pemilik DAG di tampilan dashboard Airflow.
  * `'retries': 1`: Jika eksekusi gagal (misal koneksi internet terputus), Airflow akan otomatis mencoba mengulang 1 kali lagi.
  * `'retry_delay': timedelta(minutes=2)`: Jeda waktu sebelum pengulangan adalah 2 menit.

#### 2. Definisi Parameter Orkestrasi DAG
```python
with DAG(
    dag_id='dblast_automation_pipeline',
    default_args=default_args,
    description='Pipeline to trigger DBlast Engine every 7 minutes for pending Tableau requests',
    schedule_interval='*/7 * * * *',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1
) as dag:
```
* **Fungsi kode**:
  * `dag_id`: Nama unik identitas pipeline di Airflow.
  * `schedule_interval='*/7 * * * *'`: Mengatur jadwal menggunakan ekspresi cron agar pipeline aktif **setiap 7 menit**.
  * `catchup=False`: Mencegah Airflow menjalankan tugas-tugas masa lalu yang tertinggal saat server baru dinyalakan.
  * `max_active_runs=1`: **Sangat krusial** untuk mencegah terjadinya tabrakan eksekusi ganda jika proses sebelumnya belum selesai.

#### 3. Task Eksekutor BashOperator
```python
run_engine_task = BashOperator(
    task_id='run_dblast_backend_engine',
    bash_command='python /opt/airflow/dblast/dblast_engine.py',
)
```
* **Fungsi kode**: Menginstruksikan sistem operasi kontainer Airflow untuk menjalankan perintah terminal `python /opt/airflow/dblast/dblast_engine.py`. Operator ini menjadi jembatan antara scheduler Airflow dengan skrip backend engine.

---

## 4. File 4: `docker-compose.yaml`

### A. Fungsi Utama Berkas
Berkas ini adalah **konfigurasi infrastruktur berbasis kontainer Docker**. Berkas ini mengatur bagaimana kontainer Airflow dibuat, port jaringan yang dibuka, zona waktu server, variabel lingkungan, dependensi Python tambahan yang harus dipasang, serta folder lokal mana saja yang dihubungkan (*mount*) ke dalam kontainer.

---

### B. Bedah Potongan Kode Penting

#### 1. Pemilihan Image Resmi dan Nama Kontainer
```yaml
services:
  airflow:
    image: apache/airflow:2.8.1-python3.11
    container_name: dblast-airflow
    restart: always
    ports:
      - "8080:8080"
```
* **Fungsi kode**: Menggunakan image resmi Apache Airflow versi 2.8.1 berbasis Python 3.11, memberi nama kontainer `dblast-airflow`, memastikan kontainer selalu menyala otomatis jika laptop direstart (`restart: always`), dan memetakan port `8080` agar Web UI Airflow dapat diakses dari browser komputer lokal.

#### 2. Sinkronisasi Zona Waktu Indonesia (WIB)
```yaml
    environment:
      TZ: 'Asia/Jakarta'
      AIRFLOW__CORE__DEFAULT_TIMEZONE: 'Asia/Jakarta'
      AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE: 'Asia/Jakarta'
```
* **Fungsi kode**: Menyelaraskan seluruh jam sistem kontainer, jam penjadwalan DAG, dan tampilan antarmuka web Airflow agar menggunakan waktu **Asia/Jakarta (WIB / UTC+7)**, bukan UTC.

#### 3. Pemasangan Pustaka Otomatis saat Startup
```yaml
      _PIP_ADDITIONAL_REQUIREMENTS: 'openpyxl pillow google-cloud-bigquery python-dotenv requests'
      GOOGLE_APPLICATION_CREDENTIALS: /opt/airflow/dblast/.gcloud_adc.json
```
* **Fungsi kode**: Fitur khusus image Airflow yang secara otomatis mengunduh dan memasang paket `openpyxl`, `pillow`, `google-cloud-bigquery`, dll saat kontainer pertama kali menyala, serta mengarahkan variabel path Google Cloud ke file kredensial yang telah disediakan.

#### 4. Pemetaan Folder (*Volume Bind-Mounts*)
```yaml
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
      - ./:/opt/airflow/dblast
```
* **Fungsi kode**: Menghubungkan folder fisik di laptop Anda dengan folder di dalam kontainer Linux Docker:
  * `./dags`: Tempat file DAG dibaca scheduler.
  * `./logs`: Tempat menyimpan riwayat log eksekusi.
  * `./`: Menghubungkan seluruh folder proyek ke `/opt/airflow/dblast` agar script `dblast_engine.py` dan file pendukungnya dapat diakses secara langsung dari dalam kontainer.

#### 5. Mode Standalone (Solusi Satu Kontainer Ringkas)
```yaml
    command: standalone
```
* **Fungsi kode**: Menjalankan Airflow dalam mode **`standalone`**. Perintah ini menyatukan Webserver, Scheduler, dan Triggerer dalam satu kontainer tunggal yang berbagi satu database SQLite, mengeliminasi kebutuhan database Postgres eksternal yang berat untuk kebutuhan lokal.

---

## 5. Rangkuman Hubungan Antar Berkas

| Berkas | Peran Utama | Berinteraksi Dengan |
|---|---|---|
| **`dblast_client.py`** | Menerima request user via terminal/GUI `.exe` | Menulis antrian ke **Google BigQuery** |
| **`dags/dblast_dag.py`** | Mengatur alarm jadwal otomatis (tiap 7 menit) | Memanggil **`dblast_engine.py`** melalui Airflow |
| **`dblast_engine.py`** | Memproses antrian, membuat visual, & kirim email | Membaca **BigQuery**, mengambil dari **Tableau**, mengirim via **Gmail SMTP**, & mencatat ke **`processed_tasks.txt`** |
| **`docker-compose.yaml`** | Menyediakan 'rumah' dan lingkungan server Airflow | Menjalankan kontainer yang menaungi **DAG** dan **Engine** |
