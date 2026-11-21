import json
from typing import Optional
from app.ai.context.retriever import BackendContextRetriever


def fetch_task_execution_log(
    dag_id: str, task_id: str, run_id: Optional[str] = None
) -> str:
    """
    Lấy trạng thái thực thi, số lần retry và log chi tiết của một Task cụ thể.
    """
    retriever = BackendContextRetriever()
    detail = retriever.get_task_instance_detail(
        dag_id=dag_id, task_id=task_id, run_id=run_id
    )
    return json.dumps(detail, ensure_ascii=False)


def check_recent_dag_runs(dag_id: str, limit: int = 5) -> str:
    """
    Kiểm tra lịch sử các lần chạy gần nhất của DAG để xem lỗi mới phát sinh hay lặp lại.
    """
    retriever = BackendContextRetriever()
    runs = retriever.get_recent_runs(dag_id=dag_id, limit=limit)
    return json.dumps(
        {"dag_id": dag_id, "recent_runs": runs},
        ensure_ascii=False,
    )