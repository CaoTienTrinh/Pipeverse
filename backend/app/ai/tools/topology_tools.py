import json
from app.ai.context.retriever import BackendContextRetriever


def get_dag_dependencies(dag_id: str, task_id: str | None = None) -> str:
    """
    Lấy cấu trúc phụ thuộc (upstream/downstream) của DAG hoặc của một Task cụ thể.
    Dùng để truy vết nguyên nhân gốc rễ từ upstream và đánh giá vùng ảnh hưởng downstream.
    """
    retriever = BackendContextRetriever()
    dag_data = retriever.get_dag_topology(dag_id)

    if "error" in dag_data:
        return json.dumps(dag_data, ensure_ascii=False)

    tasks = dag_data.get("tasks", {})
    if task_id:
        task_info = tasks.get(task_id)
        if not task_info:
            return json.dumps(
                {"error": f"Task '{task_id}' không tồn tại trong DAG '{dag_id}'."},
                ensure_ascii=False,
            )
        result = {
            "dag_id": dag_id,
            "task_id": task_id,
            "operator": task_info.get("operator"),
            "upstream_task_ids": task_info.get("upstream_task_ids", []),
            "downstream_task_ids": task_info.get("downstream_task_ids", []),
        }
        return json.dumps(result, ensure_ascii=False)

    return json.dumps(
        {
            "dag_id": dag_id,
            "description": dag_data.get("description"),
            "is_paused": dag_data.get("is_paused"),
            "tasks": tasks,
        },
        ensure_ascii=False,
    )