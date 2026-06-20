"""Tests for Option B configuration and JSON parsing (no live API calls)."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import option_b_ai


class OptionBConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._saved_env)

    def test_load_option_b_config_missing_returns_none(self) -> None:
        for key in list(os.environ):
            if key.startswith(("AZURE_", "OPENAI_")):
                del os.environ[key]
        self.assertIsNone(option_b_ai.load_option_b_config())

    def test_load_option_b_config_with_azure_openai(self) -> None:
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "https://di.example.com/"
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "di-key"
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://aoai.example.com/"
        os.environ["AZURE_OPENAI_API_KEY"] = "aoai-key"
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = "gpt-4o"

        config = option_b_ai.load_option_b_config()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.document_intelligence_endpoint, "https://di.example.com/")
        self.assertEqual(config.azure_openai_deployment, "gpt-4o")

    def test_load_option_b_config_with_openai_only(self) -> None:
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "https://di.example.com/"
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "di-key"
        os.environ["OPENAI_API_KEY"] = "sk-test"

        config = option_b_ai.load_option_b_config()
        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.openai_api_key, "sk-test")

    def test_option_b_status_when_ready(self) -> None:
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "https://di.example.com/"
        os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "di-key"
        os.environ["OPENAI_API_KEY"] = "sk-test"

        ready, message = option_b_ai.option_b_status()
        self.assertTrue(ready)
        self.assertIn("Option B ready", message)

    def test_option_b_status_when_missing(self) -> None:
        for key in list(os.environ):
            if key.startswith(("AZURE_", "OPENAI_")):
                del os.environ[key]

        ready, message = option_b_ai.option_b_status()
        self.assertFalse(ready)
        self.assertIn("Missing", message)


class OptionBJsonTests(unittest.TestCase):
    def test_parse_llm_json_plain(self) -> None:
        payload = {"warning": {"wording_exact": True}}
        parsed = option_b_ai.parse_llm_json(json.dumps(payload))
        self.assertTrue(parsed["warning"]["wording_exact"])

    def test_parse_llm_json_fenced(self) -> None:
        text = '```json\n{"agent_notes": "Looks good"}\n```'
        parsed = option_b_ai.parse_llm_json(text)
        self.assertEqual(parsed["agent_notes"], "Looks good")

    def test_merge_extracted_fields_prefers_llm(self) -> None:
        merged = option_b_ai.merge_extracted_fields(
            {"brand": "STONE'S THROW", "abv": ""},
            {"brand": "Stone's Throw", "abv": "45%"},
        )
        self.assertEqual(merged["brand"], "STONE'S THROW")
        self.assertEqual(merged["abv"], "45%")

    def test_build_llm_prompt_includes_warning_and_app_data(self) -> None:
        prompt = option_b_ai.build_llm_prompt(
            {"brand": "Stone's Throw", "abv": "45%"},
            "OCR LINE",
            "GOVERNMENT WARNING: (1) ...",
        )
        self.assertIn("Stone's Throw", prompt)
        self.assertIn("GOVERNMENT WARNING:", prompt)
        self.assertIn("OCR LINE", prompt)


class OptionBImageHelperTests(unittest.TestCase):
    def test_image_to_jpeg_bytes(self) -> None:
        from PIL import Image

        image = Image.new("RGB", (10, 10), color=(255, 0, 0))
        data = option_b_ai._image_to_jpeg_bytes(image)
        self.assertTrue(data.startswith(b"\xff\xd8"))


if __name__ == "__main__":
    unittest.main()
