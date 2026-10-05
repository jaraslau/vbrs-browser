#!/bin/sh
set -eu

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

exec uvicorn api.main:app \
    --host "${BACKEND_HOST:-0.0.0.0}" \
    --port "${BACKEND_PORT:-8000}"
