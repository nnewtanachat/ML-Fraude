"""
Drift Monitor DAG — ตรวจ model drift ทุกวัน

Schedule: ทุกวัน 7 โมงเช้า
Flow: check_drift → decide → retrain (ถ้า drift detected)
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.operators.python import ShortCircuitOperator

IMAGE = "{{ var.value.fraud_image | default('ml-fraud:latest') }}"
NAMESPACE = "fraud-detection"

default_args = {
    "owner": "mlops-team",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="drift_monitor",
    default_args=default_args,
    description="Daily model drift check — trigger retrain if needed",
    schedule="0 7 * * *",  # ทุกวัน 7 โมง
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "fraud", "monitoring", "drift"],
)

# ===== Task 1: Check Drift =====
check_drift = KubernetesPodOperator(
    task_id="check_drift",
    name="drift-check",
    namespace=NAMESPACE,
    image=IMAGE,
    cmds=["python", "-m", "src.monitoring.drift_monitor"],
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
    do_xcom_push=True,
    dag=dag,
)


def should_retrain(**context) -> bool:
    """Check XCom output from drift check — retrain only if drift detected."""
    ti = context["ti"]
    output = ti.xcom_pull(task_ids="check_drift")
    if not output:
        return False
    try:
        result = json.loads(output) if isinstance(output, str) else output
        return result.get("needs_retrain", False)
    except (json.JSONDecodeError, TypeError):
        return False


# ===== Task 2: Decide whether to retrain =====
decide = ShortCircuitOperator(
    task_id="decide_retrain",
    python_callable=should_retrain,
    dag=dag,
)

# ===== Task 3: Retrain (only if drift detected) =====
retrain = KubernetesPodOperator(
    task_id="retrain_model",
    name="retrain-after-drift",
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

check_drift >> decide >> retrain
