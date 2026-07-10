# Конфигурация Keycloak для HelpDesk

Авторизация реализована через паттерн **Backend-for-Frontend (BFF)**: бэкенд обменивает код авторизации на токены и передаёт их фронтенду. Пользователи создаются администратором в Keycloak, при первом логине бэкенд создаёт запись в Postgres.

---

## Оглавление

1. [Создание Realm](#1-создание-realm)
2. [Клиент helpdesk-backend](#2-клиент-helpdesk-backend)
3. [Маппинг claims токена на модель User](#3-маппинг-claims-токена-на-модель-user)
4. [Создание пользователей](#4-создание-пользователей)
5. [Роли (опционально)](#5-роли-опционально)
6. [Переменные окружения](#6-переменные-окружения)
6.1. [Production (VPS)](#61-production-vps--keycloak-и-docker-compose)
7. [Поток авторизации](#7-поток-авторизации)
8. [Устранение неполадок](#8-устранение-неполадок)
9. [Локальная разработка](#9-локальная-разработка)

---

## 1. Создание Realm

1. Откройте админ-панель Keycloak: `https://korxona.com/admin/`
2. Войдите (admin / пароль из `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`)
3. Наведите на выпадающий список Realm в левом верхнем углу
4. Нажмите **Create realm**
5. **Realm name:** `helpdesk`
6. Нажмите **Create**

---

## 2. Клиент helpdesk-backend

В Realm **helpdesk** → **Clients** → **Create client**.

### Шаг 1: General settings

| Поле | Значение |
|------|----------|
| Client type | OpenID Connect |
| Client ID | `helpdesk-backend` |

Нажмите **Next**.

### Шаг 2: Capability config

| Параметр | Значение |
|----------|----------|
| **Client authentication** | **ON** (confidential client) |
| **Authorization** | OFF |
| **Standard flow** | ✅ Включить |
| **Direct access grants** | ❌ Выключить |
| **Service accounts** | ❌ Выключить |

Нажмите **Next**.

### Шаг 3: Login settings

| Поле | Значение |
|------|----------|
| **Root URL** | `https://korxona.com` |
| **Home URL** | *(оставить пустым или `https://korxona.com`)* |
| **Valid redirect URIs** | Добавить по одному: |
| | `https://korxona.com/api/v1/auth/callback` |
| | `https://www.korxona.com/api/v1/auth/callback` |
| | `http://localhost:8000/api/v1/auth/callback` |
| **Valid post logout redirect URIs** | `https://korxona.com/login` |
| | `http://localhost:5173/login` |
| **Web origins** | `https://korxona.com` |
| | `https://www.korxona.com` |
| | `http://localhost:5173` |

Нажмите **Save**.

### Шаг 4: Получение Client secret

1. Откройте созданного клиента `helpdesk-backend`
2. Перейдите во вкладку **Credentials**
3. Скопируйте значение **Client secret**
4. Укажите его в `.env.prod` → `KEYCLOAK_CLIENT_SECRET`

### Шаг 5: Client scopes и маппинг на модель User

Бэкенд строит пользователя (модель **User**) из access token. Какие claim'ы нужны и откуда они берутся — см. [раздел 3](#3-маппинг-claims-токена-на-модель-user).

1. В клиенте **helpdesk-backend** откройте вкладку **Client scopes**.
2. В блоке **Assigned client scopes** назначьте:
   - **openid** (обязательно)
   - **email** (обязательно — для `email`, `email_verified`)
   - **profile** (для полного имени: `given_name`, `family_name`, `preferred_username` или `name`)
3. Настройте мапперы scope'ов под наши claim'ы по [разделу 3](#3-маппинг-claims-токена-на-модель-user).

Бэкенд запрашивает scope `openid email profile`. Если после логина вы попадаете на `/login?error=invalid_token`, проверьте, что в токене есть нужные claim'ы и что у пользователя в Keycloak заполнены соответствующие атрибуты.

### Шаг 6: PKCE (опционально)

Бэкенд всегда отправляет PKCE (S256): в запросе авторизации — `code_challenge` и `code_challenge_method=S256`, при обмене кода — `code_verifier`. Keycloak по умолчанию принимает PKCE для confidential-клиентов.

При необходимости в клиенте **helpdesk-backend** откройте вкладку **Advanced** → **Proof Key for Code Exchange Code Challenge Method** можно выставить **S256** (или оставить пусто/optional). Не обязательно включать «PKCE required» — достаточно optional или значение по умолчанию.

---

## 3. Маппинг claims токена на модель User

Бэкенд ожидает в access token следующие claim'ы и сопоставляет их с полями модели **User** и ответом `/auth/me`:

| Поле модели User / API | Claim в токене | Scope / источник в Keycloak |
|------------------------|----------------|-----------------------------|
| `keycloak_id`          | `sub`          | openid (всегда)             |
| `email`                | `email`        | **email**                   |
| `email_verified`       | `email_verified` | **email**                |
| `full_name`            | `name` или `given_name` + `family_name` или `preferred_username` | **profile** (см. ниже) |
| Роли                   | `realm_access.roles`, `resource_access.<client_id>.roles` | openid + роли в Keycloak |

Для **full_name** бэкенд подставляет значение в таком порядке: `name` → `given_name` + `family_name` → `preferred_username` → `email`. Достаточно, чтобы в токене было хотя бы одно из них.

### Настройка мапперов Keycloak под наши claim'ы

У scope **profile** в Keycloak по умолчанию есть мапперы на атрибуты пользователя (given name, family name, username и т.д.). Важно, чтобы в токен попадали нужные **Token Claim Name**:

1. **Realm** → **Client scopes** → **profile** → вкладка **Mappers**.
2. Проверьте или добавьте мапперы так, чтобы в access token были claim'ы:
   - **given_name** — из атрибута пользователя (например, Given name / first name).
   - **family_name** — из атрибута (Family name / last name).
   - **preferred_username** — обычно из **username** (логин пользователя в Keycloak). Если маппер называется "username", в настройках маппера должно быть **Token Claim Name**: `preferred_username`.
3. (Опционально) Один claim **name** (полное имя): в profile по умолчанию может не быть маппера с claim name `name`. Если нужно одно поле «ФИО»:
   - **Create** → **By configuration** → **User Attribute**: атрибут, где хранится полное имя (например, кастомный атрибут или конкатенация), **Token Claim Name**: `name`.

Итого по profile: достаточно, чтобы в токене были **given_name** и **family_name** (или **preferred_username**, или **name**). Бэкенд соберёт `full_name` из них автоматически.

У scope **email** должны быть claim'ы **email** и **email_verified** (обычно уже есть в стандартном scope email).

---

## 4. Создание пользователей

1. В Realm **helpdesk** → **Users** → **Add user**
2. Заполните:
   - **Username** — логин (например, `mark`)
   - **Email** — email (например, `mark@gmail.com`)
   - **Email verified** — включить
3. Нажмите **Create**
4. Перейдите во вкладку **Credentials** → **Set password**
5. Задайте пароль, при необходимости выключите **Temporary**
6. Нажмите **Save**

Пользователь сможет войти по email/паролю через форму Keycloak.

---

## 5. Роли (опционально)

### Realm roles

**Realm roles** → **Create role** — например, `user`, `admin`. Назначаются в **Users** → [пользователь] → **Role mapping** → **Assign role**.

### Client roles

В **Clients** → **helpdesk-backend** → **Roles** → **Create role**. Бэкенд сопоставляет имена ролей с перечислением **User** в БД. Создайте роли с именами **точно**: `user`, `department_head`, `executor`, `admin` (регистр не важен). Они попадут в JWT: `resource_access.helpdesk-backend.roles`. Неизвестные имена в токене обрабатываются как `user`.

---

## 5.1. Атрибуты департамента в JWT

Бэкенд хранит департаменты в своей БД (UUID `id` + admin-friendly `number`). При смене департамента у пользователя через `PUT /api/v1/users/{id}` бэкенд пишет в Keycloak два custom user attribute:

- `department_id` — UUID департамента (стабильный, неизменяемый);
- `department_number` — короткий целочисленный номер для админ-UI.

Чтобы они попадали в access token (а значит в `TokenUser.department` и в дальнейшую логику), нужно добавить мапперы:

1. **Realm helpdesk → Client scopes → profile → Mappers → Add mapper → By configuration → User Attribute**:
   - **Name:** `department_id`
   - **User Attribute:** `department_id`
   - **Token Claim Name:** `department_id`
   - **Claim JSON Type:** String
   - **Add to access token:** ON; **Add to ID token:** опционально.
2. Повторить для `department_number` (Claim JSON Type: String — Keycloak хранит атрибуты строками, бэкенд приводит к int при необходимости).

Альтернатива: создать отдельный client scope `department` с теми же мапперами и назначить его в **helpdesk-backend → Client scopes → Default**.

### Service-account клиент для Admin API

Для записи атрибутов бэкенд использует Keycloak Admin REST API (`PUT /admin/realms/helpdesk/users/{id}`) под client_credentials. Два варианта настройки:

**А) Отдельный admin-клиент (рекомендуется).**

1. **Clients → Create client → OpenID Connect**, Client ID: `helpdesk-admin`.
2. Capability config: **Client authentication** ON, **Authorization** OFF, **Service accounts roles** ✅ ON, остальные flow выключены.
3. После создания: **Service accounts roles → Assign role → Filter by clients → realm-management** → назначить **view-users** и **manage-users**.
4. **Credentials** → скопировать секрет.
5. В `.env.prod`/`.env.local`:
   ```
   KEYCLOAK_ADMIN_CLIENT_ID=helpdesk-admin
   KEYCLOAK_ADMIN_CLIENT_SECRET=<секрет>
   ```

**Б) Использовать helpdesk-backend.**

Включить **Service accounts roles** на клиенте `helpdesk-backend` и назначить ему `view-users` + `manage-users` из `realm-management`. Тогда `KEYCLOAK_ADMIN_CLIENT_ID/SECRET` оставлять пустыми — бэкенд возьмёт `KEYCLOAK_CLIENT_ID/SECRET`. Минус: расширяете права BFF-клиента, миксуете разные потоки на одном client_id.

При неудачном вызове Admin API (Keycloak недоступен, нет ролей, неверный секрет) `PUT /api/v1/users/{id}` вернёт **502 user.keycloak_sync_failed** и DB-транзакция откатится — данные в Postgres и Keycloak не разъезжаются.

---

## 6. Переменные окружения

В `.env.prod` должны быть указаны:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `KEYCLOAK_URL` | Внутренний URL Keycloak (Docker) | `http://keycloak:8080` |
| `KEYCLOAK_REALM` | Имя Realm | `helpdesk` |
| `KEYCLOAK_CLIENT_ID` | Client ID | `helpdesk-backend` |
| `KEYCLOAK_CLIENT_SECRET` | Секрет из Keycloak Credentials | *(из Keycloak)* |
| `KEYCLOAK_ADMIN_CLIENT_ID` | Опционально: отдельный client_id для Admin API. Если пусто — используется `KEYCLOAK_CLIENT_ID` (нужны service accounts на нём). | `helpdesk-admin` |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | Секрет admin-клиента. Если пусто — используется `KEYCLOAK_CLIENT_SECRET`. | *(из Keycloak)* |
| `KEYCLOAK_ISSUER` | Публичный issuer для JWT | `https://korxona.com/realms/helpdesk` |
| | **Keycloak 17+:** путь issuer — только `/realms/{realm}` (без префикса `/auth`). JWT содержит именно такой issuer; значение в `.env.prod` должно совпадать. | |
| `FRONTEND_URL` | URL фронтенда | `https://korxona.com` |
| `AUTH_CALLBACK_URL` | Callback для обмена code | `https://korxona.com/api/v1/auth/callback` |

---

## 6.1. Production (VPS) — Keycloak и docker-compose

Для продакшена на VPS используется отдельный файл **`docker-compose.prod.yml`** — полный стек со всеми сервисами, секреты и пароли только из `.env.prod`. Файл `docker-compose.yml` предназначен для локальной разработки.

### Запуск на VPS

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

**Почему при `up -d` сначала видны только часть контейнеров:** в `docker-compose.prod.yml` заданы условия зависимостей (`depends_on` с `condition`). Порядок такой:

1. Стартуют **db**, **keycloak-db**, **frontend** (у них нет блокирующих зависимостей).
2. **frontend** отрабатывает (копирует статику в volume) и завершается — контейнер в статусе Exited, это нормально.
3. **keycloak** стартует после того, как keycloak-db станет healthy, и сам должен стать healthy (healthcheck).
4. **backend** не запускается, пока не станет healthy **keycloak** (и db).
5. **nginx** не запускается, пока не станут healthy **backend** и **keycloak** (и завершится frontend).

Пока keycloak в статусе Waiting (не healthy), backend и nginx не стартуют — поэтому видно только 2–3 контейнера в работе. После того как keycloak станет healthy, Compose по очереди поднимет backend и nginx. Все контейнеры можно посмотреть командой: `docker ps -a`.

### Обязательные переменные в `.env.prod` для продакшена

| Переменная в .env.prod | Используется в docker-compose.prod.yml | Описание |
|------------------------|----------------------------------------|----------|
| `POSTGRES_USER` | db → `POSTGRES_USER` | Пользователь БД приложения. |
| `POSTGRES_PASSWORD` | db → `POSTGRES_PASSWORD` | Пароль основной БД (helpdesk). |
| `POSTGRES_DB` | db → `POSTGRES_DB` | Имя БД приложения. |
| `KEYCLOAK_DB_NAME` | keycloak-db → `POSTGRES_DB`, keycloak → `KC_DB_URL` | Имя БД Keycloak. |
| `KEYCLOAK_DB_USER` | keycloak-db → `POSTGRES_USER`, keycloak → `KC_DB_USERNAME` | Пользователь БД Keycloak. |
| `KEYCLOAK_DB_PASSWORD` | keycloak-db → `POSTGRES_PASSWORD`, keycloak → `KC_DB_PASSWORD` | Пароль БД Keycloak. |
| `KEYCLOAK_ADMIN_USERNAME` | keycloak → **KC_BOOTSTRAP_ADMIN_USERNAME** | Логин админа Keycloak (например, `admin`). |
| `KEYCLOAK_ADMIN_PASSWORD` | keycloak → **KC_BOOTSTRAP_ADMIN_PASSWORD** | Пароль админа Keycloak. |
| `KEYCLOAK_PUBLIC_URL` | keycloak → `KC_HOSTNAME` | Публичный URL Keycloak без пути: `https://korxona.com`. |

Остальные переменные — см. `.env.prod.example` и [раздел 6](#6-переменные-окружения).

**Важно: вход в админ-консоль Keycloak.** В `.env.prod` **обязательно** должны быть заданы **и** `KEYCLOAK_ADMIN_USERNAME`, **и** `KEYCLOAK_ADMIN_PASSWORD`. Если пароль отсутствует или пустой, bootstrap-админ может не создаться или оказаться непригодным для входа. Логин и пароль попадают в контейнер как `KC_BOOTSTRAP_ADMIN_USERNAME` и `KC_BOOTSTRAP_ADMIN_PASSWORD`. Keycloak применяет bootstrap-учётку **только при первой инициализации БД**. Если БД Keycloak уже существовала (например, после предыдущего запуска с другими значениями), в базе остаётся старый админ — смена переменных при перезапуске не обновляет уже созданного пользователя. Что сделать: (1) Проверить, что в контейнер действительно передаются нужные значения: `docker exec helpdesk-keycloak env | grep KC_BOOTSTRAP`. (2) Если нужно войти именно с текущими `KEYCLOAK_ADMIN_*`, пересоздать БД Keycloak (удалить volume `helpdesk_keycloak_db_data`, затем `up -d`) и заново создать realm/клиента по инструкции.

**Ошибка в логах: `LOGIN_ERROR` … `error="user_not_found"`, `username="admin"`.** Это значит, что пользователь **admin** в realm **master** в БД Keycloak отсутствует. Bootstrap-админ создаётся только при **первой** инициализации пустой БД. Если БД создавалась после сбоев (Liquibase, перезапуски) или из бэкапа, учётка могла не создаться. **Решение:** заново создать БД Keycloak и дать Keycloak инициализировать её с нуля (см. [Решение A — чистая БД](#решение-a--чистая-бд-если-данные-keycloak-не-нужны)); после этого войти как admin / пароль из `KEYCLOAK_ADMIN_PASSWORD`.

### Что даёт `docker-compose.prod.yml`

- **Полный стек**: все сервисы (nginx, frontend, backend, db, keycloak-db, keycloak) в одном файле для развёртывания на сервере.
- **Keycloak**: фиксированная версия образа (например `keycloak:25.0.6`) вместо `latest`.
- **Секреты**: пароли админа и БД Keycloak (и основной Postgres) только из `.env.prod`, не в коде.
- **Режим**: `KC_PROXY_HEADERS=xforwarded`, `KC_HOSTNAME` (полный URL из `KEYCLOAK_PUBLIC_URL`), `KC_LOG_LEVEL=WARN`.
- **Ресурсы**: лимиты памяти для контейнеров (nginx, backend, db, keycloak-db, keycloak), чтобы один сервис не исчерпывал память VPS.

### Чеклист безопасности на VPS

1. В `.env.prod` задать уникальные пароли для `POSTGRES_PASSWORD`, `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`.
2. Файл `.env.prod` не коммитить в репозиторий (должен быть в `.gitignore`).
3. Доступ к `/admin/` ограничен по IP в `nginx/nginx.conf`; при смене IP добавить новый в `allow` или временно использовать `/nginx-client-ip` для отладки.
4. TLS терминация на nginx (ключи в `./nginx/ssl/`), Keycloak за прокси с `KC_PROXY_HEADERS=xforwarded`.

---

## 7. Поток авторизации

Бэкенд использует **PKCE (S256)** для защиты обмена кода на токены: только сервер с сохранённым `code_verifier` может успешно обменять authorization code.

1. Пользователь нажимает «Войти» на фронтенде.
2. Фронт редиректит на `GET /api/v1/auth/login?redirect_uri=...`
3. Бэкенд генерирует `code_verifier` и `code_challenge`, сохраняет verifier по `state`, перенаправляет на страницу логина Keycloak с параметрами `code_challenge` и `code_challenge_method=S256`.
4. Пользователь вводит email/пароль в Keycloak.
5. Keycloak редиректит на `AUTH_CALLBACK_URL?code=...&state=...`
6. Бэкенд по `state` достаёт `code_verifier`, обменивает `code` на токены (с `client_id`, `client_secret` и `code_verifier`).
7. Бэкенд создаёт/обновляет пользователя в Postgres.
8. Бэкенд редиректит на фронт: `redirect_uri#access_token=...&refresh_token=...&expires_in=...`
9. Фронт читает токены из hash, сохраняет, вызывает `/auth/me` для профиля.

**PKCE и несколько инстансов backend:** `code_verifier` хранится в памяти одного процесса. Если callback попадёт на другой инстанс (горизонтальное масштабирование), пользователь получит `pkce_expired`. Для нескольких инстансов нужны sticky-сессии для `/auth/*` или вынос хранилища PKCE (например Redis).

**Токены:** Фронт не обновляет access token по refresh_token; после истечения access token запросы возвращают 401 и пользователь логинится заново. Выход: редирект на Keycloak end_session с `post_logout_redirect_uri` (без `id_token_hint`; при необходимости можно добавить для более точного завершения сессии в Keycloak).

---

## 8. Устранение неполадок

| Ошибка после логина | Причина | Что проверить |
|---------------------|--------|----------------|
| **We are sorry… Page not found** (при переходе на `/realms/helpdesk/...`) | Nginx не проксирует Keycloak или путь неверный. | В `nginx.conf` должны быть `location /realms/` и `location /admin/` с `proxy_pass http://keycloak;`. В `.env.prod`: `KEYCLOAK_ISSUER=https://korxona.com/realms/helpdesk`, `KEYCLOAK_PUBLIC_URL=https://korxona.com`. Перезапустить nginx и Keycloak. |
| `error=invalid_token` | Бэкенд не смог разобрать access token (нет полей или неверные типы). | Клиент **helpdesk-backend** → **Client scopes**: назначены **email** и **profile**. У пользователя в Keycloak заполнены **Email** и **Username**. На VPS в `.env.prod`: `KEYCLOAK_ISSUER=https://korxona.com/realms/helpdesk`. |
| `error=token_exchange` | Обмен кода на токены не удался. | **AUTH_CALLBACK_URL** в `.env.prod` совпадает с одной из **Valid redirect URIs** в Keycloak (вплоть до слеша). **KEYCLOAK_CLIENT_SECRET** скопирован из Keycloak. С бэкенда (контейнера) доступен **KEYCLOAK_URL** (например `http://keycloak:8080`). |
| `error=invalid_state` | Неверный или подменённый state. | Повторить вход; не менять state в URL вручную. |
| `error=pkce_expired` | code_verifier не найден или истёк (повторное использование ссылки callback, долгая задержка). | Повторить вход с начала (нажать «Войти» снова). |

**Кэширование и PKCE:** Бэкенд отправляет для всех редиректов авторизации заголовки `Cache-Control: no-store`, `Pragma: no-cache`, `Expires: 0`, чтобы ответ 302 с `/auth/login` не кэшировался браузером или прокси. Если редирект кэшируется, при следующем нажатии «Войти» браузер может использовать старый state, и при callback code_verifier не будет найден → `pkce_expired`.

**Несколько инстансов backend:** Хранилище PKCE (code_verifier) — в памяти одного процесса. Если callback попадёт на другой инстанс (несколько воркеров uvicorn или реплик за балансировщиком), пользователь получит `pkce_expired`. Решения: один процесс backend (без `--workers`), sticky-сессии для `/api/v1/auth/*` или вынос хранилища PKCE (например Redis). Не обновляйте страницу callback и не используйте ссылку callback повторно.

### Восстановление доступа админа (Admin user recovery)

Bootstrap-админ создаётся **только при первом старте**, когда realm **master** ещё не существует. Если в консоли Keycloak при логине появляется «user doesn't exist» для admin:

- **Если БД Keycloak пустая (первый деплой):**  
  Убедитесь, что в `.env.prod` заданы `KEYCLOAK_ADMIN_USERNAME` и `KEYCLOAK_ADMIN_PASSWORD`, затем запустите стек. Keycloak создаст bootstrap-админа при инициализации.

- **Если БД Keycloak уже есть, но админ не создался или недоступен:**  
  Возможны два варианта:
  1. **Чистый старт (если данные Keycloak не нужны):**  
     Остановите контейнеры, удалите volume БД Keycloak (`helpdesk_keycloak_db_data`), задайте в `.env.prod` оба параметра `KEYCLOAK_ADMIN_USERNAME` и `KEYCLOAK_ADMIN_PASSWORD`, затем снова выполните `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d`. После этого заново создайте realm и клиента по разделам 1–2.
  2. **Восстановление без потери данных:**  
     Остановите контейнер Keycloak. Запустите одноразовый контейнер с тем же образом и теми же переменными БД и админа, выполнив команду Keycloak для создания временного админа:
     ```bash
     docker run --rm -it --network helpdesk-network \
       -e KC_DB=postgres \
       -e KC_DB_URL=jdbc:postgresql://keycloak-db:5432/keycloak \
       -e KC_DB_USERNAME=keycloak -e KC_DB_PASSWORD=YOUR_KEYCLOAK_DB_PASSWORD \
       -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=your_admin_password \
       quay.io/keycloak/keycloak:25.0.6 bootstrap-admin user
     ```
     Подставьте свои значения из `.env.prod` для БД и пароля админа. Затем снова запустите контейнер Keycloak и войдите с указанным логином и паролем.

На VPS бэкенд ходит в Keycloak по внутреннему `KEYCLOAK_URL` (например `http://keycloak:8080`), а issuer в JWT должен быть публичным — для этого задаётся **KEYCLOAK_ISSUER** (например `https://korxona.com/realms/helpdesk`).

### Liquibase ValidationFailedException (changesets checksum)

Ошибка в логах Keycloak:

```
liquibase.exception.ValidationFailedException: Validation Failed:
1 changesets check sum
    META-INF/jpa-changelog-2.5.0.xml::2.5.0-unicode-oracle::... was: 9:... but is now: 9:...
```

**Причина:** БД Keycloak была инициализирована одной версией образа (например `:latest` или другой тег), затем образ сменили (например на `:25.0.6`). В новой версии тот же Liquibase-changeset имеет другой checksum — Liquibase отказывается стартовать.

**Решение A — чистая БД (если данные Keycloak не нужны):**

1. Остановить стек и удалить контейнеры и volume БД Keycloak:
   ```bash
   cd ~/helpdesk
   docker compose -f docker-compose.prod.yml --env-file .env.prod down
   docker rm -f helpdesk-keycloak helpdesk-keycloak-db 2>/dev/null || true
   docker volume rm helpdesk_keycloak_db_data
   ```
   Если `volume rm` выдаёт «volume is in use», сначала принудительно удалите контейнеры:  
   `docker rm -f helpdesk-keycloak helpdesk-keycloak-db`, затем снова `docker volume rm helpdesk_keycloak_db_data`.
2. Запустить снова — Keycloak создаст БД заново и применит миграции с актуальными checksums:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```
3. Заново создать realm, клиента и пользователей по разделам 1–4 этой инструкции.

**Решение B — сохранить данные (обновить checksum в БД):**

Подключиться к PostgreSQL Keycloak и обновить запись в таблице Liquibase (подставьте новый checksum из сообщения об ошибке — значение после «but is now: »):

```bash
docker exec -it helpdesk-keycloak-db psql -U keycloak -d keycloak -c "
UPDATE databasechangelog
SET md5sum = '9:3a32bace77c84d7678d035a7f5a8084e'
WHERE id = '2.5.0-unicode-oracle' AND author = 'hmlnarik@redhat.com';
"
```

Затем перезапустить контейнер Keycloak: `docker restart helpdesk-keycloak`.

**Профилактика:** Использовать один и тот же тег образа Keycloak (например только `:25.0.6`). При апгрейде версии Keycloak следовать [официальной инструкции по обновлению БД](https://www.keycloak.org/docs/latest/upgrading/).

### Контейнер Keycloak в статусе Waiting / не становится healthy

**Что видно:** `helpdesk-keycloak` всё время в статусе **Waiting** или **starting**, nginx не поднимается (ждёт Keycloak).

**Причины:**

1. **Keycloak падает при старте** (чаще всего — ошибка Liquibase, см. выше). Контейнер перезапускается, healthcheck не успевает пройти → сервис не переходит в healthy → зависимые сервисы ждут.
2. **Keycloak ждёт keycloak-db** — тогда сам Keycloak в статусе «Waiting» до готовности БД.
3. **Healthcheck не срабатывает** — порт 9000/8080 не открыт в ожидаемый момент или формат проверки не подходит.

**Что сделать по шагам:**

1. Посмотреть логи Keycloak:
   ```bash
   docker logs helpdesk-keycloak --tail 100
   ```
   Если есть **ValidationFailedException** (Liquibase checksum) — сначала устранить её: [Liquibase ValidationFailedException](#liquibase-validationfailedexception-changesets-checksum) (очистить volume БД или обновить checksum в БД).

2. Проверить ключ БД Keycloak:
   ```bash
   docker ps -a --filter name=helpdesk-keycloak-db
   docker logs helpdesk-keycloak-db --tail 20
   ```
   Убедиться, что контейнер `helpdesk-keycloak-db` в статусе **Up** и healthy.

3. После исправления Liquibase/БД перезапустить стек:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

4. **Keycloak «зависает» в Waiting больше 5–10 минут:**  
   - Посмотреть последние логи: `docker logs helpdesk-keycloak --tail 80`. Если есть ошибка (Liquibase, OOM и т.п.) — устранить её.  
   - Проверить, слушает ли Keycloak порт 8080 изнутри контейнера:  
     `docker exec helpdesk-keycloak bash -c 'echo -n >/dev/tcp/127.0.0.1/8080' 2>/dev/null && echo OK || echo FAIL`  
     Если **OK** — Keycloak уже слушает, но healthcheck не срабатывает (например, другой shell).  
   - *(Временно.)* Отключить healthcheck у Keycloak, чтобы nginx и backend могли стартовать: в `docker-compose.prod.yml` у сервиса `keycloak` закомментировать весь блок `healthcheck:` (все строки с `test:`, `interval:`, `timeout:`, `retries:`, `start_period:`). Затем:  
     `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate keycloak`  
     После этого Keycloak будет считаться «running» без проверки здоровья; nginx и backend поднимутся. Проверьте в браузере `/auth` — если Keycloak отвечает, позже можно вернуть healthcheck.

### Нормальные сообщения при первом старте Keycloak

При первом запуске (или после смены конфигурации) в логах ожидаемы:

- **«Changes detected in configuration. Updating the server image.»** — Keycloak собирает образ (Quarkus augmentation), это нормально.
- **«Next time you run the server, just run: kc.sh start --optimized»** — сборка завершена, при следующем запуске контейнера можно использовать быстрый старт.
- **«Run: 134, Previously run: 0, Total change sets: 134»** — Liquibase применил миграции к БД (134 changeset).

После этого Keycloak поднимает сервер (порты 8080 и 9000). Подождите 1–3 минуты и проверьте: `docker ps` (статус **healthy** у `helpdesk-keycloak`) и `docker logs helpdesk-keycloak --tail 20` (должна быть строка о запуске сервера). Keycloak доступен по `https://korxona.com/realms/` и админка по `https://korxona.com/admin/`. Предупреждения про **JGroups buffer** и **X-Forwarded-*** в проде допустимы при корректной настройке прокси.

---

## 9. Локальная разработка

- Keycloak: `http://localhost:8080` (или `docker compose up` для keycloak).
- В **Valid redirect URIs** клиента `helpdesk-backend` добавьте: `http://localhost:8000/api/v1/auth/callback`.
- В `.env` локально:
  - `KEYCLOAK_URL=http://localhost:8080`
  - `KEYCLOAK_ISSUER=http://localhost:8080/realms/helpdesk` (или пусто)
  - `FRONTEND_URL=http://localhost:5173`
  - `AUTH_CALLBACK_URL=http://localhost:8000/api/v1/auth/callback`
