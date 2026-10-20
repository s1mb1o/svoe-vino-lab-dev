# Manual tests of the account service

Testers: the temporary test code 111111 is described in
[../docs/testing-with-test-code.md](../docs/testing-with-test-code.md).

These tests need real things that the automatic tests (`./scripts/verify.sh`) cannot use:
the gx10 host and its Docker networks, real mailboxes, a real Yandex account, other LAN
hosts, phones, and real waiting time. A person runs them.

Record each run at the end of this file: the date, the commit, the tester, and the result of
each test. Mark a test `PASS`, `FAIL` (with a note), or `BLOCKED` (with the reason).

## 0. Preparation

Use the **dev** instance on gx10: project `svoe-vino-lab-account-dev`, port `29008`, its own
`data/` directory, and its own secrets. Never run these tests on prod data.

Rules for secrets (`chtozavino-deploy` rules 2 and 10):

- Do not print a secret. Load the environment file into the shell; do not `cat` it.
- Do not paste a token, a code, or a session into a chat with an AI agent.
- The session tokens and codes of these tests belong to test accounts. Delete the test
  accounts at the end (test 10.1).

Steps:

1. Build the image on gx10 from the commit under test (`account/README.md`, "Deployment").
   Tag it `svoe-vino-lab-account:dev`.
2. Make `/srv/svoe-vino-lab/dev/account/` with `compose.yaml` (from
   `deploy/compose.example.yaml`: project and container `…-dev`, port `0.0.0.0:29008:8080`),
   `.env` with `ACCOUNT_IMAGE=svoe-vino-lab-account:dev`, `config/` (mode 0700), and `data/`
   (mode 0700).
