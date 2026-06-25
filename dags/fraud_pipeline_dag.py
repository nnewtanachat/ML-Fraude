"""
Fraud ML Pipeline DAG — Retrain model weekly

Schedule: ทุกวันอาทิตย์ ตี 2
Flow: tune → train → batch_predict → restart_scorer
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

IMAGE = "{{ var.value.fraud_image | default('ml-fraud:latest') }}"
NAMESPACE = "fraud-detection"

default_args = {
    "owner": "fraud-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="fraud_ml_pipeline",
    default_args=default_args,
    description="Weekly retrain fraud detection model",
    schedule="0 2 * * 0",  # ทุกอาทิตย์ ตี 2
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "fraud", "retrain"],
)

# ===== Task 1: Hyperparameter Tuning =====
tune = KubernetesPodOperator(
    task_id="tune",
    name="fraud-tune",
    namespace=NAMESPACE,
    image=IMAGE,
    cmds=["python", "-m", "src.pipeline.tune"],
    env_from=[
        {"secretRef": {"name": "fraud-secrets"}},
        {"configMapRef": {"name": "fraud-config"}},
    ],
    resources={
        "requests": {"memory": "1Gi", "cpu": "500m"},
        "limits": {"memory": "4Gi", "cpu": "2000m"},
    },
    is_delete_operator_pod=True,  # เสร็จแล้วลบ pod
    get_logs=True,
    dag=dag,
)

# ===== Task 2: Train Model =====
train = KubernetesPodOperator(
    task_id="train",
    name="fraud-train",
    namespace=NAMESPACE,
    image=IMAGE,
    cmds=["python", "-m", "src.pipeline.train"],
    env_from=[
        {"secretRef": {"name": "fraud-secrets"}},
        {"configMapRef": {"name": "fraud-config"}},
    ],
    resources={
        "requests": {"memory": "1Gi", "cpu": "500m"},
        "limits": {"memory": "2Gi", "cpu": "1000m"},
    },
    is_delete_operator_pod=True,
    get_logs=True,
    dag=dag,
)

# ===== Task 3: Batch Predict =====
batch_predict = KubernetesPodOperator(
    task_id="batch_predict",
    name="fraud-batch-predict",
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

# ===== Dependencies =====
tune >> train >> batch_predict
