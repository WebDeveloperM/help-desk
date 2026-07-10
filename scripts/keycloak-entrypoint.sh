#!/bin/sh
# Перед стартом Keycloak создаём bootstrap-админа (см. https://www.keycloak.org/server/bootstrap-admin-recovery).
# Если пользователь уже есть — команда может вернуть ошибку, игнорируем (|| true).
/opt/keycloak/bin/kc.sh bootstrap-admin user \
  --username:env KEYCLOAK_ADMIN_USERNAME \
  --password:env KC_BOOTSTRAP_ADMIN_PASSWORD \
  --no-prompt 2>/dev/null || true
exec /opt/keycloak/bin/kc.sh "$@"
