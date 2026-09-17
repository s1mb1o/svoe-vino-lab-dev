# The sideboard of the review page

Date: 2026-09-17

## Purpose

The reviewer moves a photo to another wine. The page holds one way to do this: the
button `move` on the card opens a field for the target slug. The sideboard is a second
way. The reviewer drags the card to a panel at the right, keeps it there, and drags it
later to the row of another wine.

## What does not change

The move machinery stays as it is. A drop on a wine row calls `POST /api/reassign`, the
same route that the button `move` calls. The field `reassign_to` of the entry records
the target. The file stays where it is. The button `apply` calls
`POST /api/apply-moves`, which moves the file and drops the label of the photo, because
the label judged the old pair. This answers the request "the annotation is cleaned": the
server already does it, on `apply`.

## Decisions of the owner

| Question | Decision |
|---|---|
| Where does the sideboard hold a photo with no target? | In the memory of the browser. A reload empties the sideboard. |
| What does the sideboard show? | Only the photos that the reviewer dragged in. A photo that carries a `reassign_to` from the button `move` stays in its row. |
| What does `apply` do with a photo that has no target? | Nothing. The photo is not part of the work and `apply` states nothing about it. |

## The state

```js
let HELD = [];   // [{slug, file}] the photos in the sideboard
```

The server never learns about `HELD`. The list holds the source slug and the file name,
which is the identity of a photo everywhere else in the page.

## The rules of the drag

1. Every photo card carries `draggable="true"`. The `dragstart` writes the type
   `application/x-photo` with the value `{slug, file}`.
2. A drop on the sideboard puts the photo in `HELD`. The card leaves the row of its wine
   and stands in the panel. No request is sent.
3. A drop on a wine row calls `POST /api/reassign` with the target of that row. The
   photo leaves `HELD` and stands again in the row of its source slug, with the mark of
   a pending move.
4. A drop on the row of the source slug takes the photo out of `HELD` and sends nothing.
   This is the gesture "put it back".
5. A card that is not in the sideboard follows the same rules. A drop of such a card on
   another wine row reassigns it at once. One rule for every card is less code than two.

The existing drop of a picture from another tab tests `Files` and the URL types. The new
drag carries neither type, so the two paths do not meet.

## The render

`render()` leaves out every photo of `HELD` from the cards of its row. `tally()` is not
touched, so the counts of a row still state what the server holds. `renderHeld()` fills
the panel.

After `/api/reload` and after `/api/apply-moves`, `pruneHeld()` drops every entry of
`HELD` whose photo is no longer in `ROWS`.

## The limits

The sideboard is a holding area of one browser tab. A reload, a second tab, and a second
machine do not see it. A photo in the sideboard is unknown to the agent API and to
`match_run.py`; it keeps its label until a target is chosen and `apply` runs.
