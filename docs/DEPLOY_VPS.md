# HelpDesk — развёртывание на VPS

Цель: развернуть стек на сервере с публичным IP `195.158.14.125`, без домена,
по HTTP. Когда появится домен — переход на HTTPS описан в конце документа.

Все команды выполняются от пользователя с правом запускать `docker` (либо `root`,
либо член группы `docker`).

---

## 0. Предварительные требования на VPS

- Ubuntu 22.04+ или Debian 12+ (любой Linux с systemd подходит).
- Docker Engine 24+ и Docker Compose v2 (`docker compose`, не `docker-compose`).
- 4 GB RAM и 20 GB свободно на диске.
- Открытые порты:
  - `22` — SSH (доступ оператора).
  - `80` — HTTP (приложение через nginx, в т.ч. картинки активов через `/media/`).
  - `443` — оставить закрытым до перехода на HTTPS.
- **Не открывайте:** `8000`, `8080`, `9000`, `9001`, `5432`, `6379` — они должны
  быть доступны только внутри docker-сети. nginx в стеке проксирует то, что нужно
  (включая MinIO S3 API через `/media/`).

```bash
# Минимальный firewall (Ubuntu/UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw enable
```

---

## 1. Клонирование репозитория

```bash
sudo mkdir -p /opt/helpdesk && sudo chown $USER:$USER /opt/helpdesk
cd /opt/helpdesk
git clone https://gitlab.com/devshilov/helpdesk.git .
git checkout local-dev   # или main, когда мердж дойдёт туда
```

---

## 2. Заполнение `.env.prod`

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Что обязательно поменять (плейсхолдеры в шаблоне):

- `POSTGRES_PASSWORD` — `openssl rand -base64 24`.
- `DATABASE_URL` — подставить тот же пароль.
- `KEYCLOAK_DB_PASSWORD` — отдельный пароль, `openssl rand -base64 24`.
- `KEYCLOAK_ADMIN_PASSWORD` — пароль для bootstrap-админа Keycloak.
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` — учётка для MinIO. На старте можно
  использовать те же значения для `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`.
- `KEYCLOAK_CLIENT_SECRET` — **оставить пустым на этом шаге**, заполните после §4.

Все остальные `*URL` и `ALLOWED_CORS_ORIGINS` уже настроены на `http://195.158.14.125`.
Если IP другой — замените глобально.

`chmod 600 .env.prod` — файл с секретами не должен быть читаем для других
пользователей.

---

## 3. Первый запуск стека

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend
```

Что должно произойти:

- `db`, `keycloak-db`, `redis`, `minio` стартуют первыми.
- `backend` запустится после healthy `db`/`keycloak`/`redis`. На старте entrypoint
  выполнит `alembic upgrade head` (миграция 008 создаст extension `vector` —
  это работает потому что `db` поднят на образе `pgvector/pgvector:pg16`).
- `frontend` собирается одноразовым контейнером и завершается с кодом 0 — это
  нормально, его статика лежит в volume `helpdesk_frontend_static`, который
  читает nginx.
- `nginx` поднимется последним.

Проверка:

```bash
curl -s http://195.158.14.125/health           # → {"status":"healthy"}
curl -sI http://195.158.14.125/                # → 200 OK, frontend index
```

На этом этапе вход в систему ещё не работает — Keycloak realm пуст.

---

## 4. Первичная настройка Keycloak

Админка Keycloak (`/admin/`) в `nginx/nginx.conf` ограничена приватными
сетями (127.0.0.1, 10/8, 192.168/16, 172.16/12). С интернета она недоступна
сознательно — это правильно. Доступ — через SSH-туннель.

С локальной машины:

```bash
ssh -L 8080:localhost:80 user@195.158.14.125
```

Тоннель оставляем открытым. В браузере на локальной машине открываем
`http://localhost:8080/admin/` (Host header — `localhost`, allow-list пропускает).

Логин: `admin` / `<KEYCLOAK_ADMIN_PASSWORD>` из `.env.prod`.

Дальше следуйте `docs/KEYCLOAK_SETUP.md`. Краткий чек-лист:

1. **Создать realm** `helpdesk`.
2. **Создать client** `helpdesk-backend` (тип «OpenID Connect», access type
   «confidential»).
