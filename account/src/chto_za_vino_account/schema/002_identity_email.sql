-- Email of an identity: the address of an email identity, or the default address that Yandex ID
-- returns for a Yandex identity. A login of an unknown identity joins the one account that has
-- the same email, instead of a new sign-up (owner request, 2026-10-19, issue #48).
ALTER TABLE identities ADD COLUMN email TEXT;
UPDATE identities SET email = subject WHERE provider = 'email';
CREATE INDEX identities_email ON identities (email);
ALTER TABLE signup_tickets ADD COLUMN email TEXT;
