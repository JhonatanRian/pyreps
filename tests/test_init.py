import pytest
import pyreps
from importlib.metadata import PackageNotFoundError


def test_init_version_package_not_found(monkeypatch):
    # Mock version to raise PackageNotFoundError
    import importlib.metadata

    def mock_version(name):
        if name == "pyreps":
            raise PackageNotFoundError
        return "other"

    # Patch it in the source module
    monkeypatch.setattr(importlib.metadata, "version", mock_version)

    # Reload the module to trigger the try-except block
    importlib.reload(pyreps)

    assert pyreps.__version__ == "0.0.0-dev"


def test_init_version_success(monkeypatch):
    # Test __getattr__ directly since __version__ is already in the module
    # We can temporarily change the global __version__ in the module
    monkeypatch.setattr(pyreps, "__version__", "1.2.3")
    assert pyreps.__getattr__("__version__") == "1.2.3"


def test_init_version_not_found_getattr(monkeypatch):
    monkeypatch.setattr(pyreps, "__version__", "0.0.0-dev")
    assert pyreps.__getattr__("__version__") == "0.0.0-dev"


def test_init_invalid_getattr():
    with pytest.raises(AttributeError) as excinfo:
        pyreps.__getattr__("non_existent")
    assert "module 'pyreps' has no attribute 'non_existent'" in str(excinfo.value)


def test_init_all_content():
    assert "generate_report" in pyreps.__all__
    assert "ReportSpec" in pyreps.__all__
    assert "infer_report_spec" in pyreps.__all__
    assert "__version__" in pyreps.__all__
