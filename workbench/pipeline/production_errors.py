"""Import safe request evidence. Publish only an operator-reviewed identity."""
import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import imagestore
import labdb
import testsets

MAX_BYTES = 10 * 1024 * 1024
KEY = re.compile(r'[A-Za-z0-9_.:-]{1,160}')


class ReviewError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def image_path(conn, digest, extension):
    db = conn.execute('PRAGMA database_list').fetchone()[2]
    return Path(labdb.data_root(db)) / 'production-errors' / (digest + '.' + extension)


def key(source, request_id):
    if not all(isinstance(v, str) and KEY.fullmatch(v) for v in (source, request_id)):
        raise ReviewError('source and request_id MUST be bounded identifiers')
    return source, request_id


def capture(conn, record, data):
    """Keep the original snapshot immutable. Repeated imports are idempotent."""
    source, request_id = key(record.get('source'), record.get('request_id'))
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ReviewError('image MUST be at most 10 MiB')
    extension, _, _ = testsets.read_upload(data)
    digest = hashlib.sha256(data).hexdigest()
    if record.get('image_sha256') != digest:
        raise ReviewError('image SHA-256 does not match the request')
    candidates = record.get('candidates')
    feedback = record.get('feedback')
    if not isinstance(candidates, list) or len(candidates) > 100 or not isinstance(feedback, dict):
        raise ReviewError('candidates and feedback MUST be explicit evidence')
    # Store only recognition evidence. A bot export MUST NOT include user identity.
    clean = []
    for c in candidates:
        if not isinstance(c, dict) or not isinstance(c.get('slug'), str):
            raise ReviewError('each candidate MUST hold a slug')
        clean.append({k: c[k] for k in ('slug', 'rank', 'score') if k in c})
    feedback = {k: feedback[k] for k in ('match', 'selected_slug', 'selected_rank', 'at', 'quality_issues') if k in feedback}
    old = conn.execute('SELECT image_sha256 FROM production_error WHERE source=? AND request_id=?', (source, request_id)).fetchone()
    if old:
        if old[0] != digest:
            raise ReviewError('this request already holds a different image')
        return {'ok': True, 'duplicate': True, 'source': source, 'request_id': request_id}
    path = image_path(conn, digest, extension)
    path.parent.mkdir(parents=True, exist_ok=True)
    imagestore.store_bytes(data, str(path), digest)
    conn.execute('INSERT INTO production_error(source,request_id,image_sha256,extension,candidates_json,feedback_json,imported_at) VALUES(?,?,?,?,?,?,?)',
                 (source, request_id, digest, extension, json.dumps(clean), json.dumps(feedback), now()))
    return {'ok': True, 'duplicate': False, 'source': source, 'request_id': request_id}


def get(conn, source, request_id):
    cursor = conn.execute('SELECT * FROM production_error WHERE source=? AND request_id=?', key(source, request_id))
    row = cursor.fetchone()
    if not row:
        raise ReviewError('request is not in the review queue')
    return dict(zip([c[0] for c in cursor.description], row))


def related_hashes(conn, digest):
    """Include exact processed descendants and ancestors, not only source bytes."""
    hashes = {digest}
    while True:
        marks = ','.join('?' for _ in hashes)
        rows = conn.execute(f'SELECT source_sha256,sha256 FROM image_derivative WHERE source_sha256 IN ({marks}) OR sha256 IN ({marks})', tuple(hashes) * 2).fetchall()
        more = hashes | {v for r in rows for v in r}
        if more == hashes:
            return hashes
        hashes = more


def check_purpose(conn, digest, purpose):
    hashes = related_hashes(conn, digest)
    marks = ','.join('?' for _ in hashes)
    if conn.execute(f'SELECT 1 FROM production_error WHERE image_sha256 IN ({marks}) AND state IN (\'reviewed\',\'published\') AND purpose<>? LIMIT 1', (*hashes, purpose)).fetchone():
        raise ReviewError('this image family has a different assigned purpose')
    table = 'test_photo' if purpose == 'reference' else 'wine_image'
    if conn.execute(f'SELECT 1 FROM {table} WHERE sha256 IN ({marks}) LIMIT 1', tuple(hashes)).fetchone():
        raise ReviewError('reference and benchmark image families MUST be separate')


def review(conn, source, request_id, identity, purpose, reviewer, note, reject=False):
    row = get(conn, source, request_id)
    if row['state'] == 'published':
        raise ReviewError('published provenance is immutable')
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(note, str) or not note.strip():
        raise ReviewError('reviewer and review note are required')
    if len(reviewer) > 160 or len(note) > 4000:
        raise ReviewError('review text is too long')
    if not reject:
        if purpose not in ('reference', 'benchmark'):
            raise ReviewError('assign reference or benchmark purpose')
        if identity is not None and (not isinstance(identity, str) or not conn.execute('SELECT 1 FROM wine_catalog WHERE wine_slug=? AND state=\'Active\'', (identity,)).fetchone()):
            raise ReviewError('reviewed identity MUST be an active catalog slug or explicit null')
        if identity is None and purpose != 'benchmark':
            raise ReviewError('a reference MUST have a resolved catalog identity')
        check_purpose(conn, row['image_sha256'], purpose)
        other = conn.execute('SELECT identity FROM production_error WHERE image_sha256=? AND state IN (\'reviewed\',\'published\') AND NOT (source=? AND request_id=?)', (row['image_sha256'], source, request_id)).fetchall()
        if any(r[0] != identity for r in other):
            raise ReviewError('the same image already has a different reviewed identity')
    state = 'rejected' if reject else 'reviewed'
    event = dict(state=state, identity=identity, purpose=purpose, reviewer=reviewer, note=note)
    conn.execute('UPDATE production_error SET state=?,identity=?,purpose=?,reviewer=?,review_note=? WHERE source=? AND request_id=?',
                 (state, identity if not reject else None, purpose if not reject else None, reviewer, note, source, request_id))
    conn.execute('INSERT INTO production_error_review(source,request_id,at,review_json) VALUES(?,?,?,?)', (source, request_id, now(), json.dumps(event)))
    return {'ok': True, **event}


