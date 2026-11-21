from typing import Any, Dict


class ContextMasker:
    """Stub tối giản — cần nâng cấp bộ lọc Regex & cắt tỉa log."""

    def mask_text(self, text: str) -> str:
        return text

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data