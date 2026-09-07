"""Validate GFLI's release identity and optional publication ref before building."""

import argparse
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def check_release(root: Path, ref: str | None = None) -> str:
    """Require matching project/lock versions and GFLI-owned release tags."""
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    lock = tomllib.loads((root / "uv.lock").read_text())
    if project["name"] != "gfli":
        raise ValueError("Release distribution must be gfli")
    version = project["version"]
    packages = [p for p in lock["package"] if p["name"] == "gfli"]
    if len(packages) != 1 or packages[0]["version"] != version:
        raise ValueError("GFLI project and lockfile versions must match")
    expected = f"refs/tags/gfli-v{version}"
    if ref is not None and ref != expected:
        raise ValueError(f"Publish must run on {expected}")
    return version


def main() -> None:
    """Check the current checkout, optionally enforcing a publication ref."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref")
    args = parser.parse_args()
    print(f"Release identity verified: gfli {check_release(Path.cwd(), args.ref)}")


if __name__ == "__main__":
    main()
