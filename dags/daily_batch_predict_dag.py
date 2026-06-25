"""
Daily Batch Prediction DAG

Schedule: ทุกวัน 6 โมงเช้า
Flow: batch_predict (กวาด transactions ที่ยังไม่ถูก predict)
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

IMAGE = "{{ var.value.fraud_image | default('ml-fraud:latest') }}"
NAMESPACE = "fraud-detection"

default_args = {
    "owner": "fraud-team",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}

dag = DAG(
    dag_id="daily_batch_predict",
    default_args=default_args,
    description="Score new transactions that Kafka missed",
    schedule="0 6 * * *",  # ทุกวัน 6 โมง
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "fraud", "daily"],
)

batch_predict = KubernetesPodOperator(
    task_id="batch_predict",
    name="fraud-daily-predict",
    namespace=NAMESPACE,
    image=IMAGE,
    cmds=["python", "-m", "src.monitoring.batch_prediction"],
    env_from=[
        {"secretRef": {"name": "fraud-secrets"}},
        {"configMapRef": {"name": "fraud-config"}},
    ],
    resources={
        "requests": {"memory": "512Mi", "cpu": "250m"},
        "limits": {"memory": "1Gi", "cpu": "500m"},
    },
    is_delete_operator_pod=True,
    get_logs=True,
    dag=dag,
)
