# Context chto-za-vino-account

This component is the account service of «Винный дневник».
Read `README.md`, `../docs/plans/04_user-accounts.md`, and `../docs/plans/05_max-authorization.md`
before a change. Write technical documents in STE-style English. Keep user-visible text in Russian.

## Rules

1. Login methods are the email code and Yandex ID. Never add login through a foreign service
   (Telegram, Google, Apple): 149-FZ art. 8 p. 10, KoAP 13.55.
2. Telegram is linked only. A Telegram identity never opens a session.
3. MAX opens a session only when `MAX_LOGIN_ENABLED` is true (issue #50).
4. Never put a one-time code for MAX into a MAX message or deep link (MAX requirement 1.5).
   MAX identity comes only from the signed mini-app launch data.
5. Store only hashes of bearer secrets. Store email codes as an HMAC with `ACCOUNT_CODE_KEY`.
6. Never write a token, code, email address, launch data, or Yandex token to a log or an error.
   Validation errors never echo the input.
7. Keep the service on the LAN. Every route except the health checks needs an allowed network
   and a consumer bearer token.
8. A request never waits for the mail server. Mail goes through the dispatcher.
9. Put each schema change in a new numbered file in `src/chto_za_vino_account/schema/`.
10. Keep secrets out of the repository, the image, and the Compose file.
11. Never name a real host, address, or path of an installation in this component.

## Verification

```sh
./scripts/verify.sh
```

Update `ChangeLog.md` when behavior changes.
