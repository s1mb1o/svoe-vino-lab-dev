from __future__ import annotations

import argparse
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .storage import DataDeletionPlan, Repository

LOG = logging.getLogger("chto_za_vino_bot.data_lifecycle")
DATA_DIRECTORIES = ("accepted", "quarantine", "artifacts")


@dataclass(frozen=True, slots=True)
class DeletionResult:
    requests: int
    users: int
    files: int


def _delete_files(data_root: Path, plan: DataDeletionPlan) -> int:
    resolved_root = data_root.resolve()
    allowed_roots = tuple((resolved_root / name).resolve() for name in DATA_DIRECTORIES)
    deleted = 0
    for relative_path in plan.paths:
        candidate = (resolved_root / relative_path).resolve()
        if not any(root in candidate.parents for root in allowed_roots):
            raise ValueError(f"stored data path is outside an allowed directory: {relative_path}")
        try:
            candidate.unlink()
        except FileNotFoundError:
            continue
        deleted += 1
    artifacts_root = (resolved_root / "artifacts").resolve()
    for relative_path in plan.artifact_directories:
        candidate = (resolved_root / relative_path).resolve()
        if artifacts_root not in candidate.parents:
            raise ValueError(f"artifact directory is outside the artifact store: {relative_path}")
        if not candidate.exists():
            continue
        if not candidate.is_dir():
            raise ValueError(f"artifact directory is not a directory: {relative_path}")
        deleted += sum(path.is_file() or path.is_symlink() for path in candidate.rglob("*"))
        shutil.rmtree(candidate)
    return deleted


def purge_expired_data(
    repository: Repository,
    data_root: Path,
    *,
    cutoff: int,
) -> DeletionResult:
    plan, users, files = repository.delete_expired_data(
        cutoff,
        lambda selected: _delete_files(data_root, selected),
    )
    return DeletionResult(requests=plan.request_count, users=users, files=files)


def delete_user_data(
    repository: Repository,
    data_root: Path,
    *,
    user_id: int,
) -> DeletionResult:
    plan = repository.user_data_deletion_plan(user_id)
    files = _delete_files(data_root, plan)
    requests, users = repository.delete_user_data(user_id)
    return DeletionResult(requests=requests, users=users, files=files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete all stored data of one Telegram user. Stop the bot before this command."
    )
    parser.add_argument("user_id", type=int)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm permanent deletion.",
    )
    arguments = parser.parse_args()
    if arguments.user_id <= 0:
        parser.error("user_id must be positive")
    if not arguments.confirm:
        parser.error("--confirm is required")
    data_root = Path(os.getenv("BOT_DATA_ROOT", "data")).expanduser()
    database_file = Path(
        os.getenv("BOT_DATABASE", str(data_root / "bot.sqlite3"))
    ).expanduser()
    repository = Repository(database_file)
    try:
        result = delete_user_data(
            repository,
            data_root,
            user_id=arguments.user_id,
        )
    finally:
        repository.close()
    print(
        f"Deleted user {arguments.user_id}: "
        f"requests={result.requests} files={result.files}"
    )


if __name__ == "__main__":
    main()
