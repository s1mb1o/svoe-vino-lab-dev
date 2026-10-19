# Legal pages

Date: 2026-10-19. Issues: #37 (publication), #10 (bot texts), #41 (cookie consent), #45 (lawyer review).

## Scope

The site publishes one shared set of legal pages:

| Path | Russian title | Bot setting |
| --- | --- | --- |
| `/terms` | Условия использования | `BOT_TERMS_URL` |
| `/privacy` | Политика обработки персональных данных | `BOT_PRIVACY_URL` |
| `/contacts` | Контакты | `BOT_CONTACT_URL` |

The pages cover all services: the website, the Telegram bot, the MAX bot, the Android app, and the iOS app.
Each page has a common part and one section for each service that differs.
The service sections use stable fragments: `#site`, `#telegram`, `#max`, `#android`, `#ios`.
Links from a service MAY point to its fragment, for example `https://chtozavino.ru/privacy#max`.

The published paths and fragments MUST NOT change.
If a service needs a separate document, add it under the document type, for example `/terms/max`.
Do not add service-first paths such as `/max/terms`.

## Source of the data

`app/data/legal.ts` holds the operator details, the contact channels, the page links, and the revision date.
All pages and the footer read these values. Do not copy them into page text.

The operator is a natural person with the self-employed tax status (НПД).
The pages show the full name, the status, and the INN.
The INN has a valid check sum. A unit test verifies it.

## Revision

`legalRevision` is the date of the current texts in ISO format.
The pages show it as «Редакция от …».
The bots MUST store `legalRevision` as the version of the accepted terms (#10).
Change `legalRevision` on every change of the text.
The owner decides which changes are material. Only a material change makes the bots ask for acceptance again.

## Age gate

The legal pages do not show the 18+ age gate.
A bot shows the terms link before the user confirms age. The user must be able to read the terms first.
The pages keep the shared header, the footer, the 18+ mark, and the health warning.
All other pages keep the age gate.

## Content rules

Every statement about data processing MUST match the code and the deployment on the revision date.
`ResearchLog.md` ("Legal pages: data flow facts, 2026-10-19") lists the evidence for each statement.
When the code changes the data flow, update the page text, `legalRevision`, and the evidence.

The texts MUST NOT claim consent for Yandex.Metrika until the consent banner of #41 exists.
The texts MUST NOT claim that a photo is never stored. The matcher can archive the original photo.

A lawyer has not reviewed the texts. The review is postponed until after the hackathon (#45).

## Release conditions

The owner decided on 2026-10-19 that every photo is kept for 30 days.
This includes the matcher request archive and its backups.
On 2026-10-19 the matcher has no retention job, and no job removes old snapshots.
Do not deploy the pages before a cleanup job enforces the 30-day period on the archive and the backups.
Before deployment, also delete the old Telegram data on the NAS and the Telegram deployment backup of 2026-09-29, or document why they stay.

The owner confirmed on 2026-10-19 that all hosts with user data are in Russia: Princess, gx10, the ds1825 NAS, and the owner's Mac with the T7 drive.

## Discovery and navigation

The shared footer links to all three pages.
`/sitemap` lists the pages in the section «Правовая информация».
`/sitemap.xml` includes the three paths.
Each page has a canonical URL and social metadata.

## Layout and accessibility

`app/components/LegalPage.vue` renders the heading, the revision date, the table of contents, and the related documents.
Each section is a `section` element with a heading and `aria-labelledby`.
The table of contents is a `nav` element with a visible heading.
Links in the text are underlined. Interactive targets are at least 44 px high in the related-documents navigation.
The pages use the theme tokens, so the light and dark themes both apply.