3. Fill `config/account.env` (mode 0600) from `.env.example`:
   - new secrets for `ACCOUNT_WEB_TOKEN`, `ACCOUNT_TELEGRAM_TOKEN`, `ACCOUNT_MAX_TOKEN`,
     `ACCOUNT_CODE_KEY` (`openssl rand -hex 32` each);
   - the REG.RU SMTP settings (#52) and `ACCOUNT_ALLOWED_NETWORKS=172.16.0.0/12`;
   - the Compose file sets `ACCOUNT_ENVIRONMENT=production`, the database path, the host,
     and the port. Values of these keys in `config/account.env` have no effect;
   - `TELEGRAM_BOT_USERNAME=ChtoZaVinoBot`.
4. Yandex ID for tests: in the Yandex OAuth app, add the debug Redirect URI
   `https://oauth.yandex.ru/verification_code` («Подставить URL для отладки»). Yandex then
   shows the code on its own page, so no site page sees it. In `config/yandex-oauth.env` of
   the dev instance, set `YANDEX_REDIRECT_URIS=https://oauth.yandex.ru/verification_code`.
5. `docker compose up -d`.
6. Shell helpers on gx10 (the token stays in the shell variable):

   ```sh
   set -a; . /srv/svoe-vino-lab/dev/account/config/account.env; set +a
   A=http://127.0.0.1:29008
   IP=203.0.113.7    # any address; it stands for the browser address that Nuxt sends
   web() { curl -s -H "Authorization: Bearer $ACCOUNT_WEB_TOKEN" -H "X-Client-IP: $IP" \
             -H "Content-Type: application/json" "$@"; }
   ```

Have ready: one mailbox each at Gmail, Yandex Mail, and Mail.ru; one Yandex account; a
second Yandex account; another computer on the home LAN; a phone with mobile data.

## 1. Container on gx10 (aarch64)

- [ ] **1.1 Build on gx10.** `docker image inspect svoe-vino-lab-account:dev --format
  '{{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}'` prints
  `arm64` and the commit under test.
- [ ] **1.2 Start and health.** `docker compose ps` shows `healthy` within 1 minute.
  `curl -s $A/readyz` prints `{"status":"ok"}`.
- [ ] **1.3 User and files.** `docker exec svoe-vino-lab-account-dev id -u` prints `1000`.
  `ls -la data/` on the host shows `account.sqlite3` owned by the deploy user (uid 1000).
  `stat -c %a data` prints `700`.
- [ ] **1.3a Container settings win.** Leave the development values of `.env.example` for
  `ACCOUNT_DATABASE`, `ACCOUNT_HOST`, and `ACCOUNT_PORT` in `config/account.env`. The
  container still starts, listens on 8080, and writes `data/account.sqlite3`.
- [ ] **1.4 Read-only root.** `docker exec svoe-vino-lab-account-dev touch /app/x` fails with
  "Read-only file system".
- [ ] **1.5 Data survives recreation.** Do test 2.3 first. Then
  `docker compose up -d --force-recreate`. `web $A/v1/me -H "X-Session-Token: $S"` still
  returns the account.
- [ ] **1.6 Start at boot (optional, needs a planned reboot).** After a reboot of gx10, the
  container runs again without a manual command.

## 2. Email code with real mailboxes

- [ ] **2.1 SMTP from gx10.** On gx10: `nc -vz mail.hosting.reg.ru 465` connects. Inside the
  container network: `docker exec svoe-vino-lab-account-dev python -c "import socket;
  socket.create_connection(('mail.hosting.reg.ru', 465), 5); print('ok')"` prints `ok`.
  If it fails, the account service cannot send mail from gx10 (see #52).
- [ ] **2.2 Delivery to three providers.** For Gmail, Yandex Mail, and Mail.ru:
  `web $A/v1/auth/email/start -d '{"email":"<address>"}'`. Within 1 minute, the message is in
  «Входящие», not in «Спам». The sender is `noreply@chtozavino.ru`. The subject «Код для
  входа в «Винный дневник»» shows correct Cyrillic and quotes. The text has the 6-digit code,
  «Никому не сообщайте этот код», and no links. In "Show original" / «Свойства письма»:
  SPF `pass`, DKIM `pass` with `d=chtozavino.ru`, DMARC `pass`.
- [ ] **2.3 Sign-up and login with the real code.**

  ```sh
  C=$(web $A/v1/auth/email/start -d '{"email":"<address>"}' | jq -r .challenge_id)
  # read the code in the mailbox, then:
  web $A/v1/auth/email/verify -d "{\"challenge_id\":\"$C\",\"code\":\"<code>\"}"
  ```

  The answer is `signup_required` with a `signup_ticket`. Then
  `web $A/v1/auth/signup -d '{"signup_ticket":"<ticket>","username":"tester1",
  "consent_version":"<ACCOUNT_CONSENT_VERSION>","terms_version":"<ACCOUNT_TERMS_VERSION>"}'`
  returns `status: session`. Keep the token: `S=<token>`. A second login with a new code
  returns `status: session` directly.
- [ ] **2.4 Expiry in real time.** Request a code. Wait 11 minutes. The code gives
  `invalid_challenge`.
- [ ] **2.5 Lock after wrong codes.** Request a code. Send 5 wrong codes: `attempts_left`
  goes 4, 3, 2, 1, 0. Then the correct code gives `too_many_attempts`.
- [ ] **2.6 Send limits.** Two requests for one address within 60 s: the second gives HTTP 429
  with `Retry-After`. Four requests within one hour (60 s apart): the fourth gives 429.
- [ ] **2.7 Mail server down.** Set a wrong `SMTP_PASSWORD` in the dev env file and run
  `docker compose up -d --force-recreate`. `email/start` still answers in less than 1 s.
  `docker logs svoe-vino-lab-account-dev` shows "Mail delivery failed" three times and no
  address. Restore the password.
- [ ] **2.8 Email change.** With a session, start with
  `{"email":"<new address>","purpose":"link"}` and `-H "X-Session-Token: $S"`, then verify the
  code from the new mailbox. `GET /v1/me` shows the new address. Known gap: the old address
  gets no notice yet (#52).

## 3. Yandex ID with a real account

- [ ] **3.1 First login.**

  ```sh
  R=$(web $A/v1/auth/yandex/start -d '{"redirect_uri":"https://oauth.yandex.ru/verification_code"}')
  echo "$R" | jq -r .authorize_url   # open this URL in a browser, logged in to Yandex
  ```

  The Yandex screen shows the app name and asks for access. Record whether Yandex shows a
  warning about an unverified service (then the Gosuslugi verification is not done, #48).
  After «Разрешить», Yandex shows a code. Then
  `web $A/v1/auth/yandex/finish -d '{"flow_id":"<flow_id from R>","state":"<state from the
  authorize URL>","code":"<code>"}'` gives `signup_required` without an email. Sign up as in
  2.3. The account has the identity `yandex`.
- [ ] **3.2 Second login.** A new start and finish returns `status: session` for the same
  username. Yandex may skip the consent screen.
- [ ] **3.3 Refusal.** Start a login and press «Отказать» (or close the screen). Nothing is
  created. A finish with an invented code gives `provider_rejected`.
- [ ] **3.4 Code reuse.** Finish once successfully. Start again, get a new code, finish, then
  repeat the same finish call: `invalid_flow`.
- [ ] **3.5 Second Yandex account.** Log out of Yandex in the browser and log in with the
  second account. The login creates a different sign-up, not the first account.
- [ ] **3.6 Link Yandex to an email account.** With the session of 2.3, start with `"purpose":"link"` and `-H "X-Session-Token: $S"`. Finish with the
  same session header. `GET /v1/me` lists `email` and `yandex`. A Yandex login now opens the
  email account.
- [ ] **3.7 Access revoked at Yandex.** At <https://id.yandex.ru/> → «Безопасность» →
  «Доступы» (or «Сервисы»), remove the access of the app. The next login asks for consent
  again and opens the same account.

## 4. Network and access on the real hosts

- [ ] **4.1 Another LAN computer is refused.** From the Mac:
  `curl -s -o /dev/null -w '%{http_code}' http://192.168.86.14:29008/v1/config` prints `403`.
  `docker logs svoe-vino-lab-account-dev` shows "Refused a request from a network that is not
  allowed" with the address of the Mac.
- [ ] **4.2 A bot container is allowed.** From the MAX bot container:
  `docker exec -e T="$ACCOUNT_WEB_TOKEN" svoe-vino-lab-max-bot-prod python -c "import os,
  urllib.request as u; r=u.Request('http://192.168.86.14:29008/v1/config',
  headers={'Authorization':'Bearer '+os.environ['T']}); print(u.urlopen(r).status)"` prints
  `200`. If it prints 403, the log shows the bot address; add its network to
  `ACCOUNT_ALLOWED_NETWORKS`.
- [ ] **4.3 Not reachable from the internet.** From a phone on mobile data, open
  `http://<public address of the home network>:29008/healthz`. No answer.
- [ ] **4.4 Through the tunnel (after the tunnel to Claudette exists).** On Claudette:
  `curl -s http://127.0.0.1:28008/healthz` prints `{"status":"ok"}`. The production port
  28008 is not open in the Claudette firewall.

## 5. Logs and stored data

- [ ] **5.1 No personal data in logs.** After tests 2 and 3:
  `docker logs svoe-vino-lab-account-dev 2>&1 | grep -c '@'` prints `0`.
  `docker logs … | grep -c 'Ваш код'` prints `0`. The log has only event names, such as
  "Email challenge created (login)" and "Session created (yandex)".
- [ ] **5.2 Only hashes are stored.** On gx10, with Python on the host:
  `python3 -c "import sqlite3; c=sqlite3.connect('data/account.sqlite3');
  print(c.execute('select length(token_hash) from sessions limit 1').fetchone())"` prints
  `(64,)`. The database has no column with a plain session token or a plain code.

## 6. Backup and restore

- [ ] **6.1 Backup.** `docker exec svoe-vino-lab-account-dev chto-za-vino-account backup
  /data/backups/account-test.sqlite3` prints the path. On the host the file has mode `600`.
  A second run with the same name fails and keeps the first file.
- [ ] **6.2 Integrity.** `python3 -c "import sqlite3; print(sqlite3.connect(
  'data/backups/account-test.sqlite3').execute('pragma integrity_check').fetchone())"`
  prints `('ok',)`.
- [ ] **6.3 Restore drill.** `docker compose stop`. Move `account.sqlite3`, `-wal`, and `-shm`
  aside. Copy the backup to `data/account.sqlite3`. `docker compose start`. The login of 2.3
  works, and the session from before the backup still works.
- [ ] **6.4a Two backups at once.** Start two backups with the same file name at the same
  time (two shells). One prints the path; the other says the file exists. `data/backups/`
  has no `.backup-*.tmp` file afterwards.
- [ ] **6.4b Retention.** Set the time of a test backup to 8 days ago
  (`touch -d '8 days ago' <file>`), run the cleanup command of `README.md`. The file is gone;
  a backup of today stays.
- [ ] **6.4 Backup under load.** Run `for i in $(seq 50); do web $A/v1/config >/dev/null; done &`
  and a backup at the same time. Test 6.2 passes for the new file.

## 7. Clock

- [ ] **7.1 Time is synchronized.** On gx10, `timedatectl` shows
  `System clock synchronized: yes`. Codes, sessions, and MAX launch checks use the clock.

## 8. Blocked until other parts exist

Run these when the parts exist. Until then, mark them `BLOCKED`.

- [ ] **8.1 Yandex production callback** (Nuxt route `/api/account/yandex/callback`): a login
  from the site ends on `/account` without the code in the address bar, and Metrika gets no
  hit with `code=`.
- [ ] **8.2 MAX, Phase 0 of #50** (test bot and mini-app page), on mobile data and on Wi-Fi:
  `initData.user.id` equals the Bot API `user_id` of the same person; `ip` is present and
  equals the address that Caddy reports; the URL fragment survives the redirect from `/` to
  `/max`; a launch URL opened in another browser gets `launch_reused` or
  `launch_ip_mismatch`.
- [ ] **8.3 Telegram link (#51)** on iOS, Android, and Telegram Desktop: the button opens the
  bot with `/start link_<code>`; the bot shows the diary name; «Привязать» links; a second
  press links nothing more.
- [ ] **8.4 Accessibility** of the account pages with VoiceOver and TalkBack (#35).

## 9. Diary lists (plan 07)

Use the session `S` of test 2.3. `W=wine-slug-of-a-real-catalog-wine`.

- [ ] **9.1 Migration.** Start the new image on the data of the previous image. The log has no
  error. `web $A/v1/me -H "X-Session-Token: $S"` shows `"save_history":true`.
- [ ] **9.2 Record and list.** `web $A/v1/me/history -H "X-Session-Token: $S"
  -d "{\"slug\":\"$W\",\"source\":\"photo\"}"` gives `recorded` and today's Moscow date.
  A second call gives `already`. `web $A/v1/me/history -H "X-Session-Token: $S"` (GET) lists the
  wine with `days_count` 1.
- [ ] **9.3 Moscow midnight (real time).** Record a wine at 23:58 Moscow time and again at 00:02.
  The second call gives `recorded` with the new date. The wine has two dates.
- [ ] **9.4 Switch.** `web -X PATCH $A/v1/me -H "X-Session-Token: $S" -d '{"save_history":false}'`
  shows `"save_history":false`. A record gives `off`. Turn the switch on again.
- [ ] **9.5 Saved.** `web -X PUT $A/v1/me/saved/$W -H "X-Session-Token: $S"
  -d '{"status":"want","source":"history"}'` gives HTTP 201; the same call with `"liked"` gives
  200 with the first `added_at`. `DELETE /v1/me/history/$W` keeps the saved wine with
  `"in_history":false`.
- [ ] **9.5a Note.** The same `PUT` with `"note":"Купить к ужину"` shows the note. A `PUT` without
  `note` keeps it; `"note":""` clears it. `docker logs <container> 2>&1 | grep -c 'Купить'`
  prints `0`.
- [ ] **9.6 Telegram chat** (needs the Telegram bot with plan 07 and a linked Telegram). Send a
  bottle photo to the bot. The history shows the wine with the source `telegram`. «❌ Не совпало»
  removes the date of today. A selected alternative is recorded, and the rejected wine has no
  date of today.
- [ ] **9.7 MAX chat** (needs the MAX bot with plan 07, `ACCOUNT_MAX_TOKEN` in both
  environments, and a MAX identity linked through the mini app). Send a bottle photo to the MAX
  bot. The history shows the wine with the source `max`. If the bot log shows `not_linked`, the
  mini-app user ID is not the Bot API user ID (plan 05): record it in the results.
- [ ] **9.8 Logs.** `docker logs <container> 2>&1 | grep -c "$W"` prints `0`. The log has only
  event names, such as "History recorded (photo)" and "Saved wine added (history)".

## 10. Cleanup

- [ ] **10.1 Delete the test accounts.** For each test account, `web -X DELETE $A/v1/me -H "X-Session-Token: $S"`
  gives HTTP 204. `GET /v1/me` then gives `session_invalid`.
- [ ] **10.2 Remove the debug Redirect URI** from the Yandex OAuth app if it is no longer needed.
- [ ] **10.3 Remove the test backups** from `data/backups/`.

## Results

| Date | Commit | Tester | Result |
| --- | --- | --- | --- |
