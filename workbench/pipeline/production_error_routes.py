"""Local reviewed-error queue. JSON import accepts one safe image per request."""
import base64
import binascii
import json
import urllib.parse
from contextlib import closing

import lab_pages
import production_errors as errors
import testsets

JSON = 'application/json; charset=utf-8'


def handles(route):
    return route == '/production-errors' or route.startswith('/api/production-errors')


def respond(server, method, path, read_body, open_database):
    route = urllib.parse.urlsplit(path).path
    if route == '/production-errors' and method == 'GET':
        return 200, lab_pages.page('production-errors.html'), 'text/html; charset=utf-8', 'no-store'
    try:
        with closing(open_database(server.db_path, write=method != 'GET')) as conn, conn:
            if method != 'GET':
                conn.execute('PRAGMA foreign_keys=ON')
                conn.execute('BEGIN IMMEDIATE')
            if route == '/api/production-errors' and method == 'GET':
                body = {'records': errors.list_queue(conn)}
            elif route == '/api/production-errors/image' and method == 'GET':
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                row = errors.get(conn, q.get('source', [''])[0], q.get('request_id', [''])[0])
                return 200, errors.image_path(conn, row['image_sha256'], row['extension']).read_bytes(), 'image/' + ('jpeg' if row['extension'] == 'jpg' else row['extension']), 'no-store'
            elif method == 'POST' and route in ('/api/production-errors/import', '/api/production-errors/review', '/api/production-errors/publish'):
                raw = read_body(14 * 1024 * 1024 if route.endswith('/import') else 8192)
                body = json.loads(raw) if raw else None
                if not isinstance(body, dict):
                    raise errors.ReviewError('request MUST be a JSON object')
                if route.endswith('/import'):
                    data = base64.b64decode(body.pop('image_base64', ''), validate=True)
                    body = errors.capture(conn, body, data)
                elif route.endswith('/review'):
                    if 'identity' not in body and not body.get('reject'):
                        raise errors.ReviewError('identity MUST be explicit; null needs an operator no-match review')
                    body = errors.review(conn, body.get('source'), body.get('request_id'), body.get('identity'), body.get('purpose'), body.get('reviewer'), body.get('note'), body.get('reject') is True)
                else:
                    body = errors.publish(conn, body.get('source'), body.get('request_id'), body.get('set', 'production-reviewed'), body.get('image_type', 'full_front'))
            else:
                return 405, {'error': 'unsupported queue route or method'}, JSON, 'no-store'
        return 200, body, JSON, 'no-store'
    except (errors.ReviewError, testsets.TestsetError, ValueError, binascii.Error) as exc:
        return 400, {'error': str(exc)}, JSON, 'no-store'
    except OSError as exc:
        return 409, {'error': str(exc)}, JSON, 'no-store'
