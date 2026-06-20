"""Unit and integration tests for TTB label verification logic."""

import importlib.util
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class FakeStreamlitModule:
    session_state: dict = {}

    @staticmethod
    def _chain(*args, **kwargs):
        mock = MagicMock()
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    def tabs(self, labels):
        return tuple(self._chain() for _ in labels)

    def columns(self, spec, **kwargs):
        count = len(spec) if isinstance(spec, (list, tuple)) else spec
        return tuple(self._chain() for _ in range(count))

    def file_uploader(self, *args, **kwargs):
        return None

    def button(self, *args, **kwargs):
        return False

    def selectbox(self, *args, **kwargs):
        return kwargs.get("index", 0) and args[1][0] if len(args) > 1 else "All"

    def text_input(self, *args, **kwargs):
        return kwargs.get("value", "")

    def download_button(self, *args, **kwargs):
        return False

    def stop(self):
        return None

    @property
    def column_config(self):
        return MagicMock(TextColumn=MagicMock, NumberColumn=MagicMock)

    def __getattr__(self, name):
        if name == "session_state":
            return FakeStreamlitModule.session_state
        return self._chain


def load_app_module():
    sys.modules["streamlit"] = FakeStreamlitModule()
    spec = importlib.util.spec_from_file_location("app", PROJECT_ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_app_module()


class BrandMatchingTests(unittest.TestCase):
    def test_stones_throw_title_case_vs_all_caps(self):
        result = app.compare_brand_name("Stone's Throw", "STONE'S THROW")
        self.assertEqual(result.status, "Match")

    def test_old_tom_case_difference(self):
        result = app.compare_brand_name("OLD TOM DISTILLERY", "Old Tom Distillery")
        self.assertEqual(result.status, "Match")

    def test_different_brand_is_not_match(self):
        result = app.compare_brand_name("Stone's Throw", "Blue Ridge Vodka")
        self.assertIn(result.status, {"Mismatch", "Partial", "Not Found"})

    def test_missing_extracted_brand(self):
        result = app.compare_brand_name("Stone's Throw", "")
        self.assertEqual(result.status, "Not Found")


class AbvAndNetTests(unittest.TestCase):
    def test_abv_percent_match(self):
        result = app.compare_abv("45% Alc./Vol. (90 Proof)", "45% Alc./Vol.")
        self.assertEqual(result.status, "Match")

    def test_abv_mismatch(self):
        result = app.compare_abv("45% Alc./Vol.", "40% Alc./Vol.")
        self.assertEqual(result.status, "Mismatch")

    def test_net_contents_match(self):
        result = app.compare_net_contents("750 mL", "750ml")
        self.assertEqual(result.status, "Match")


class WarningValidationTests(unittest.TestCase):
    def test_exact_warning_passes_wording_check(self):
        text = app.GOVERNMENT_WARNING_CANONICAL
        warning = app.validate_government_warning(text, _blank_gray_image())
        self.assertTrue(warning.detected)
        self.assertGreaterEqual(warning.wording_similarity, app.WARNING_WORD_THRESHOLD)

    def test_title_case_warning_header_flagged(self):
        text = app.GOVERNMENT_WARNING_CANONICAL.replace("GOVERNMENT WARNING:", "Government Warning:")
        warning = app.validate_government_warning(text, _blank_gray_image())
        self.assertTrue(warning.detected)
        self.assertFalse(warning.header_exact_caps)

    def test_missing_warning_fails(self):
        warning = app.validate_government_warning("OLD TOM DISTILLERY 45% 750 mL", _blank_gray_image())
        self.assertFalse(warning.detected)
        self.assertEqual(warning.overall_status, "fail")


class BatchAndExportTests(unittest.TestCase):
    def test_parse_batch_csv(self):
        csv_bytes = (PROJECT_ROOT / "sample_batch_template.csv").read_bytes()
        upload = MagicMock()
        upload.getvalue.return_value = csv_bytes
        rows = app.parse_batch_csv(upload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["brand"], "Stone's Throw")

    def test_parse_batch_csv_missing_column(self):
        upload = MagicMock()
        upload.getvalue.return_value = b"application_id,brand\nAPP-1,Test\n"
        with self.assertRaises(ValueError):
            app.parse_batch_csv(upload)

    def test_load_batch_images_from_zip(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("stones_throw.jpg", _minimal_jpeg_bytes())
        upload = MagicMock()
        upload.getvalue.return_value = buffer.getvalue()
        images = app.load_batch_images([], upload)
        self.assertIn("stones_throw.jpg", images)

    def test_single_pdf_export(self):
        result = _sample_analysis_result(app)
        pdf = app.build_single_report_pdf(result)
        self.assertGreater(len(pdf), 500)
        self.assertTrue(bytes(pdf).startswith(b"%PDF"))

    def test_batch_csv_export(self):
        result = _sample_analysis_result(app)
        csv_text = app.results_to_csv([result])
        self.assertIn("APP-001", csv_text)
        self.assertIn("Match", csv_text)


class FieldExtractionTests(unittest.TestCase):
    def test_extract_fields_from_sample_ocr(self):
        ocr_text = """
        STONE'S THROW
        Kentucky Straight Bourbon Whiskey
        45% Alc./Vol. (90 Proof)
        750 mL
        Old Tom Distillery, Louisville, KY
        """ + app.GOVERNMENT_WARNING_CANONICAL
        app_data = {
            "brand": "Stone's Throw",
            "class_type": "Kentucky Straight Bourbon Whiskey",
            "abv": "45% Alc./Vol. (90 Proof)",
            "net": "750 mL",
            "bottler": "Old Tom Distillery, Louisville, KY",
        }
        fields = app.extract_fields_from_ocr(ocr_text, app_data)
        self.assertIn("STONE", fields["brand"].upper())
        self.assertIn("45", fields["abv"])
        self.assertIn("750", fields["net"])


class OverallStatusTests(unittest.TestCase):
    def test_pass_when_brand_and_warning_ok(self):
        result = _sample_analysis_result(app)
        status, _ = app.compute_overall_status(result.comparisons, result.warning)
        self.assertEqual(status, "pass")


class EnvironmentTests(unittest.TestCase):
    def test_tesseract_status(self):
        ok, detail = app.tesseract_status()
        if ok:
            self.assertTrue(detail)
        else:
            self.assertIn("Tesseract", detail)


class OcrIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(app.tesseract_status()[0], "Tesseract not installed")
    def test_ocr_on_synthetic_label_image(self):
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (900, 700), "white")
        draw = ImageDraw.Draw(image)
        lines = [
            "STONE'S THROW",
            "Kentucky Straight Bourbon Whiskey",
            "45% Alc./Vol. (90 Proof)",
            "750 mL",
        ]
        y = 40
        for line in lines:
            draw.text((40, y), line, fill="black")
            y += 50

        app_data = {
            "brand": "Stone's Throw",
            "class_type": "Kentucky Straight Bourbon Whiskey",
            "abv": "45% Alc./Vol. (90 Proof)",
            "net": "750 mL",
            "bottler": "Old Tom Distillery, Louisville, KY",
        }
        result = app.analyze_label(image, app_data, application_id="TEST-OCR", image_name="synthetic.png")
        brand = next(item for item in result.comparisons if item.label == "Brand Name")
        self.assertEqual(brand.status, "Match")
        self.assertIn("45", result.extracted_fields.get("abv", ""))


def _blank_gray_image():
    import numpy as np

    return np.full((200, 400), 255, dtype="uint8")


def _minimal_jpeg_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def _sample_analysis_result(module):
    warning = module.WarningValidation(
        detected=True,
        header_exact_caps=True,
        header_bold=True,
        wording_exact=True,
        wording_similarity=0.99,
        extracted_snippet=module.GOVERNMENT_WARNING_CANONICAL[:80],
        issues=[],
        overall_status="pass",
    )
    comparisons = [
        module.compare_brand_name("Stone's Throw", "STONE'S THROW"),
        module.compare_text_field("Class / Type", "Kentucky Straight Bourbon Whiskey", "Kentucky Straight Bourbon Whiskey"),
        module.compare_abv("45% Alc./Vol. (90 Proof)", "45% Alc./Vol."),
        module.compare_net_contents("750 mL", "750 mL"),
        module.compare_text_field("Bottler / Producer", "Old Tom Distillery, Louisville, KY", "Old Tom Distillery, Louisville, KY"),
    ]
    overall_status, overall_message = module.compute_overall_status(comparisons, warning)
    return module.AnalysisResult(
        application_id="APP-001",
        image_name="stones_throw.jpg",
        app_data={
            "brand": "Stone's Throw",
            "class_type": "Kentucky Straight Bourbon Whiskey",
            "abv": "45% Alc./Vol. (90 Proof)",
            "net": "750 mL",
            "bottler": "Old Tom Distillery, Louisville, KY",
        },
        extracted_fields={"brand": "STONE'S THROW"},
        extracted_text="STONE'S THROW",
        comparisons=comparisons,
        warning=warning,
        overall_status=overall_status,
        overall_message=overall_message,
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
