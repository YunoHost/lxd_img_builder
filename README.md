# Incus image builder for images to be used for the YunoHost dev env, app CI, core CI

## Prepare workspace

Before anything, run `./patch_gitlab_runner` to generate a small-ish gitlab runner debian package.

Also, the tool needs PyYaml so either install it in your distribution, or you can run
`pdm install` to generate a relevant venv.

## How to use

Run `./image_builder.py <version> <distribution> <variants>`.

* The `version` is the Debian version, `bullseye` or `bookworm` (or `trixie` etc).
* The `distribution` is `stable`, `unstable` or `testing`.
* The `variants` can be `all`, `appci-only` or `build-and-lint`.

`all` will build those images:
- `before-install` - a Debian image with every YunoHost dependency installed, but not YunoHost itself (meant for core CI)
- `dev` - ditto, but with YunoHost installed, but no postinstall yet (meant for ynh-dev)
- `appci`- ditto, but with postinstall done (meant for app CI)
- `core-tests` - ditto, but with a bunch of extra dependencies + pytest modules (meant for core CI)

`appci-only` will only rebuild `appci` on top of the existing `dev` image.

`build-and-lint` builds a "minimal" Debian image used by the core CI to build .debs, run black/flake/mypy linters etc. (meant for core CI)
