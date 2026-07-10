# Namecheap Positive SSL — активация и установка

Пошаговая инструкция по [активации SSL в Namecheap](https://www.namecheap.com/support/knowledgebase/article.aspx/794/67/how-do-i-activate-an-ssl-certificate/) и установке на nginx (korxona.com).

---

## 1. Подготовка на VPS

Убедитесь, что DNS для **korxona.com** и **www.korxona.com** указывает на IP вашего сервера.

```bash
cd ~/helpdesk
git pull
docker compose up -d
```

Проверьте, что сайт открывается по `http://korxona.com`.

---

## 2. Генерация CSR и приватного ключа

На VPS в папке проекта:

```bash
chmod +x scripts/generate-csr.sh
./scripts/generate-csr.sh
```

Скрипт создаст:
- `nginx/ssl/privkey.pem` — приватный ключ (хранить в секрете, не коммитить).
- `nginx/ssl/korxona.com.csr` — Certificate Signing Request для вставки в Namecheap.

Откройте CSR и скопируйте содержимое (включая `-----BEGIN CERTIFICATE REQUEST-----` и `-----END CERTIFICATE REQUEST-----`):

```bash
cat nginx/ssl/korxona.com.csr
```

---

## 3. Активация сертификата в Namecheap

1. Войдите в [Namecheap](https://www.namecheap.com) → **SSL Certificates**.
2. Нажмите **Activate** рядом с вашим Positive SSL.
3. Выберите **Manually** (ручная установка).
4. Вставьте **CSR** в форму и нажмите **Next**.
5. **Domain Control Validation (DCV)**:
   - Выберите **HTTP file-based validation**.
   - Namecheap/Sectigo покажет имя файла (например `xxxxxxxxxxxx.txt`) и его содержимое.
   - Вам нужно будет разместить этот файл по пути:
     ```
     http://korxona.com/.well-known/pki-validation/<имя_файла>
     ```
6. Укажите email для получения готового сертификата → **Next** → **Submit**.

---

## 4. Размещение файла валидации (DCV)

На VPS создайте файл в каталоге валидации:

```bash
cd ~/helpdesk

# Создайте файл (имя и содержимое — из Namecheap)
mkdir -p nginx/well-known/pki-validation
echo "СОДЕРЖИМОЕ_ИЗ_NAMECHEAP" > nginx/well-known/pki-validation/ИМЯ_ФАЙЛА_ИЗ_NAMECHEAP.txt
```

**Важно:** не меняйте содержимое и регистр символов — проверка Sectigo учитывает это.

Проверьте доступность по HTTP:

```bash
curl -I "http://korxona.com/.well-known/pki-validation/ИМЯ_ФАЙЛА_ИЗ_NAMECHEAP.txt"
# Ожидается 200 OK
```

Перезапустите nginx, если меняли что-то в `nginx/`:

```bash
docker compose restart nginx
```

Дождитесь письма от Namecheap о выдаче сертификата (обычно до 10–30 минут). Скачайте архив с сертификатом.

---

## 5. Установка сертификата на nginx

Namecheap присылает:
- `korxona_com.crt` — ваш сертификат
- `korxona_com.ca-bundle` — цепочка CA

**Шаги на VPS:**

```bash
cd ~/helpdesk
mkdir -p nginx/ssl

# 1. Положите в nginx/ssl/ файлы из письма Namecheap:
#    korxona_com.crt, korxona_com.ca-bundle
#    privkey.pem уже там (из generate-csr.sh).

# 2. Соберите fullchain (сертификат + цепочка)
cat nginx/ssl/korxona_com.crt nginx/ssl/korxona_com.ca-bundle > nginx/ssl/fullchain.pem

# Или используйте скрипт (ожидает файлы в nginx/ssl/):
chmod +x scripts/install-ssl.sh && ./scripts/install-ssl.sh

# 3. Перезапуск (порт 443 и том nginx/ssl уже в docker-compose)
docker compose up -d
```

После этого HTTPS и редирект с HTTP включены (см. раздел 6).

---

## 6. Включение HTTPS (после установки сертификата)

В текущей конфигурации порт **443** и том `./nginx/ssl` уже добавлены в docker-compose, а nginx настроен на HTTPS и редирект с HTTP. Достаточно собрать `fullchain.pem` (шаг 5) и выполнить `docker compose up -d`.

Если правите конфиг вручную: образец HTTPS‑сервера — `nginx/nginx.https.conf.example`.

---

## 7. Проверка

- [SSL Labs](https://www.ssllabs.com/ssltest/analyze.html?d=korxona.com)
- [decoder.link](https://decoder.link) — проверка установки SSL

---

## Полезные ссылки

- [How do I activate an SSL certificate — Namecheap](https://www.namecheap.com/support/knowledgebase/article.aspx/794/67/how-do-i-activate-an-ssl-certificate/)
- [How to install SSL certificates — Namecheap](https://www.namecheap.com/support/knowledgebase/article.aspx/795/69/how-to-install-ssl-certificates/)
