import os
import json
import requests
import openpyxl
from openpyxl.drawing.image import Image
from io import BytesIO
import smtplib
from email.message import EmailMessage
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# Gunakan .gcloud_adc.json jika GOOGLE_APPLICATION_CREDENTIALS belum ada
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _adc_file = os.path.join(_script_dir, ".gcloud_adc.json")
    if os.path.exists(_adc_file):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _adc_file

# ==============================================================================
# 1. SYSTEM CONFIGURATION (GMAIL EDITION FOR LOCAL TESTING)
# ==============================================================================
SENDER_EMAIL = os.getenv("SENDER_EMAIL")       
APP_PASSWORD = os.getenv("APP_PASSWORD")      
PIC_EMAIL = os.getenv("PIC_EMAIL")

# Pastikan ID Proyek dan Dataset sudah sesuai dengan milik Anda
PROJECT_ID = "project-raka-485012"
TABLE_ID = "project-raka-485012.dblast_data.dblast_queue"

# ==============================================================================
# 2. DBLAST HTML TEMPLATES
# ==============================================================================
def get_main_html_template(sheet_name, include_image=True):
    image_html = ""
    if include_image:
        image_html = """
        <div>
            <img src="cid:dashboard_image" alt="Dashboard Image" style="max-width: 100%; border: 1px solid #ddd;">
        </div>
        <br><br>
        """

    html = f"""
    <html>
        <body style="font-family: Calibri, Verdana; font-size: 14px; color: black;">
            <p>Dear All,</p>
            <p>Please find the following dashboard will be blast to recipients as per your request,</p>
            
            <div style="background-color:#F1F1F1; font-size:18px; color:black; font-weight:bold; padding:10px; text-align:center;">
                {sheet_name}
            </div>
            <br>
            
            {image_html}
            
            <div style="font-family: Calibri, Verdana; font-size: 14px;">
                <strong>If you have an inquiry, please contact :</strong>
                <ul>
                    <li><a href="mailto:{PIC_EMAIL}">{PIC_EMAIL}</a></li>
                </ul>
            </div>
            <br>
            
            <div style="font-family: Calibri, Verdana; font-size: 16px;">
                <strong>MIS &amp; Business Finance Group</strong>
            </div>
            <div style="font-family: Calibri, Verdana; font-size: 16px;">
                Strategy &amp; Finance Directorate
            </div>
            <div style="font-family: Calibri, Verdana; font-size: 14px; color: Gray;">
                PT Bank CIMB Niaga Tbk.
            </div>
        </body>
    </html>
    """
    return html

def get_notification_html_template(report_key):
    html = f"""
    <html>
        <body style="font-family: Calibri, Verdana; font-size: 14px; color: black;">
            <p>Dear <a href="mailto:{PIC_EMAIL}">{PIC_EMAIL}</a>,</p>
            <br>
            <p>Register Report Key <strong>{report_key}</strong> to <span style="background-color: yellow;">DashBlast</span> successfully!!!</p>
            <br>
            <div style="font-family: Calibri, Verdana; font-size: 14px;">
                <strong>If you have an inquiry, please contact :</strong>
                <ul>
                    <li><a href="mailto:{PIC_EMAIL}">{PIC_EMAIL}</a></li>
                </ul>
            </div>
            <br>
            <div style="font-family: Calibri, Verdana; font-size: 16px;">
                <strong>MIS &amp; Business Finance Group</strong>
            </div>
            <div style="font-family: Calibri, Verdana; font-size: 16px;">
                Strategy &amp; Finance Directorate
            </div>
            <div style="font-family: Calibri, Verdana; font-size: 14px; color: Gray;">
                PT Bank CIMB Niaga Tbk.
            </div>
        </body>
    </html>
    """
    return html

PROCESSED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_tasks.txt")

def get_processed_tasks():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_task_as_processed(task_id):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{task_id}\n")

