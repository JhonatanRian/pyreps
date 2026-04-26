import json
import pytest
from pyreps.__main__ import main


def test_cli_infer_valid_file(tmp_path, capsys, monkeypatch):
    # Create a dummy JSON file
    data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps(data))

    # Mock sys.argv
    monkeypatch.setattr("sys.argv", ["pyreps", "infer", str(json_file)])

    main()

    captured = capsys.readouterr()
    assert captured.err == ""
    output = json.loads(captured.out)
    assert output["output_format"] == "csv"
    assert len(output["columns"]) == 2
    sources = [c["source"] for c in output["columns"]]
    assert "id" in sources
    assert "name" in sources


def test_cli_infer_streaming(tmp_path, capsys, monkeypatch):
    # Create a dummy JSON file
    data = [{"id": 1, "name": "Alice"}]
    json_file = tmp_path / "test_stream.json"
    json_file.write_text(json.dumps(data))

    # Mock sys.argv with --stream
    monkeypatch.setattr("sys.argv", ["pyreps", "infer", str(json_file), "--stream"])

    main()

    captured = capsys.readouterr()
    assert captured.err == ""
    output = json.loads(captured.out)
    assert any(c["source"] == "id" for c in output["columns"])


def test_cli_file_not_found(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pyreps", "infer", "non_existent.json"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error: File non_existent.json not found." in captured.err


def test_cli_invalid_json(tmp_path, capsys, monkeypatch):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("invalid json")

    monkeypatch.setattr("sys.argv", ["pyreps", "infer", str(invalid_file)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error during inference" in captured.err


def test_cli_no_command(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pyreps"])

    main()
    captured = capsys.readouterr()
    assert "usage: pyreps" in captured.out


def test_cli_invalid_read(tmp_path, capsys, monkeypatch):
    # Test a case where read_bytes fails (e.g. directory instead of file)
    dir_path = tmp_path / "is_a_dir"
    dir_path.mkdir()

    monkeypatch.setattr("sys.argv", ["pyreps", "infer", str(dir_path)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error reading file" in captured.err
