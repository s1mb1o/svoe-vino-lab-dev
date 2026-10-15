"""Move one Testset photo between sets without changing its annotations."""
import re

import testsets


def destination_name(conn, set_name, place, source):
    """Choose an unused name. Keep the source prefix for rank and confidence."""
    name = source["file_name"]
    number = 1
    while conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? "
                       "AND file_name = ?", (set_name, place, name)).fetchone():
        number += 1
        name = f"{source['file_name']}.moved{number}.{source['extension']}"
    return name


def transfer_photo(conn, set_name, place, file_name, to_set, sha256):
    """Move one entry in the caller's transaction. Keep its image and annotations."""
    source = testsets._photo_row(conn, set_name, place, file_name)
    if not isinstance(to_set, str) or not to_set:
        raise testsets.TestsetError(400, "the request holds no `to_set`")
    testsets._check_set(conn, to_set)
    if to_set == set_name:
        raise testsets.TestsetError(400, "choose a different testset")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise testsets.TestsetError(400, "`sha256` MUST be a lowercase SHA-256 string")
    if sha256 != source["sha256"]:
        raise testsets.TestsetError(409, "the source image changed before the move")
    if conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? "
                    "AND sha256 = ?", (to_set, place, sha256)).fetchone():
        raise testsets.TestsetError(409, "this image already belongs to the same wine in %s"
                                   % to_set)
    name = destination_name(conn, to_set, place, source)
    conn.execute("UPDATE test_photo SET set_name = ?, file_name = ? "
                 "WHERE set_name = ? AND place = ? AND file_name = ?",
                 (to_set, name, set_name, place, file_name))
    # The foreign key moves comments with the photo. Cover connections with it off too.
    conn.execute("UPDATE test_photo_comment SET set_name = ?, file_name = ? "
                 "WHERE set_name = ? AND place = ? AND file_name = ?",
                 (to_set, name, set_name, place, file_name))
    now = testsets.now_local()
    for name_of_set in (set_name, to_set):
        testsets._edited(conn, name_of_set, now)
    moved = testsets._photo_row(conn, to_set, place, name)
    answer = testsets._photo_answer(conn, to_set, place, name, moved)
    answer.update(from_set=set_name, to_set=to_set, source_file=file_name,
                  source_counts=testsets.counts(conn, set_name), sets=testsets._sets(conn))
    return answer
