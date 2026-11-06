import pytest

from prereg.llm import LLMError, extract_code, extract_json


def test_extract_json_handles_fences_and_chatter():
    text = 'Sure! Here is the plan:\n```json\n{"test": "ols", "alpha": 0.05}\n```\nGood luck.'
    assert extract_json(text) == {"test": "ols", "alpha": 0.05}


@pytest.mark.parametrize("text", ["no json here", "{not: valid}", "[1, 2]"])
def test_extract_json_rejects_bad_replies(text):
    with pytest.raises(LLMError):
        extract_json(text)


def test_extract_code_takes_the_longest_python_block():
    text = "```python\nx = 1\n```\nand the full script:\n```python\nimport pandas\nprint(1)\n```"
    assert extract_code(text) == "import pandas\nprint(1)"


def test_extract_code_accepts_a_bare_script():
    assert extract_code("print('hi')\n") == "print('hi')"
