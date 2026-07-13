from caption_generator import build_prompt_context, generate_caption, main
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_main_accepts_menu_flag_and_generates_requested_count(capsys):
    with patch("caption_generator.generate_caption", side_effect=["caption-1", "caption-2"]) as mock_generate:
        exit_code = main(["--menu", "ชาไทย", "--n", "2"])

    assert exit_code == 0
    assert mock_generate.call_count == 2

    captured = capsys.readouterr().out
    assert "caption-1" in captured
    assert "caption-2" in captured


def test_build_prompt_context_includes_price_and_ingredients_from_nested_dict():
    menu = {
        "name": "ชานมไอซ์",
        "details": {
            "price": 65,
            "ingredients": ["นมสด", "ชานม", "น้ำแข็ง"],
        },
    }

    prompt_context = build_prompt_context(menu)

    assert "ชานมไอซ์" in prompt_context
    assert "ราคา: 65" in prompt_context
    assert "ส่วนผสม: นมสด, ชานม, น้ำแข็ง" in prompt_context


def test_generate_caption_retries_when_output_is_too_long():
    responses = iter(["x" * 300, "short caption"])

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

        @property
        def models(self):
            return self

        def generate_content(self, model, contents):
            return SimpleNamespace(text=next(responses))

    with patch("caption_generator.genai.Client", side_effect=FakeClient):
        caption = generate_caption(
            {"name": "ชาไทย"}, api_key="test-key", max_attempts=2)

    assert caption == "short caption"
