# HelpDesk — развёртывание во внутренней сети организации

Эта инструкция предназначена для **системного администратора корпоративной
сети**, которому поручено развернуть HelpDesk на сервере, доступном **только
из внутренней сети организации** (corporate intranet, LAN). В интернет приложение
не выставляется.

В отличие от `docs/DEPLOY_VPS.md` (внешний VPS, доступ по голому IP по HTTP),
этот сценарий предполагает:

- внутренний FQDN из корпоративной DNS-зоны (не `localhost`, не голый IP);
- TLS-сертификат от **внутреннего CA** организации (не Let's Encrypt — он не
  выпускает на приватные домены);
- доступ по сети только из CIDR корпоративной LAN;
- ни один порт стека (кроме HTTPS на nginx) не публикуется наружу.

`docs/DEPLOY_VPS.md` остаётся источником истины по командам запуска,
обновлению, бэкапу — этот документ дополняет его требованиями корпоративной
эксплуатации. Где это уместно, ниже даются ссылки.

---

## 0. Архитектура целевого развёртывания

```
   Корпоративная LAN (10.0.0.0/8 или 192.168.0.0/16)
   ─────────────────────────────────────────────────
              │
              │ HTTPS (443) + HTTP-редирект (80)
              ▼
   ┌──────────────────────────────────────┐
   │  VPS / bare-metal в серверной        │
   │  helpdesk.corp.example.lan           │
   │                                      │
   │  ┌─────────────────────────────────┐ │
   │  │ nginx (443)                     │ │  ← единственная точка входа
   │  │   ├─ /            → frontend    │ │
   │  │   ├─ /api/        → backend     │ │
   │  │   ├─ /realms/     → keycloak    │ │
   │  │   ├─ /admin/      → keycloak (allow-list LAN)
   │  │   └─ /media/      → minio       │ │
   │  └─────────────────────────────────┘ │
   │      backend, keycloak, postgres,    │
   │      redis, minio — только в         │
   │      docker-сети, без публикации     │
   │      портов на хост                  │
   └──────────────────────────────────────┘
```

Никакой внешний IP / NAT / public DNS не используется. Доступ из дома —
только через корпоративный VPN.

---

## 1. Что нужно согласовать заранее

До начала работ соберите от смежных команд (DNS-инженер, безопасность,
PKI, сетевики):

| Артефакт | От кого | Пример |
|---|---|---|
| Внутренний FQDN | DNS-инженер | `helpdesk.corp.example.lan` |
| A-запись FQDN → LAN-IP сервера | DNS-инженер | `helpdesk.corp.example.lan A 10.20.30.40` |
| TLS-сертификат на FQDN | PKI / Security | `fullchain.pem` + `privkey.pem` от внутреннего CA |
| CIDR корпоративной LAN | Сетевики | `10.0.0.0/8`, `192.168.0.0/16` |
| LAN-IP сервера | Сетевики | `10.20.30.40` |
| Контакт для распространения корневого CA | Workplace IT | обычно через GPO/MDM, должен уже быть в trust store рабочих машин |

