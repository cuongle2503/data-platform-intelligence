from __future__ import annotations

import re
from typing import AsyncGenerator

from google import genai
from google.genai import types

from services.shared.config import settings
from services.shared.logging import get_logger

logger = get_logger(__name__)

class LlmGenerator:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate_stream(self, context: str, user_query: str, model: str = "gemini-2.0-flash") -> AsyncGenerator[str, None]:
        """Generate streaming response using Gemini with retry for missing citations."""

        prompt_path = settings.project_root / "services" / "ai" / "prompts" / "system_prompt.txt"
        system_instruction = prompt_path.read_text(encoding="utf-8")

        prompt = f"Context thông tin có sẵn:\n{context}\n\nCâu hỏi của người dùng: {user_query}"

        max_retries = 3
        attempt = 0
        success = False
        full_text = ""

        while attempt < max_retries and not success:
            attempt += 1
            if attempt > 1:
                prompt = prompt.split("\n\nLưu ý:")[0]  # Remove previous retry note
                prompt += "\n\nLưu ý: Bạn QUÊN trích dẫn hoặc trích dẫn sai định dạng [Doc_N]. HÃY CHẮC CHẮN MỖI DỮ LIỆU ĐỀU ĐI KÈM [Doc_N] hợp lệ."
                logger.warning("Retrying LLM generation due to missing citations", attempt=attempt)

            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )

                full_text = response.text or ""

                if self.verify_citations(full_text, context.count("[Doc_")):
                    success = True
                elif attempt < max_retries:
                    continue  # Retry

            except Exception as e:
                logger.error("LLM Generation failed", error=str(e), attempt=attempt)
                if attempt == max_retries:
                    yield f"\n[Lỗi: Không thể kết nối tới mô hình AI. {str(e)}]"
                    return

        # Yield best response (with or without valid citations)
        if full_text:
            # Simulate streaming by chunking
            chunk_size = 80
            for i in range(0, len(full_text), chunk_size):
                yield full_text[i:i+chunk_size]

        # Append disclaimer if the LLM didn't already
        from datetime import datetime
        if "Dữ liệu tổng hợp từ hệ thống IDP" not in full_text:
            yield "\n\n---\n*Dữ liệu tổng hợp từ hệ thống IDP. Chỉ mang tính tham khảo.*"

    @staticmethod
    def verify_citations(response: str, context_blocks: int) -> bool:
        """Verify if generated citations are valid."""
        if context_blocks == 0:
            return True
        citations = re.findall(r'\[Doc_(\d+)\]', response)
        if not citations:
            return False
        for c in citations:
            if int(c) > context_blocks or int(c) < 1:
                return False
        return True
