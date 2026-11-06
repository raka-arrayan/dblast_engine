# Panduan DBlast Tanpa `.exe`

Dokumen ini menjelaskan cara menjalankan DBlast dengan memasukkan request
secara manual ke Google BigQuery. Pada alur ini, `dblast_client.py` dan
`dblast_client.exe` tidak digunakan.

## 1. Arsitektur

```text
Operator
   |
   | Memasukkan satu row request secara manual
   v
Google BigQuery: dblast_queue
   |
   | status = PENDING
   v
Airflow di dalam Docker
   |
   | Menjalankan DAG setiap 7 menit
   v
dblast_engine.py
   |
   +--> Membaca task PENDING dari BigQuery
   +--> Mengambil gambar/PDF dari Tableau
   +--> Membuat Excel bila diperlukan
   +--> Membaca attachment lokal bila diperlukan
   +--> Mengirim email melalui SMTP
   +--> Mencatat ID pada processed_tasks.txt
   +--> Mencoba mengubah status menjadi DONE
```

Peran komponen:

| Komponen | Fungsi |
|---|---|
| BigQuery | Menyimpan antrean request |
| `dblast_dag.py` | Menentukan jadwal dan memanggil engine |
| `dblast_engine.py` | Memproses request dan mengirim email |
| Docker | Menyediakan lingkungan Airflow dan library |
| Tableau | Sumber gambar dan PDF dashboard |
| SMTP | Mengirim email |
| `processed_tasks.txt` | Mencegah task yang sama dikirim ulang |

## 2. Prasyarat

Komputer yang menjalankan backend perlu memiliki:

1. Docker Desktop.
2. Docker Compose (biasanya sudah tersedia pada Docker Desktop).
3. Akses internet ke BigQuery, Tableau, dan SMTP.
4. Project Google Cloud dan tabel BigQuery yang sudah dibuat.
5. File kredensial Google Cloud yang valid.
6. File `.env` dengan konfigurasi SMTP.

Python dan library backend tidak perlu dipasang di Windows untuk menjalankan
Airflow, karena library tersebut dipasang di dalam container berdasarkan
`docker-compose.yaml`. Python lokal hanya diperlukan jika ingin menguji script
di luar Docker.

## 3. Struktur folder yang digunakan

Jalankan semua perintah dari folder:

```text
C:\Users\rifqi\Documents\Magang_cimb\Tableau\dblast
```

File utama:

```text
dblast\
├── dags\
│   └── dblast_dag.py
├── dblast_engine.py
├── docker-compose.yaml
├── .env
├── .gcloud_adc.json
├── processed_tasks.txt
├── logs\
└── plugins\
```

Jangan membagikan `.env` atau `.gcloud_adc.json`. Keduanya berisi konfigurasi
atau kredensial yang sensitif.

## 4. Membuat file `.env`

File `.env` menyimpan konfigurasi email yang dibaca oleh
`dblast_engine.py`. Buat file tersebut dari folder proyek.

Pada PowerShell:

```powershell
cd C:\Users\rifqi\Documents\Magang_cimb\Tableau\dblast
New-Item -Path .env -ItemType File -Force
notepad .env
```

Isi file `.env` dengan nilai milik Anda:

```dotenv
SENDER_EMAIL=alamatpengirim@gmail.com
APP_PASSWORD=abcdefghijklmnop
PIC_EMAIL=pic@gmail.com
```

`SENDER_EMAIL` adalah akun Gmail yang digunakan untuk mengirim laporan.
`PIC_EMAIL` adalah alamat yang menerima notifikasi bahwa request berhasil
diproses. Jangan menambahkan tanda kutip pada nilai dan jangan menuliskan
spasi di dalam `APP_PASSWORD`.

### 4.1 Mengapa menggunakan `APP_PASSWORD`?