Без подписанного TLS-сертификата от **доверенного клиентами CA** браузеры будут
показывать предупреждение, и Keycloak не сможет ставить `Secure`-куки —
соответственно вход в систему будет ломаться. Самоподписанный сертификат — **не**
рабочий вариант для прод-эксплуатации. Если внутреннего CA в организации нет,
поднимите [step-ca](https://smallstep.com/docs/step-ca) и распространите
корневой через GPO.

---

## 2. Подготовка хоста

Минимальные требования к серверу:

- Ubuntu 22.04 LTS / Debian 12 (или совместимый Linux с systemd).
- Docker Engine 24+ и Docker Compose v2 (`docker compose`, **не** `docker-compose`).
- 4 ГБ RAM, 20 ГБ свободного диска (база + minio + образы).
- Учётка в группе `docker` для запуска стека (не root в обычной работе).
- Временный исходящий доступ в интернет на этапе установки — нужен для
  `apt`, `docker pull`, `git clone`. После запуска стек работает офлайн.

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 ufw git
sudo usermod -aG docker $USER
# Перелогиниться, чтобы группа docker применилась
```

---

## 3. Файрвол: впускать только корпоративную LAN

Базовая политика — `default deny`, разрешено только из CIDR корпоративной сети
на 22 (SSH), 80 (редирект на HTTPS) и 443 (HTTPS).

```bash
# Подставьте свой CIDR корпоративной LAN
CORP_CIDR=10.0.0.0/8

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from $CORP_CIDR to any port 22  proto tcp
sudo ufw allow from $CORP_CIDR to any port 80  proto tcp
sudo ufw allow from $CORP_CIDR to any port 443 proto tcp
sudo ufw enable
sudo ufw status verbose
```

### ⚠️ Docker умеет обходить UFW

Когда Docker публикует порт через `ports: "80:80"`, он добавляет правила
напрямую в iptables, **минуя цепочки UFW**. Правила `ufw deny` его не остановят.
Решение — публиковать порты только на LAN-интерфейс сервера, а не на
`0.0.0.0`. В `docker-compose.prod.yml` для сервиса `nginx`:

```yaml
nginx:
  ports:
    - "10.20.30.40:80:80"     # ← подставьте реальный LAN-IP сервера
    - "10.20.30.40:443:443"
```

Так Docker привяжет сокет только к LAN-интерфейсу. Если у сервера есть
второй (внешний) интерфейс с публичным IP, `nginx` на нём слушать не будет.

Проверка после запуска:

```bash
sudo ss -tlnp | grep -E ':(80|443) '
# Должно быть только на LAN-IP, не на 0.0.0.0 / *.
```

---

## 4. DNS

Попросите DNS-инженера завести A-запись в корпоративной зоне:

```
helpdesk.corp.example.lan.    IN  A   10.20.30.40
```

Никаких публичных DNS-провайдеров (Cloudflare, Route53) — только внутренний
DNS-сервер организации. Проверьте с рабочей станции:

```bash
nslookup helpdesk.corp.example.lan
```

Если внутренний DNS в организации отсутствует, временный fallback — записи
в `/etc/hosts` на каждой клиентской машине, но это **не** решение для прода
(сложно поддерживать, ломается с любого нового устройства).

---

## 5. TLS-сертификат

1. Запросите у PKI-команды сертификат на `helpdesk.corp.example.lan`,
   выпущенный внутренним корпоративным CA. Формат — PEM:
   `fullchain.pem` (сертификат + промежуточные) и `privkey.pem`.
2. Положите файлы на сервере:

   ```bash
   sudo mkdir -p /opt/helpdesk/nginx/ssl
   sudo cp fullchain.pem /opt/helpdesk/nginx/ssl/
   sudo cp privkey.pem   /opt/helpdesk/nginx/ssl/
   sudo chmod 600 /opt/helpdesk/nginx/ssl/privkey.pem
   sudo chown root:root /opt/helpdesk/nginx/ssl/*
   ```
3. Срок действия: внутренние CA обычно выпускают на 1–2 года. Поставьте в
   календарь напоминание за 30 дней до истечения, ротация — копированием
   новых файлов в ту же папку и `make prod-recreate`.

Корневой сертификат внутреннего CA должен быть в trust store у всех
клиентских машин. У корпоративных рабочих станций это обычно уже сделано
через GPO (Windows) или MDM (macOS). Уточните у Workplace IT.

---

## 6. Клонирование репозитория и `.env.prod`

```bash
sudo mkdir -p /opt/helpdesk && sudo chown $USER:$USER /opt/helpdesk
cd /opt/helpdesk
git clone https://gitlab.com/devshilov/helpdesk.git .
git checkout main
make env-prod
```

Откройте `.env.prod` и замените **все** заглушки IP/доменов на ваш FQDN.
Ключевые поля для интранет-развёртывания (схема — обязательно `https://`):

```dotenv
KEYCLOAK_PUBLIC_URL=https://helpdesk.corp.example.lan
KEYCLOAK_ISSUER=https://helpdesk.corp.example.lan/realms/helpdesk
FRONTEND_URL=https://helpdesk.corp.example.lan
AUTH_CALLBACK_URL=https://helpdesk.corp.example.lan/api/v1/auth/callback
ALLOWED_CORS_ORIGINS=https://helpdesk.corp.example.lan
MINIO_PUBLIC_BASE_URL=https://helpdesk.corp.example.lan/media
```

`MINIO_PUBLIC_BASE_URL` обязательно с суффиксом `/media` — порт 9000 на
хост не публикуется, картинки активов идут через nginx (см. §8). Использовать
`/assets` нельзя: по этому пути отдаются JS/CSS-бандлы фронта (Vite собирает
в `dist/assets/`).

Сгенерируйте сильные секреты:

```bash
openssl rand -base64 24   # для каждого: POSTGRES_PASSWORD, KEYCLOAK_DB_PASSWORD,
                          # KEYCLOAK_ADMIN_PASSWORD, MINIO_ROOT_PASSWORD
```

Подставьте `POSTGRES_PASSWORD` ещё и в `DATABASE_URL`. `KEYCLOAK_CLIENT_SECRET`
оставьте пустым — он заполняется после §10.

Закройте файл от чтения:

```bash
chmod 600 .env.prod
```

---

## 7. Конфигурация nginx (HTTPS + редирект)

Замените `nginx/nginx.conf` на HTTPS-вариант. Шаблон есть в
`nginx/nginx.https.conf.example` — он уже включает `/api/`, `/realms/`,
`/admin/` (с allow-list LAN), `/media/` и `/health`. Что нужно поправить
руками:

1. **`server_name`** — ваш внутренний FQDN:
   ```nginx
   server_name helpdesk.corp.example.lan;
   ```
2. **Пути к сертификату** — проверьте:
   ```nginx
   ssl_certificate     /etc/nginx/ssl/fullchain.pem;
   ssl_certificate_key /etc/nginx/ssl/privkey.pem;
   ```
3. **`upstream`-блоки** — скопируйте из `nginx/nginx.conf` в начало файла
   (`backend`, `keycloak`, `minio`):
   ```nginx
   upstream backend  { server backend:8000; }
   upstream keycloak { server keycloak:8080; }
   upstream minio    { server minio:9000; }
   ```
4. **HTTP-сервер на :80** — оставьте только редирект:
   ```nginx
   server {
       listen 80;
       server_name helpdesk.corp.example.lan;
       location / { return 301 https://$host$request_uri; }
   }
   ```
5. **Allow-list для `/admin/`** — добавьте CIDR корпоративной LAN, удалите
   публичные IP из шаблона:
   ```nginx
   location /admin/ {
       allow 10.0.0.0/8;            # ← ваш CORP_CIDR
       allow 192.168.0.0/16;
       deny all;
       proxy_pass http://keycloak;
       ...
   }
   ```

Ничего больше из шаблона править не нужно — `/media/` уже корректно
проксирует на `minio:9000` и стрипает префикс.

---

## 8. Привязка nginx к LAN-интерфейсу

В `docker-compose.prod.yml` найдите сервис `nginx` и пропишите LAN-IP
сервера в `ports` (см. §3):

```yaml
nginx:
  ports:
    - "10.20.30.40:80:80"
    - "10.20.30.40:443:443"
```

Это гарантирует, что Docker не опубликует порты на любые другие интерфейсы
(в т.ч. `0.0.0.0`), и UFW-политика становится единственным каналом доступа.

---

## 9. Первый запуск стека

```bash
cd /opt/helpdesk
make prod-up
make prod-ps
make prod-logs-backend     # Ctrl+C когда увидите "Application startup complete"
```

Ожидаемый порядок:

1. `db`, `keycloak-db`, `redis`, `minio` стартуют первыми.
2. `keycloak` — после healthy `keycloak-db`.
3. `backend` — после healthy `db`/`redis`/`minio`. На старте entrypoint
   автоматически выполняет `alembic upgrade head` (миграция 008 создаёт
   PostgreSQL extension `vector` — это работает, потому что `db` поднят
   на образе `pgvector/pgvector:pg16`).
4. `frontend` — одноразовый build-контейнер, завершается с кодом 0
   (статика остаётся в volume `helpdesk_frontend_static`).
5. `nginx` — последним, после успешной сборки фронта и healthy backend.

Smoke-тесты (с самого сервера или из LAN):

```bash
curl -sk https://helpdesk.corp.example.lan/health     # → {"status":"healthy"}
curl -skI https://helpdesk.corp.example.lan/          # → 200 OK, index.html
```

С внешней (не-LAN) машины — должен быть `Connection refused` или таймаут.
Это и есть подтверждение, что firewall работает.

---

## 10. Первичная настройка Keycloak

Админка Keycloak (`/admin/`) ограничена allow-list корпоративной LAN, прямого
доступа из интернета нет. С рабочей машины внутри LAN откройте:

```
https://helpdesk.corp.example.lan/admin/
```

Логин — `admin` / `<KEYCLOAK_ADMIN_PASSWORD>` из `.env.prod`. Дальше следуйте
[`docs/KEYCLOAK_SETUP.md`](./KEYCLOAK_SETUP.md). Краткий чек-лист с поправкой
на FQDN:

1. **Realm** `helpdesk`.
2. **Client** `helpdesk-backend`, type «OpenID Connect», access type «confidential».
3. **Valid Redirect URIs:**
   - `https://helpdesk.corp.example.lan/api/v1/auth/callback`
   - `https://helpdesk.corp.example.lan/login`
4. **Valid Post Logout Redirect URIs:** `https://helpdesk.corp.example.lan/login`
5. **Web Origins:** `https://helpdesk.corp.example.lan`
6. **Client → Credentials → Client Secret** — скопируйте.
7. На сервере вставьте в `KEYCLOAK_CLIENT_SECRET` в `.env.prod`.
8. Перезапустите бэкенд (Keycloak трогать не нужно):

   ```bash
   make prod-build-backend
   ```

После этого: смените пароль bootstrap-админа на сильный и (опционально)
удалите его, создав отдельного реального админа — bootstrap-учётка задумана
как одноразовая.

---

## 11. Финальная проверка

С рабочей станции в LAN:

1. Открыть `https://helpdesk.corp.example.lan/` — браузер показывает страницу
   без предупреждений по сертификату (если корневой CA в trust store клиента —
   это так).
2. Нажать «Войти» → редирект на Keycloak (тот же FQDN, через `/realms/...`),
   логин, редирект обратно на дашборд.
3. Создать тестовый актив с изображением → картинка должна показываться
   (это проверяет, что `/media/` → minio проксирование работает).
4. С машины **вне** LAN: `curl https://helpdesk.corp.example.lan/` должен
   завершиться отказом / таймаутом.
5. На сервере проверить, что пользователь синхронизировался:

   ```bash
   docker exec helpdesk-db psql -U postgres -d helpdesk \
     -c "SELECT email, full_name FROM users;"
   ```

---

## 12. Эксплуатация

### Обновление приложения

```bash
cd /opt/helpdesk
git pull
make prod-build-backend
make prod-build-frontend
make prod-logs-backend
```

Миграции применяются автоматически в entrypoint бэкенда.

### Бэкап

См. `docs/DEPLOY_VPS.md` §8 — команды идентичны. Краткое:

```bash
# postgres helpdesk + keycloak + minio data
docker exec helpdesk-db          pg_dump -U postgres helpdesk  | gzip > /opt/backups/helpdesk-$(date +%F).sql.gz
docker exec helpdesk-keycloak-db pg_dump -U keycloak keycloak  | gzip > /opt/backups/keycloak-$(date +%F).sql.gz
docker run --rm -v helpdesk_minio_data:/data -v /opt/backups:/b alpine \
  tar czf /b/minio-$(date +%F).tar.gz -C /data .
```

Поставьте в cron, бэкапы складывайте на корпоративный backup-storage
(не оставляйте на том же сервере).

### Гигиена секретов

- `.env.prod` — `chmod 600`, владелец root или сервисный пользователь.
- Никогда не коммитьте его в git, не выкладывайте в Slack/Confluence.
- При смене состава команды — ротация всех секретов: пароли БД, Keycloak
  client secret, MinIO ключи.

### Обновления безопасности

«Внутренний» ≠ «безопасный». Раз в месяц:

```bash
sudo apt update && sudo apt upgrade
docker compose -f docker-compose.prod.yml pull
make prod-recreate
```

Образы Keycloak и Postgres pin'ятся в compose-файле — если вышел CVE на
текущий тег, обновите тег в `docker-compose.prod.yml` и пересоберите.

### Мониторинг и логи

Минимум — логи в `journalctl` через `docker logs`. Если в организации есть
ELK/Loki — направьте туда. Метрик внешних не настроено; для prod-нагрузки
рекомендуется добавить Prometheus + Grafana отдельным compose-файлом.

---

## 13. Типичные проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `pkce_expired` после логина | FQDN на фронте, в Keycloak public URL и в callback URL не совпадают | Проверить, что во всех `.env.prod`-полях один и тот же `https://helpdesk.corp.example.lan` |
| Браузер показывает «Not Secure» | Корневой CA не доверен на клиенте | Workplace IT должен раскатать корневой CA через GPO/MDM |
| 404/400 при загрузке картинок активов | `MINIO_PUBLIC_BASE_URL` указывает на `:9000` или на `/assets` (конфликт с фронтом) | Поправить на `https://<fqdn>/media`, перезапустить backend |
| Белая страница вместо фронта, в DevTools 400 на `/assets/index-*.js` | nginx-конфиг проксирует `/assets/` в minio (старая схема) | Префикс должен быть `/media/`, см. `nginx/nginx.conf` |
| `audience invalid` в логах backend | JWT-аудитория не совпадает | Установите `KEYCLOAK_AUDIENCE` равным client_id (`helpdesk-backend`) или оставьте пустым |
| CORS ошибки в браузере | `ALLOWED_CORS_ORIGINS` не совпадает со схемой/хостом | Должен быть ровно один origin: `https://helpdesk.corp.example.lan` |
| Keycloak редиректит на `keycloak:8080` | `KEYCLOAK_PUBLIC_URL` не задан или указывает внутрь docker | Должен быть публичный FQDN с `https://`. Settings-валидатор в проде это проверяет — если бэкенд не стартует с ошибкой про issuer, причина здесь |
| `connection refused` из самой LAN | UFW режет, или Docker привязал nginx не на LAN-интерфейс | `sudo ss -tlnp \| grep ':443'` — должен быть LAN-IP. Поправьте `ports:` в compose |
| `connection refused` из дома (через VPN) | Корпоративный VPN не маршрутизирует подсеть с сервером | Сетевикам — добавить маршрут на VPN-концентраторе |

---

## 14. Контрольный список перед сдачей в эксплуатацию

- [ ] FQDN резолвится из всех клиентских подсетей.
- [ ] Сертификат — от внутреннего корпоративного CA, не самоподписанный.
- [ ] Корневой CA доверен на всех рабочих станциях (нет браузерных warning'ов).
- [ ] UFW активен, политика `default deny`, разрешён только корпоративный CIDR.
- [ ] `docker-compose.prod.yml`: nginx `ports:` привязаны к LAN-IP, а не `0.0.0.0`.
- [ ] `ss -tlnp` подтверждает, что 80/443 открыты только на LAN-IP.
- [ ] `.env.prod` имеет `chmod 600`, все секреты — длинные случайные строки.
- [ ] `MINIO_PUBLIC_BASE_URL` оканчивается на `/media` (не `/assets` — конфликт с фронтом и не `:9000`).
- [ ] `KEYCLOAK_*_URL` и `FRONTEND_URL` используют `https://` и единый FQDN.
- [ ] Bootstrap-админ Keycloak заменён на именованного админа.
- [ ] Cron-задача снимает дампы БД и MinIO и складывает на отдельный storage.
- [ ] Календарное напоминание за 30 дней до истечения сертификата.
- [ ] Тест: вход и просмотр карточки актива с картинкой работают с рабочей машины.
- [ ] Тест: соединение с не-LAN адреса отвергается.
