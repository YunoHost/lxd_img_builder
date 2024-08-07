
### Create LXC (Incus) images to be used for the YunoHost dev env, app CI, core CI

- `before-install` - a Debian image with every YunoHost dependency installed, but not YunoHost itself (meant for core CI)
- `dev` - ditto, but with YunoHost installed, but no postinstall yet (meant for ynh-dev)
- `appci`- ditto, but with postinstall done (meant for app CI)
- `core-tests` - ditto, but with a bunch of extra dependencies + pytest modules (meant for core CI)

And:

- `build-and-lint` - a "minimal" Debian image used by the core CI to build .debs, run black/flake/mypy linters etc. (meant for core CI)


