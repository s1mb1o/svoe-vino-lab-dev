# MLflow tracking in Workbench

Read the [shared tracking contract](../../matcher/docs/mlflow.md).
Issue: [19](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/19).

`pipeline/benchmark.py` exports results after it saves the local benchmark files.
This hook covers Testset runs, remote matcher runs, and embedding self-tests that use `run_benchmark`.
The Runs page continues to use the existing local files.
The run job log reports `MLflow export synced` or `MLflow export pending`.
The local run directory holds `.mlflow/state.json` when tracking is enabled.

Install the optional client in the environment that starts the Workbench run job.
Set `MLFLOW_TRACKING_ENABLED=true`, `MLFLOW_TRACKING_URI`, and `MLFLOW_EXPERIMENT_NAME` in that environment.
The Workbench server must inherit these variables before it starts a run subprocess.
This implementation does not change the running server environment.

Use the export command for existing run directories and ArcFace outputs.
The command does not repeat recognition or training.
Read [COMMANDS.md](../COMMANDS.md) for commands from the Workbench root.

Do not delete local experiment results after export.
This integration is experiment tracking. Backup and restore require the work in issue 18.
