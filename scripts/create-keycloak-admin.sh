#!/usr/bin/env bash
# Создание bootstrap-админа в Keycloak (см. https://www.keycloak.org/server/bootstrap-admin-recovery).
# Keycloak должен быть остановлен. Скрипт: останавливает keycloak → создаёт админа в БД → запускает keycloak.
# Запуск из корня проекта: ./scripts/create-keycloak-admin.sh
# Вход в админку: http://localhost/admin/ (KEYCLOAK_ADMIN_USERNAME / KEYCLOAK_ADMIN_PASSWORD из .env.local)

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env.local ]; then
  echo "Файл .env.local не найден. Создайте: cp .env.local.example .env.local"
  exit 1
fi

echo "Останавливаем Keycloak..."
docker compose --env-file .env.local stop keycloak

echo "Создаём пользователя admin в master realm (bootstrap-admin user, Keycloak 26+)..."
docker compose --env-file .env.local run --rm \
  --entrypoint /opt/keycloak/bin/kc.sh \
  keycloak \
  bootstrap-admin user \
  --username:env KEYCLOAK_ADMIN_USERNAME \
  --password:env KC_BOOTSTRAP_ADMIN_PASSWORD \
  --no-prompt

echo "Запускаем Keycloak..."
docker compose --env-file .env.local start keycloak

echo ""
echo "Готово. Подождите ~1 минуту, затем откройте http://localhost/admin/ и войдите с KEYCLOAK_ADMIN_USERNAME / KEYCLOAK_ADMIN_PASSWORD из .env.local."
