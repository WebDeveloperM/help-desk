# Локальная разработка (локальная сеть)

Ветка для запуска HelpDesk в локальной сети. NGINX слушает порт 80 на всех интерфейсах (`80:80`), доступ с этой машины и с других ПК в сети. HTTPS отключён.

---

## 1. Подготовка

```bash
cp .env.local.example .env.local
```

Откройте `.env.local` и задайте **единый базовый URL** — тот же адрес, по которому вы будете открывать приложение в браузере:

- **Только с этой машины:** оставьте `http://localhost` во всех URL (KEYCLOAK_PUBLIC_URL, FRONTEND_URL, AUTH_CALLBACK_URL, KEYCLOAK_ISSUER). Keycloak 17+: issuer — только `/realms/{realm}` (без `/auth`), например `http://localhost/realms/helpdesk`.
- **С других ПК в сети:** замените `localhost` на IP этой машины (например `http://192.168.1.100`) во всех этих переменных и добавьте этот URL в `ALLOWED_CORS_ORIGINS`.

Без этого при авторизации возможна ошибка **"Connection Failed, Browser Connection was refused"**: браузер после логина в Keycloak переходит по callback-URL из настроек; если там указан `http://localhost`, а вы зашли с другого ПК, браузер обращается к своему localhost, а не к серверу.

---

## 2. Запуск

```bash
docker compose --env-file .env.local up -d
```

Использование `--env-file .env.local` нужно, чтобы Keycloak создал bootstrap-админа с логином и паролем из `KEYCLOAK_ADMIN_USERNAME` и `KEYCLOAK_ADMIN_PASSWORD`.

- С этой машины: **http://localhost** или **http://127.0.0.1**
- С других ПК в сети: **http://\<IP этой машины\>** (например http://192.168.1.100)

При старте backend автоматически выполняются миграции БД (Alembic `upgrade head`). Если таблицы уже созданы, повторный запуск просто проверит актуальность схемы.

**Миграции вручную** (если нужно выполнить их отдельно):

```bash
docker compose --env-file .env.local exec backend python -m alembic upgrade head
```

---

## 3. Keycloak — клиент и redirect URIs (обязательно для авторизации)

После первого запуска откройте Keycloak Admin: **http://localhost/admin/** или **http://\<IP\>/admin/** (логин/пароль из `KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD` в `.env.local`).

Создайте realm **helpdesk** и клиента **helpdesk-backend** по [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md). В настройках клиента:

- **Valid redirect URIs:** добавьте ваш базовый URL + путь, например:
  - `http://localhost/api/v1/auth/callback` — если открываете по localhost;
  - при доступе по LAN добавьте `http://\<IP\>/api/v1/auth/callback`.
- **Web origins:** добавьте ваш базовый URL без пути: `http://localhost` и/или `http://\<IP\>`.

Во вкладке **Credentials** скопируйте **Client secret** и вставьте в `.env.local` в `KEYCLOAK_CLIENT_SECRET`. Затем перезапустите backend:

```bash
docker compose restart backend
```

Если redirect URIs или базовый URL в `.env.local` не совпадают с тем, как вы открываете приложение, при логине будет ошибка "Connection was refused".

---

## 4. Кратко: почему был "Connection refused"

1. **Callback-URL недоступна для браузера.** В `.env.local` задаётся `AUTH_CALLBACK_URL` (и другие URL). После входа Keycloak перенаправляет браузер на этот адрес. Если вы заходите с другого ПК по `http://192.168.1.100`, а в настройках стоит `http://localhost`, браузер пойдёт на свой localhost → соединение отклонено.
2. **NGINX слушал только 127.0.0.1.** В этой ветке порт уже открыт как `80:80`, сервер доступен по IP из локальной сети.

Итог: везде (в `.env.local` и в Keycloak) используйте один и тот же базовый URL, по которому вы реально открываете приложение.

---

## 5. Ошибка "token_exchange" / "unauthorized_client" / "invalid_client_credentials"

После входа в Keycloak браузер переходит на callback, backend обменивает код на токены.

- **401 "unauthorized_client" / "Invalid client"** — клиент должен быть Confidential и в `.env.local` задан `KEYCLOAK_CLIENT_SECRET` (см. ниже).
- **CODE_TO_TOKEN_ERROR / invalid_client_credentials** — секрет в `.env.local` не совпадает с секретом в Keycloak (опечатка, старый секрет после Regenerate, лишние пробелы/кавычки).

**Вариант A — публичный клиент (без секрета):**

