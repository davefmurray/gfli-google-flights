# Releasing GLFI

Nothing is published automatically. The initial Python version is 0.1.0.
Inherited `v*` tags belong to Fli, not GLFI. Use `glfi-vX.Y.Z` for our releases.

## Before Publishing

1. Confirm `glfi` can be registered on PyPI. A metadata 404 is not a reservation.
2. Configure a PyPI trusted publisher for `davefmurray/glfi`, workflow `publish.yml`,
   environment `pypi`. Protect that GitHub environment with required approval.
3. Update `pyproject.toml`, run `uv lock`, and commit the matching version and lockfile.
4. Run `make lint`, `make test-offline`, and a small live search from the release host.
5. Run `uv build` and `uv run twine check dist/*`. Install the wheel in a fresh
   environment and verify `glfi`, `glfi-mcp`, and `glfi-mcp-http`.
6. Tag the tested commit `glfi-vX.Y.Z`. Dispatch **Publish GLFI** on that tag,
   initially leaving `publish=false` to inspect the build artifact. Then dispatch
   on the same tag with `publish=true` after the environment is configured.
7. Announce the release and replace the pre-release installation note in README.

Do not publish the inherited TypeScript transport. `fli-js/package.json` is
private until live parity is repaired and verified. No public HTTP deployment
is included in this baseline. Configure authentication before any such deployment.

Once PyPI is live, other users can install with:

```sh
uv tool install 'glfi[mcp]'
# Or:
pipx install 'glfi[mcp]'
```

Upgrade with `uv tool upgrade glfi` or `pipx upgrade glfi` respectively.
