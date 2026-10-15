from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Pengaturan argumen dasar pipeline
default_args = {
    'owner': 'raka_arrayan',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Definisi DAG Orchestration
with DAG(
    dag_id='dblast_automation_pipeline',
    default_args=default_args,
    description='Pipeline to trigger DBlast Engine every 7 minutes for pending Tableau requests',
    schedule_interval='*/7 * * * *',  # Berjalan otomatis setiap 7 menit
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1                 # Mencegah tabrakan eksekusi ganda
) as dag:

    # Perintah untuk menjalankan engine di dalam environment Airflow
    run_engine_task = BashOperator(
        task_id='run_dblast_backend_engine',
        bash_command='python /opt/airflow/dblast/dblast_engine.py',
    )

    run_engine_task