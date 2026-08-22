import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_package_metadata_and_cli_entrypoint() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project = data["project"]
    assert project["name"] == "orbit-ai"
    assert project["version"]
    assert project["requires-python"] == ">=3.11"
    assert project["scripts"]["orbit"] == "orbit.cli:main"


def test_release_validation_script_is_strict() -> None:
    script = (ROOT / "release.sh").read_text()
    assert "set -euo pipefail" in script
    assert "python -m build" in script
    assert "orbit --help" in script
