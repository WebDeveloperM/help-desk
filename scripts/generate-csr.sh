#!/usr/bin/env bash
# Generate CSR + private key for Namecheap Positive SSL (korxona.com).
# Run from project root: ./scripts/generate-csr.sh
# Output: nginx/ssl/privkey.pem, nginx/ssl/korxona.com.csr

set -e
DOMAIN="${DOMAIN:-korxona.com}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSL_DIR="$ROOT/nginx/ssl"
mkdir -p "$SSL_DIR"

openssl req -new -newkey rsa:2048 -nodes \
  -keyout "$SSL_DIR/privkey.pem" \
  -out "$SSL_DIR/korxona.com.csr" \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN}" \
  -addext "subjectAltName=DNS:${DOMAIN},DNS:www.${DOMAIN}"

chmod 600 "$SSL_DIR/privkey.pem"
echo ""
echo "Generated:"
echo "  Private key: $SSL_DIR/privkey.pem  (keep secret, do not commit)"
echo "  CSR:         $SSL_DIR/korxona.com.csr"
echo ""
echo "Next: Activate SSL at Namecheap, paste the CSR when prompted."
echo "      Use 'Manually' and HTTP file-based DCV; place the validation"
echo "      file in nginx/well-known/pki-validation/ then restart nginx."
