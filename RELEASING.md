# Releasing GLFI

Nothing is published automatically. The initial Python version is 0.1.0.
Inherited `v*` tags belong to Fli, not GLFI. Use `glfi-vX.Y.Z` for our releases.

## Before Publishing

Public GitHub source publication was approved on 2026-09-05. That approval does
not authorize PyPI, container-registry, or public service publication. Obtain an
explicit package release decision and require successful remote CI/container
verification before releasing artifacts.

1. Confirm `glfi` can be registered on PyPI. A metadata 404 is not a reservation.
2. Configure a PyPI trusted publisher for `davefmurray/glfi`, workflow `publish.yml`,
   environment `pypi`. Protect that GitHub environment with required approval.
3. Update `pyproject.toml`, run `uv lock`, and commit the matching version and lockfile.
4. Run `make lint`, `make test-offline`, `make audit`, and a small live search from
   the release host. Require all CI jobs, including security and container, to pass.
5. Run `make verify-install` with only the intended version's artifacts in `dist/`.
   It builds wheel/sdist, runs Twine, and tests disposable core and MCP installs
   outside the source tree. No Google calls or global installations are made.
6. Tag the tested commit `glfi-vX.Y.Z`. Dispatch **Publish GLFI** on that tag,
   initially leaving `publish=false` to inspect the build artifact. Then dispatch
   on the same tag with `publish=true` after the environment is configured.
7. Announce the release and replace the pre-release installation note in README.

The workflow is manual-only with `publish=false` by default. Publishing additionally
requires the exact `glfi-vVERSION` tag matching project and lockfile, the owned
`davefmurray/glfi` repository, successful verification jobs, and the `pypi`
environment. Configure required reviewers and restrict that environment to GLFI
release tags in GitHub; YAML cannot configure those account-side protections.
Third-party actions are commit-pinned and checkout credentials are not persisted.

Python 3.10-3.13 is the supported initial range. The upper bound prevents untested
newer interpreters from resolving an older MCP SDK fallback. Expand it only after
auditing the resulting dependency graph and passing the compatibility matrix.

## Container Gate

On a Docker-equipped host, run:

```sh
docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
docker compose exec -T glfi-mcp glfi --version
docker compose exec -T glfi-mcp python -c 'import os; assert os.geteuid() != 0'
docker compose down
```

The image installs non-editably and runs non-root. Compose binds only to loopback,
uses a read-only root filesystem, drops capabilities, and disables privilege gains.
CI builds/runs this image but never pushes it. Base-image OS vulnerability scanning
is still required before a public container distribution; the Python audit is not
an OS-image audit. Windows and other CPU architectures are not locally verified.

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
