"""Option B: Azure Document Intelligence + vision LLM hybrid analysis."""

from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from typing import Any

from PIL import Image

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class OptionBConfig:
    document_intelligence_endpoint: str
    document_intelligence_key: str
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_openai_api_version: str
    openai_api_key: str


def load_option_b_config() -> OptionBConfig | None:
    endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "").strip()
    di_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY", "").strip()
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
    azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview").strip()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    has_di = bool(endpoint and di_key)
    has_azure_llm = bool(azure_endpoint and azure_key and azure_deployment)
    has_openai_llm = bool(openai_key)

    if not has_di or not (has_azure_llm or has_openai_llm):
        return None

    return OptionBConfig(
        document_intelligence_endpoint=endpoint,
        document_intelligence_key=di_key,
        azure_openai_endpoint=azure_endpoint,
        azure_openai_api_key=azure_key,
        azure_openai_deployment=azure_deployment,
        azure_openai_api_version=azure_version,
        openai_api_key=openai_key,
    )


def option_b_status() -> tuple[bool, str]:
    config = load_option_b_config()
    if config is None:
        missing: list[str] = []
        if not os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT") or not os.environ.get(
            "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        ):
            missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT + AZURE_DOCUMENT_INTELLIGENCE_KEY")
        if not (
            (os.environ.get("AZURE_OPENAI_ENDPOINT") and os.environ.get("AZURE_OPENAI_API_KEY"))
            or os.environ.get("OPENAI_API_KEY")
        ):
            missing.append("Azure OpenAI (endpoint, key, deployment) or OPENAI_API_KEY")
        return False, "Option B not configured. Missing: " + "; ".join(missing)
    provider = "Azure OpenAI" if config.azure_openai_endpoint else "OpenAI"
    return True, f"Option B ready — Azure Document Intelligence + {provider} vision LLM."


def _image_to_jpeg_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def document_intelligence_ocr(image: Image.Image, config: OptionBConfig) -> str:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(
        endpoint=config.document_intelligence_endpoint,
        credential=AzureKeyCredential(config.document_intelligence_key),
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        analyze_request=AnalyzeDocumentRequest(bytes_source=_image_to_jpeg_bytes(image)),
    )
    result = poller.result()
    lines: list[str] = []
    if result.pages:
        for page in result.pages:
            if page.lines:
                for line in page.lines:
                    if line.content:
                        lines.append(line.content)
    if lines:
        return "\n".join(lines)
    return result.content or ""


def build_llm_prompt(app_data: dict[str, str], ocr_text: str, canonical_warning: str) -> str:
    return f"""
You are assisting TTB alcohol label compliance review. Analyze the label image and OCR text.

Application data (from COLA):
- Brand: {app_data.get("brand", "")}
- Class/Type: {app_data.get("class_type", "")}
- ABV: {app_data.get("abv", "")}
- Net contents: {app_data.get("net", "")}
- Bottler: {app_data.get("bottler", "")}

Required exact government warning (27 CFR 16.21):
{canonical_warning}

OCR text from Azure Document Intelligence:
{ocr_text[:4000]}

Return JSON only:
{{
  "extracted_fields": {{
    "brand": "",
    "class_type": "",
    "abv": "",
    "net": "",
    "bottler": ""
  }},
  "warning": {{
    "detected": true,
    "header_exact_caps": true,
    "header_bold": true,
    "wording_exact": true,
    "issues": [],
    "summary": "one sentence"
  }},
  "brand_notes": "",
  "agent_notes": ""
}}

Rules:
- Government warning must be word-for-word exact; header must be GOVERNMENT WARNING: in all caps and bold.
- Brand names that differ only by case/punctuation are the same brand.
- If unsure, recommend manual review in issues.
"""


def parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def vision_llm_assessment(
    image: Image.Image,
    app_data: dict[str, str],
    ocr_text: str,
    canonical_warning: str,
    config: OptionBConfig,
) -> dict[str, Any]:
    prompt = build_llm_prompt(app_data, ocr_text, canonical_warning)
    data_url = f"data:image/jpeg;base64,{base64.b64encode(_image_to_jpeg_bytes(image)).decode('ascii')}"

    if config.azure_openai_endpoint:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version,
            azure_endpoint=config.azure_openai_endpoint,
        )
        model = config.azure_openai_deployment
    else:
        from openai import OpenAI

        client = OpenAI(api_key=config.openai_api_key)
        model = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = response.choices[0].message.content or "{}"
    return parse_llm_json(content)


def merge_extracted_fields(
    llm_fields: dict[str, Any],
    fallback_fields: dict[str, str],
) -> dict[str, str]:
    merged = dict(fallback_fields)
    for key, value in (llm_fields or {}).items():
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()
    return merged
