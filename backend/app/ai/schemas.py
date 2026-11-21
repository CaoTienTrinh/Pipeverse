from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class UIContextState(BaseModel):
    """Ngữ cảnh hiện tại trên giao diện 3D/2D mà người dùng đang quan sát."""
    user_role: Literal["VIEWER", "OPERATOR"] = Field(
        default="VIEWER", description="Vai trò vận hành hiện tại theo mô hình Zero-Admin"
    )
    active_view: Literal["GLOBAL_3D", "DAG_DETAIL", "LOG_VIEWER"] = Field(
        default="GLOBAL_3D", description="Màn hình người dùng đang mở"
    )
    selected_dag_id: Optional[str] = Field(
        default=None, description="ID của DAG đang được chọn trên đồ thị"
    )
    selected_run_id: Optional[str] = Field(
        default=None, description="ID lần chạy (execution/run_id) đang kiểm tra"
    )
    selected_task_id: Optional[str] = Field(
        default=None, description="ID của Task node đang được click chọn"
    )
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Thông tin mở rộng từ UI (bộ lọc trạng thái, cụm node đang khoanh vùng, góc nhìn...)"
    )

class AIRequestPayload(BaseModel):
    """Dữ liệu đầu vào gửi tới AI Gateway (C1)."""
    session_id: str = Field(..., description="Mã phiên hội thoại")
    user_query: str = Field(..., description="Câu hỏi hoặc yêu cầu phân tích của người dùng")
    ui_context: UIContextState = Field(default_factory=UIContextState)
    operational_extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dữ liệu vận hành động từ Backend/Airflow (try_number, duration, queue, trigger_rule, conf...)"
    )

class EvidenceItem(BaseModel):
    """Bằng chứng cụ thể trích xuất từ hệ thống để chống ảo giác (Hallucination)."""
    source_type: Literal["TASK_LOG", "DAG_TOPOLOGY", "RUN_HISTORY", "AIRFLOW_CONFIG"]
    dag_id: str
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    snippet: str = Field(..., description="Trích dẫn nguyên văn từ log hoặc metadata thực tế")

class UICommand(BaseModel):
    """Lệnh điều khiển tương tác ngược lại lên không gian 3D/2D của Frontend."""
    command_type: Literal["FOCUS_NODE", "HIGHLIGHT_PATH", "OPEN_LOG_VIEWER", "NONE"] = "NONE"
    target_dag_id: Optional[str] = None
    target_task_ids: List[str] = Field(default_factory=list)

class SuggestedAction(BaseModel):
    """Đề xuất thao tác vận hành cho Operator xác nhận (Human-in-the-loop)."""
    action_type: Literal["CLEAR_TASK", "TRIGGER_DAG", "PAUSE_DAG", "MARK_SUCCESS"]
    dag_id: str
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    reason: str = Field(..., description="Lý do đề xuất hành động này")
    required_params: Dict[str, Any] = Field(
        default_factory=dict, description="Các tham số đã có sẵn"
    )
    missing_params: List[str] = Field(
        default_factory=list, description="Danh sách tham số còn thiếu yêu cầu Operator nhập"
    )
    requires_operator_auth: bool = Field(
        default=True, description="Bắt buộc nâng quyền OPERATOR trước khi thực thi"
    )

class AIResponsePayload(BaseModel):
    """Hợp đồng dữ liệu đầu ra chuẩn từ AI Layer trả về Backend/Frontend."""
    session_id: str
    confidence_level: Literal["CONFIDENT", "UNCERTAIN"] = Field(
        ..., description="UNCERTAIN khi thiếu log/bằng chứng thực tế (BR-UC10-003)"
    )
    summary: str = Field(..., description="Tóm tắt ngắn gọn kết luận chính")
    root_cause_analysis: str = Field(..., description="Phân tích chi tiết nguyên nhân gốc rễ")
    impacted_downstream: List[str] = Field(
        default_factory=list, description="Danh sách các task/DAG downstream bị ảnh hưởng dây chuyền"
    )
    evidences: List[EvidenceItem] = Field(
        default_factory=list, description="Danh sách bằng chứng đối chiếu được"
    )
    ui_command: UICommand = Field(default_factory=UICommand)
    suggested_action: Optional[SuggestedAction] = None
    tools_invoked: List[str] = Field(
        default_factory=list, description="Danh sách các tool AI đã chủ động gọi để truy vấn ngữ cảnh"
    )