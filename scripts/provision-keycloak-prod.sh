#!/usr/bin/env bash
# ==============================================================================
# Провижининг realm Keycloak для прода — реплицирует docs/KEYCLOAK_SETUP.md (1-5)
# через kcadm.sh. Запускать ОДИН РАЗ на свежей (пустой) БД Keycloak.
#
# Запуск из корня проекта на сервере:
#   ./scripts/provision-keycloak-prod.sh
#
# Создаёт: realm helpdesk, клиент helpdesk-backend (confidential, service accounts),
# роли realm-management для Admin API, мапперы department_id/department_number,
# client-роли (user/department_head/executor/admin) и одного тестового пользователя.
# Идемпотентен: повторный запуск пропускает уже существующие объекты.
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=.env.prod
COMPOSE="docker compose -f docker-compose.prod.yml --env-file $ENV_FILE"
KC="$COMPOSE exec -T keycloak /opt/keycloak/bin/kcadm.sh"

REALM=helpdesk
CLIENT_ID=helpdesk-backend
PUBLIC_URL=http://195.158.14.125:36631

# --- тестовый пользователь (поменяйте при необходимости) ----------------------
TEST_USER=admin
TEST_EMAIL=admin@helpdesk.local
TEST_PASSWORD=Admin12345
# ------------------------------------------------------------------------------

# Значения берём из .env.prod, чтобы не было рассинхрона.
get_env() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }
ADMIN_USER=$(get_env KEYCLOAK_ADMIN_USERNAME)
ADMIN_PASS=$(get_env KEYCLOAK_ADMIN_PASSWORD)
CLIENT_SECRET=$(get_env KEYCLOAK_CLIENT_SECRET)

if [ -z "$CLIENT_SECRET" ] || [ "$CLIENT_SECRET" = "PASTE_REAL_SECRET_AFTER_RECREATING_CLIENT" ]; then
  echo "ОШИБКА: задайте реальный KEYCLOAK_CLIENT_SECRET в $ENV_FILE (любая надёжная строка)," >&2
  echo "затем перезапустите backend и снова запустите этот скрипт." >&2
  exit 1
fi

echo "==> Логин в kcadm (realm master)"
$KC config credentials --server http://localhost:8080 --realm master \
  --user "$ADMIN_USER" --password "$ADMIN_PASS"

echo "==> Realm $REALM"
if $KC get "realms/$REALM" >/dev/null 2>&1; then
  echo "    уже существует — пропуск"
else
  $KC create realms -s realm="$REALM" -s enabled=true
fi

echo "==> Клиент $CLIENT_ID"
CLIENT_UUID=$($KC get clients -r "$REALM" -q clientId="$CLIENT_ID" \
  --fields id --format csv --noquotes 2>/dev/null | tr -d '\r\n ' || true)
if [ -n "$CLIENT_UUID" ]; then
  echo "    уже существует ($CLIENT_UUID) — пропуск создания"
else
  $KC create clients -r "$REALM" \
    -s clientId="$CLIENT_ID" \
    -s enabled=true \
    -s protocol=openid-connect \
    -s publicClient=false \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=true \
    -s secret="$CLIENT_SECRET" \
    -s "rootUrl=$PUBLIC_URL" \
    -s "redirectUris=[\"$PUBLIC_URL/api/v1/auth/callback\"]" \
    -s "webOrigins=[\"$PUBLIC_URL\"]" \
    -s "attributes.\"post.logout.redirect.uris\"=$PUBLIC_URL/login"
  CLIENT_UUID=$($KC get clients -r "$REALM" -q clientId="$CLIENT_ID" \
    --fields id --format csv --noquotes | tr -d '\r\n ')
fi
echo "    client uuid: $CLIENT_UUID"

echo "==> Роли realm-management для service account (Admin API)"
$KC add-roles -r "$REALM" --uusername "service-account-$CLIENT_ID" \
  --cclientid realm-management --rolename view-users --rolename manage-users \
  || echo "    роли уже назначены — пропуск"

echo "==> Мапперы department_id / department_number в access token"
for attr in department_id department_number; do
  $KC create "clients/$CLIENT_UUID/protocol-mappers/models" -r "$REALM" \
    -s name="$attr" \
    -s protocol=openid-connect \
    -s protocolMapper=oidc-usermodel-attribute-mapper \
    -s "config.\"user.attribute\"=$attr" \
    -s "config.\"claim.name\"=$attr" \
    -s 'config."jsonType.label"=String' \
    -s 'config."access.token.claim"=true' \
    -s 'config."id.token.claim"=true' \
    -s 'config."userinfo.token.claim"=true' \
    2>/dev/null && echo "    + $attr" || echo "    $attr уже есть — пропуск"
done

echo "==> Client-роли: user, department_head, executor, admin"
for role in user department_head executor admin; do
  $KC create "clients/$CLIENT_UUID/roles" -r "$REALM" -s name="$role" \
    2>/dev/null && echo "    + $role" || echo "    $role уже есть — пропуск"
done

echo "==> Тестовый пользователь $TEST_USER"
if $KC get users -r "$REALM" -q username="$TEST_USER" --fields id --format csv --noquotes \
   2>/dev/null | tr -d '\r\n ' | grep -q .; then
  echo "    уже существует — пропуск"
else
  $KC create users -r "$REALM" \
    -s username="$TEST_USER" \
    -s email="$TEST_EMAIL" \
    -s emailVerified=true \
    -s enabled=true \
    -s firstName=Admin -s lastName=User
  $KC set-password -r "$REALM" --username "$TEST_USER" \
    --new-password "$TEST_PASSWORD"
  $KC add-roles -r "$REALM" --uusername "$TEST_USER" \
    --cclientid "$CLIENT_ID" --rolename admin
fi

echo ""
echo "Готово. Realm '$REALM' и клиент '$CLIENT_ID' настроены."
echo "Вход в приложение: $PUBLIC_URL — пользователь '$TEST_USER' / пароль '$TEST_PASSWORD'."
echo "KEYCLOAK_CLIENT_SECRET в $ENV_FILE уже совпадает с секретом клиента — копировать ничего не нужно."
