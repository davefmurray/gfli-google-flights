"""Release version and publication-ref guards."""

from pathlib import Path

import pytest

from scripts.check_release import check_release


@pytest.fixture
def release(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="glfi"\nversion="0.1.0"\n')
    (tmp_path / "uv.lock").write_text('[[package]]\nname="glfi"\nversion="0.1.0"\n')
    return tmp_path


@pytest.mark.parametrize("ref", [None, "refs/tags/glfi-v0.1.0"])
def test_valid_release(release, ref):
    assert check_release(release, ref) == "0.1.0"


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/tags/v0.1.0", "refs/tags/glfi-v0.2.0"])
def test_wrong_publication_ref(release, ref):
    with pytest.raises(ValueError, match="Publish must run"):
        check_release(release, ref)


def test_lock_mismatch(release):
    (release / "uv.lock").write_text('[[package]]\nname="glfi"\nversion="0.2.0"\n')
    with pytest.raises(ValueError, match="versions must match"):
        check_release(release)


def test_distribution_identity(release):
    (release / "pyproject.toml").write_text('[project]\nname="flights"\nversion="0.1.0"\n')
    with pytest.raises(ValueError, match="distribution must be glfi"):
        check_release(release)


def test_checkout_release_identity():
    assert check_release(Path(__file__).resolve().parents[1])


def test_publication_is_manual_and_scoped():
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/publish.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["publish"]["default"] == "false"
    job = workflow["jobs"]["publish"]
    assert "inputs.publish" in job["if"]
    assert "davefmurray/glfi" in job["if"]
    assert job["environment"]["name"] == "pypi"
    assert workflow["permissions"] == {"contents": "read"}


def test_actions_are_pinned():
    import re

    import yaml

    root = Path(__file__).resolve().parents[1]
    for path in (root / ".github/workflows").glob("*.yml"):
        workflow = yaml.safe_load(path.read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
