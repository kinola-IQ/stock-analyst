import json

from system.utility.result_storage import ResultStorage, default_storage


def test_save_get_list_keys(tmp_path):
    rs = ResultStorage()
    rs.save("k1", {"value": 123})
    assert rs.get("k1") == {"value": 123}
    keys = rs.list_keys()
    assert "k1" in keys


def test_persist_to_file(tmp_path):
    rs = ResultStorage()
    rs.save("k1", {"value": 123})
    out_file = tmp_path / "sub" / "store.json"
    rs.persist_to_file(str(out_file))
    loaded = json.loads(out_file.read_text(encoding="utf-8"))
    assert loaded.get("k1") == {"value": 123}


def test_default_storage_instance():
    assert isinstance(default_storage, ResultStorage)
