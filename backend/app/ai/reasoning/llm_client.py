import json
import os
from typing import Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """
    Client giao tiếp LLM (chuẩn OpenAI/DeepSeek).
    Tự động chạy chế độ Offline Mock nếu chưa cấu hình DEEPSEEK_API_KEY thật trong .env.
    """

    def __init__(self):
        raw_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        # Bỏ qua nếu là chuỗi mẫu placeholder trong .env
        is_placeholder = any(
            word in raw_key.lower() for word in ["your", "placeholder", "o-day", "xxx"]
        )
        self.api_key = "" if is_placeholder else raw_key
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.client = (
            OpenAI(api_key=self.api_key, base_url=self.base_url)
            if self.api_key
            else None
        )

    def chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if self.client:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0.1,
            )
            msg = response.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in (msg.tool_calls or [])
                ],
            }

        return self._simulate_offline_reasoning(messages)

    def _simulate_offline_reasoning(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        if len(tool_msgs) == 0:
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "get_dag_dependencies",
                        "arguments": json.dumps({"dag_id": "etl_daily_sales", "task_id": "transform_revenue"}),
                    },
                    {
                        "id": "call_2",
                        "name": "fetch_task_execution_log",
                        "arguments": json.dumps({"dag_id": "etl_daily_sales", "task_id": "transform_revenue"}),
                    },
                ],
            }
        if len(tool_msgs) == 2:
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_3",
                        "name": "fetch_task_execution_log",
                        "arguments": json.dumps({"dag_id": "etl_daily_sales", "task_id": "extract_orders"}),
                    }
                ],
            }

        final_json = {
            "root_cause_task_id": "extract_orders",
            "summary": "Task 'transform_revenue' lỗi dây chuyền do upstream 'extract_orders' bị API đối tác chặn giới hạn (HTTP 429).",
            "root_cause_analysis": (
                "1. Task 'extract_orders' gọi API đối tác thất bại sau 3 lần thử với lỗi HTTPError 429: Too Many Requests nên không xuất ra file parquet.\n"
                "2. Task 'transform_revenue' không tìm thấy file đầu vào s3://pipeverse-raw/orders/2026-11-21.parquet (FileNotFoundError).\n"
                "3. Task downstream 'load_warehouse' chuyển sang trạng thái upstream_failed."
            ),
            "impacted_downstream": ["load_warehouse"],
            "evidences": [
                {
                    "source_type": "TASK_LOG",
                    "dag_id": "etl_daily_sales",
                    "task_id": "extract_orders",
                    "run_id": "scheduled__2026-11-21T00:00:00",
                    "snippet": "ERROR - HTTPError 429: Too Many Requests from https://api.partner.vn/v2/orders",
                },
                {
                    "source_type": "TASK_LOG",
                    "dag_id": "etl_daily_sales",
                    "task_id": "transform_revenue",
                    "run_id": "scheduled__2026-11-21T00:00:00",
                    "snippet": "ERROR - FileNotFoundError: Path does not exist: s3://pipeverse-raw/orders/2026-11-21.parquet",
                },
            ],
        }
        return {"content": json.dumps(final_json, ensure_ascii=False), "tool_calls": []}