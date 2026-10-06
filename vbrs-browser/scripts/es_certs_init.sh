#!/bin/sh
# Generates the cluster CA and a node TLS certificate for Elasticsearch into
# the shared `es_certs` volume, and exits. Runs once (idempotently) as the
# unprivileged elasticsearch user from the es-certs-init service before the
# Elasticsearch node starts; the node then runs with explicit TLS settings and
# the backend reads the CA read-only from the same volume.
#
# Written by hand (not by Elasticsearch's first-boot auto-configuration) for
# reproducibility: the auto-configuration cannot stage its certificate
# directory onto a mounted volume and fails at
# `Files.move(..., COPY_ATTRIBUTES)`.

set -eu

CERTS_DIR=/usr/share/elasticsearch/config/certs

if [ ! -f "$CERTS_DIR/ca/ca.crt" ] || [ ! -f "$CERTS_DIR/es01/es01.crt" ]; then
    /usr/share/elasticsearch/bin/elasticsearch-certutil ca --silent --pem \
        -out "$CERTS_DIR/ca.zip"
    unzip -o "$CERTS_DIR/ca.zip" -d "$CERTS_DIR" >/dev/null
    rm -f "$CERTS_DIR/ca.zip"

    mkdir -p "$CERTS_DIR/es01"
    printf 'instances:\n  - name: es01\n    dns:\n      - elasticsearch\n      - localhost\n    ip:\n      - 127.0.0.1\n' \
        > "$CERTS_DIR/es01/instances.yml"

    /usr/share/elasticsearch/bin/elasticsearch-certutil cert --silent --pem \
        -out "$CERTS_DIR/certs.zip" \
        --in "$CERTS_DIR/es01/instances.yml" \
        --ca-cert "$CERTS_DIR/ca/ca.crt" \
        --ca-key "$CERTS_DIR/ca/ca.key"
    unzip -o "$CERTS_DIR/certs.zip" -d "$CERTS_DIR" >/dev/null
    rm -f "$CERTS_DIR/certs.zip" "$CERTS_DIR/es01/instances.yml"
fi

# The certificate and key files are readable by the Elasticsearch node (owner)
# and the CA certificate is read read-only by the backend container, which runs
# as a different unprivileged user, so the directory tree is traversable by
# all; private keys stay owner-only.
chmod 0755 "$CERTS_DIR"
chmod 0755 "$CERTS_DIR/ca" "$CERTS_DIR/es01"
chmod 0644 "$CERTS_DIR/ca/ca.crt"
chmod 0600 "$CERTS_DIR/ca/ca.key"
chmod 0644 "$CERTS_DIR/es01/es01.crt"
chmod 0600 "$CERTS_DIR/es01/es01.key"