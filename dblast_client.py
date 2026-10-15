import os
import json
import uuid
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. SYSTEM CONFIGURATION
# ==============================================================================
PROJECT_ID = "project-raka-485012" 
TABLE_ID = "project-raka-485012.dblast_data.dblast_queue"

def main():
    print("=====================================================================================")
    print("                         DBLAST CLIENT INTERFACE V2.0")
    print("                 Automated Tableau Dashboard & Email Blasting")
    print("=====================================================================================\n")
    print("Welcome! Please provide the parameters for your report request.\n")

    
    print("+----------+------------------------------------------------+")
    print("| Optional |                  Description                   |")
    print("+----------+------------------------------------------------+")
    print("|    1     | Only sheet1                                    |")
    print("|    2     | sheet1 + sheet2                                |")
    print("|    3     | sheet1 + sheet3                                |")
    print("|    4     | sheet1 + sheet2 + sheet3                       |")
    print("|    5     | Only sheet2                                    |")
    print("|    6     | sheet2 + sheet3                                |")
    print("|    7     | Only sheet3                                    |")
    print("|    8     | Attachment Look up                             |")
    print("|    9     | sheet1 + Attachment Look up                    |")
    print("+----------+------------------------------------------------+\n")

    print("+--------------------+--------------------------------------------------------------+")
    print("|                                      Legend                                       |")
    print("+--------------------+--------------------------------------------------------------+")
    print("| sheet1             | : Capture image Dashboard Jarvis, put on body email          |")
    print("| sheet2             | : export Sheet Jarvis into excel put on as email attachment  |")
    print("| sheet3             | : capture Dashboard Jarvis export as PDF and put on as email |")
    print("| Attachment Look up | : refer to a file in MISHARE and put on as email attachment  |")
    print("+--------------------+--------------------------------------------------------------+\n")

    try:
        # --- BLOCK 1: USER INPUT ---
        print(">>> OUTPUT SETTINGS")
        output_option = input("[*] Enter Output Option (1-9)            : ").strip()
        
        if output_option not in [str(i) for i in range(1, 10)]:
            print("\n[ERROR] Invalid option! Program terminated.")
            return

        report_key = input("[*] Enter Report Key                     : ").strip()
        if not report_key: report_key = "AutoTask"

        local_file_path = ""
        workbook_url = ""
        custom_tableau_name = ""
        custom_local_name = ""

        if output_option in ['1', '2', '3', '4', '5', '6', '7', '9']:
            workbook_url = input("[*] Enter Tableau Workbook/Sheet Path    : ").strip()

        if output_option in ['8', '9']:
            local_file_path = input("[*] Enter Local File Path (ex: C:\\data.pdf): ").strip()

        if output_option in ['1', '2', '3', '4', '5', '6', '7']:
            custom_tableau_name = input("[*] Enter Custom Attachment Name (Press ENTER for default) : ").strip()
        elif output_option == '8':
            custom_local_name = input("[*] Enter New Name for Local File (Press ENTER to keep original): ").strip()
        elif output_option == '9':
            custom_tableau_name = input("[*] Enter Custom Name for Tableau File (Press ENTER for default): ").strip()
            custom_local_name = input("[*] Enter New Name for Local File (Press ENTER to keep original)  : ").strip()

        print("\n>>> FILTER SETTINGS (Press ENTER on Filter Name to stop/skip)")
        filter_params = {}
        filter_counter = 1
        while True:
            f_name = input(f"[{filter_counter}] Enter Parameter Filter Name  : ").strip()
            if not f_name:
                break 
            f_val = input(f"[{filter_counter}] Enter Parameter Filter Value : ").strip()
            filter_params[f_name] = f_val
            filter_counter += 1

        print("\n>>> EMAIL SETTINGS (PIC is automatically assigned to system)")
        email_to = input("[*] Enter 'To' Recipients (Comma separated) : ").strip()
        email_cc = input("[*] Enter 'CC' Emails (Comma separated)     : ").strip()
        email_bcc = input("[*] Enter 'BCC' Emails (Comma separated)    : ").strip()
        email_subject = input("[*] Enter Email Subject                     : ").strip()

        print("\n=======================================================================")
        print("[SYSTEM] Sending request to BigQuery Queue...")
        
        # --- BLOCK 2: BIGQUERY LOAD JOB (FREE TIER COMPLIANT) ---
        client = bigquery.Client(project=PROJECT_ID)
        
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
            "created_at": datetime.now(timezone.utc).isoformat() # Diperbarui agar tidak muncul DeprecationWarning
        }]

        # Menggunakan mode Load Job agar gratis dan diizinkan di akun Sandbox
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        )
        
        load_job = client.load_table_from_json(row_to_insert, TABLE_ID, job_config=job_config)
        load_job.result()  # Menunggu proses selesai

        print("[SUCCESS] Your report request has been queued successfully!")
        print("[INFO] The engine will process and send your email shortly.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] System failure occurred: {e}")

    finally:
        input("\nPress ENTER to close this window...")

if __name__ == "__main__":
    main()