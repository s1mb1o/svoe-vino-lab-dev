# Test «Винный дневник» with the test code 111111

Date: 2026-10-20. Audience: testers of the diary on the site and in MAX.

## What the test code is

The diary sends a 6-digit login code by email. For the tests, the production service also accepts
the fixed code **111111** in place of that code.

- It works for any email address: a new address (registration) or an existing account (login).
- It works only for the email login. It does not link an email address to an account, and it is
  not a MAX or Telegram login.
- It is temporary. The owner turns it off after the tests. Then 111111 gives
  «Неверный код. Осталось попыток: …», and you need the code from the letter.

Anyone who knows an address and 111111 can open that diary while the code is on. So:

- Do not tell the code to people outside the test team.
- Do not use addresses of real people. Use your own address or test addresses (next section).
- Do not save private data in a test diary.

## Before you start

| Item | Value |
|---|---|
| Site | https://chtozavino.ru/account (the header link «Дневник»). The site asks for an HTTP Basic login: get it from the owner |
| MAX mini app | In MAX, open the bot «Что за вино?» and select the mini-app button below the chat (for example «Открыть»). In a browser, https://max.chtozavino.ru shows only the QR code |
| Telegram bot | https://t.me/ChtoZaVinoBot |

Test addresses: use the "+" form of your own mailbox, for example `yourname+t1@gmail.com`,
`yourname+t2@gmail.com`. Each one is a different diary address, and the letters come to your
mailbox. Do not use invented addresses: their letters bounce, and many bounces harm the sender
address of the site.

Limits of the service (they also apply to 111111):

- one code request per minute and three per hour for each address;
- 20 code requests per hour from one network address;
- a code request is valid for 10 minutes and allows 5 attempts.

## 1. Register a new diary

1. On the site, open «Дневник».
2. In «Электронная почта», type a new test address. Select «Получить код».
3. In «Код из 6 цифр», type `111111`. Select «Войти».
4. The sign-up form opens. Type a name in «Имя пользователя»: 3 to 32 characters, lowercase
   Latin letters, digits, dot, hyphen, or underscore.
5. Tick «Принимаю условия использования» and «Даю согласие на обработку персональных данных».
6. Select «Создать дневник».

Expected: the diary page opens. «Способы входа» shows «Почта» with your address.

## 2. Log in to an existing diary

1. Select «Выйти», or use another browser.
2. Type the address of an existing diary. Select «Получить код».
3. Type `111111`. Select «Войти».

Expected: the diary of that address opens without the sign-up form.

## 3. Link Telegram

1. On the diary page of the site, select «Привязать мессенджер» → «Telegram» → «Открыть Telegram».
2. In the bot, check the diary name and select «Привязать».

Expected: «Готово: Telegram привязан к дневнику «…»». The diary page shows Telegram under
«Связанные мессенджеры» after a page reload.

To undo: send `/unlink` to the bot, or select «Отвязать» on the diary page.

## 4. Link MAX

1. In MAX, open the bot «Что за вино?» and select the mini-app button. The diary opens inside MAX.
2. Type your test address, select «Получить код», type `111111`, select «Войти».
   MAX does not keep the login between openings: you log in each time.
3. Check the MAX name in the question and select «Привязать».

Expected: MAX appears under «Связанные мессенджеры».

From the site: «Привязать мессенджер» → «MAX» shows a QR code. Scan it with the phone, then do steps 2–3
in MAX. Then select «Я привязал» on the site.

If MAX shows «Данные запуска MAX устарели. Закройте дневник и откройте его в MAX снова.», close the
mini app, open it again from the bot, and repeat. Report the time of the attempt (step "Report a
problem").

## 5. Delete the test diary

After the tests, delete each test diary: «Удалить аккаунт» → «Удалить навсегда».
The diary, its login methods, and its linked messengers are deleted at once.

## Messages and their meaning

| Message | Meaning |
|---|---|
| «Неверный код. Осталось попыток: N.» | The code is wrong. If 111111 gives this message, the test code is off |
| «Этот код больше не действует. Запросите новый.» | The request expired (10 minutes), used 5 attempts, or the browser lost its cookie. Select «Получить код» again |
| «Слишком много попыток. Попробуйте через N мин.» | A limit of the section "Before you start". Wait, or use another test address |
| «Это имя уже занято.» | Select another name |

## Report a problem

Send the owner (contacts: https://max.chtozavino.ru/contacts, no site login needed):

- the time of the attempt (Moscow time) and the place: site, MAX app (phone or computer), or Telegram;
- the test address that you used;
- a screenshot of the message.

The service logs never contain email addresses or codes. The time is the only way to find your attempt.
