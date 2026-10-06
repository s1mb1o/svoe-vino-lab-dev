# Plan 92: Question-option scores for cluster re-rank

Date: 2026-09-30

Status: implemented and verified on 2026-09-30.

## Problem

The cluster re-rank lets the VLM select a card in `verdict` mode.
The Aratti rule treated missing `ПОЛУСУХОЕ` text as proof of the other card.
The base embedding had the correct 2024 card at rank 1.
The direct VLM verdict moved that card to rank 2.

## Selected approach

The owner selected question-option scores.
One VLM call MUST return a score from 0 to 100 for every option of every question.
The scores of one question MUST total 100.
Each question MUST include the option `not visible`.
The option `other` means that the label shows a different value.
The option `not visible` means that the value is absent, unreadable, or outside the photo.
The VLM MUST NOT select a card.

## Scoreable questions

The re-rank MUST use each valid difference-sheet question.
The re-rank MUST also use a one-sided `feature` or `vintage` question.
A one-sided question has one non-null expected answer and null expected answers for the
other cards.
The re-rank MUST NOT use an empty question.
The re-rank MUST NOT use a `serial` or `bottle` question.
If a rule has no scoreable question, the re-rank MUST keep the base order and MUST NOT
call the VLM.

## Evidence calculation

For one question, the support of a card is the score of its expected option divided by
100.
The neutral score is the score of `not visible` divided by 100.
The adjusted support is `max(0, support - neutral score)`.
A null expected answer MUST have adjusted support 0.
The evidence score of a card is the mean adjusted support of its non-null expected
answers.
A card with no non-null expected answer has evidence score 0.

The decision score is:

```text
embedding score + 0.05 * evidence score
```

The code MUST order the cards by decision score.
A decision-score tie MUST keep the base order.
Only cards of the triggered cluster inside the configured window MAY move.
The output positions MUST keep their original public `score` values for compatibility.

The value `0.05` limits a perfect VLM evidence score to a cosine correction of 0.05.
This limit lets strong label evidence correct a close visual match.
This limit prevents weak evidence from replacing a substantially better visual match.

## VLM response

The response MUST be one JSON object.
Each top-level key MUST be a question ID.
Its value MUST be an object that maps every option to an integer score.
The JSON Schema MUST require all questions and all options.
The code MUST reject a missing score, an extra score, a non-integer score, an
out-of-range score, or a total other than 100.
An invalid response MUST keep the base order.

Example:

```json
{
  "q1": {
    "semi-dry": 3,
    "other": 2,
    "not visible": 95
  }
}
```

This example gives no positive evidence to either Aratti card.
The null-valued card gets no evidence.
The 2024 card gets `max(0, 0.03 - 0.95)`, which is 0.
The base embedding order stays.

## Observability

The candidate explanation and the trace step MUST hold these values:

- The scoreable questions and their options.
- The raw option scores from the VLM.
- The embedding score of each card in the window.
- The evidence score of each card in the window.
- The decision score of each card in the window.
- The order before and after the decision.
- The decision weight.
- An error when the response is invalid or the VLM call fails.

The `/recognize` step view MUST show a step named `VLM evidence re-rank`.
The step MUST show the option scores and the three scores of each candidate.

## Compatibility

The runtime MAY read existing `sheet` and `verdict` rule artifacts.
The runtime MUST ignore the direct verdict text and the card letters.
No rule artifact rebuild is required.
No schema change is required.

## Tests

Tests MUST cover these cases:

1. A strong expected-option score moves a close candidate to rank 1.
2. `not visible` gives no positive evidence.
3. A null expected answer gets no positive evidence.
4. The Aratti one-sided question keeps the correct base order when the feature is not
   visible.
5. A one-sided question can move its card when the feature is visible.
6. An invalid score object keeps the base order and records the error.
7. A legacy verdict rule with no scoreable question calls no VLM.
8. The trace and the `/recognize` step record expose the option, embedding, evidence,
   and decision scores.

## Result

The focused tests pass.
The full suite has 1,503 passing tests and one skipped test.
The JavaScript syntax check passes.
The original Aratti photo was sent through `/api/recognize` with
`barcode-rerank-siglip2-512-crop`.
The VLM returned `semi-dry: 0`, `other: 0`, and `not visible: 100`.
Both evidence scores were 0.
The decision scores stayed 0.8286 and 0.8082.
The 2024 card stayed at rank 1.

## Response validation recovery, 2026-10-02

The owner approved one retry for an invalid evidence response.
The retry MUST bypass model cache lookup for that call alone.
The retry MUST include the validation errors and require a complete corrected response.
The runtime MUST NOT retry a transport failure through this recovery path.
If the retry is invalid or fails, the base order MUST stay.
Partial scores MUST NOT contribute to the decision.

Each attempt MUST retain `raw_text`, `raw_option_scores`, `validation_errors`,
`error`, `cached`, and `ms` in `attempts`.
Each completed response MUST also record `finish_reason`.
The explanation MUST expose the last received raw scores and validation errors.
The accepted scores remain in `option_scores`.
Fresh invalid responses MUST NOT enter the model cache.
Existing invalid cache records remain available as diagnostic evidence.
A cached invalid response still triggers the fresh retry.
The retry prompt has its own cache key. It does not overwrite the original request.

The row view and the step popup MUST use the same evidence renderer.
The renderer MUST show the raw scores and mark the rejected question.
It MUST expose both attempts after a retry.
An older run without raw scores MUST state that the scores were not recorded.
It MUST NOT describe a recorded validation failure as an absent model answer.