3. **Client → Settings → Valid Redirect URIs:**
   - `http://195.158.14.125/api/v1/auth/callback`
   - `http://195.158.14.125/login`
4. **Valid Post Logout Redirect URIs:**
   - `http://195.158.14.125/login`
5. **Web Origins:** `http://195.158.14.125`
6. **Client → Credentials → Client Secret** — скопировать.
7. На VPS открыть `.env.prod`, вставить секрет в `KEYCLOAK_CLIENT_SECRET`.
8. Перезапустить только backend (Keycloak трогать не нужно):

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend
   ```

---

## 5. Финальная проверка

1. Открыть `http://195.158.14.125/` в браузере.
2. Нажать «Войти» → должен открыться экран логина Keycloak (на том же IP, через
   nginx → `/realms/helpdesk/...`).
3. Войти любым созданным в Keycloak пользователем.
4. После редиректа обратно — фронтенд показывает дашборд.
5. На бэкенде проверить, что пользователь синхронизировался:

   ```bash
   docker exec helpdesk-db psql -U postgres -d helpdesk \
     -c "SELECT email, full_name, department_id FROM users;"
   ```

   `department_id` будет `NULL`, если в Keycloak у пользователя не задан атрибут
   `department` (см. предыдущее обсуждение про связку user ↔ department).

---

## 6. Что **не** запускается по умолчанию

- **Notification dispatcher (RabbitMQ)** — `RABBITMQ_URL` в `.env.prod`
  закомментирован. Без него уведомления записываются в outbox, но не
  публикуются. Чтобы включить — добавьте сервис rabbitmq в
  `docker-compose.prod.yml` и раскомментируйте URL.
- **MinIO console (`:9001`)** — порт сознательно не публикуется. Доступ — через
  SSH-туннель: `ssh -L 9001:localhost:9001 user@195.158.14.125` →
  `http://localhost:9001` (логин — `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`).

---

## 7. Обновление приложения

```bash
cd /opt/helpdesk
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build backend frontend
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend
```

Миграции применяются автоматически в entrypoint backend.

---

## 8. Бэкап

Минимум, который надо снимать:

```bash
# Дамп основной БД
docker exec helpdesk-db pg_dump -U postgres helpdesk \
  | gzip > /opt/helpdesk-backups/helpdesk-$(date +%F).sql.gz

# Дамп Keycloak БД (нужен для восстановления realm/users)
docker exec helpdesk-keycloak-db pg_dump -U keycloak keycloak \
  | gzip > /opt/helpdesk-backups/keycloak-$(date +%F).sql.gz

# MinIO data — снимок volume
docker run --rm -v helpdesk_minio_data:/data -v /opt/helpdesk-backups:/backup \
  alpine tar czf /backup/minio-$(date +%F).tar.gz -C /data .
```

Поставьте это в cron.

---

## 9. Переход на HTTPS (когда появится домен)

Bare IP не подписывается ни Let's Encrypt, ни коммерческими CA — поэтому
сейчас стек работает по HTTP. Когда будет домен (или free DDNS вроде
`<ip-with-dashes>.sslip.io`):

1. DNS A-запись → `195.158.14.125`.
2. На VPS установить certbot и получить cert:

   ```bash
   sudo apt install certbot
   sudo certbot certonly --webroot -w /opt/helpdesk/nginx/well-known -d <domain>
   ```

   (`/well-known/` уже проксируется в шаблоне `nginx/nginx.https.conf.example`.)
3. Скопировать `nginx/nginx.https.conf.example` в `nginx/nginx.conf`,
   подставить путь к сертификату.
4. В `.env.prod` глобально заменить `http://195.158.14.125` →
   `https://<domain>`. Особое внимание: `KEYCLOAK_PUBLIC_URL`,
   `KEYCLOAK_ISSUER`, `FRONTEND_URL`, `AUTH_CALLBACK_URL`,
   `ALLOWED_CORS_ORIGINS`, `MINIO_PUBLIC_BASE_URL`.
5. В Keycloak Admin обновить Valid Redirect URIs / Web Origins / Post Logout
   на новый домен.
6. `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx backend frontend`.
7. Открыть 443/tcp в firewall, закрыть 80/tcp (или оставить с 301-редиректом
   на HTTPS — есть в `nginx.https.conf.example`).