Pada percobaan ini pengiriman email menggunakan domain `@gmail.com` melalui
Gmail SMTP. Gmail tidak seharusnya diakses menggunakan password akun utama
yang ditulis di `.env`. Sebagai gantinya, Google menyediakan **App Password**,
yaitu password khusus untuk aplikasi seperti DBlast. App Password berbeda dari
password login Gmail dan dapat dicabut tanpa mengganti password akun utama.

Cara membuat App Password:

1. Login ke akun Gmail pengirim.
2. Buka [Google Account](https://myaccount.google.com/).
3. Pilih **Security**.
4. Aktifkan **2-Step Verification** jika belum aktif.
5. Pada halaman Security, buka **App passwords**.
6. Masukkan nama aplikasi, misalnya `DBlast`.
7. Pilih **Create/Generate**.
8. Salin password 16 karakter yang diberikan Google.
9. Masukkan password tersebut ke `APP_PASSWORD` pada `.env`, tanpa spasi.

Menu App passwords dapat tidak tersedia jika akun dikelola organisasi dan
administrator menonaktifkannya. Dalam kondisi tersebut, gunakan SMTP relay
kantor atau minta konfigurasi yang disetujui administrator. Jangan menyimpan
password Gmail utama di source code, `.env`, atau file yang dibagikan.

## 5. Virtual environment (opsional)

Virtual environment tidak diperlukan untuk Airflow yang berjalan di Docker.
Namun, environment ini dapat digunakan untuk menguji atau menjalankan script
Python secara lokal.

Jika Anda melakukan clone project ini dan menggunakan Docker Compose, bagian
ini dapat dilewati. Anda tidak perlu membuat atau mengaktifkan `venv`.
Setelah menyelesaikan pembuatan `.env` pada Bagian 4 dan menyiapkan
`.gcloud_adc.json` pada Bagian 6, lanjutkan ke Bagian 8 untuk menjalankan
`docker compose up -d`.

Buat environment dengan nama `venv`:

```cmd
cd C:\Users\rifqi\Documents\Magang_cimb\Tableau\dblast
python -m venv venv
```

Aktifkan pada CMD:

```cmd
venv\Scripts\activate
```

Aktifkan pada PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Jika berhasil, prompt akan diawali dengan `(venv)`. Install library lokal
hanya jika diperlukan:

```cmd
python -m pip install --upgrade pip
pip install google-cloud-bigquery openpyxl pillow python-dotenv requests
```

`pyinstaller` hanya diperlukan untuk membuat `.exe`, sehingga tidak diperlukan
untuk alur dalam dokumen ini.

Untuk keluar dari environment:

```cmd
deactivate
```

## 6. Menyiapkan konfigurasi

### 6.1 Kredensial Google Cloud

`docker-compose.yaml` tidak membuat file kredensial Google Cloud secara
otomatis. File `.gcloud_adc.json` harus disiapkan terlebih dahulu di folder
proyek sebelum container dijalankan.

Jika menggunakan Application Default Credentials, jalankan autentikasi pada
komputer yang memiliki Google Cloud CLI:

```cmd
gcloud auth application-default login
```

Perintah tersebut menyimpan kredensial ADC pada konfigurasi Google Cloud user,
bukan otomatis sebagai `.gcloud_adc.json` di folder project. Salin file ADC
tersebut ke root project dan ubah namanya menjadi `.gcloud_adc.json`, atau
gunakan file kredensial service account yang disetujui organisasi dengan nama
yang sama. Pastikan akun tersebut memiliki akses ke BigQuery yang diperlukan.

Setelah itu, pastikan file kredensial tersedia di folder proyek dan konfigurasi pada
`docker-compose.yaml` menunjuk ke lokasi container:

```text
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/dblast/.gcloud_adc.json
```

File lokal dipasang ke container melalui volume:

```yaml
- ./:/opt/airflow/dblast
```

Jangan menuliskan isi kredensial ke dalam dokumentasi atau source code.

## 7. Fungsi Docker dalam sistem

Docker bukan pengganti Airflow dan bukan komponen yang mengirim email.
Docker menyediakan container, yaitu lingkungan terisolasi tempat Airflow,
Python, DAG, engine, dan library pendukung dijalankan bersama.

Pada proyek ini, Docker Compose membaca `docker-compose.yaml` untuk:

- Menjalankan image Apache Airflow dengan Python 3.11.
- Menyediakan library `openpyxl`, `pillow`, `google-cloud-bigquery`,
  `python-dotenv`, dan `requests` di dalam container.
- Menjalankan Airflow Scheduler dan Webserver.
- Memasang folder `dags` agar DAG dapat dibaca Airflow.
- Memasang folder proyek agar engine dan kredensial dapat diakses melalui
  path container `/opt/airflow/dblast`.
- Meneruskan port container sehingga UI tersedia di
  `http://localhost:8080`.

Dengan demikian, Python dan library tersebut tidak perlu dipasang langsung di
Windows untuk menjalankan Airflow. Docker Desktop tetap harus terpasang pada
komputer yang menjalankan backend.

## 8. Menjalankan Airflow dengan Docker

Jalankan Docker hanya setelah `.env` dan `.gcloud_adc.json` sudah tersedia.
Docker Compose tidak membentuk kedua file tersebut; Docker hanya membaca dan
memasang file yang sudah ada ke dalam container.

Buka PowerShell atau CMD, lalu jalankan:

```cmd
cd C:\Users\rifqi\Documents\Magang_cimb\Tableau\dblast
docker compose up -d
```

Perintah ini akan:

1. Mengambil image Apache Airflow 2.8.1 dengan Python 3.11 bila belum ada.
2. Membuat container bernama `dblast-airflow`.
3. Memasang dependency tambahan yang tercantum di
   `docker-compose.yaml`.
4. Memasang folder DAG dan folder proyek ke container.
5. Menjalankan Airflow dalam mode `standalone`.

Periksa status container:

```cmd
docker compose ps
```

Lihat log jika diperlukan:

```cmd
docker compose logs -f airflow
```

Hentikan tampilan log dengan `Ctrl+C`; container tetap berjalan. Untuk
menghentikan service:

```cmd
docker compose down
```

## 9. Membuka dan mengaktifkan Airflow

Buka browser ke:

```text
http://localhost:8080
```

Login menggunakan akun yang dikonfigurasi pada `docker-compose.yaml`:

```text
Username: airflow
Password: airflow
```

Di halaman DAG:

1. Cari `dblast_automation_pipeline`.
2. Pastikan DAG dalam keadaan **Unpaused/ON**.
3. Pastikan jadwalnya setiap 7 menit.

Jadwal tersebut didefinisikan di `dags/dblast_dag.py`:

```python
schedule_interval='*/7 * * * *'
```

Task DAG kemudian menjalankan:

```bash
python /opt/airflow/dblast/dblast_engine.py
```

## 10. Skema data BigQuery

Engine membaca tabel:

```text
project-raka-485012.dblast_data.dblast_queue
```

Kolom request yang digunakan:

| Kolom | Contoh | Keterangan |
|---|---|---|
| `id` | UUID | ID unik task |
| `output_option` | `1` | Pilihan output `1` sampai `9` |
| `report_key` | `Daily Sales` | Identitas laporan |
| `workbook_url` | `Workbook/Sheet` | Path workbook Tableau |
| `local_file_path` | `C:\Reports\a.pdf` | Path file lokal/shared drive bila digunakan |
| `custom_tableau_name` | `sales_report` | Nama attachment Tableau tanpa ekstensi |
| `custom_local_name` | `supporting_file` | Nama attachment lokal tanpa ekstensi |
| `filter_params` | `{"Region":"West"}` | JSON string filter Tableau |
| `email_to` | `user@example.com` | Penerima utama |
| `email_cc` | `manager@example.com` | Penerima CC |
| `email_bcc` |  | Penerima BCC |
| `email_subject` | `Daily Sales Report` | Subject email |
| `status` | `PENDING` | Status yang dicari engine |
| `created_at` | timestamp | Urutan antrean |

### Fungsi setiap kolom

| Kolom | Fungsi dan aturan pengisian |
|---|---|
| `id` | ID unik untuk setiap task. Wajib diisi dan tidak boleh sama dengan task lain karena digunakan untuk idempotensi di `processed_tasks.txt`. |
| `output_option` | Menentukan jenis output. Wajib diisi dengan nilai string `1` sampai `9`. |
| `report_key` | Nama atau identitas laporan yang digunakan pada notifikasi ke PIC. Sebaiknya selalu diisi. Jika kosong, engine menggunakan `AutoTask` hanya pada client lama, sehingga input manual sebaiknya tidak mengosongkannya. |
| `workbook_url` | Path workbook/sheet Tableau yang akan diakses. Wajib untuk opsi `1` sampai `7` dan `9`; kosong untuk opsi `8`. |
| `local_file_path` | Path file lokal atau shared drive yang akan dilampirkan. Wajib untuk opsi `8` dan `9`; kosong untuk opsi `1` sampai `7`. File tersebut juga harus dapat diakses dari dalam container Docker. |
| `custom_tableau_name` | Nama kustom attachment dari Tableau tanpa ekstensi. Diisi bila ingin mengganti nama file pada opsi yang menghasilkan output Tableau (`1` sampai `7` dan `9`); boleh kosong agar engine membuat nama otomatis. |
| `custom_local_name` | Nama kustom attachment lokal tanpa ekstensi. Relevan hanya untuk opsi `8` dan `9`; boleh kosong agar nama file asli dipertahankan. |
| `filter_params` | Filter Tableau dalam bentuk JSON string. Wajib diisi dengan `{}` jika tidak memakai filter, atau JSON valid seperti `{"Region":"West"}` jika memakai filter. |
| `email_to` | Alamat penerima utama. Wajib diisi agar email laporan memiliki penerima. Jika lebih dari satu, pisahkan dengan koma. |
| `email_cc` | Alamat penerima CC. Opsional; kosongkan jika tidak digunakan. Jika lebih dari satu, pisahkan dengan koma. |
| `email_bcc` | Alamat penerima BCC. Opsional; kosongkan jika tidak digunakan. Jika lebih dari satu, pisahkan dengan koma. |
| `email_subject` | Judul email laporan. Sebaiknya selalu diisi agar penerima mengetahui isi laporan. |
| `status` | Status antrean. Wajib diisi persis `PENDING` agar dibaca engine. |
| `created_at` | Waktu pembuatan task yang digunakan untuk mengurutkan antrean dari yang paling lama. Wajib diisi dengan timestamp. |

### Kolom wajib berdasarkan `output_option`

Tabel berikut menunjukkan kolom yang harus diisi. Kolom yang ditandai
**opsional** boleh dikosongkan, sedangkan kolom yang ditandai **kosong**
sebaiknya tidak diisi karena tidak digunakan pada opsi tersebut.

| Opsi | Output | Kolom output yang wajib diisi | Kolom output yang tidak digunakan |
|---:|---|---|---|
| `1` | Gambar dashboard di body email | `workbook_url` | `local_file_path`, `custom_local_name` |
| `2` | Gambar dashboard dan Excel | `workbook_url` | `local_file_path`, `custom_local_name` |
| `3` | Gambar dashboard dan PDF | `workbook_url` | `local_file_path`, `custom_local_name` |
| `4` | Gambar, Excel, dan PDF | `workbook_url` | `local_file_path`, `custom_local_name` |
| `5` | Excel | `workbook_url` | `local_file_path`, `custom_local_name` |
| `6` | Excel dan PDF | `workbook_url` | `local_file_path`, `custom_local_name` |
| `7` | PDF | `workbook_url` | `local_file_path`, `custom_local_name` |
| `8` | File lokal | `local_file_path` | `workbook_url`, `custom_tableau_name` |
| `9` | Gambar dashboard dan file lokal | `workbook_url`, `local_file_path` | Tidak ada; `custom_tableau_name` dan `custom_local_name` tetap opsional |

Selain kolom output pada tabel tersebut, setiap opsi membutuhkan kolom umum:
`id`, `output_option`, `report_key`, `filter_params`, `email_to`,
`email_subject`, `status`, dan `created_at`. Kolom `email_cc` dan `email_bcc`
bersifat opsional.

Contoh aturan praktis:

- Opsi `1` sampai `7`: isi `workbook_url`, kosongkan dua kolom file lokal.
- Opsi `8`: isi `local_file_path`, kosongkan `workbook_url` dan
  `custom_tableau_name`.
- Opsi `9`: isi `workbook_url` dan `local_file_path`.
- Jika tidak memakai filter, isi `filter_params` dengan `{}`, bukan teks
  penjelasan atau JSON yang tidak valid.
- Jika nama kustom tidak diperlukan, isi `custom_tableau_name` atau
  `custom_local_name` dengan string kosong.

### Arti `output_option`

| Opsi | Output |
|---:|---|
| `1` | Gambar dashboard di body email |
| `2` | Gambar dan Excel |
| `3` | Gambar dan PDF |
| `4` | Gambar, Excel, dan PDF |
| `5` | Excel |
| `6` | Excel dan PDF |
| `7` | PDF |
| `8` | File lokal |
| `9` | Gambar dan file lokal |

## 11. Memasukkan request secara manual

### Cara yang disarankan untuk Sandbox

Jika SQL DML seperti `INSERT` dibatasi oleh BigQuery Sandbox, gunakan BigQuery
Console:

1. Buka Google Cloud Console dan pilih project
   `project-raka-485012`.
2. Buka BigQuery.
3. Buka dataset `dblast_data` dan tabel `dblast_queue`.
4. Pilih **Add data** atau **Edit schema/Insert rows** sesuai tampilan console.
5. Isi semua kolom sesuai skema.
6. Gunakan `PENDING` pada kolom `status`.
7. Simpan row.

Buat UUID unik untuk kolom `id`, misalnya dengan PowerShell:

```powershell
[guid]::NewGuid().ToString()
```

### Contoh SQL

Jika project dan billing mengizinkan query DML, request dapat dimasukkan
dengan query berikut. Contoh ini menggunakan opsi `4` untuk laporan
`US_Flight_Report` dengan dua filter Tableau:

```sql
INSERT INTO `project-raka-485012.dblast_data.dblast_queue`
(
  id,
  output_option,
  report_key,
  workbook_url,
  local_file_path,
  custom_tableau_name,
  custom_local_name,
  filter_params,
  email_to,
  email_cc,
  email_bcc,
  email_subject,
  status,
  created_at
)
VALUES
(
  GENERATE_UUID(),
  '4',
  'US_Flight_Report',
  'US_17679270950870/Dashboard1',
  '',
  'Laporan_US_Flight_Food_Business',
  '',
  '{"Pick a metric":"Food","Traveller Type":"Business"}',
  'rakaarrayan27@gmail.com',
  '',
  '',
  'Dash Blast',
  'PENDING',
  CURRENT_TIMESTAMP()
);
```

Penjelasan contoh:

- `output_option = '4'` meminta gambar dashboard, Excel, dan PDF.
- `workbook_url` diisi karena opsi `4` mengambil data dari Tableau.
- `local_file_path` dan `custom_local_name` dikosongkan karena opsi `4`
  tidak menggunakan file lokal.
- `filter_params` berisi JSON valid di dalam string SQL:
  `{"Pick a metric":"Food","Traveller Type":"Business"}`.
- `id` dibuat otomatis oleh BigQuery menggunakan `GENERATE_UUID()`, sehingga
  setiap request memperoleh ID unik.
- `status` harus `PENDING` agar dapat ditemukan engine.

Untuk memeriksa request:

```sql
SELECT
  id,
  output_option,
  report_key,
  status,
  created_at
FROM `project-raka-485012.dblast_data.dblast_queue`
WHERE status = 'PENDING'
ORDER BY created_at ASC;
```

## 12. Proses setelah row dibuat

Setelah row berstatus `PENDING` tersimpan:

1. Scheduler Airflow menunggu jadwal berikutnya.
2. DAG menjalankan engine setiap 7 menit.
3. Engine mengambil task `PENDING` berdasarkan `created_at`.
4. Engine mengecek `processed_tasks.txt`.
5. Engine mengunduh output Tableau sesuai opsi.
6. Engine membuat attachment dan mengirim email.
7. ID task ditulis ke `processed_tasks.txt`.
8. Engine mencoba mengubah status menjadi `DONE`.

Jika BigQuery Sandbox menolak `UPDATE`, email tetap sudah terkirim dan
`processed_tasks.txt` mencegah task dikirim ulang pada siklus berikutnya.

## 13. Verifikasi dan troubleshooting

### Memeriksa task Airflow

Di Airflow UI, buka DAG `dblast_automation_pipeline`, lalu buka task
`run_dblast_backend_engine` dan lihat lognya.

### Memeriksa log container

```cmd
docker compose logs --tail=200 airflow
```

### Memeriksa status container

```cmd
docker compose ps
```

### Masalah umum

| Masalah | Pemeriksaan |
|---|---|
| DAG tidak terlihat | Pastikan folder `dags` ter-mount dan container berjalan |
| DAG paused | Ubah toggle DAG menjadi ON |
| Engine tidak menemukan task | Pastikan `status` persis `PENDING` |
| Kredensial gagal | Periksa `.gcloud_adc.json` dan path container |
| Email gagal | Periksa `.env`, app password, dan akses SMTP |
| File lokal tidak terbaca | Pastikan file berada di folder yang terlihat oleh container |
| Task dilewati | Periksa apakah ID sudah ada di `processed_tasks.txt` |

## 14. Mengapa `processed_tasks.txt` diperlukan?

`processed_tasks.txt` adalah catatan lokal berisi ID task yang sudah berhasil
dikirim. Engine membaca file ini sebelum memproses task baru.

Pada akun BigQuery Free/Sandbox, operasi perubahan data seperti `UPDATE` dapat
dibatasi. Akibatnya, engine mungkin tidak dapat mengubah status task dari
`PENDING` menjadi `DONE`. Jika status tetap `PENDING`, task yang sama akan
terlihat lagi pada jadwal 7 menit berikutnya.

Untuk mencegah email terkirim berulang kali, setelah email berhasil dikirim
engine mencatat ID task ke `processed_tasks.txt`. Pada siklus berikutnya,
engine menemukan ID tersebut dan melewati task itu. Engine tetap mencoba
menjalankan `UPDATE ... SET status = 'DONE'`; jika BigQuery mengizinkan,
status akan berubah menjadi `DONE`, dan jika ditolak karena pembatasan Free
Tier, catatan lokal menjadi perlindungan idempotensi.

File ini harus tetap berada di folder proyek yang di-mount ke container.
Jangan menghapus atau mengosongkannya selama masih ada task `PENDING` yang
pernah berhasil dikirim. File ini juga tidak boleh dibagikan sebagai pengganti
database atau kredensial.

## 15. Komponen yang tidak digunakan

Dalam alur tanpa `.exe`:

- `dblast_client.py` tidak dijalankan.
- `dblast_client.exe` tidak dijalankan.
- PyInstaller tidak diperlukan.
- Input request dilakukan langsung di BigQuery.

File client boleh disimpan sebagai backup. Tidak perlu menghapusnya agar
rollback ke alur lama tetap mudah dilakukan.

## 16. Ringkasan perintah utama

```cmd
cd C:\Users\rifqi\Documents\Magang_cimb\Tableau\dblast
docker compose up -d
docker compose ps
```

Kemudian:

1. Buka `http://localhost:8080`.
2. Aktifkan DAG `dblast_automation_pipeline`.
3. Masukkan row request ke BigQuery dengan `status = PENDING`.
4. Tunggu maksimal sekitar 7 menit.
5. Periksa log task Airflow dan inbox penerima.
