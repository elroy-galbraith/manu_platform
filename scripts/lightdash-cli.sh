#!/bin/bash
# Runs the pinned Lightdash CLI inside a throwaway container attached to the
# Compose network, so commands needing a live warehouse connection (deploy,
# set-warehouse, validate) can resolve `postgres` the same way the Lightdash
# server itself does. Pure content commands (upload, download) don't strictly
# need this, but running everything through it keeps behavior consistent.
#
# Usage: scripts/lightdash-cli.sh <lightdash-cli-args...>
# Requires: LIGHTDASH_PAT set in the environment.
# Example:  LIGHTDASH_PAT=... scripts/lightdash-cli.sh deploy --target lightdash -y
set -euo pipefail

LIGHTDASH_CLI_VERSION="0.3363.1"
DBT_CORE_VERSION="1.11.12"
DBT_POSTGRES_VERSION="1.10.2"
COMPOSE_NETWORK="compose_default"
LIGHTDASH_URL="http://lightdash:8080"

if [ -z "${LIGHTDASH_PAT:-}" ]; then
    echo "LIGHTDASH_PAT must be set" >&2
    exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm \
    --network "$COMPOSE_NETWORK" \
    -v "$repo_root/transform:/workspace/transform" \
    -w /workspace/transform \
    -e LIGHTDASH_PAT="$LIGHTDASH_PAT" \
    -e LIGHTDASH_PROJECT="${LIGHTDASH_PROJECT:-}" \
    node:20-slim \
    sh -c '
        set -e
        apt-get update -qq >/dev/null && apt-get install -qq -y python3-pip python3-venv >/dev/null 2>&1
        python3 -m venv /tmp/dbtvenv
        /tmp/dbtvenv/bin/pip install -q dbt-core=="$1" dbt-postgres=="$2"
        export PATH=/tmp/dbtvenv/bin:$PATH
        npm install -g @lightdash/cli@"$3" >/dev/null 2>&1
        lightdash login "$4" --token "$LIGHTDASH_PAT" ${LIGHTDASH_PROJECT:+--project "$LIGHTDASH_PROJECT"}
        shift 4
        lightdash "$@"
    ' -- "$DBT_CORE_VERSION" "$DBT_POSTGRES_VERSION" "$LIGHTDASH_CLI_VERSION" "$LIGHTDASH_URL" "$@"
