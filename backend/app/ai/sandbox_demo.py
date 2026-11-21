import sys
sys.stdout.reconfigure(encoding="utf-8")

from app.ai.schemas import AIRequestPayload, UIContextState
from app.ai.gateway import AIGateway


def main():
    req = AIRequestPayload(
        session_id="sess-win-sandbox-001",
        user_query="Tại sao task transform_revenue bị lỗi? Hãy tìm nguyên nhân gốc rễ và vùng ảnh hưởng.",
        ui_context=UIContextState(
            user_role="VIEWER",
            active_view="DAG_DETAIL",
            selected_dag_id="etl_daily_sales",
            selected_task_id="transform_revenue",
            selected_run_id="scheduled__2026-11-21T00:00:00",
        ),
        operational_extra={"try_number": 1, "queue": "spark_default"},
    )

    gateway = AIGateway()
    res = gateway.process_request(req)
    print(res.model_dump_json(indent=2))


if __name__ == "__main__":
    main()