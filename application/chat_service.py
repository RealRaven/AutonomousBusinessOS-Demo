# application/chat_service.py
"""
Chat Service - streaming with robust Gradio 6 compatibility.
"""

from typing import Generator, List


class ChatService:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client

    def stream_chat(self, message: str, files: List[str] = None, history: List = None) -> Generator[str, None, None]:
        if files is None:
            files = []
        if history is None:
            history = []

        prompt = self._build_prompt(message, history)

        # Encode images if any files are images or PDFs
        encoded_images = []
        for file_path in files:
            if not file_path:
                continue
            fp = str(file_path).lower()
            if fp.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                b64 = self.ollama_client.encode_image(file_path)
                if b64:
                    encoded_images.append(b64)
            elif fp.endswith('.pdf'):
                try:
                    img_paths = self.ollama_client.pdf_to_images(str(file_path), max_pages=1)
                    if img_paths:
                        b64 = self.ollama_client.encode_image(img_paths[0])
                        if b64:
                            encoded_images.append(b64)
                except Exception as e:
                    print(f"PDF chat conversion failed: {e}")

        # Ensure we always yield at least one token so Gradio doesn't get an empty generator
        first_yield = True

        for chunk in self.ollama_client.stream_generate(
            prompt=prompt,
            images=encoded_images if encoded_images else None
        ):
            if first_yield and not chunk.strip():
                continue  # Skip empty first chunks
            first_yield = False
            yield chunk

        # Safety: if nothing was yielded, emit a message so Gradio doesn't crash
        if first_yield:
            yield "I received your message but couldn't generate a response."

    def _build_prompt(self, user_message: str, history: List) -> str:
        if not history:
            return user_message

        prompt_parts = []
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = " ".join(text_parts) if text_parts else ""

            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append(f"User: {user_message}")
        return "\n".join(prompt_parts)

    def call_llm(self, prompt: str, images: List[str] = None) -> str:
        encoded_images = []
        if images:
            for img in images:
                b64 = self.ollama_client.encode_image(img)
                if b64:
                    encoded_images.append(b64)

        return self.ollama_client.call_generate(
            prompt=prompt,
            images=encoded_images if encoded_images else None
        )

    def safe_json_parse(self, text: str) -> dict:
        return self.ollama_client.safe_json_parse(text)