"""Create a separate Testset entry for the same stored image."""
import json

import testsets


def duplicate_photo(conn, set_name, place, file_name, sha256=None):
    """Duplicate one entry in the transaction of the caller. Keep the source intact."""
    source = testsets._photo_row(conn, set_name, place, file_name)
    if sha256 is not None:
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise testsets.TestsetError(400, "`sha256` MUST be a SHA-256 string")
        if sha256 != source["sha256"]:
            raise testsets.TestsetError(409, "the source image changed before duplication")
    number = 2
    name = f"{file_name}.duplicate{number}.{source['extension']}"
    while conn.execute("SELECT 1 FROM test_photo WHERE set_name = ? AND place = ? "
                        "AND file_name = ?", (set_name, place, name)).fetchone():
        number += 1
        name = f"{file_name}.duplicate{number}.{source['extension']}"
    now = testsets.now_local()
    extra = json.dumps({"duplicated_from": file_name})
    conn.execute(
        "INSERT INTO test_photo (set_name, place, file_name, sha256, ts, copied_from, "
        "source_url, extra, box_left, box_top, box_right, box_bottom) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (set_name, place, name, source["sha256"], now, place, source["source_url"], extra,
         *(source[column] for column in testsets.BOX_COLUMNS)))
    testsets._edited(conn, set_name, now)
    row = testsets._photo_row(conn, set_name, place, name)
    return testsets._photo_answer(conn, set_name, place, name, row,
                                  duplicated_from=file_name)
