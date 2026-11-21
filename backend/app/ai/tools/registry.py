import json
from typing import Any, Callable, Dict, List
from app.ai.tools.topology_tools import get_dag_dependencies
from app.ai.tools.execution_tools import (
    fetch_task_execution_log,
    check_recent_dag_runs,
)

# Danh sách hàm Python thực tế ánh xạ theo tên tool
TOOL_FUNCTIONS: Dict[str, Callable[..., str]] = {
    "get_dag_dependencies": get_dag_dependencies,
    "fetch_task_execution_log": fetch_task_execution_log,
    "check_recent_dag_runs": check_recent_dag_runs,
}

# Định nghĩa chuẩn OpenAI / DeepSeek Function Calling Schema
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_dag_dependencies",
            "description": (
                "Truy vấn cấu trúc đồ thị phụ thuộc (upstream và downstream tasks) của một DAG "
                "hoặc một Task cụ thể để tìm nguồn gốc lỗi dây chuyền và vùng ảnh hưởng."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dag_id": {
                        "type": "string",
                        "description": "Mã định danh của DAG (ví dụ: etl_daily_sales)",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Mã định danh của Task cần xem upstream/downstream (tùy chọn)",
                    },
                },
                "required": ["dag_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_task_execution_log",
            "description": (
                "Lấy log thực thi chi tiết, trạng thái (failed/success/upstream_failed) và số lần retry "
                "của một Task cụ thể trong một lần chạy (run_id)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "Mã định danh của DAG"},
                    "task_id": {"type": "string", "description": "Mã định danh của Task"},
                    "run_id": {
                        "type": "string",
                        "description": "Mã lần chạy cụ thể (bỏ trống sẽ lấy lần chạy gần nhất)",
                    },
                },
                "required": ["dag_id", "task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_recent_dag_runs",
            "description": (
                "Lấy lịch sử các lần chạy gần nhất của một DAG để so sánh trạng thái giữa các lần chạy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "Mã định danh của DAG"},
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng lần chạy gần nhất cần lấy (mặc định 5)",
                        "default": 5,
                    },
                },
                "required": ["dag_id"],
            },
        },
    },
]


def execute_tool_call(tool_name: str, arguments_json: str) -> str:
    """Thực thi tool do LLM yêu cầu và trả kết quả chuỗi JSON về cho vòng lặp suy luận."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return json.dumps(
            {"error": f"Tool '{tool_name}' chưa được đăng ký trong hệ thống."},
            ensure_ascii=False,
        )
    try:
        args = json.loads(arguments_json) if arguments_json else {}
        return func(**args)
    except Exception as exc:
        return json.dumps(
            {"error": f"Lỗi khi thực thi tool '{tool_name}': {str(exc)}"},
            ensure_ascii=False,
        )