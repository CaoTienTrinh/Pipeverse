import json
from typing import Any, Dict, List
from app.ai.schemas import (
    AIRequestPayload,
    AIResponsePayload,
    EvidenceItem,
)
from app.ai.context.masker import ContextMasker
from app.ai.tools.registry import TOOLS_SCHEMA, execute_tool_call
from app.ai.reasoning.llm_client import LLMClient
from app.ai.reasoning.prompts import SYSTEM_PROMPT
from app.ai.reasoning.verifier import EvidenceVerifier
from app.ai.actions.planner import ActionPlanner


class AIGateway:
    """
    Cổng điều phối trung tâm của AI Layer (C1).
    Kết nối: Request -> Masker -> LLM Tool-Calling Loop -> Verifier -> ActionPlanner -> Response.
    """

    def __init__(self, max_tool_rounds: int = 4):
        self.max_tool_rounds = max_tool_rounds
        self.masker = ContextMasker()
        self.llm = LLMClient()
        self.verifier = EvidenceVerifier()
        self.planner = ActionPlanner()

    def process_request(self, payload: AIRequestPayload) -> AIResponsePayload:
        # 1. Làm sạch dữ liệu đầu vào
        safe_query = self.masker.mask_text(payload.user_query)
        safe_op_extra = self.masker.mask_dict(payload.operational_extra)

        user_prompt = (
            f"Ngữ cảnh giao diện (UI Context): {payload.ui_context.model_dump_json()}\n"
            f"Dữ liệu vận hành bổ sung: {json.dumps(safe_op_extra, ensure_ascii=False)}\n"
            f"Câu hỏi người dùng: {safe_query}"
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        tools_invoked: List[str] = []
        raw_tool_outputs: List[str] = []
        final_text = ""

        # 2. Vòng lặp AI chủ động gọi Tool lấy bằng chứng từ Backend
        for _ in range(self.max_tool_rounds):
            reply = self.llm.chat_with_tools(messages=messages, tools=TOOLS_SCHEMA)
            tool_calls = reply.get("tool_calls", [])

            if not tool_calls:
                final_text = reply.get("content") or "{}"
                break

            # Ghi nhận assistant message yêu cầu gọi tool
            messages.append(
                {
                    "role": "assistant",
                    "content": reply.get("content"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            # Thực thi từng tool và trả kết quả về cho LLM
            for tc in tool_calls:
                t_name = tc["name"]
                t_args = tc["arguments"]
                tools_invoked.append(t_name)

                raw_result = execute_tool_call(t_name, t_args)
                masked_result = self.masker.mask_text(raw_result)
                raw_tool_outputs.append(masked_result)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": masked_result,
                    }
                )

        # 3. Phân tích JSON kết quả từ LLM
        parsed = self._parse_llm_json(final_text)
        evidences = [
            EvidenceItem(**ev)
            for ev in parsed.get("evidences", [])
            if isinstance(ev, dict)
        ]

        # 4. Hậu kiểm bằng chứng (C5)
        confidence = self.verifier.verify(evidences, raw_tool_outputs)

        # 5. Lập kế hoạch hành động & điều hướng 3D (C6)
        ui_command, suggested_action = self.planner.plan(
            ui_context=payload.ui_context,
            confidence_level=confidence,
            target_dag_id=payload.ui_context.selected_dag_id,
            root_cause_task_id=parsed.get("root_cause_task_id"),
            impacted_downstream=parsed.get("impacted_downstream", []),
        )

        return AIResponsePayload(
            session_id=payload.session_id,
            confidence_level=confidence,
            summary=parsed.get("summary", "Không thể tổng hợp kết quả phân tích."),
            root_cause_analysis=parsed.get("root_cause_analysis", final_text),
            impacted_downstream=parsed.get("impacted_downstream", []),
            evidences=evidences,
            ui_command=ui_command,
            suggested_action=suggested_action,
            tools_invoked=tools_invoked,
        )

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"summary": cleaned, "root_cause_analysis": cleaned}