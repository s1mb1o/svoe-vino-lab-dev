# Semantic-v2 selection, isolation and label retention

Implementation revision: `2026-10-20-imagegen-selection-isolation-and-label-bounds`.

The selector consumes RGB and detector proposals. It does not consume benchmark
targets, expected identities, OCR answers or evaluation scores. An explicit tap
retains priority. The `_fallback` function and frozen benchmark expectations are
unchanged.

For live semantic inference with multiple package detections, one optional SAM3
request supplies fixed English context nouns: poster, screen, mirror, bottle held
in hand, transparent wrapping, and empty gift bag. This request shares the original
deadline and has a maximum 30-second timeout. A context failure keeps the valid
primary response. Caller-supplied instances remain an exact offline replay and
never trigger requests. Context detections are appended; primary detection IDs
and order remain stable.

A narrow finger can cross an unrelated bottle on its way to the subject. Its
outward ray must reach the selected bottle beyond the fingertip. Multiple opening
scales support different visible finger widths. Strong independent grip evidence
retains priority, including opposed terminal contact during a real pour. Very
small background fragments cannot establish a grip through a large projected
hand. A held-bottle text mask provides supporting evidence only alongside measured
body contact; the noun alone is insufficient.

Context masks can exclude a depiction on a poster, screen or mirror. When a screen
mask omits its displayed bottle as a hole, enclosing frame geometry also requires
an independent physical bottle outside the frame and no hand contact with the
enclosed object. Unattended carton artwork retains the existing separate-bottle
and hand-contact safeguards. A transparent wrapper or an opaque carrier with an
open window can refer to one visible physical bottle; a confirmed carrier grip
then supplies interaction evidence for that bottle, whose own silhouette is cropped.

Label ownership uses visible overlap before rectangle recovery. A surface envelope
and relative paper scale prevent small background shelf labels from inheriting a
foreground bottle's tilted rectangular box. Price cards require visible attachment.
Peeling paper, neck labels and attached tags still receive their own views. A sole
substantial labeled bottle can be distinguished from tiny shelf fragments after
interaction checks, without changing the geometric fallback order.

The output preserves source RGB, fills missing paper inside the subject rectangle,
and removes positively detected neighboring bottle pixels outside protected subject
and paper surfaces. Dense tilted paper masks delimit paper corners; sparse artwork
masks retain their complete declared paper rectangle. Every pixel in every returned
attached label mask is retained, including pixels outside its detector box. Remote
mask outliers can enlarge the crop bounds without enlarging the paper rectangle used
for ownership. Label views retain context around small tags.

A label-dominated close-up clipped at both opposite frame edges returns the original
context. A tiny unlabelled fragment also returns original context while preserving
its selected ID and decision reason. Empty valid responses return the original
frame. All these paths return a crop. Returning context cannot create missing label
detail or establish a readable label in a poor photograph.

The 152-image comparison is a development replay with unchanged primary proposals
plus new fixed RGB-only context requests. Scene-v1 and semantic-v2 receive identical
appended inputs; DIS runs independently on the original RGB. Fifty scenes have scene
approval, 102 remain pending, and no segmentation masks or crop-usability judgments
are human-approved. Target agreement, mask retention and isolation are diagnostic
proxies. Fewer false label attachments change the audit denominator; complete
retention of returned masks does not certify true label ownership or legibility.

Regression fixtures retain frozen expectations and image hashes. Tests cover recorded
pointing, framed depictions, window carriers, shelf-paper ownership, original RGB,
complete observed paper masks, camera roll, competing hands, real pours, shared
deadlines, optional failures and request-free replay.
