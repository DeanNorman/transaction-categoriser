import pytest

from transactions.categories import CATEGORY_NAMES
from transactions.prompt import load_prompt


def test_the_prompt_file_has_a_version_and_names_every_category():
    prompt = load_prompt()

    assert prompt.version == "1"
    assert all(name in prompt.text for name in CATEGORY_NAMES)
    assert "JSON" in prompt.text and not prompt.text.startswith("---")


def test_a_prompt_without_a_version_is_refused(tmp_path):
    bad = tmp_path / "p.md"
    bad.write_text("---\nmodel: x\n---\nhello")

    with pytest.raises(ValueError):
        load_prompt(bad)
