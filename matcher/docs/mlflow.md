# MLflow experiment tracking

Issue: [19](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/19).

MLflow tracking is optional.
The matcher inference service does not require MLflow.
The label-only and label-parts evaluators export results after they save `summary.json`.
Workbench exports each completed benchmark through the same adapter.
Use the command below to export an existing experiment or retry an export.

## Configuration

Install the optional client in the Python environment that runs the experiment.
Run this command from the repository root.

```sh
python -m pip install -r matcher/requirements-mlflow.txt
```

Set these variables in that environment:

| Variable | Meaning | Default |
| --- | --- | --- |
| `MLFLOW_TRACKING_ENABLED` | Enable automatic export with `true`, `1`, or `yes`. | Disabled |
| `MLFLOW_TRACKING_URI` | Set the tracking server URI. This value is required for export. | None |
| `MLFLOW_EXPERIMENT_NAME` | Set the experiment name. | `svoe-vino-lab` |
| `MLFLOW_TRACKING_USERNAME` | Supply the username when the server requires basic authentication. | SDK default |
| `MLFLOW_TRACKING_PASSWORD` | Supply the password through the environment. | SDK default |
| `MLFLOW_TRACKING_TOKEN` | Supply a bearer token through the environment. | SDK default |
| `MLFLOW_HTTP_REQUEST_TIMEOUT` | Set the timeout in seconds for each SDK HTTP request. | `5` for this exporter |
| `MLFLOW_HTTP_REQUEST_MAX_RETRIES` | Set SDK HTTP retry count. Use the explicit export command for later retry. | `0` for this exporter |

Use the existing server URI. Do not put credentials in a URI or a configuration file.
The SDK reads authentication from the environment.
Automatic export runs after local result finalization.
Export time is outside the measured recognition latency.
Export time can delay process completion.
The timeout applies to each HTTP request. It is not a total export deadline.

The adapter uses `MlflowClient`. It does not use a process-global active run.
The default inference dependencies and Docker image do not install the optional client.
Use a separate evaluation environment when tracking is required.

## Export and retry

Set `MLFLOW_TRACKING_URI` before the command.
The explicit command enables export even when automatic export is disabled.
Run these examples from the repository root. Replace each placeholder path.

```sh
python -m matcher.mlflow_tracking workbench/runs/RUN_ID
python -m matcher.mlflow_tracking PATH_TO_MATCHER_EVALUATION --kind matcher
python -m matcher.mlflow_tracking PATH_TO_ARCFACE_OUTPUT --kind arcface
```

The command prints a JSON status.
Exit code `0` means `synced`. Exit code `1` means `pending`.
Automatic export reports a pending status without changing the experiment result.
A missing SDK and an unavailable server both leave local results available.
Correct the environment or restore the server. Then repeat the command.

The directory `.mlflow/` stores the local export state and lock.
`state.json` holds one record per destination and experiment.
The destination key is a hash. The file does not store the tracking URI or credentials.
Each record holds the source ID, remote run ID, experiment ID, payload hash, and artifact hashes.
An error record holds only the exception type. SDK exception text can contain credentials.

Keep `.mlflow/` with the experiment directory.
Repeated export reuses the remote run and skips a complete unchanged export.
Retry reuses uploaded artifacts and the remote run ID.
The adapter can recover a lost create response through the source ID tag.
The lock prevents concurrent export from the same local directory.
Independent copies that omit `.mlflow/` are independent sources.
Do not delete the state file to retry.
Changed source artifacts require a new experiment directory.
The exporter refuses to replace artifacts of a recorded run with changed content.

## Artifact contract

The exporter reads only these files:

| Format | Required files | Optional files |
| --- | --- | --- |
| Workbench | `run.json`, `metrics.json` | `queries.jsonl`, `predictions.jsonl`, `results.jsonl` |
| Matcher evaluation | `provenance.json`, `summary.json` | `config.yaml`, `predictions.jsonl`, and `results.jsonl` in each cell listed in `summary.json` |
| ArcFace | `training-snapshot.json`, `report.json` | `config.yaml` |

The exported files are sanitized copies. Local files remain unchanged.
YAML configuration becomes a JSON artifact named `config.yaml.json`.
Credential fields become `<redacted>`.
HTTP URL credentials, query parameters, and fragments are removed.
Raw traces, groups, headers, messages, image bodies, and base64 fields are omitted.
An error payload becomes a Boolean failure indicator.
Logs, free-text reports, arbitrary files, image files, and model weights are not exported.
Existing provenance and checkpoint hashes remain in the structured artifacts.
Review custom configuration before export. Do not place secrets in unstructured descriptions.
Artifact symlinks are not supported.

`manifest.json` records the byte count and SHA-256 of every exported data artifact.
The manifest describes the sanitized bytes.
Numeric dictionaries become dot-separated metric keys.
Null, Boolean, and non-finite values are not metrics.
Unsupported characters in key segments become underscores plus a short hash.
ArcFace history records use the epoch as the MLflow step.
Parameters include run options, backend settings, model state, and available input hashes.
Full values remain in the artifacts. MLflow parameter values are limited to 1,000 characters.

A partial Workbench run has MLflow status `KILLED`.
A matcher evaluation with query errors has MLflow status `FAILED`.
An experiment that completes its benchmark has status `FINISHED`.
Per-query failures remain in the metrics and results.
An experiment that fails before saving its required reports has no automatic export.
ArcFace export is explicit. Training does not acquire an MLflow dependency.

## Storage boundaries

Use local artifact storage or an MLflow artifact proxy.
The adapter refuses direct S3 artifact locations.
Direct SDK uploads do not implement the workspace checksum contract.
The operator must configure durable storage and checksum handling behind a proxy separately.
This change does not deploy a server or change a running service.
Backup and restore remain in [issue 18](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/18).
Model Registry promotion and production request tracing are outside this integration.

## Validation

Run the adapter tests from the repository root. These tests use synthetic data.

```sh
python -m unittest discover -s matcher/tests -p 'test_mlflow_tracking.py' -v
```

Use an isolated Python environment for the real store check.
Install `matcher/requirements-mlflow.txt`, `sqlalchemy`, and `alembic` there.
The test creates a temporary SQLite database and local artifacts.
It opens no listening port. It runs no model inference.

```sh
MLFLOW_TEST_INTEGRATION=1 python -m unittest discover -s matcher/tests -p 'test_mlflow_integration.py' -v
```
