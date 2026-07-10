#!/usr/bin/env bash
# Build fullchain.pem from Namecheap cert + ca-bundle.
# Usage: ./scripts/install-ssl.sh
# Place korxona_com.crt and korxona_com.ca-bundle in nginx/ssl/ first.
# privkey.pem must already exist (from generate-csr.sh).

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSL_DIR="$ROOT/nginx/ssl"
CRT="${1:-$SSL_DIR/korxona_com.crt}"
BUNDLE="${2:-$SSL_DIR/korxona_com.ca-bundle}"

mkdir -p "$SSL_DIR"
for f in "$CRT" "$BUNDLE" "$SSL_DIR/privkey.pem"; do
  [ -f "$f" ] || { echo "Missing: $f"; exit 1; }
done

cat "$CRT" "$BUNDLE" > "$SSL_DIR/fullchain.pem"
chmod 644 "$SSL_DIR/fullchain.pem"
echo "Created $SSL_DIR/fullchain.pem"
echo "Ensure privkey.pem is in nginx/ssl/. Then: docker compose up -d"
