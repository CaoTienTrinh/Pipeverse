from typing import List, Literal
from app.ai.schemas import EvidenceItem


class EvidenceVerifier:
    """Stub tối giản — Văn Hậu sẽ nâng cấp bộ đối chiếu nguyên văn log gốc vào Thứ 2."""

    def verify(
        self, evidences: List[EvidenceItem], raw_tool_outputs: List[str]
    ) -> Literal["CONFIDENT", "UNCERTAIN"]:
        if not evidences:
            return "UNCERTAIN"
        # Kiểm tra sơ bộ xem snippet có xuất hiện trong dữ liệu tool trả về không
        combined_raw = "\n".join(raw_tool_outputs)
        for ev in evidences:
            if ev.snippet and ev.snippet in combined_raw:
                return "CONFIDENT"
        return "UNCERTAIN"