def publish(conn, source, request_id, set_name='production-reviewed', image_type='full_front'):
    row = get(conn, source, request_id)
    if row['state'] == 'published':
        return {'ok': True, 'duplicate': True, 'destination': row['destination']}
    if row['state'] != 'reviewed':
        raise ReviewError('an operator MUST review the identity before publication')
    check_purpose(conn, row['image_sha256'], row['purpose'])
    data = image_path(conn, row['image_sha256'], row['extension']).read_bytes()
    if hashlib.sha256(data).hexdigest() != row['image_sha256']:
        raise ReviewError('quarantine image SHA-256 changed')
    if row['identity'] and not conn.execute('SELECT 1 FROM wine_catalog WHERE wine_slug=? AND state=\'Active\'', (row['identity'],)).fetchone():
        raise ReviewError('reviewed identity is no longer active')
    if row['purpose'] == 'benchmark':
        if not conn.execute('SELECT 1 FROM test_set WHERE set_name=?', (set_name,)).fetchone():
            testsets.create_set(conn, set_name)
        place = row['identity'] or testsets.NULL_SLUG
        existing = conn.execute('SELECT file_name FROM test_photo WHERE set_name=? AND place=? AND sha256=?', (set_name, place, row['image_sha256'])).fetchone()
        if existing:
            file_name = existing[0]
        else:
            result = testsets.upload_photo(conn, set_name, place, data, request_id)
            file_name = result['file']
            testsets.set_label(conn, set_name, place, file_name, 'positive')
        testsets.add_photo_comment(conn, set_name, place, file_name, f'Reviewed production request {source}/{request_id}; reviewer {row["reviewer"]}; {row["review_note"]}', source='script')
        destination = f'testset:{set_name}/{place}/{file_name}'
    else:
        if image_type not in ('full_front', 'label_front', 'full_back', 'label_back'):
            raise ReviewError('choose an explicit reference image type')
        extension, width, height = testsets.read_upload(data)
        db = conn.execute('PRAGMA database_list').fetchone()[2]
        path = Path(labdb.image_dir(db, 'additional')) / (row['image_sha256'] + '.' + extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        imagestore.store_bytes(data, str(path), row['image_sha256'])
        conn.execute('INSERT OR IGNORE INTO image(sha256,folder,extension,width,height) VALUES(?,\'additional\',?,?,?)', (row['image_sha256'], extension, width, height))
        conn.execute('INSERT OR IGNORE INTO wine_image(wine_slug,image_type,sha256,source_name,match_method) VALUES(?,?,?,?,\'production-reviewed\')', (row['identity'], image_type, row['image_sha256'], source + '/' + request_id))
        destination = f'reference:{row["identity"]}/{image_type}/{row["image_sha256"]}'
    conn.execute('UPDATE production_error SET state=\'published\',destination=? WHERE source=? AND request_id=?', (destination, source, request_id))
    return {'ok': True, 'destination': destination, 'index_update_required': row['purpose'] == 'reference'}


def list_queue(conn):
    cursor = conn.execute('SELECT source,request_id FROM production_error ORDER BY imported_at DESC,source,request_id LIMIT 1000')
    records = [get(conn, *row) for row in cursor.fetchall()]
    for r in records:
        r['candidates'] = json.loads(r.pop('candidates_json'))
        r['feedback'] = json.loads(r.pop('feedback_json'))
    return records


def import_bot(db_path, bot_path, image_root):
    """Read the bot database without writing it. Import negative safe feedback only."""
    root = Path(image_root).resolve()
    bot = sqlite3.connect(Path(bot_path).resolve().as_uri() + '?mode=ro', uri=True)
    bot.row_factory = sqlite3.Row
    imported = 0
    skipped = 0
    try:
        with labdb.connect(db_path) as conn:
            for r in bot.execute('SELECT request_id,image_sha256,storage_path,feedback_match,feedback_selected_slug,feedback_selected_rank,feedback_at,quality_issues FROM requests WHERE feedback_match=0 AND moderation_safe=1 AND storage_path IS NOT NULL'):
                path = (root / r['storage_path']).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    skipped += 1
                    continue
                candidates = [dict(c) for c in bot.execute('SELECT rank,slug,score FROM request_candidates WHERE request_id=? ORDER BY rank', (r['request_id'],))]
                evidence = dict(source='telegram', request_id=r['request_id'], image_sha256=r['image_sha256'], candidates=candidates,
                    feedback=dict(match=False, selected_slug=r['feedback_selected_slug'], selected_rank=r['feedback_selected_rank'], at=r['feedback_at'], quality_issues=r['quality_issues']))
                capture(conn, evidence, path.read_bytes())
                imported += 1
    finally:
        bot.close()
    return {'imported': imported, 'skipped_missing_or_outside_root': skipped}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--bot-db', required=True)
    parser.add_argument('--image-root', required=True)
    args = parser.parse_args()
    print(json.dumps(import_bot(args.db, args.bot_db, args.image_root)))