1. Keycloak: **helpdesk-backend** → **Settings** → **Client authentication** = **OFF** → Save.
2. В `.env.local`: строка `KEYCLOAK_CLIENT_SECRET=` (пусто, без значения).
3. Пересобрать и перезапустить backend (чтобы подтянулся код, который не отправляет secret):  
   `docker compose --env-file .env.local up -d --build backend`.

**Вариант B — конфиденциальный клиент (с секретом):**

1. Keycloak: **helpdesk-backend** → **Settings** → **Client authentication** = **ON** → Save.
2. Вкладка **Credentials** → скопировать **Client secret** (или Regenerate и скопировать).
3. В `.env.local`: `KEYCLOAK_CLIENT_SECRET=<скопированное_значение>` без кавычек и пробелов.
4. **Пересоздать контейнер backend** (переменные подхватываются только при создании контейнера, не при `restart`):  
   `docker compose --env-file .env.local up -d --force-recreate backend`.

**Если ошибка не исчезла:** после смены варианта (A↔B) обязательно делайте `--build backend`, не только `restart`, иначе в контейнере может остаться старый код.

**Ошибка `pkce_expired`:** Бэкенд отправляет для редиректов авторизации заголовки `Cache-Control: no-store`, чтобы ответ «Войти» не кэшировался. Если ошибка всё равно появляется: не запускайте backend с несколькими воркерами (`uvicorn --workers`); не обновляйте страницу callback и не переходите по ссылке callback повторно. Подробнее — [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md), раздел «Устранение неполадок».

---

## 6. Keycloak Admin — не принимает логин/пароль

Вход в панель Keycloak: **http://localhost/admin/** (или **http://\<IP\>/admin/**). Логин и пароль берутся из `.env.local`: `KEYCLOAK_ADMIN_USERNAME` и `KEYCLOAK_ADMIN_PASSWORD`.

**Почему admin/admin не подходит:** В Keycloak 25 пользователь admin создаётся либо при первом запуске с пустой БД (env KC*BOOTSTRAP*\*), либо явной командой `bootstrap-admin user`. Если БД уже была инициализирована без админа (или с другим паролем), входа по `.env.local` не будет.

**Что сделать:**

1. **Создать админа без сброса БД** — остановить Keycloak, выполнить `bootstrap-admin user` в отдельном контейнере, снова запустить Keycloak (требуется Keycloak 26+):

   ```bash
   ./scripts/create-keycloak-admin.sh
   ```

   Скрипт остановит контейнер Keycloak, создаст пользователя admin в realm master ([документация](https://www.keycloak.org/server/bootstrap-admin-recovery)), затем запустит Keycloak. Подождите ~1 минуту, откройте http://localhost/admin/ и войдите с `KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD` из `.env.local`.

2. **Сбросить БД Keycloak** — если пункт 1 не помог или нужна чистая БД:

   ```bash
   ./scripts/reset-keycloak-db.sh
   ```

   Realm **helpdesk** и клиент **helpdesk-backend** после сброса нужно будет создать заново по [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md).

3. **Не сбрасывать БД** — вспомнить или подобрать пароль, который был задан при самом первом запуске Keycloak.

---

## 7. Ошибка "Could not establish connection. Receiving end does not exist" (при нажатии Login)

Сообщение появляется в консоли браузера (часто из `polyfill.js` / `wrappedSendMessageCallback`). Это **не ошибка приложения** — его генерирует расширение браузера (парольный менеджер, блокировщик рекламы и т.п.), когда страница уходит на редирект и расширение пытается связаться с content script на новой странице.

**Что делать:** можно игнорировать; логин при этом должен проходить. Либо отключить расширение на `localhost` / для этого сайта.

---

## 8. Ошибка "invalid_token" / "Token claims validation failed: Invalid audience"

После входа Keycloak перенаправляет на callback, backend проверяет JWT. По умолчанию Keycloak может выдавать access token с полем `aud` (audience) = `"account"` (realm-level), а не client_id приложения.

**Что сделано в коде:** backend принимает оба варианта — и `KEYCLOAK_CLIENT_ID` (helpdesk-backend), и `"account"`. Обычно дополнительная настройка не нужна.

**Если у вас свой audience в токене:** задайте в `.env.local` переменную `KEYCLOAK_AUDIENCE` (одно значение или несколько через запятую). Тогда будет проверяться только указанный audience.

---

## 9. Ошибка "relation \"users\" does not exist"

Означает, что миграции БД не были выполнены — таблицы в PostgreSQL не созданы.

**Что сделать:** backend при старте сам запускает миграции (см. раздел 2). Пересоберите и перезапустите backend:

```bash
docker compose --env-file .env.local up -d --build backend
```

Либо выполните миграции вручную в уже запущенном контейнере:

```bash
docker compose --env-file .env.local exec backend python -m alembic upgrade head
```
