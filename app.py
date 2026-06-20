#!/usr/bin/env python3
"""
TTB AI Label Verification - Streamlit prototype.
Run locally: streamlit run app.py
See README.md for setup instructions.
"""

import csv
import io
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

import cv2
import numpy as np
import pytesseract
import streamlit as st
from fpdf import FPDF
from PIL import Image

def configure_tesseract() -> None:
    candidates = [
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def tesseract_status() -> tuple[bool, str]:
    configure_tesseract()
    try:
        version = pytesseract.get_tesseract_version()
        return True, str(version)
    except pytesseract.TesseractNotFoundError:
        return False, "Tesseract OCR is not installed or not found on your computer."
    except Exception as exc:
        return False, str(exc)


configure_tesseract()

GOVERNMENT_WARNING_HEADER = "GOVERNMENT WARNING:"
GOVERNMENT_WARNING_CANONICAL = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

MATCH_THRESHOLD = 0.88
REVIEW_THRESHOLD = 0.72
WARNING_WORD_THRESHOLD = 0.97

st.set_page_config(
    page_title="TTB Label Verification Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    :root {
        --navy: #003366;
        --navy-dark: #002244;
        --surface: #ffffff;
        --canvas: #eef2f7;
        --border: #d5dee8;
        --muted: #5c6b7a;
        --text: #1a2b3c;
    }

    .stApp { background: var(--canvas); }

    [data-testid="stAppViewContainer"] > section.main > div {
        max-width: 1280px;
        padding-top: 1.25rem;
        padding-bottom: 1.25rem;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {
        display: none;
    }

    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: 1px solid var(--border) !important;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(0, 35, 70, 0.04);
        padding: 0.15rem;
    }

    .app-header {
        background: linear-gradient(135deg, var(--navy) 0%, #004080 100%);
        color: white;
        padding: 1.1rem 1.35rem;
        border-radius: 10px;
        margin-bottom: 0.85rem;
    }

    .app-header h1 {
        margin: 0;
        font-size: 1.45rem;
        font-weight: 700;
        color: white;
        line-height: 1.25;
    }

    .app-header p {
        margin: 0.35rem 0 0;
        color: #b8cce0;
        font-size: 0.92rem;
    }

    .panel-title {
        color: var(--navy);
        font-size: 1rem;
        font-weight: 700;
        margin: 0 0 0.15rem;
    }

    .panel-subtitle {
        color: var(--muted);
        font-size: 0.82rem;
        margin: 0 0 0.75rem;
    }

    .step-badge {
        display: inline-block;
        background: var(--navy);
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        margin-right: 0.35rem;
        vertical-align: middle;
    }

    .status-pass, .status-review, .status-fail, .status-idle {
        padding: 0.65rem 0.85rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.92rem;
        margin: 0.5rem 0 0.75rem;
        border: 1px solid transparent;
    }

    .status-pass { background: #e8f5ea; color: #1f6b31; border-color: #b9dfc2; }
    .status-review { background: #fff8e6; color: #7a5b00; border-color: #f0dfa0; }
    .status-fail { background: #fdecef; color: #8b1e2d; border-color: #f0b8c0; }
    .status-idle { background: #edf2f7; color: #425466; border-color: var(--border); }

    .hint-line { color: var(--muted); font-size: 0.82rem; margin: 0.35rem 0 0; }

    .upload-empty {
        border: 1px dashed #b8c5d6;
        background: #f7f9fc;
        border-radius: 8px;
        padding: 2.4rem 1rem;
        text-align: center;
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.45;
        min-height: 220px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.84rem;
        margin-top: 0.35rem;
    }

    .comparison-table th, .comparison-table td {
        border-bottom: 1px solid var(--border);
        padding: 0.55rem 0.45rem;
        text-align: left;
        vertical-align: top;
    }

    .comparison-table th {
        background: #f4f7fa;
        color: var(--navy);
        font-weight: 700;
    }

    .comparison-table tr:last-child td { border-bottom: none; }

    .pill-ok { color: #1f6b31; font-weight: 600; }
    .pill-review { color: #7a5b00; font-weight: 600; }
    .pill-fail { color: #8b1e2d; font-weight: 600; }

    .section-label {
        color: var(--navy);
        font-size: 0.88rem;
        font-weight: 700;
        margin: 0.85rem 0 0.35rem;
    }

    .checklist {
        list-style: none;
        padding: 0;
        margin: 0.35rem 0 0.75rem;
        font-size: 0.84rem;
    }

    .checklist li {
        padding: 0.35rem 0;
        border-bottom: 1px solid var(--border);
        color: var(--text);
    }

    .checklist li:last-child { border-bottom: none; }

    .footer-note {
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.45;
        margin-top: 0.75rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.35rem;
        background: transparent;
        border-bottom: 1px solid var(--border);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0 0;
        padding: 0.45rem 0.85rem;
        color: var(--muted);
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background: var(--surface);
        color: var(--navy);
        border: 1px solid var(--border);
        border-bottom-color: var(--surface);
    }

    .stButton > button {
        background: var(--navy);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        min-height: 2.6rem;
    }

    .stButton > button:hover {
        background: var(--navy-dark);
        color: white;
        border: none;
    }

    .stButton > button:disabled {
        background: #c5ced8;
        color: #f8fafc;
    }

    div[data-testid="stFileUploader"] section { padding: 0.35rem; }

    div[data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] {
        background: #f7f9fc;
        border: 1px dashed #b8c5d6;
        border-radius: 8px;
        min-height: 88px;
    }

    div[data-testid="stImage"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid var(--border);
    }

    div[data-testid="stExpander"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
    }

    .stTextInput label {
        color: var(--text);
        font-size: 0.84rem;
        font-weight: 600;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 8px;
        border-color: var(--border);
        background: #fbfcfe;
    }
</style>
""",
    unsafe_allow_html=True,
)


@dataclass
class FieldComparison:
    label: str
    entered: str
    extracted: str
    score: float
    status: str
    detail: str


@dataclass
class WarningValidation:
    detected: bool
    header_exact_caps: bool
    header_bold: bool | None
    wording_exact: bool
    wording_similarity: float
    extracted_snippet: str
    issues: list[str]
    overall_status: str


@dataclass
class AnalysisResult:
    application_id: str
    image_name: str
    app_data: dict[str, str]
    extracted_fields: dict[str, str]
    extracted_text: str
    comparisons: list[FieldComparison]
    warning: WarningValidation
    overall_status: str
    overall_message: str


BATCH_CSV_COLUMNS = [
    "application_id",
    "brand",
    "class_type",
    "abv",
    "net",
    "bottler",
    "image_file",
]

BATCH_CSV_TEMPLATE = """application_id,brand,class_type,abv,net,bottler,image_file
APP-001,Stone's Throw,Kentucky Straight Bourbon Whiskey,45% Alc./Vol. (90 Proof),750 mL,"Old Tom Distillery, Louisville, KY",stones_throw.jpg
APP-002,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,45% Alc./Vol. (90 Proof),750 mL,"Old Tom Distillery, Louisville, KY",old_tom.jpg
"""


def render_status_banner(status: str, message: str) -> None:
    st.markdown(f'<div class="status-{status}">{message}</div>', unsafe_allow_html=True)


def normalize_text(value: str) -> str:
    cleaned = value.lower()
    cleaned = cleaned.replace("’", "'").replace("“", '"').replace("”", '"')
    cleaned = re.sub(r"[^a-z0-9%./\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fix_common_ocr_errors(value: str) -> str:
    replacements = {
        "govemment": "government",
        "surgeon genera1": "surgeon general",
        "alc0hol": "alcohol",
        "birtb": "birth",
        "defects.": "defects.",
        "machinery.": "machinery,",
    }
    result = value
    for wrong, right in replacements.items():
        result = re.sub(re.escape(wrong), right, result, flags=re.IGNORECASE)
    return result


def similarity_score(left: str, right: str) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def classify_match(score: float, extracted: str) -> tuple[str, str]:
    if not extracted:
        return "Not Found", "No reliable OCR match for this field."
    if score >= MATCH_THRESHOLD:
        return "Match", "Entered value aligns with label text."
    if score >= REVIEW_THRESHOLD:
        return "Partial", "Close match — confirm spelling, punctuation, or layout."
    return "Mismatch", "Label text differs materially from application data."


def extract_abv_tokens(value: str) -> dict[str, float | None]:
    text = value.lower()
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:alc|abv|alcohol)?", text)
    proof_match = re.search(r"(\d+(?:\.\d+)?)\s*proof", text)
    percent = float(percent_match.group(1)) if percent_match else None
    proof = float(proof_match.group(1)) if proof_match else None
    if percent is None and proof is not None:
        percent = proof / 2.0
    return {"percent": percent, "proof": proof}


def compare_abv(entered: str, extracted: str) -> FieldComparison:
    entered_tokens = extract_abv_tokens(entered)
    extracted_tokens = extract_abv_tokens(extracted)
    if entered_tokens["percent"] is not None and extracted_tokens["percent"] is not None:
        delta = abs(entered_tokens["percent"] - extracted_tokens["percent"])
        if delta <= 0.25:
            return FieldComparison(
                "ABV / Proof",
                entered,
                extracted or "—",
                1.0 - min(delta / 5.0, 0.2),
                "Match",
                "Alcohol percentage aligns.",
            )
        if delta <= 1.0:
            return FieldComparison(
                "ABV / Proof",
                entered,
                extracted or "—",
                0.78,
                "Partial",
                f"Percent differs by {delta:.1f} points.",
            )
        return FieldComparison(
            "ABV / Proof",
            entered,
            extracted or "—",
            max(0.0, 1.0 - delta / 10.0),
            "Mismatch",
            f"Percent differs by {delta:.1f} points.",
        )
    status, detail = classify_match(score, extracted)
    return FieldComparison("ABV / Proof", entered, extracted or "—", score, status, detail)


def extract_net_ml(value: str) -> float | None:
    text = value.lower().replace(",", "")
    ml_match = re.search(r"(\d+(?:\.\d+)?)\s*ml", text)
    if ml_match:
        return float(ml_match.group(1))
    liter_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:l|liter|litre)\b", text)
    if liter_match:
        return float(liter_match.group(1)) * 1000.0
    floz_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz|fluid ounce)", text)
    if floz_match:
        return float(floz_match.group(1)) * 29.5735
    return None


def compare_net_contents(entered: str, extracted: str) -> FieldComparison:
    entered_ml = extract_net_ml(entered)
    extracted_ml = extract_net_ml(extracted)
    if entered_ml is not None and extracted_ml is not None:
        delta = abs(entered_ml - extracted_ml)
        if delta <= 5:
            return FieldComparison(
                "Net Contents",
                entered,
                extracted or "—",
                1.0,
                "Match",
                "Net contents volume aligns.",
            )
        if delta <= 50:
            return FieldComparison(
                "Net Contents",
                entered,
                extracted or "—",
                0.75,
                "Partial",
                f"Volume differs by about {delta:.0f} mL.",
            )
    score = similarity_score(entered, extracted)
    status, detail = classify_match(score, extracted)
    return FieldComparison("Net Contents", entered, extracted or "—", score, status, detail)


def compare_text_field(label: str, entered: str, extracted: str) -> FieldComparison:
    score = similarity_score(entered, extracted)
    status, detail = classify_match(score, extracted)
    return FieldComparison(label, entered, extracted or "—", score, status, detail)


def normalize_brand_key(value: str) -> str:
    cleaned = value.lower().replace("’", "'")
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
    return cleaned


def brand_word_set(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalize_text(value))
    return {word for word in words if len(word) > 1 or word.isdigit()}


def compare_brand_name(entered: str, extracted: str) -> FieldComparison:
    if not extracted:
        return FieldComparison(
            "Brand Name",
            entered,
            "—",
            0.0,
            "Not Found",
            "No reliable OCR match for brand name on label.",
        )

    entered_key = normalize_brand_key(entered)
    extracted_key = normalize_brand_key(extracted)
    entered_words = brand_word_set(entered)
    extracted_words = brand_word_set(extracted)
    same_brand_detail = (
        "Same brand — only presentation differs (case, punctuation, or spacing). "
        "Per agent guidance, this is treated as a match."
    )

    if entered_key and entered_key == extracted_key:
        return FieldComparison("Brand Name", entered, extracted, 1.0, "Match", same_brand_detail)

    if entered_words and entered_words == extracted_words:
        return FieldComparison("Brand Name", entered, extracted, 1.0, "Match", same_brand_detail)

    if entered_words and entered_words <= extracted_words:
        return FieldComparison(
            "Brand Name",
            entered,
            extracted,
            0.96,
            "Match",
            "Same brand words found on label (label may include extra descriptors).",
        )

    text_score = similarity_score(entered, extracted)
    key_score = (
        SequenceMatcher(None, entered_key, extracted_key).ratio()
        if entered_key and extracted_key
        else 0.0
    )
    score = max(text_score, key_score)

    if score >= MATCH_THRESHOLD:
        return FieldComparison("Brand Name", entered, extracted, score, "Match", same_brand_detail)

    if entered_words and extracted_words:
        overlap = len(entered_words & extracted_words) / max(len(entered_words), 1)
        if overlap >= 0.85:
            return FieldComparison(
                "Brand Name",
                entered,
                extracted,
                max(score, 0.82),
                "Partial",
                "Likely same brand — confirm spelling or extra label wording.",
            )

    status, detail = classify_match(score, extracted)
    return FieldComparison("Brand Name", entered, extracted, score, status, detail)


def best_line_match(needle: str, lines: list[str]) -> tuple[str, float]:
    best_text = ""
    best_score = 0.0
    for line in lines:
        score = similarity_score(needle, line)
        if score > best_score:
            best_score = score
            best_text = line
    joined = " ".join(lines)
    joined_score = similarity_score(needle, joined)
    if joined_score > best_score:
        return joined[:180], joined_score
    return best_text, best_score


def find_abv_line(lines: list[str]) -> str:
    patterns = [
        r"\d+(?:\.\d+)?\s*%\s*(?:alc|abv|alcohol)?",
        r"\d+(?:\.\d+)?\s*proof",
        r"alc\.?\s*/\s*vol",
    ]
    for line in lines:
        lower = line.lower()
        if any(re.search(pattern, lower) for pattern in patterns):
            return line
    return ""


def find_net_line(lines: list[str]) -> str:
    for line in lines:
        lower = line.lower()
        if re.search(r"\b\d+(?:\.\d+)?\s*(?:ml|l|litre|liter|fl\.?\s*oz)\b", lower):
            return line
    return ""


def extract_fields_from_ocr(
    raw_text: str,
    app_data: dict[str, str],
) -> dict[str, str]:
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

    brand, _ = best_line_match(app_data["brand"], lines)
    class_type, _ = best_line_match(app_data["class_type"], lines)
    bottler, _ = best_line_match(app_data["bottler"], lines)
    abv = find_abv_line(lines)
    net = find_net_line(lines)

    if similarity_score(app_data["brand"], brand) < 0.35:
        for line in lines[:8]:
            if len(line) >= 4 and line.isupper():
                brand = line
                break

    if similarity_score(app_data["class_type"], class_type) < 0.35:
        for line in lines:
            lower = line.lower()
            if any(token in lower for token in ("whiskey", "bourbon", "wine", "vodka", "beer", "rum", "gin")):
                class_type = line
                break

    return {
        "brand": brand,
        "class_type": class_type,
        "abv": abv,
        "net": net,
        "bottler": bottler,
    }


def extract_warning_snippet(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    for index, line in enumerate(lines):
        if re.search(r"gov[ea]rn?ment\s+warn", line, flags=re.IGNORECASE):
            end = min(len(lines), index + 6)
            return " ".join(lines[index:end])
    compact = re.sub(r"\s+", " ", raw_text).strip()
    match = re.search(
        r"(?i)(gov[ea]rn?ment\s+warn[\w\s:,\.\(\)\-]+health problems\.?)",
        compact,
    )
    return match.group(1).strip() if match else ""


def normalize_warning_text(value: str) -> str:
    cleaned = fix_common_ocr_errors(value)
    cleaned = cleaned.replace("’", "'").replace("“", '"').replace("”", '"')
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def detect_improper_header_case(raw_text: str) -> bool:
    improper_patterns = [
        r"\bGovernment Warning\b",
        r"\bGOVERNMENT warning\b",
        r"\bGovernment WARNING\b",
        r"\bgovernment warning\b",
    ]
    return any(re.search(pattern, raw_text) for pattern in improper_patterns)


def assess_header_bold(gray_image: np.ndarray, ocr_data: dict[str, list[Any]]) -> bool | None:
    header_words = {"government", "warning"}
    header_boxes: list[tuple[int, int, int, int]] = []
    body_boxes: list[tuple[int, int, int, int]] = []
    in_warning = False

    for index, word in enumerate(ocr_data["text"]):
        if not word or int(ocr_data["conf"][index]) < 35:
            continue
        token = re.sub(r"[^a-z]", "", word.lower())
        if token in header_words:
            in_warning = True
        if not in_warning:
            continue

        left = int(ocr_data["left"][index])
        top = int(ocr_data["top"][index])
        width = int(ocr_data["width"][index])
        height = int(ocr_data["height"][index])
        if width <= 0 or height <= 0:
            continue
        box = (left, top, width, height)
        if token in header_words:
            header_boxes.append(box)
        elif len(token) >= 4:
            body_boxes.append(box)

    if not header_boxes:
        return None

    def ink_density(box: tuple[int, int, int, int]) -> float:
        left, top, width, height = box
        pad = 2
        y1 = max(0, top - pad)
        y2 = min(gray_image.shape[0], top + height + pad)
        x1 = max(0, left - pad)
        x2 = min(gray_image.shape[1], left + width + pad)
        region = gray_image[y1:y2, x1:x2]
        if region.size == 0:
            return 0.0
        _, binary = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return float(np.count_nonzero(binary)) / float(binary.size)

    header_density = max(ink_density(box) for box in header_boxes)
    if not body_boxes:
        return header_density >= 0.16

    body_density = float(np.mean([ink_density(box) for box in body_boxes[:8]]))
    if body_density <= 0:
        return None
    return header_density >= body_density * 1.12


def validate_government_warning(raw_text: str, gray_image: np.ndarray) -> WarningValidation:
    snippet = extract_warning_snippet(raw_text)
    issues: list[str] = []

    if not snippet:
        return WarningValidation(
            detected=False,
            header_exact_caps=False,
            header_bold=None,
            wording_exact=False,
            wording_similarity=0.0,
            extracted_snippet="",
            issues=["Government warning block not detected in OCR output."],
            overall_status="fail",
        )

    if detect_improper_header_case(snippet):
        issues.append("Header is not fully uppercase (e.g. 'Government Warning' instead of 'GOVERNMENT WARNING:').")

    header_exact_caps = GOVERNMENT_WARNING_HEADER in snippet or snippet.startswith("GOVERNMENT WARNING")
    if not header_exact_caps:
        issues.append("Required header 'GOVERNMENT WARNING:' was not found in exact all-caps form.")

    ocr_data = pytesseract.image_to_data(gray_image, output_type=pytesseract.Output.DICT, config="--oem 3 --psm 6")
    header_bold = assess_header_bold(gray_image, ocr_data)
    if header_bold is False:
        issues.append("'GOVERNMENT WARNING:' does not appear bold relative to surrounding warning text.")

    normalized_snippet = normalize_warning_text(snippet)
    normalized_canonical = normalize_warning_text(GOVERNMENT_WARNING_CANONICAL)
    wording_similarity = SequenceMatcher(None, normalized_canonical, normalized_snippet).ratio()
    wording_exact = wording_similarity >= WARNING_WORD_THRESHOLD and header_exact_caps

    if wording_similarity < WARNING_WORD_THRESHOLD:
        issues.append(
            "Warning wording is not word-for-word exact. Paraphrases, omissions, and punctuation changes are not allowed."
        )

    if not wording_exact and wording_similarity >= 0.85:
        issues.append("Text is close but not exact — manual read-back against 27 CFR 16.21 is required.")

    if header_bold is None:
        issues.append("Bold formatting could not be confirmed automatically — visual review required.")

    if wording_exact and header_exact_caps and header_bold is True and not issues:
        overall_status = "pass"
    elif wording_exact and header_exact_caps and header_bold is None:
        overall_status = "review"
    elif not header_exact_caps or wording_similarity < REVIEW_THRESHOLD:
        overall_status = "fail"
    else:
        overall_status = "review"

    return WarningValidation(
        detected=True,
        header_exact_caps=header_exact_caps,
        header_bold=header_bold,
        wording_exact=wording_exact,
        wording_similarity=wording_similarity,
        extracted_snippet=snippet,
        issues=issues,
        overall_status=overall_status,
    )


def preprocess_image(image: Image.Image) -> tuple[np.ndarray, Image.Image]:
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    coords = np.column_stack(np.where(gray > 0))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.5:
            height, width = gray.shape[:2]
            center = (width // 2, height // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(
                gray,
                matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, sharpen_kernel)
    return sharpened, Image.fromarray(sharpened)


def run_ocr(pil_image: Image.Image) -> str:
    configs = ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 3 --psm 11"]
    chunks: list[str] = []
    for config in configs:
        chunks.append(pytesseract.image_to_string(pil_image, config=config))
    merged = "\n".join(chunks)
    return fix_common_ocr_errors(merged)


def analyze_label(
    image: Image.Image,
    app_data: dict[str, str],
    application_id: str = "SINGLE",
    image_name: str = "upload",
) -> AnalysisResult:
    gray, pil_enhanced = preprocess_image(image)
    extracted_text = run_ocr(pil_enhanced)
    extracted_fields = extract_fields_from_ocr(extracted_text, app_data)
    warning_validation = validate_government_warning(extracted_text, gray)

    comparisons = [
        compare_brand_name(app_data["brand"], extracted_fields["brand"]),
        compare_text_field("Class / Type", app_data["class_type"], extracted_fields["class_type"]),
        compare_abv(app_data["abv"], extracted_fields["abv"]),
        compare_net_contents(app_data["net"], extracted_fields["net"]),
        compare_text_field("Bottler / Producer", app_data["bottler"], extracted_fields["bottler"]),
    ]

    overall_status, overall_message = compute_overall_status(comparisons, warning_validation)

    return AnalysisResult(
        application_id=application_id,
        image_name=image_name,
        app_data=app_data,
        extracted_fields=extracted_fields,
        extracted_text=extracted_text,
        comparisons=comparisons,
        warning=warning_validation,
        overall_status=overall_status,
        overall_message=overall_message,
    )


def run_analysis(image: Image.Image, app_data: dict[str, str]) -> None:
    result = analyze_label(image, app_data)
    st.session_state["extracted"] = result.extracted_fields
    st.session_state["extracted_text_raw"] = result.extracted_text
    st.session_state["analysis_result"] = result
    st.session_state["field_comparisons"] = result.comparisons
    st.session_state["warning_validation"] = result.warning
    st.session_state["analysis_complete"] = True


def render_comparison_table(comparisons: list[FieldComparison]) -> None:
    body = []
    for item in comparisons:
        if item.status == "Match":
            css_class = "pill-ok"
        elif item.status in {"Partial", "Not Found"}:
            css_class = "pill-review"
        else:
            css_class = "pill-fail"
        score_pct = f"{item.score * 100:.0f}%"
        body.append(
            f"<tr>"
            f"<td>{item.label}</td>"
            f"<td>{item.entered}</td>"
            f"<td>{item.extracted}</td>"
            f"<td>{score_pct}</td>"
            f'<td class="{css_class}">{item.status}</td>'
            f"</tr>"
        )

    st.markdown(
        f"""
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Field</th>
                    <th>Application</th>
                    <th>Label (OCR)</th>
                    <th>Score</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>{"".join(body)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_warning_checklist(warning: WarningValidation) -> None:
    def mark_ok(value: bool | None) -> str:
        if value is True:
            return "✅"
        if value is False:
            return "❌"
        return "⚠️"

    items = [
        f"{mark_ok(warning.header_exact_caps)} Header reads exactly <code>GOVERNMENT WARNING:</code> in all caps",
        f"{mark_ok(warning.header_bold)} Header appears bold relative to warning body text",
        f"{mark_ok(warning.wording_exact)} Full statement matches 27 CFR 16.21 word-for-word "
        f"({warning.wording_similarity * 100:.1f}% similarity)",
    ]
    html_items = "".join(f"<li>{item}</li>" for item in items)
    st.markdown(f'<ul class="checklist">{html_items}</ul>', unsafe_allow_html=True)

    if warning.issues:
        st.markdown("**Issues flagged**")
        for issue in warning.issues:
            st.markdown(f"- {issue}")


def compute_overall_status(
    comparisons: list[FieldComparison],
    warning: WarningValidation,
) -> tuple[str, str]:
    field_failures = sum(1 for item in comparisons if item.status in {"Mismatch", "Not Found"})
    field_reviews = sum(1 for item in comparisons if item.status == "Partial")

    if warning.overall_status == "fail" or field_failures >= 2:
        return "fail", "Fail — regulatory or application mismatches require manual review."
    if warning.overall_status == "review" or field_failures == 1 or field_reviews >= 2:
        return "review", "Review recommended — one or more fields or warning formatting checks need confirmation."
    if field_reviews == 1:
        return "review", "Review recommended — one field is only a partial match."
    return "pass", "Pass — application data and mandatory warning checks are aligned."


def status_rank(status: str) -> int:
    return {"fail": 0, "review": 1, "pass": 2}.get(status, 3)


def parse_batch_csv(upload) -> list[dict[str, str]]:
    content = upload.getvalue().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty or missing a header row.")

    missing = [column for column in BATCH_CSV_COLUMNS if column not in reader.fieldnames]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

    rows: list[dict[str, str]] = []
    for index, row in enumerate(reader, start=1):
        app_id = (row.get("application_id") or f"ROW-{index}").strip()
        image_file = (row.get("image_file") or "").strip()
        if not image_file:
            raise ValueError(f"Row {index} ({app_id}) is missing image_file.")
        rows.append(
            {
                "application_id": app_id,
                "brand": (row.get("brand") or "").strip(),
                "class_type": (row.get("class_type") or "").strip(),
                "abv": (row.get("abv") or "").strip(),
                "net": (row.get("net") or "").strip(),
                "bottler": (row.get("bottler") or "").strip(),
                "image_file": image_file,
            }
        )
    return rows


def load_batch_images(uploaded_files, zip_upload) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}

    if zip_upload is not None:
        with zipfile.ZipFile(io.BytesIO(zip_upload.getvalue())) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                base_name = os.path.basename(name)
                if base_name.lower().endswith((".jpg", ".jpeg", ".png")):
                    with archive.open(name) as handle:
                        images[base_name] = Image.open(io.BytesIO(handle.read())).convert("RGB")

    for upload in uploaded_files or []:
        images[upload.name] = Image.open(upload).convert("RGB")

    return images


def summarize_result(result: AnalysisResult) -> dict[str, Any]:
    field_issues = sum(
        1 for item in result.comparisons if item.status in {"Mismatch", "Not Found", "Partial"}
    )
    brand_item = next((item for item in result.comparisons if item.label == "Brand Name"), None)
    return {
        "application_id": result.application_id,
        "image_file": result.image_name,
        "brand": result.app_data["brand"],
        "overall_status": result.overall_status,
        "warning_status": result.warning.overall_status,
        "field_issues": field_issues,
        "brand_status": brand_item.status if brand_item else "—",
        "summary": result.overall_message,
    }


def results_to_csv(results: list[AnalysisResult]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "application_id",
            "image_file",
            "overall_status",
            "warning_status",
            "brand_status",
            "field_issues",
            "summary",
        ]
    )
    for result in results:
        summary = summarize_result(result)
        writer.writerow(
            [
                summary["application_id"],
                summary["image_file"],
                summary["overall_status"],
                summary["warning_status"],
                summary["brand_status"],
                summary["field_issues"],
                summary["summary"],
            ]
        )
    return output.getvalue()


def pdf_safe_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")


def pdf_content_width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin


def build_single_report_pdf(result: AnalysisResult) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf_content_width(pdf)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe_text("TTB Label Verification Report"), ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, pdf_safe_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.cell(0, 6, pdf_safe_text(f"Application ID: {result.application_id}"), ln=True)
    pdf.cell(0, 6, pdf_safe_text(f"Image: {result.image_name}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, pdf_safe_text(f"Overall: {result.overall_status.upper()}"), ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(width, 5, pdf_safe_text(result.overall_message))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, pdf_safe_text("Field Comparison"), ln=True)
    pdf.set_font("Helvetica", size=10)
    for item in result.comparisons:
        line = (
            f"{item.label} | App: {item.entered} | Label: {item.extracted} | "
            f"{item.score * 100:.0f}% | {item.status}"
        )
        pdf.multi_cell(width, 5, pdf_safe_text(line))
        pdf.multi_cell(width, 5, pdf_safe_text(f"Note: {item.detail}"))
        pdf.ln(1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, pdf_safe_text("Government Warning (27 CFR 16.21)"), ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(width, 5, pdf_safe_text(f"Warning status: {result.warning.overall_status.upper()}"))
    pdf.multi_cell(
        width,
        5,
        pdf_safe_text(f"Header all caps: {result.warning.header_exact_caps}"),
    )
    pdf.multi_cell(
        width,
        5,
        pdf_safe_text(f"Header bold: {result.warning.header_bold}"),
    )
    pdf.multi_cell(
        width,
        5,
        pdf_safe_text(f"Wording similarity: {result.warning.wording_similarity * 100:.1f}%"),
    )
    if result.warning.issues:
        pdf.multi_cell(width, 5, pdf_safe_text("Issues:"))
        for issue in result.warning.issues:
            pdf.multi_cell(width, 5, pdf_safe_text(f"- {issue}"))

    return bytes(pdf.output())


def build_batch_summary_pdf(results: list[AnalysisResult]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf_content_width(pdf)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, pdf_safe_text("TTB Batch Verification Summary"), ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, pdf_safe_text(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.cell(0, 6, pdf_safe_text(f"Labels processed: {len(results)}"), ln=True)
    pdf.ln(4)

    pass_count = sum(1 for result in results if result.overall_status == "pass")
    review_count = sum(1 for result in results if result.overall_status == "review")
    fail_count = sum(1 for result in results if result.overall_status == "fail")
    pdf.multi_cell(width, 5, pdf_safe_text(f"Pass: {pass_count} | Review: {review_count} | Fail: {fail_count}"))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, pdf_safe_text("Results"), ln=True)
    pdf.set_font("Helvetica", size=10)
    for result in sorted(results, key=lambda item: (status_rank(item.overall_status), item.application_id)):
        line = (
            f"{result.application_id} | {result.image_name} | "
            f"{result.overall_status.upper()} | warning={result.warning.overall_status}"
        )
        pdf.multi_cell(width, 5, pdf_safe_text(line))

    return bytes(pdf.output())


def render_analysis_results(result: AnalysisResult) -> None:
    render_status_banner(result.overall_status, result.overall_message)

    st.markdown('<p class="section-label">Field Comparison</p>', unsafe_allow_html=True)
    render_comparison_table(result.comparisons)

    with st.expander("Field match details"):
        for item in result.comparisons:
            st.markdown(f"**{item.label}** — {item.detail}")

    st.markdown(
        '<p class="section-label">Government Warning (27 CFR 16.21)</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Must be word-for-word exact. "
        "'GOVERNMENT WARNING:' must appear in all caps and bold. "
        "Title case, paraphrasing, or tiny buried text are common rejection reasons."
    )

    if result.warning.overall_status == "pass":
        render_status_banner("pass", "Warning statement passes automated formatting and wording checks.")
    elif result.warning.overall_status == "review":
        render_status_banner("review", "Warning statement detected but requires manual confirmation.")
    else:
        render_status_banner("fail", "Warning statement fails automated compliance checks — rejection likely.")

    render_warning_checklist(result.warning)

    if result.warning.extracted_snippet:
        with st.expander("Detected warning text"):
            st.text(result.warning.extracted_snippet)

    with st.expander("Required exact warning text"):
        st.text(GOVERNMENT_WARNING_CANONICAL)

    with st.expander("Raw OCR text"):
        st.text(result.extracted_text[:2500])


st.markdown(
    """
<div class="app-header">
    <h1>TTB Alcohol Label Verification Assistant</h1>
    <p>Prototype only — not for production use • Local OCR • Nothing is saved</p>
</div>
""",
    unsafe_allow_html=True,
)

tesseract_ok, tesseract_detail = tesseract_status()
if not tesseract_ok:
    st.error(
        "**Setup required:** The OCR engine (Tesseract) is not installed yet. "
        "The app cannot read label text until you install it."
    )
    st.markdown(
        """
**Windows (easiest):** open PowerShell and run:

```
winget install UB-Mannheim.TesseractOCR
```

Then close this page, double-click **`run.bat`** again (or run `streamlit run app.py`).

**Mac:** `brew install tesseract`  
**Need help?** See **README.md** in the project folder — section *Start here (everyone)*.

No API key is required. This app runs entirely on your computer.
        """
    )
    st.stop()
else:
    st.caption(f"OCR engine ready (Tesseract {tesseract_detail}). No API key required.")

tab_single, tab_batch = st.tabs(["Single Label", "Batch Processing"])

with tab_single:
    col_left, col_mid, col_right = st.columns([1, 1.05, 1], gap="medium")

    with col_left:
        with st.container(border=True):
            st.markdown(
                '<p class="panel-title"><span class="step-badge">1</span>Application Data</p>'
                '<p class="panel-subtitle">Example: application lists <strong>Stone\'s Throw</strong> while '
                "label artwork reads <strong>STONE'S THROW</strong>.</p>",
                unsafe_allow_html=True,
            )
            brand = st.text_input("Brand Name", value="Stone's Throw", key="brand")
            class_type = st.text_input(
                "Class / Type Designation",
                value="Kentucky Straight Bourbon Whiskey",
                key="class_type",
            )
            abv = st.text_input("Alcohol Content (ABV)", value="45% Alc./Vol. (90 Proof)", key="abv")
            net = st.text_input("Net Contents", value="750 mL", key="net")
            bottler = st.text_input(
                "Bottler / Producer Name & Address",
                value="Old Tom Distillery, Louisville, KY",
                key="bottler",
            )

    with col_mid:
        with st.container(border=True):
            st.markdown(
                '<p class="panel-title"><span class="step-badge">2</span>Label Image</p>'
                '<p class="panel-subtitle">Upload a straight-on photo with even lighting.</p>',
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Label Image (JPG, PNG)",
                type=["jpg", "jpeg", "png"],
                label_visibility="collapsed",
                key="single_label_upload",
            )

            image = None
            if uploaded_file:
                image = Image.open(uploaded_file).convert("RGB")
                st.image(image, use_container_width=True)
                st.markdown(
                    '<p class="hint-line">Ready for analysis. Preprocessing runs when you click Analyze.</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="upload-empty">
                        <div>
                            <strong>No image yet</strong><br>
                            Drop or browse for a JPG/PNG label photo
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_right:
        with st.container(border=True):
            st.markdown(
                '<p class="panel-title"><span class="step-badge">3</span>Analyze & Review</p>'
                '<p class="panel-subtitle">Fuzzy field matching plus strict government warning checks.</p>',
                unsafe_allow_html=True,
            )

            analyze_btn = st.button(
                "Analyze Label",
                type="primary",
                use_container_width=True,
                disabled=image is None,
                key="analyze_single_label",
            )

            app_data = {
                "brand": brand,
                "class_type": class_type,
                "abv": abv,
                "net": net,
                "bottler": bottler,
            }

            if analyze_btn and image is not None:
                with st.spinner("Preprocessing, extracting fields, and validating warning statement..."):
                    run_analysis(image, app_data)

            if st.session_state.get("analysis_complete"):
                result = st.session_state.get("analysis_result")
                if result:
                    render_analysis_results(result)

                    action_left, action_right = st.columns(2)
                    with action_left:
                        st.download_button(
                            "Export PDF Report",
                            data=build_single_report_pdf(result),
                            file_name=f"label_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_single_pdf",
                        )
                    with action_right:
                        if st.button("Clear Results", use_container_width=True, key="clear_single_results"):
                            for key in [
                                "extracted",
                                "extracted_text_raw",
                                "analysis_result",
                                "field_comparisons",
                                "warning_validation",
                                "analysis_complete",
                            ]:
                                st.session_state.pop(key, None)
                            st.rerun()
            else:
                render_status_banner(
                    "idle",
                    "Upload a label image, then run analysis to see results here.",
                )

with tab_batch:
    with st.container(border=True):
        st.markdown(
            '<p class="panel-title">Batch Label Verification</p>'
            '<p class="panel-subtitle">Upload application CSV plus label images (multi-select or ZIP). '
            "Example row: application brand <strong>Stone's Throw</strong>, label artwork "
            "<strong>STONE'S THROW</strong>.</p>",
            unsafe_allow_html=True,
        )

        template_col, upload_col = st.columns([1, 1.4])
        with template_col:
            st.markdown("**1. Application CSV**")
            st.download_button(
                "Download CSV template",
                data=BATCH_CSV_TEMPLATE,
                file_name="label_batch_template.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_batch_template",
            )
            batch_csv = st.file_uploader(
                "Upload completed CSV",
                type=["csv"],
                key="batch_csv",
            )

        with upload_col:
            st.markdown("**2. Label images**")
            batch_images = st.file_uploader(
                "Select multiple JPG/PNG files",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="batch_images",
            )
            batch_zip = st.file_uploader(
                "Or upload a ZIP of label images",
                type=["zip"],
                key="batch_zip",
            )

        run_batch = st.button(
            "Run Batch Analysis",
            type="primary",
            use_container_width=True,
            disabled=batch_csv is None or (not batch_images and batch_zip is None),
            key="run_batch_analysis",
        )

        if run_batch and batch_csv is not None:
            try:
                rows = parse_batch_csv(batch_csv)
                image_map = load_batch_images(batch_images, batch_zip)
            except ValueError as exc:
                render_status_banner("fail", str(exc))
                rows = []
                image_map = {}
                st.session_state.pop("batch_results", None)
                st.session_state["batch_errors"] = [str(exc)]

            if rows:
                results: list[AnalysisResult] = []
                errors: list[str] = []
                progress = st.progress(0.0, text="Starting batch analysis...")
                status_line = st.empty()

                for index, row in enumerate(rows):
                    image_key = os.path.basename(row["image_file"])
                    status_line.markdown(f"Processing **{row['application_id']}** ({image_key})...")
                    image = image_map.get(image_key)
                    if image is None:
                        image = image_map.get(row["image_file"])
                    if image is None:
                        errors.append(f"{row['application_id']}: image '{row['image_file']}' not found in uploads.")
                        progress.progress((index + 1) / len(rows))
                        continue

                    app_data = {
                        "brand": row["brand"],
                        "class_type": row["class_type"],
                        "abv": row["abv"],
                        "net": row["net"],
                        "bottler": row["bottler"],
                    }
                    results.append(
                        analyze_label(
                            image,
                            app_data,
                            application_id=row["application_id"],
                            image_name=image_key,
                        )
                    )
                    progress.progress((index + 1) / len(rows), text=f"Completed {index + 1} of {len(rows)}")

                progress.empty()
                status_line.empty()
                st.session_state["batch_errors"] = errors
                if results:
                    st.session_state["batch_results"] = results
                else:
                    st.session_state.pop("batch_results", None)

                if not results and errors:
                    render_status_banner(
                        "fail",
                        "Batch finished — no labels processed. Check image filenames against the CSV.",
                    )
                elif errors:
                    render_status_banner(
                        "review",
                        f"Batch finished with {len(errors)} unmatched image(s). See details below.",
                    )
                else:
                    render_status_banner(
                        "pass",
                        f"Batch complete — processed {len(results)} label(s).",
                    )

        if st.session_state.get("batch_errors"):
            st.markdown("**Batch warnings**")
            for error in st.session_state["batch_errors"]:
                st.markdown(f"- {error}")

        if "batch_results" in st.session_state:
            results = st.session_state["batch_results"]
            if not results:
                render_status_banner(
                    "idle",
                    "No batch results yet. Upload CSV and images, then run batch analysis.",
                )
            else:
                summaries = [summarize_result(result) for result in results]
                summaries.sort(key=lambda item: (status_rank(item["overall_status"]), item["application_id"]))

                filter_col, export_col, export_pdf_col = st.columns([2, 1, 1])
                with filter_col:
                    status_filter = st.selectbox(
                        "Filter by overall status",
                        ["All", "fail", "review", "pass"],
                        index=0,
                        key="batch_status_filter",
                    )
                with export_col:
                    st.download_button(
                        "Export results CSV",
                        data=results_to_csv(results),
                        file_name=f"label_batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_batch_csv",
                    )
                with export_pdf_col:
                    st.download_button(
                        "Export summary PDF",
                        data=build_batch_summary_pdf(results),
                        file_name=f"label_batch_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_batch_pdf",
                    )

                filtered = summaries
                if status_filter != "All":
                    filtered = [item for item in summaries if item["overall_status"] == status_filter]

                st.dataframe(
                    filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "overall_status": st.column_config.TextColumn("Overall"),
                        "warning_status": st.column_config.TextColumn("Warning"),
                        "field_issues": st.column_config.NumberColumn("Field flags"),
                        "brand_status": st.column_config.TextColumn("Brand"),
                    },
                )

                st.markdown('<p class="section-label">Drill-down</p>', unsafe_allow_html=True)
                result_by_id = {result.application_id: result for result in results}
                for summary in filtered:
                    label = (
                        f"{summary['application_id']} • {summary['overall_status'].upper()} • "
                        f"{summary['brand']} ({summary['image_file']})"
                    )
                    with st.expander(label):
                        render_analysis_results(result_by_id[summary["application_id"]])
                        st.download_button(
                            "Export this label PDF",
                            data=build_single_report_pdf(result_by_id[summary["application_id"]]),
                            file_name=f"{summary['application_id']}_report.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_batch_item_pdf_{summary['application_id']}",
                        )

                if st.button("Clear Batch Results", use_container_width=True, key="clear_batch_results"):
                    st.session_state.pop("batch_results", None)
                    st.session_state.pop("batch_errors", None)
                    st.rerun()

with st.expander("Prototype notes and regulatory reference"):
    st.markdown(
        f"""
**Mandatory (same field of vision):** Brand name, class/type designation, alcohol content.

**Other mandatory:** Net contents, bottler/producer name and address, government warning (27 CFR 16.21).

**Government warning — strict requirements:**
- Wording must match the statute **word-for-word** (no substitutions, omissions, or creative rewrites)
- The header must read **`{GOVERNMENT_WARNING_HEADER}`** in **all caps**
- The header must be **bold** (title case such as "Government Warning" is not acceptable)
- Common failure modes: smaller type, paraphrased language, or warning buried in fine print

**Field matching:** Application values are compared to OCR output using fuzzy matching with field-specific
rules (for example ABV percentages and net contents volumes). Brand names use agent-style judgment so
presentation-only differences (e.g. `Stone's Throw` vs `STONE'S THROW`) count as a match.

**Batch processing:** Upload a CSV plus multiple images or a ZIP. Results sort by risk severity with drill-down
and CSV export.

**Limitations:** Bold detection and OCR accuracy are imperfect on poor photos. Production should add vision-model
validation for typography and placement. Nothing is stored after the session ends.
        """
    )

st.markdown(
    f"""
<p class="footer-note">
Session {datetime.now().strftime("%Y-%m-%d %H:%M")} • Treasury internal prototype • Not for production use
</p>
""",
    unsafe_allow_html=True,
)
