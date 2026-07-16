# infrastructure/llm/ollama_client.py
"""
Centralized Ollama client - Single source of truth for all LLM calls.
Upgraded with LangChain for RAG chains, but uses direct prompting for
structured extraction (more reliable with local models like Qwen3.5).
"""

import requests
import json
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Generator, List

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.settings import settings


# =========================================================
# PYDANTIC SCHEMA (for documentation / fallback)
# =========================================================
class CustomerExtractionSchema(BaseModel):
    customer_name: str = Field(default="", description="Full name")
    customer_email: str = Field(default="", description="Email")
    customer_phone: str = Field(default="", description="Phone")
    customer_company: str = Field(default="", description="Company")
    customer_address: str = Field(default="", description="Address")
    customer_notes: str = Field(default="", description="Notes")


class OllamaClient:
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        self._chat_model: Optional[ChatOllama] = None

    def get_chat_model(self, temperature: float = None) -> ChatOllama:
        if self._chat_model is None:
            self._chat_model = ChatOllama(
                model=self.model,
                base_url=self.host,
                temperature=temperature if temperature is not None else self.temperature,
                num_predict=self.max_tokens,
            )
        return self._chat_model

    # =========================================================
    # PDF → IMAGE CONVERSION
    # =========================================================
    @staticmethod
    def pdf_to_images(pdf_path: str, dpi: int = 200, max_pages: int = 3) -> List[str]:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=max_pages)
        paths = []
        for i, img in enumerate(images):
            tmp = tempfile.NamedTemporaryFile(suffix=f"_page_{i+1}.png", delete=False)
            img.save(tmp.name, "PNG")
            paths.append(tmp.name)
        return paths

    # =========================================================
    # STRUCTURED EXTRACTION (Direct prompting - robust for local models)
    # =========================================================
    def _extraction_prompt(self) -> str:
        return """Extract customer data from this document.
Return ONLY a valid JSON object. No markdown, no explanations, no code fences.

Required format:
{
  "customer_name": "",
  "customer_email": "",
  "customer_phone": "",
  "customer_company": "",
  "customer_address": "",
  "customer_notes": ""
}

Rules:
- Use empty string "" if a field is not found
- Return ONLY the JSON object, nothing else"""

    def extract_from_image(self, image_path: str, prompt: str = None) -> Dict[str, Any]:
        encoded = self.encode_image(image_path)
        if not encoded:
            return {}

        full_prompt = prompt if prompt else self._extraction_prompt()
        raw = self.call_generate(full_prompt, images=[encoded])
        return self.safe_json_parse(raw)

    def extract_from_pdf(self, pdf_path: str, prompt: str = None) -> Dict[str, Any]:
        try:
            image_paths = self.pdf_to_images(pdf_path, max_pages=1)
            if not image_paths:
                return {}
            return self.extract_from_image(image_paths[0], prompt)
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return {}

    # =========================================================
    # RAG CHAIN BUILDER (LangChain LCEL - works fine with Qwen)
    # =========================================================
    def build_rag_chain(self, system_prompt: str = None):
        if system_prompt is None:
            system_prompt = ("You are a helpful business assistant. Use the provided context "
                             "to answer accurately and concisely.")
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Context:\n{context}\n\nQuestion: {question}")
        ])
        return prompt | self.get_chat_model() | StrOutputParser()

    # =========================================================
    # LEGACY HTTP METHODS
    # =========================================================
    def _get_url(self, endpoint: str) -> str:
        return f"{self.host}/api/{endpoint}"

    def call_generate(self, prompt: str, images: Optional[List[str]] = None, stream: bool = False) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens}
        }
        if images:
            payload["images"] = images
        try:
            response = requests.post(self._get_url("generate"), json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"LLM Error: {str(e)}"

    def stream_generate(self, prompt: str, images: Optional[List[str]] = None) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens}
        }
        if images:
            payload["images"] = images
        try:
            with requests.post(self._get_url("generate"), json=payload, stream=True, timeout=180) as response:
                response.raise_for_status()
                full = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            tok = data.get("response", "")
                            if tok:
                                full += tok
                                yield full
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"Streaming Error: {str(e)}"

    def encode_image(self, image_path: str) -> Optional[str]:
        try:
            path = Path(image_path)
            if not path.exists():
                return None
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    def safe_json_parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        import re
        m = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {}