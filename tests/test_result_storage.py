"""module to test result storage functionality"""
import pytest
from ..system.utility.result_storage import ResultStorage


# prearing test environment with fixture
@pytest.fixture(autouse=True)
def result_storage():
    """provides a clean ResultStorage instance for each test."""
    # Ensure a clean slate before each test
    ResultStorage.clear()
    ret = ResultStorage.save(
        {"research_findings": "Found X",
            "final_report": "Report Y"}
        )
    yield ret
    # teardown code
    ResultStorage.clear()


def test_result_storage():
    """tests storage funcionality"""
    # save should return None
    # (side-effect: instance appended to memory)
    assert result_storage is None

    # inspect memory
    items = ResultStorage.all()
    assert len(items) == 1

    inst = items[-1]
    assert inst.research_findings == "Found X"
    assert inst.final_report == "Report Y"

    # find by key
    matches = ResultStorage.find_by_key("research_findings", "Found X")
    assert len(matches) == 1
    assert matches[0] is inst

    # clear memory
    ResultStorage.clear()
    assert len(ResultStorage.all()) == 0


def test_result_storage_invalid_content():
    """tests behaviour for invalid content"""
    # ensure a clean slate
    ResultStorage.clear()

    # save with invalid content type (non-dict) should not add to memory
    ret = ResultStorage.save("this is not a dict")
    assert ret is None
    items = ResultStorage.all()
    assert len(items) == 0

    # save with missing keys
    # (valid dict) should create an instance but attributes remain None
    ret = ResultStorage.save({"some_other_key": "value"})
    assert ret is None

    items = ResultStorage.all()
    assert len(items) == 1

    inst = items[-1]
    assert inst.content == {"some_other_key": "value"}
    assert inst.research_findings is None
    assert inst.final_report is None

    # cleanup
    ResultStorage.clear()
    assert len(ResultStorage.all()) == 0
