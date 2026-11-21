from typing import List, Optional, Tuple
from app.ai.schemas import (
    SuggestedAction,
    UICommand,
    UIContextState,
)


class ActionPlanner:
    """
    Bộ lập kế hoạch hành động & điều khiển giao diện (C6).
    Chuyển đổi kết quả chẩn đoán của AI thành lệnh tương tác 3D và đề xuất thao tác an toàn.
    """

    def plan(
        self,
        ui_context: UIContextState,
        confidence_level: str,
        target_dag_id: Optional[str],
        root_cause_task_id: Optional[str],
        impacted_downstream: List[str],
        action_hint: Optional[str] = None,
    ) -> Tuple[UICommand, Optional[SuggestedAction]]:
        dag_id = target_dag_id or ui_context.selected_dag_id
        current_task = ui_context.selected_task_id

        # 1. Xây dựng lệnh điều khiển không gian 3D (UICommand)
        ui_command = self._build_ui_command(
            dag_id=dag_id,
            root_cause_task_id=root_cause_task_id,
            current_task_id=current_task,
            impacted_downstream=impacted_downstream,
        )

        # 2. Xây dựng đề xuất thao tác vận hành (SuggestedAction)
        # Chỉ đề xuất thao tác can thiệp hệ thống khi đủ bằng chứng (CONFIDENT)
        if confidence_level != "CONFIDENT" or not dag_id:
            return ui_command, None

        suggested_action = self._build_suggested_action(
            ui_context=ui_context,
            dag_id=dag_id,
            target_task_id=root_cause_task_id or current_task,
            action_hint=action_hint,
        )

        return ui_command, suggested_action

    def _build_ui_command(
        self,
        dag_id: Optional[str],
        root_cause_task_id: Optional[str],
        current_task_id: Optional[str],
        impacted_downstream: List[str],
    ) -> UICommand:
        if not dag_id:
            return UICommand(command_type="NONE")

        # Gom danh sách node theo thứ tự truyền lỗi: Root Cause -> Current -> Downstream
        path_nodes: List[str] = []
        for node in [root_cause_task_id, current_task_id, *impacted_downstream]:
            if node and node not in path_nodes:
                path_nodes.append(node)

        if len(path_nodes) >= 2:
            return UICommand(
                command_type="HIGHLIGHT_PATH",
                target_dag_id=dag_id,
                target_task_ids=path_nodes,
            )

        if len(path_nodes) == 1:
            return UICommand(
                command_type="FOCUS_NODE",
                target_dag_id=dag_id,
                target_task_ids=path_nodes,
            )

        return UICommand(command_type="NONE")

    def _build_suggested_action(
        self,
        ui_context: UIContextState,
        dag_id: str,
        target_task_id: Optional[str],
        action_hint: Optional[str],
    ) -> Optional[SuggestedAction]:
        run_id = ui_context.selected_run_id
        requires_auth = ui_context.user_role != "OPERATOR"

        # Nếu xác định được task gốc gây lỗi -> đề xuất CLEAR_TASK để chạy lại từ gốc
        if target_task_id:
            required_params = {"dag_id": dag_id, "task_id": target_task_id}
            missing_params: List[str] = []

            if run_id:
                required_params["run_id"] = run_id
            else:
                missing_params.append("run_id")

            return SuggestedAction(
                action_type="CLEAR_TASK",
                dag_id=dag_id,
                task_id=target_task_id,
                run_id=run_id,
                reason=(
                    f"Xoá trạng thái lỗi tại node gốc '{target_task_id}' để kích hoạt chạy lại "
                    f"node này cùng toàn bộ nhánh downstream phụ thuộc."
                ),
                required_params=required_params,
                missing_params=missing_params,
                requires_operator_auth=requires_auth,
            )

        # Trường hợp lỗi ở cấp độ toàn DAG (không gắn với 1 task cụ thể)
        if action_hint == "TRIGGER_DAG":
            return SuggestedAction(
                action_type="TRIGGER_DAG",
                dag_id=dag_id,
                reason=f"Kích hoạt lại một lượt chạy mới cho DAG '{dag_id}'.",
                required_params={"dag_id": dag_id},
                missing_params=[],
                requires_operator_auth=requires_auth,
            )

        return None