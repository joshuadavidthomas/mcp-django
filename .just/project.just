set unstable := true

justfile := justfile_directory() + "/.just/project.just"

[private]
default:
    @just --list --justfile {{ justfile }}

[private]
fmt:
    @just --fmt --justfile {{ justfile }}

[no-cd]
@bump *ARGS:
    uv run {{ justfile_directory() }}/.bin/bump.py {{ ARGS }}

[no-cd]
@release *ARGS:
    uv run {{ justfile_directory() }}/.bin/release.py {{ ARGS }}