# ==============================================================================
# 3. MAIN ENGINE LOGIC
# ==============================================================================
def main():
    print("[SYSTEM] DBlast Backend Engine Started. Checking BigQuery for PENDING tasks...")
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
        SELECT * FROM `{TABLE_ID}`
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
    """
    query_job = client.query(query)
    pending_tasks = query_job.result()

    task_count = pending_tasks.total_rows
    if task_count == 0:
        print("[SYSTEM] No pending tasks found. Exiting gracefully.")
        return
        
    print(f"[SYSTEM] Found {task_count} pending tasks. Starting process...")

    processed_tasks = get_processed_tasks()

    for row in pending_tasks:
        if str(row.id) in processed_tasks:
            print(f"[SYSTEM] Task ID {row.id} already processed. Skipping.")
            continue

        try:
            print(f"\n=======================================================================")
            print(f">>> Processing Task ID: {row.id} (Key: {row.report_key})")
            
            output_option = str(row.output_option)
            workbook_url = row.workbook_url
            filter_params = json.loads(row.filter_params) if row.filter_params else {}
            
            sheet_name = "Dashboard Report"
            if workbook_url:
                sheet_name = workbook_url.split('/')[-1].replace('%20', ' ')
            
            base_url = f"https://public.tableau.com/views/{workbook_url}"
            params = {"?:showVizHome": "no", "&:resolution": "high"}
            params.update(filter_params)
            
            needs_body_image = output_option in ['1', '2', '3', '4', '9']
            needs_excel      = output_option in ['2', '4', '5', '6']
            needs_pdf        = output_option in ['3', '4', '6', '7']
            needs_local_file = output_option in ['8', '9']
            
            img_data, pdf_data, excel_data, local_data = None, None, None, None
            local_filename = ""
            current_time = datetime.now().strftime("%Y%m%d_%H%M")
            base_filename = row.custom_tableau_name if row.custom_tableau_name else f"{sheet_name}_{current_time}"
            
            if needs_body_image or needs_excel:
                print("[TABLEAU] Fetching Dashboard Image... ", end="")
                response_img = requests.get(f"{base_url}.png", params=params)
                if response_img.status_code == 200:
                    img_data = response_img.content
                    print("[SUCCESS]")
                else:
                    raise Exception(f"HTTP {response_img.status_code} fetching Image")
                
            if needs_excel:
                print("[TABLEAU] Generating Excel File...    ", end="")
                img_stream = BytesIO(img_data)
                wb = openpyxl.Workbook()
                sheet = wb.active
                sheet.title = "Dashboard Report"
                sheet['B2'] = f"Report: {sheet_name}"
                
                row_idx = 3
                for k, v in filter_params.items():
                    sheet[f'B{row_idx}'] = f"Filter ({k}): {v}"
                    row_idx += 1
                    
                sheet['B2'].font = openpyxl.styles.Font(bold=True, size=14)
                img_xl = Image(img_stream)
                sheet.add_image(img_xl, f'B{row_idx + 1}') 
                
                excel_stream = BytesIO()
                wb.save(excel_stream)
                excel_data = excel_stream.getvalue()
                print("[SUCCESS]")
                
            if needs_pdf:
                print("[TABLEAU] Fetching PDF Document...    ", end="")
                response_pdf = requests.get(f"{base_url}.pdf", params=params)
                if response_pdf.status_code == 200:
                    pdf_data = response_pdf.content
                    print("[SUCCESS]")
                else:
                    raise Exception(f"HTTP {response_pdf.status_code} fetching PDF")

            if needs_local_file:
                print("[SYSTEM]  Fetching Local File...      ", end="")
                with open(row.local_file_path, 'rb') as f:
                    local_data = f.read()
                original_name = os.path.basename(row.local_file_path)
                name_only, ext = os.path.splitext(original_name)
                local_filename = f"{row.custom_local_name}{ext}" if row.custom_local_name else original_name
                print("[SUCCESS]")

            print("[EMAIL]   Rendering and Attaching...  ", end="")
            msg_main = EmailMessage()
            msg_main['Subject'] = row.email_subject
            msg_main['From'] = SENDER_EMAIL
            msg_main['To'] = row.email_to
            if row.email_cc: msg_main['Cc'] = row.email_cc
            if row.email_bcc: msg_main['Bcc'] = row.email_bcc
            
            html_body = get_main_html_template(sheet_name, include_image=needs_body_image)
            msg_main.set_content("Please enable HTML viewer in your email client to see this report.")
            msg_main.add_alternative(html_body, subtype='html')
            
            if needs_body_image and img_data:
                msg_main.add_attachment(img_data, maintype='image', subtype='png', cid="<dashboard_image>", filename=f"{base_filename}.png")
            if excel_data:
                msg_main.add_attachment(excel_data, maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{base_filename}.xlsx")
            if pdf_data:
                msg_main.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f"{base_filename}.pdf")
            if local_data:
                subtype = 'pdf' if local_filename.lower().endswith('.pdf') else 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' if local_filename.lower().endswith('.xlsx') else 'octet-stream'
                msg_main.add_attachment(local_data, maintype='application', subtype=subtype, filename=local_filename)
            print("[SUCCESS]")

            print("[EMAIL]   Sending via Gmail SMTP...   ", end="")
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(SENDER_EMAIL, APP_PASSWORD)
                smtp.send_message(msg_main)
                
                msg_notif = EmailMessage()
                msg_notif['Subject'] = f"MIS & BFG Info: DashBlast Register - {sheet_name}"
                msg_notif['From'] = SENDER_EMAIL
                msg_notif['To'] = PIC_EMAIL
                html_notif = get_notification_html_template(row.report_key)
                msg_notif.set_content("DashBlast Registration Notification")
                msg_notif.add_alternative(html_notif, subtype='html')
                
                smtp.send_message(msg_notif)
            print("[SUCCESS]")
            
            # Catat ID task ke file log lokal agar tidak pernah dikirim dobel
            mark_task_as_processed(str(row.id))
            processed_tasks.add(str(row.id))

            # [PERUBAHAN]: Penanganan khusus untuk batasan UPDATE di Free Tier
            print("[SYSTEM]  Updating BigQuery status... ", end="")
            try:
                update_query = f"""
                    UPDATE `{TABLE_ID}`
                    SET status = 'DONE'
                    WHERE id = '{row.id}'
                """
                client.query(update_query).result()
                print("[SUCCESS]")
            except Exception as update_err:
                if "DML queries are not allowed in the free tier" in str(update_err):
                    print("[SKIPPED] (Free Tier restriction: Cannot UPDATE to 'DONE', but Email was sent!)")
                else:
                    raise update_err
            
        except Exception as e:
            print(f"\n[FAILED] Error processing Task {row.id}: {e}")
            try:
                fail_query = f"UPDATE `{TABLE_ID}` SET status = 'FAILED' WHERE id = '{row.id}'"
                client.query(fail_query).result()
            except Exception:
                print("          -> (Free Tier restriction: Cannot UPDATE status to 'FAILED' either)")

    print("\n[COMPLETED] All PENDING tasks have been processed.")

if __name__ == "__main__":
    main()