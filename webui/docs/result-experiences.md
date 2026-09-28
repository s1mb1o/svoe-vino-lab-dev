# Result experience specification

Status: implemented and browser-verified on 2026-09-28.

## Scope

The portal MUST show a mandatory age confirmation before it shows the application.
The portal MUST show four demonstration actions after it resolves wine metadata.
All four actions MUST run in the browser.
The actions MUST NOT call a retailer, geolocation, audio, recommendation, or product-line API.

## Age confirmation

The gate MUST ask whether the visitor is at least 18 years old.
The gate MUST block the application until the visitor confirms.
The confirmation MUST use the local storage key `svoe-vino.age-confirmed.v1`.
The value MUST be `yes`.
The portal MUST NOT store a birth date.
The negative action MUST show a blocked state.

## Result actions

The result MUST show these actions:

1. `Подобрать продукты`.
2. `Рассказать об этикетке`.
3. `История о вине`.
4. `Путеводитель по линейке`.

Each action MUST open one native dialog.
The dialog MUST close with its close control, Escape, and a backdrop click.
The dialog MUST return focus to the action that opened it.
Every dialog MUST state that its content is a demonstration.

## Product demonstration

The first view MUST explain why a future service asks for location.
The confirmation control MUST simulate location permission.
It MUST NOT use `navigator.geolocation`.
It MUST NOT store coordinates.
The result MUST identify a demonstration `СуперЛента` store.
The result MUST show three fictional domestic food products.
Each product MUST explain its pairing with the recognized wine.
One product MUST show an explicit `Продвижение · демо` label.
The dialog MUST explain that a future service can prioritize a brand only with a visible label.

## Label explanation

The dialog MUST show the grape varieties from the resolved wine metadata.
The dialog MUST use Syrah and Viognier as a fixed explanation example.
The copy MUST state that this example is not a claim about the recognized wine.
The copy MUST explain why variety information changes the expected wine style.

## Story demonstration

The dialog MUST show one fictional story at random.
It MUST provide a control for another story.
It MUST state that a future version can use audio.
It MUST state that the story is fiction and is not advertising or a producer fact.

## Product-line guide

The dialog MUST show a demonstration map for `Абрау-Дюрсо`.
The map MUST place premium examples at the top and mass-market examples at the bottom.
The map MUST state that this placement is not a quality rating.
The user MUST be able to zoom in and zoom out.
The direction control MUST move the current demonstration wine into view.
A double click on a node MUST open its `vino-svoe.ru` page.
The selected node MUST also show a normal link for keyboard and touch users.

## Privacy and compliance

The result actions MUST not promote alcohol or contain purchase actions for alcohol.
The product demonstration MAY explain the future promotion of domestic food products.
Paid food priority MUST always have a visible label.
The portal MUST retain the health warning in its footer.
