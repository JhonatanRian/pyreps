import tomllib
from pathlib import Path


def define_env(env):
    """Hook for mkdocs-macros-plugin."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    project_metadata = pyproject.get("project", {})

    # Expose variables to Jinja2 templates
    env.variables.version = project_metadata.get("version", "unknown")
    env.variables.python_requires = project_metadata.get("requires-python", ">=3.12")
