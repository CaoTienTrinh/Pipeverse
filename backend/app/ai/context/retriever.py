import os
from typing import Any, Dict, List, Optional

# Cờ chuyển đổi giữa Sandbox giả lập (Windows dev) và Backend Service thật
USE_MOCK_SANDBOX = os.getenv("USE_MOCK_SANDBOX", "true").lower() == "true"


class BackendContextRetriever:
    """
    Lớp trung gian truy xuất dữ liệu từ Backend Services / Airflow.
    Hỗ trợ chạy Sandbox độc lập khi Backend chưa hoàn thiện API.
    """

    def __init__(self, use_mock: bool = USE_MOCK_SANDBOX):
        self.use_mock = use_mock
        self._mock_db = self._init_sandbox_data()

    def _init_sandbox_data(self) -> Dict[str, Any]:
        """Dữ liệu giả lập kịch bản lỗi dây chuyền (Cascading Failure) trong Airflow."""
        return {
            "dags": {
                "etl_daily_sales": {
                    "dag_id": "etl_daily_sales",
                    "description": "Pipeline tổng hợp doanh thu bán hàng hằng ngày",
                    "is_paused": False,
                    "schedule_interval": "0 0 * * *",
                    "tasks": {
                        "extract_orders": {
                            "task_id": "extract_orders",
                            "operator": "PythonOperator",
                            "upstream_task_ids": [],
                            "downstream_task_ids": ["transform_revenue"],
                        },
                        "transform_revenue": {
                            "task_id": "transform_revenue",
                            "operator": "SparkSubmitOperator",
                            "upstream_task_ids": ["extract_orders"],
                            "downstream_task_ids": ["load_warehouse"],
                        },
                        "load_warehouse": {
                            "task_id": "load_warehouse",
                            "operator": "PostgresOperator",
                            "upstream_task_ids": ["transform_revenue"],
                            "downstream_task_ids": [],
                        },
                    },
                }
            },
            "runs": {
                "etl_daily_sales": [
                    {
                        "run_id": "scheduled__2026-11-21T00:00:00",
                        "state": "failed",
                        "execution_date": "2026-11-21T00:00:00Z",
                        "task_instances": {
                            "extract_orders": {
                                "state": "failed",
                                "try_number": 3,
                                "duration_sec": 45.2,
                                "log": (
                                    "[2026-11-21 00:01:12] INFO - Starting extraction from Partner Orders API...\n"
                                    "[2026-11-21 00:01:40] WARNING - Rate limit approaching (remaining: 2)\n"
                                    "[2026-11-21 00:01:57] ERROR - HTTPError 429: Too Many Requests from https://api.partner.vn/v2/orders\n"
                                    "[2026-11-21 00:01:57] ERROR - Task extract_orders failed after 3 retries. Output parquet was not generated."
                                ),
                            },
                            "transform_revenue": {
                                "state": "failed",
                                "try_number": 1,
                                "duration_sec": 4.1,
                                "log": (
                                    "[2026-11-21 00:02:05] INFO - Reading input dataset s3://pipeverse-raw/orders/2026-11-21.parquet\n"
                                    "[2026-11-21 00:02:09] ERROR - FileNotFoundError: Path does not exist: s3://pipeverse-raw/orders/2026-11-21.parquet\n"
                                    "[2026-11-21 00:02:09] ERROR - Spark job aborted with exit code 1."
                                ),
                            },
                            "load_warehouse": {
                                "state": "upstream_failed",
                                "try_number": 0,
                                "duration_sec": 0.0,
                                "log": "Task did not run because upstream task 'transform_revenue' failed.",
                            },
                        },
                    },
                    {
                        "run_id": "scheduled__2026-11-20T00:00:00",
                        "state": "success",
                        "execution_date": "2026-11-20T00:00:00Z",
                        "task_instances": {
                            "extract_orders": {"state": "success", "try_number": 1, "duration_sec": 38.0, "log": "INFO - Extracted 14,200 orders successfully."},
                            "transform_revenue": {"state": "success", "try_number": 1, "duration_sec": 19.5, "log": "INFO - Revenue aggregation completed."},
                            "load_warehouse": {"state": "success", "try_number": 1, "duration_sec": 11.2, "log": "INFO - Loaded 14,200 rows into fact_revenue."},
                        },
                    },
                ]
            },
        }

    def get_dag_topology(self, dag_id: str) -> Dict[str, Any]:
        """Lấy cấu trúc đồ thị (upstream/downstream) của một DAG."""
        if self.use_mock:
            dag = self._mock_db["dags"].get(dag_id)
            if not dag:
                return {"error": f"DAG '{dag_id}' not found in sandbox."}
            return dag
        # TODO: Nối vào backend.app.services.dag_service khi Backend hoàn thiện
        raise NotImplementedError("Real backend service integration pending.")

    def get_recent_runs(self, dag_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Lấy danh sách các lần chạy gần nhất của DAG để đối chiếu lịch sử."""
        if self.use_mock:
            runs = self._mock_db["runs"].get(dag_id, [])
            return [
                {
                    "run_id": r["run_id"],
                    "state": r["state"],
                    "execution_date": r["execution_date"],
                    "task_states": {k: v["state"] for k, v in r["task_instances"].items()},
                }
                for r in runs[:limit]
            ]
        raise NotImplementedError("Real backend service integration pending.")

    def get_task_instance_detail(
        self, dag_id: str, task_id: str, run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy trạng thái chi tiết và log thực thi của một task trong lần chạy cụ thể."""
        if self.use_mock:
            runs = self._mock_db["runs"].get(dag_id, [])
            if not runs:
                return {"error": f"No runs found for DAG '{dag_id}'."}

            target_run = runs[0] if not run_id else next((r for r in runs if r["run_id"] == run_id), None)
            if not target_run:
                return {"error": f"Run '{run_id}' not found for DAG '{dag_id}'."}

            task_info = target_run["task_instances"].get(task_id)
            if not task_info:
                return {"error": f"Task '{task_id}' not found in run '{target_run['run_id']}'."}

            return {
                "dag_id": dag_id,
                "run_id": target_run["run_id"],
                "task_id": task_id,
                **task_info,
            }
        raise NotImplementedError("Real backend service integration pending.")