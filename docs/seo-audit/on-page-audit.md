# On-page SEO and Russian search intent

[README](README.md) defines baseline/statuses. Observed metadata is from anonymous production GETs (E01), not assumed from the local branch. Proposed copy was not applied. Search volume, rankings and keyword difficulty are unavailable.

## Observed page metadata

All 16 production sitemap pages have nonempty distinct titles/descriptions, one main H1 and one route canonical. Presentation is nevertheless noindex in its header (SEO-005). No blanket duplicated-title or missing-description defect was established. E01 preserves social tags and schema too. H1 extraction can concatenate text around a visual `<br>`; this alone is not a spacing defect.

| Production URL | Title | Meta description | H1 |
|---|---|---|---|
| [/](https://chtozavino.ru/) | Найти вино по фото — Что за вино? | Сфотографируйте этикетку российского вина. Найдите название, фото бутылки и карточку на портале «Свое Вино». | Найти вино по фото |
| [/shelf](https://chtozavino.ru/shelf) | Найти вино на полке по фото — Что за вино? | Снимите полку целиком. Мы найдём бутылки и покажем совпадения с каталогом российского вина. | Найти вино по фото |
| [/dish](https://chtozavino.ru/dish) | Вино к блюду — Что за вино? | Подберите российское вино к блюду: по фотографии или названию, с учётом соуса и ваших пожеланий. | Найти вино к блюду |
| [/lineup](https://chtozavino.ru/lineup) | Карты линеек производителей — Что за вино? | Путеводители по линейкам 25 российских производителей вина: группы, ступени внутри линейки и бутылки. | Карты линеек производителей |
| [/android](https://chtozavino.ru/android) | Что за вино? для Android — распознавание без интернета | Определяйте российское вино по фотографии, QR-коду или штрихкоду. Каталог и модели работают на Android без интернета. | Узнайте вино.Даже без интернета. |
| [/iphone](https://chtozavino.ru/iphone) | Что за вино? для iPhone — распознавание на устройстве | Нативное приложение для iPhone определяет российское вино по фотографии, QR-коду или штрихкоду. Core ML и каталог работают без интернета. | Вино в кадре.Ответ на iPhone. |
| [/telegram-bot](https://chtozavino.ru/telegram-bot) | Бот «Что за вино?» в Telegram — вино по фото в чате | Отправьте фото бутылки боту @ChtoZaVinoBot в Telegram. Он найдёт российское вино и пришлёт карточку: винодельня, цвет, сахар, сорта винограда и ссылка на vino-svoe.ru. | Вино в кадре.Ответ в Telegram. |
| [/max-bot](https://chtozavino.ru/max-bot) | Бот «Что за вино?» в MAX — вино по фото в чате | Отправьте фото бутылки боту «Что за вино?» в MAX. Он найдёт российское вино и пришлёт карточку: винодельня, цвет, сахар, сорта винограда и ссылка на vino-svoe.ru. | Вино в кадре.Ответ в MAX. |
| [/presentation](https://chtozavino.ru/presentation) | Что за вино? — презентация проекта | Презентация проекта «Что за вино?» в форматах PowerPoint и PDF. | Презентация проекта |
| [/ideas](https://chtozavino.ru/ideas) | Больше, чем распознавание — Что за вино? | Что происходит после фото: готовые функции, четыре интерактивных демо и макеты новых идей для знакомства с российским вином. | Распознать —только начало. |
| [/game](https://chtozavino.ru/game) | Wine&Dine Merge — маленькое бистро, большая история вкуса | Собирайте блюда, подбирайте вино и практикуйте подачу в Wine&Dine Merge. Уютная игра в браузере с путешествием по винным регионам России. | Хороший вкус начинается с игры. |
| [/crocodile](https://chtozavino.ru/crocodile) | Винный крокодил — настольная игра для хорошей компании | Слова, жесты и неожиданные ассоциации. 30 иллюстрированных карточек о вине, три режима и правила, которые можно объяснить за минуту. Распечатайте и играйте. | Винныйкрокодил |
| [/terms](https://chtozavino.ru/terms) | Условия использования — Что за вино? | Правила использования сайта, ботов в Telegram и MAX и приложений «Что за вино?»: возраст, допустимые фотографии, жалобы и ответственность. | Условия использования |
| [/privacy](https://chtozavino.ru/privacy) | Политика обработки персональных данных — Что за вино? | Какие данные обрабатывают сайт, боты в Telegram и MAX и приложения «Что за вино?», сколько их хранят и как их удалить. | Политика обработки персональных данных |
| [/contacts](https://chtozavino.ru/contacts) | Контакты — Что за вино? | Оператор сервиса «Что за вино?», способы связи, жалобы на контент и запросы о персональных данных. | Контакты |
| [/sitemap](https://chtozavino.ru/sitemap) | Карта сайта — Что за вино? | Все разделы «Что за вино?»: поиск вина по фото, полки и вина к блюду, карты линеек производителей, приложения для Android и iPhone, боты в Telegram и MAX, игры, идеи, презентация проекта и правовая информация. | Карта сайта |

Sources: `webui/nuxt.config.ts:7–63`; `webui/app/components/ScannerPage.vue:27–33`; page-specific shelf/dish/app metadata; `webui/app/components/BotLanding.vue:19–52` and `webui/app/components/LegalPage.vue:13–20`. The [technical audit URL map](technical-audit.md#public-url-to-implementation-map) lists exact routes/files.

## Intent-to-landing-page map

These are semantic candidate clusters, not measured demand or current SERP findings. Consolidate same-task synonyms rather than publishing doorway-like variants.

| Russian candidates | Intent | Existing target | Project-specific assessment |
|---|---|---|---|
| найти вино по фото; определить вино по этикетке; распознать бутылку вина; сканер винных этикеток | Perform recognition | `/` | Correct task page. Explain Russian-catalog scope, result fields, file/photo requirements, uncertainty/no-match and source catalogue. SEO-011. |
| распознать вина на полке; найти вино на фото полки | Recognize multiple bottles in a still photo | `/shelf` | Working separate web route; title specific, H1 shared. Explain bottle selection. SEO-009/011. |
| распознавание винной полки по видео; приложение для сканирования полки | Continuous video/Android mode | `/shelf-lens` in source | Production 404, omitted live XML. Different intent from photo shelf; release candidate, not an existing landing. SEO-012. |
| подбор вина к блюду; подобрать вино по фото еды; какое вино к [блюду] | Pair a dish | `/dish` | SSR picker, sauce/spice controls. Explain decisions/limitations; don't create indexed URLs for every picker option. SEO-008/011. |
| российские винодельни; производители российского вина; линейки [производитель] | Explore producers/ranges | `/lineup`, conditionally details | Range-map directory, not a full travel directory. Details intentionally noindex. Do not invent addresses/tours/hours or completeness. SEO-010/018. |
| сканер вина Android; распознавание вина без интернета; скачать приложение для вина | Install Android tool | `/android` | Specific metadata/offline explanation. Artifact identity reconciled for 0.3.0: [E10 verification](android-030-verification.md). Maintain truthful release/feature claims; HEAD-only follow-up is separate. |
| сканер вина iPhone; распознавание вина iOS | Find iPhone app | `/iphone` | Native features described, TestFlight explicitly next step. No public install link established; don't promise immediate download. |
| бот вино по фото Telegram; распознать вино в Телеграм; бот вино MAX | Use messaging platform | `/telegram-bot`, `/max-bot` | Appropriate platform-specific landings and metadata. Recognition/chat was not exercised. |
| как читать этикетку вина; сорта винограда на этикетке; что означает брют | Learn terminology | `/ideas` demo, result label guide | Useful interaction content exists; optional reviewed standalone guide would better serve explanatory intent. SEO-011/018. |
| винный крокодил распечатать; винная настольная игра | Read rules/print | `/crocodile` | SSR rules and actual printable links; preserve adult context and review audience/promotion copy. |
| игра про сочетание еды и вина | Discover game | `/game` → game subdomain | Keep SSR explanation. Separate game root sample is CSR with no meaningful initial body copy and different project/source. |

## SEO-008 — Route-specific dish social metadata

**VERIFIED defect, P2/S.** E01/E04: dish ordinary title/description/canonical are correct, but OG URL/title/description and Twitter text belong to home. This is a preview/identity problem, not proof that search canonical is wrong or OG directly affects ranking.

Root: `webui/app/pages/dish.vue:1–5` partially overrides `webui/nuxt.config.ts:38–52`. Use complete route metadata like shelf:

```ts
const title = 'Вино к блюду — Что за вино?'
const description = 'Подберите российское вино к блюду: по фотографии или названию, с учётом соуса и ваших пожеланий.'
const canonical = 'https://chtozavino.ru/dish'
useSeoMeta({ title, description, ogType: 'website',
  ogTitle: title, ogDescription: description, ogUrl: canonical,
  twitterTitle: title, twitterDescription: description })
useHead({ link: [{ rel: 'canonical', href: canonical }] })
```

Existing product image can remain if accurate. Producer review pages also inherit home social defaults (`webui/app/pages/lineup/[producer].vue:17`); complete them when approved for publication under SEO-010. **Side effects:** duplicate-tag avoidance and social cache refresh. **Verify:** direct GET and navigation into/away from dish; one canonical and correct distinct tags, no residual dish metadata on home.

## SEO-009 — Make shelf intent explicit in the H1

**VERIFIED optimization, P2/S.** Home and shelf have H1 “Найти вино по фото”; shelf title is already specific. Source `webui/app/components/ScannerPage.vue:29–31` branches only on dish.

```vue
<h1 v-if="mode === 'dish'">Найти вино <span>к блюду</span></h1>
<h1 v-else-if="mode === 'shelf'">Найти вина <span>на полке по фото</span></h1>
<h1 v-else>Найти вино <span>по фото</span></h1>
```

**Side effects:** longer mobile wrapping. **Verify:** one specific SSR/rendered H1 per mode; actual 360/390/768/desktop width and overflow check. No duplicate-H1 ranking penalty was measured.

## SEO-011 — Strengthen useful explanations on existing task pages

**VERIFIED content architecture, P2/M opportunity.** E01 core task pages focus on controls/instructions rather than a dedicated explanation. Source result experiences depend on interaction: `webui/app/components/PhotoScanner.vue:120`, `webui/app/components/ShelfScanner.vue:95`, `webui/app/components/WineExperiences.vue:36–50,106–118`. `/ideas` already distinguishes implemented functions, demos and mockups; preserve that honesty.

No thin-content penalty was observed. Keep the tool first and add concise, useful mode-specific SSR sections near `webui/app/components/ScannerPage.vue:40–45`, preferably separate small components. No arbitrary word-count target is needed.

| Target | Concrete brief | Source / verification |
|---|---|---|
| Home | “Как определить вино по этикетке”; result contents; uncertain/no-match behavior; catalogue scope, formats and one-front-label photo tips | `webui/app/components/PhotoScanner.vue:74–120`, `webui/shared/catalog.ts:19–31`, terms service section. Match actual behavior; visible without JS; no invented accuracy/universal catalogue/sale claims. |
| Shelf | Whole-photo flow and selecting a bottle; distinguish photo from continuous video | `webui/app/components/ShelfScanner.vue:62–95`, `webui/server/api/config.get.ts:11–18`. Match available/unavailable states; link only to real production routes. |
| Dish | How sauce/spice changes suggestions; how to check a result; reviewed decision-process examples | `webui/app/components/DinnerScanner.vue`, `webui/app/components/DinnerDishPicker.vue`, `webui/shared/dinner.ts`, taxonomy JSON. SSR copy, usable picker, reviewed factual examples, no indexed user inputs. |
| Producer directory | Explain range grouping, verification dates and actual producer coverage | `webui/app/pages/lineup/index.vue:28–47`, map JSON references. Match 25 entries, avoid claiming exhaustive Russian-winery coverage. |
| Optional label guide | New original sourced explanatory article at proposed `/guides/wine-label` (not an observed URL) | Proposed `webui/app/pages/guides/` page; existing `webui/app/components/WineLabelGuide.vue:13–27`, `webui/shared/label-reference.ts:5–40`, `webui/docs/label-guide-sources.md`. Editorial/legal review, SSR article, ordinary home/ideas links, traceable sources. |

Existing label documentation does not claim independent human wine-editor approval. Assign a real reviewer; do not fabricate credentials. Educational content can reuse original paraphrases/source registry, with attribution and a real revision date.

Internal linking should follow the task: scanner to shelf/dish (already present); explanatory sections to directory/reviewed guides once live; guides to genuine references. Footer→HTML map already gives shallow complete discovery. No orphan-based navigation rebuild is justified. Separate bot pages sharing a design are not automatically duplicate-content defects: they describe distinct destinations/platforms.

Keep currently good titles as baseline. Optional tested variants: home “Сканер винных этикеток: найти российское вино по фото — Что за вино?”; directory “Российские производители вина: карты линеек — Что за вино?”. These are proposals, not measured improvements. Use actual query/page evidence before adopting. [Google title guidance](https://developers.google.com/search/docs/appearance/title-link) supports descriptive distinct titles without synonym stuffing; there is no universal character-limit defect.

## SEO-018 — Russian alcohol-information publication review

**REQUIRES VERIFICATION, P2/M dependency; no violation is asserted.** `webui/app/pages/terms.vue:39–51` describes informational use, uncertainty, no sales/orders and adult access. `webui/app/app.vue:55,60` and `webui/app/components/AgeGate.vue:37` carry the warning; E01 confirms public gate/warning text.

Article 21(2)(8) of 38-FZ prohibits internet alcohol advertising. The current reproduced text also has distinct winery/tourism provisions in parts 10–11. Classifying actual information vs advertising matters; age confirmation or an “information/not an offer” label does not decide it. [Article 21, reproduced by ConsultantPlus](https://www.consultant.ru/document/cons_doc_LAW_58968/e4311f6720a4a4457f53bce4382af75b7858054e/).

FAS discusses informational assortments on producer/seller resources; that is not an automatic exemption for this independent recognition service. Examine operator relationships, placements, ranking of wines and calls to action. [FAS Order 1079/23 guidance, reproduced text](https://www.consultant.ru/document/cons_doc_LAW_478673/7655e692d8266ad2c58af5ab0aca1cac706aacf6/). These legal-source copies were read; no formal legal opinion was obtained.

Review actual copy/data in `webui/app/pages/lineup/[producer].vue`, `webui/app/components/ProductLineMap.vue`, producer JSON and `webui/app/components/WineExperiences.vue` before widening SEO-010. Review audience/promotion language in game/crocodile/ideas/bot pages, including any social-success or consumption incentives. The separate game needs its own source review. Preserve age/warning context; avoid health-benefit claims, fabricated tastings/ratings or wine-price Offers. Free-software schema offers are a different subject.

**Verification:** accountable Russian-law reviewer records decisions against actual content/commercial arrangements and proposed publication examples. Engineering compares approved decisions with SSR/UI/metadata/schema/outbound links. Specific changes follow those decisions rather than a generic compliance checklist.

## Google and Yandex measurement plan

Read-only Search Console/Yandex Webmaster exports are needed for selected canonicals, index/exclusion state, query-to-page mapping and clicks. They were unavailable. Inspect representative live URLs/rendered output in Google; validate XML and JS rendering/exclusions in Yandex. `.ru`, Russian content and `lang=ru` are coherent; actual regional settings are unknown. Do not invent a city address or add international alternates to a single-language site without a real need.

For content changes preserve a dated query/page baseline, then compare the same clusters after recrawl. Track successful tool/install/bot use separately from impressions. Traffic/CTR changes can have multiple causes; no numeric growth forecast is supported.
