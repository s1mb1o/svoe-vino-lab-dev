# DINOv3 + ArcFace

ArcFace trains an embedding space from labelled wine images. Each wine identity is
one training class. The loss adds an angular margin to the target class. This makes
images of the same identity closer and makes different identities easier to separate.
ArcFace is a training loss. Recognition uses the trained embedding and cosine search.

The source design is [Pomelkin/vinishko](https://github.com/Pomelkin/vinishko/tree/cbb148703bb33aa302c9916f0165e33a1ae975ab/vis_seacher_training).
The inspected revision is `cbb148703bb33aa302c9916f0165e33a1ae975ab`.
Its encoder combines the DINOv3 CLS token with GeM pooling of patch tokens.
Its projection uses BatchNorm, Linear, and BatchNorm. It trains with three sub-centers
per wine and a class-frequency angular margin. It can fine-tune the backbone.
Its inference export removes the loss and the class centers.

This implementation uses the existing cached DINOv3 CLS features. It freezes the
backbone and trains a linear projection to 512 dimensions. It implements sub-center
ArcFace and the class-frequency margin. It does not reproduce vinishko's patch pooling
or backbone fine-tuning. The implementation does not copy vinishko source files.

## Training

`pipeline/train_arcface.py` reads a built DINOv3 index and the catalogue database.
The training command sends no images to an external service.
PyTorch is required for training. NumPy is sufficient for projection inference.
The base DINOv3 features still come from the configured model backend.
See [COMMANDS.md](../COMMANDS.md) for executable commands.

The trainer MUST use the base embedding without an `arcface` entry. It reads only
current rows for Active catalogue wines. It applies the catalogue's `main_patched`
selection. It excludes images and duplicate groups assigned to multiple wine IDs.
It does not read benchmark query labels or test-set tables.

The trainer groups all views and rotations of one source image. It also joins source
groups that share an exact prepared image or derivative. A group remains in one split.
The validation split holds out source groups within wine identities. A wine with one
source group remains in training. Such a wine has no independent validation query.
Near-duplicate photographs with different bytes can still cross the split.
The catalogue labels and image groups SHOULD be reviewed before a large training run.

The projection starts from PCA fitted on training rows alone. Class centers start
from the projected training features. The trainer samples wine identities with equal
expected weight. Three centers allow different visual variants of each wine.
The default target margin is `0.5 * source_count ** -0.25 + 0.05` radians.
The default logit scale is 30. These settings are configurable through the CLI.

For the target class, the logit uses `scale * cos(theta + margin)`. Other classes use
`scale * cos(theta)`. Each class cosine is the maximum cosine of its sub-centers.
A monotonic fallback handles angles close to pi. The loss is cross entropy.

The trainer evaluates recall@1, recall@5, and recall@10 after every epoch. The
validation gallery contains training sources alone. A query uses references in the
same view. Multiple reference images count as one wine. Each query row receives
`1 / validation_rows_in_its_source_group` weight. Queries without a same-view
reference are counted as skipped. Only eligible rows enter the metric denominator.
A group with skipped rows therefore contributes less total weight.
Checkpoint selection uses validation recall@1. A tied score keeps the earlier epoch.
Epoch 0 is the PCA initialization. The report identifies an epoch-0 selection explicitly.
These results measure validation on known wine identities. They do not measure
performance on an untouched test set or on new wine identities.

The new artifact directory contains:

- `projection.npz`: projection weights, bias, and model metadata. It contains no pickle.
- `report.json`: baseline metrics, epoch metrics, split indices, settings, and checkpoint hash.
- `training-snapshot.json`: catalogue IDs, source groups, vector rows, and input hashes.
- `config.yaml`: a separate copy of the configuration with the new embedding and pipelines.

The command refuses an existing artifact directory or output index. Use a new name
for a new training run. `--export-index` transforms the current source vectors and
copies their prepared images into a new catalogue index. This needs no inference call.
The original configuration and index remain available.

## Recognition

An embedding entry MAY contain:

```yaml
arcface:
  checkpoint: data/models/example/projection.npz
  sha256: <64 lowercase hexadecimal characters>
```

Relative checkpoint paths resolve from the Workbench root. The digest MUST match the
checkpoint bytes. The checkpoint's base model and `extra_body` MUST match the entry.
The digest enters the item hash. A new checkpoint therefore requires a new index or
a rebuild. Base DINOv3 vectors and projected vectors MUST NOT share an index.

`build_embeddings.make_backend` wraps either the HTTP backend or the local backend.
The wrapper L2-normalizes the base feature, applies the projection, and L2-normalizes
the result. The catalogue builder and the query runner use this same wrapper.
The local backend also supports DINOv3's `pooler_output` without `get_image_features`.
The trained class centers are not needed for recognition. A new catalogue wine can
be indexed with the projection without adding a new classifier output.

The generated full-photo and crop pipelines use the existing Workbench cosine
search. Their names are the output embedding name and that name with `-crop`.
Existing OCR and reranking steps MAY use the resulting candidates. A cosine score
is not a calibrated probability. Existing SigLIP2 thresholds MUST NOT be transferred
without validation. Visually identical labels can still require OCR for vintage or
product details.

## Further training

The cached-feature implementation cannot learn image augmentations, GeM pooling,
or changes to the DINOv3 backbone. Full fine-tuning needs local backbone weights,
labelled images with multiple independent photographs, and a separate image trainer.
The first deployment SHOULD compare this projection against base DINOv3 and SigLIP2
on an untouched real-photo test set. Validation recall from checkpoint selection
MUST NOT be reported as that test result.

References: [ArcFace paper](https://arxiv.org/abs/1801.07698),
[official DINOv3 implementation](https://github.com/facebookresearch/dinov3),
[vinishko loss](https://github.com/Pomelkin/vinishko/blob/cbb148703bb33aa302c9916f0165e33a1ae975ab/vis_seacher_training/losses.py).

## Local artifact of 2026-10-06

The artifact is `data/models/dinov3-vitl16-arcface-20261006-v2/`.
Its separate embedding is `gx10-dinov3-vitl16-arcface-v2`.
Its source is `gx10-dinov3-vitl16`.
Training uses 5,909 current unambiguous vectors from 2,028 wine identities.
The split contains 5,420 training rows and 489 validation rows in 294 source groups.
Two validation rows have no same-view training reference. The metrics use 487 rows
with total source-group weight 293. The catalogue has 1,798 identities with one
source group. These identities have no independent validation query.

Thirty epochs completed. Validation selected epoch 24. The exported index contains
5,939 current vectors. The index includes ambiguous references for catalogue search;
the trainer excludes those references from its labels.

| Source-disjoint catalogue validation | Base DINOv3 | DINOv3 + ArcFace |
| --- | ---: | ---: |
| Recall@1 | 32.25% | 43.34% |
| Recall@5 | 59.90% | 80.20% |
| Recall@10 | 67.41% | 89.76% |

The report and snapshot files preserve the exact split and metrics. These are
checkpoint-selection validation results. An untouched real-photo test is not yet run.
The saved configuration contains the two new pipelines. The shared lab configuration
and production endpoints were not changed.
