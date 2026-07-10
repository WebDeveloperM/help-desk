#!/usr/bin/env bash
# Сброс БД Keycloak: после этого bootstrap-админ создаётся заново с логином/паролем из .env.local.
# Запуск из корня проекта: ./scripts/reset-keycloak-db.sh
# Вход в админку: http://localhost/admin/ (KEYCLOAK_ADMIN_USERNAME / KEYCLOAK_ADMIN_PASSWORD из .env.local)

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env.local ]; then
  echo "Файл .env.local не найден. Создайте: cp .env.local.example .env.local"
  exit 1
fi

echo "Останавливаем контейнеры..."
docker compose down

echo "Удаляем volume БД Keycloak..."
docker volume rm helpdesk_keycloak_db_data 2>/dev/null || true

echo "Запускаем стек с .env.local..."
docker compose --env-file .env.local up -d

echo ""
echo "При старте Keycloak entrypoint выполнит bootstrap-admin user (создаст админа в master), затем запустится сервер."
echo "Подождите 1–2 минуты, затем откройте http://localhost/admin/ и войдите с KEYCLOAK_ADMIN_USERNAME / KEYCLOAK_ADMIN_PASSWORD из .env.local."
echo "Realm helpdesk и клиент helpdesk-backend после сброса нужно создать заново (см. docs/KEYCLOAK_SETUP.md)."
