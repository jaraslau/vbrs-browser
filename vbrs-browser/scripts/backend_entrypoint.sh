#!/bin/sh
set -eu

# Imports the mounted dictionary dataset before serving traffic. Runs on every
# start; the importer's data-and-schema fingerprint makes this a no-op when
# the dataset is unchanged, and a single Compose replica avoids migration
# races. Multi-replica deployments must move this into a dedicated release
# step instead.
if [ -n "${DICTIONARY_IMPORT_DIR:-}" ]; then
    if [ ! -d "$DICTIONARY_IMPORT_DIR" ]; then
        echo "Dictionary import directory does not exist: $DICTIONARY_IMPORT_DIR" >&2
        exit 1
    fi

    set --
    for path in "$DICTIONARY_IMPORT_DIR"/*.json; do
        [ -f "$path" ] || continue
        # Sayings use a separate source schema, not DictionaryArticle.
        [ "${path##*/}" = "sayings.json" ] || set -- "$@" "$path"
    done
    if [ "$#" -eq 0 ]; then
        echo "Dictionary import directory contains no JSON files: $DICTIONARY_IMPORT_DIR" >&2
        exit 1
    fi

    python -m scripts.import_dictionary --if-changed "$@"
fi

exec uvicorn backend.main:app \
    --host "${BACKEND_HOST:?BACKEND_HOST must be set}" \
    --port "${BACKEND_PORT:?BACKEND_PORT must be set}"