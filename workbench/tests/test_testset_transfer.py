"""Check atomic Testset moves, annotation retention, and destination conflicts."""
import concurrent.futures
import hashlib
import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import testset_transfer as TRANSFER  # noqa: E402
import test_testsets as MT  # noqa: E402
import test_testset_routes as RT  # noqa: E402
import testsets as TS  # noqa: E402


class TransferModelTest(unittest.TestCase):
    tearDown = MT.TestsetsTest.tearDown
    query = MT.TestsetsTest.query
    write = MT.TestsetsTest.write
    view = MT.TestsetsTest.view

    def setUp(self):
        MT.TestsetsTest.setUp(self)
        with sqlite3.connect(self.db) as conn:
            TS.create_set(conn, 'target')
            self.digest = TS._photo_row(conn, 'my', 'wine-a', '02_conf080.jpg')['sha256']

    def move(self, place='wine-a', file='02_conf080.jpg', target='target', digest=None):
        return self.write(TRANSFER.transfer_photo, place, file, target, digest or self.digest)

    def snapshot(self):
        with sqlite3.connect(self.db) as conn:
            return {table: conn.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                    for table in ['test_set', 'test_photo', 'test_photo_comment', 'test_variant', 'image']}

    def photo(self, set_name, place='wine-a', file='02_conf080.jpg'):
        with sqlite3.connect(self.db) as conn:
            row = TS._photo_row(conn, set_name, place, file)
            notes = TS.photo_comments(conn, set_name, place, file).get((place, file), ())
            return TS.photo_view(row, notes, TS.image_tags_of(conn, row['sha256']))

    def image_files(self):
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (self.root / 'data').rglob('*') if path.is_file()
                and path.suffix.lower() in {'.jpg', '.png', '.webp'}}

    def test_every_annotation_and_image_field_is_preserved(self):
        with sqlite3.connect(self.db) as conn:
            values = {'label':'positive', 'marked_delete':1, 'ts':'2026-10-01T12:13:14+0300',
                      'proposed':'negative', 'proposed_by':'agent', 'confidence':.97,
                      'source_url':'https://example.test/photo.jpg', 'moved_from':'old-wine',
                      'copied_from':'another-wine', 'reassign_to':'wine-b',
                      'prefilled_from':json.dumps({'run':'saved-run','rank':3}),
                      'extra':json.dumps({'custom':{'preserve':True}}),
                      'box_left':1,'box_top':2,'box_right':10,'box_bottom':15}
            conn.execute('UPDATE test_photo SET '+', '.join(key+' = ?' for key in values)
                         +' WHERE set_name = ? AND place = ? AND file_name = ?',
                         list(values.values())+['my','wine-a','02_conf080.jpg'])
            TS.add_photo_comment(conn,'my','wine-a','02_conf080.jpg','user note','user')
            TS.add_photo_comment(conn,'my','wine-a','02_conf080.jpg','script note','script')
            TS.add_photo_tag(conn,'my','wine-a','02_conf080.jpg','scene_photo')
            raw_before = conn.execute('SELECT * FROM test_photo WHERE set_name=? AND place=? AND file_name=?',
                                      ('my','wine-a','02_conf080.jpg')).fetchone()
        photo_before = self.photo('my')
        files = self.image_files()
        answer = self.move()
        self.assertEqual((answer['from_set'],answer['to_set'],answer['place']),('my','target','wine-a'))
        self.assertEqual(answer['photo'],photo_before)
        self.assertEqual(self.photo('target'),photo_before)
        self.assertEqual(self.image_files(),files)
        self.assertEqual(self.query('SELECT * FROM test_photo WHERE set_name=? AND place=? AND file_name=?',
                                    'target','wine-a','02_conf080.jpg')[0][1:],raw_before[1:])
        self.assertEqual(self.query('SELECT count(*) FROM test_photo WHERE set_name=? AND place=? AND file_name=?',
                                    'my','wine-a','02_conf080.jpg')[0][0],0)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_a_filename_collision_keeps_both_images(self):
        with sqlite3.connect(self.db) as conn:
            other = TS._photo_row(conn,'my','wine-c','01.jpg')['sha256']
            conn.execute('INSERT INTO test_photo(set_name,place,file_name,sha256,label) VALUES(?,?,?,?,?)',
                         ('target','wine-a','02_conf080.jpg',other,'negative'))
        before = self.photo('my')
        answer = self.move()
        self.assertEqual(answer['file'],'02_conf080.jpg.moved2.jpg')
        expected = dict(before,file=answer['file'])
        self.assertEqual(answer['photo'],expected)
        self.assertEqual(self.query('SELECT sha256,label FROM test_photo WHERE set_name=? AND place=? AND file_name=?',
                                    'target','wine-a','02_conf080.jpg'),[(other,'negative')])
        self.assertEqual(self.photo('target',file=answer['file']),expected)

    def test_a_collision_uses_the_first_unused_filename(self):
        with sqlite3.connect(self.db) as conn:
            other = TS._photo_row(conn,'my','wine-c','01.jpg')['sha256']
            for name in ['02_conf080.jpg','02_conf080.jpg.moved2.jpg']:
                conn.execute('INSERT INTO test_photo(set_name,place,file_name,sha256) VALUES(?,?,?,?)',
                             ('target','wine-a',name,other))
        self.assertEqual(self.move()['file'],'02_conf080.jpg.moved3.jpg')

    def test_invalid_destination_values_are_rejected(self):
        before = self.snapshot()
        for target in [None, True, [], {}, '']:
            with self.subTest(target=target), self.assertRaises(TS.TestsetError) as caught:
                self.move(target=target)
            self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_an_existing_image_assignment_does_not_merge_or_remove_entries(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('INSERT INTO test_photo(set_name,place,file_name,sha256,label) VALUES(?,?,?,?,?)',
                         ('target','wine-a','different-name.jpg',self.digest,'negative'))
        before = self.snapshot()
        with self.assertRaises(TS.TestsetError) as caught:
            self.move()
        self.assertEqual(caught.exception.code,409)
        self.assertEqual(self.snapshot(),before)

    def test_an_image_in_another_destination_wine_does_not_block_the_move(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('INSERT INTO test_photo(set_name,place,file_name,sha256) VALUES(?,?,?,?)',
                         ('target','wine-b','copy.jpg',self.digest))
        self.move()
        self.assertEqual(self.query('SELECT place FROM test_photo WHERE set_name=? ORDER BY place','target'),
                         [('wine-a',),('wine-b',)])

    def test_stale_image_identity_is_rejected_without_changes(self):
        before = self.snapshot()
        with self.assertRaises(TS.TestsetError) as caught:
            self.move(digest='f'*64)
        self.assertEqual(caught.exception.code,409)
        self.assertEqual(self.snapshot(),before)

    def test_invalid_digest_values_are_rejected(self):
        before = self.snapshot()
        for digest in [None,True,[],{},'short','A'*64]:
            with self.subTest(digest=digest), self.assertRaises(TS.TestsetError) as caught:
                self.write(TRANSFER.transfer_photo,'wine-a','02_conf080.jpg','target',digest)
            self.assertEqual(caught.exception.code,400)
        self.assertEqual(self.snapshot(),before)

    def test_unknown_or_same_sets_and_missing_photos_are_rejected(self):
        before = self.snapshot()
        for place,file,target,code in [('wine-a','02_conf080.jpg','missing',404),
                                      ('wine-a','02_conf080.jpg','my',400),
                                      ('wine-a','missing.jpg','target',404),
                                      ('','02_conf080.jpg','target',400)]:
            with self.subTest(place=place,file=file,target=target), self.assertRaises(TS.TestsetError) as caught:
                self.move(place,file,target)
            self.assertEqual(caught.exception.code,code)
        self.assertEqual(self.snapshot(),before)

    def test_no_match_keeps_its_place_and_verdict(self):
        self.write(TS.set_label,'__null__','n1.jpg','positive')
        before = self.photo('my','__null__','n1.jpg')
        answer = self.move('__null__','n1.jpg',digest=before['sha256'])
        self.assertEqual((answer['place'],answer['photo']),('__null__',before))

    def test_drawer_keeps_its_place_and_annotations(self):
        moved = self.write(TS.move_photo,'wine-a','02_conf080.jpg','__drawer__')
        name = moved['photo']['file']
        before = self.photo('my','__drawer__',name)
        answer = self.move('__drawer__',name,digest=before['sha256'])
        self.assertEqual((answer['place'],answer['photo']),('__drawer__',before))

    def test_an_old_slug_outside_the_catalogue_is_preserved(self):
        before = self.photo('my','unknown-wine','01.jpg')
        answer = self.move('unknown-wine','01.jpg',digest=before['sha256'])
        self.assertEqual((answer['place'],answer['photo']),('unknown-wine',before))

    def test_comments_move_with_foreign_keys_disabled_too(self):
        before = self.photo('my')
        with sqlite3.connect(self.db) as conn:
            conn.execute('PRAGMA foreign_keys=OFF')
            TRANSFER.transfer_photo(conn,'my','wine-a','02_conf080.jpg','target',self.digest)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(self.photo('target'),before)

    def test_a_transaction_failure_rolls_back_both_entries_and_comments(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TRIGGER reject_transfer AFTER UPDATE OF set_name ON test_photo "
                         "WHEN NEW.set_name='target' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        before = self.snapshot()
        with self.assertRaises(sqlite3.IntegrityError):
            self.move()
        self.assertEqual(self.snapshot(),before)

    def test_both_set_timestamps_change_but_photo_timestamp_is_preserved(self):
        before = self.photo('my')['entry']['ts']
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE test_set SET edited_at='old'")
        self.move()
        values = self.query('SELECT edited_at FROM test_set ORDER BY set_name')
        self.assertEqual(len(set(values)),1)
        self.assertNotEqual(values[0][0],'old')
        self.assertEqual(self.photo('target')['entry']['ts'],before)

    def test_set_level_variant_groups_are_not_changed(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('INSERT INTO test_variant(set_name,wine_slug,group_no) VALUES(?,?,?)',
                         ('target','wine-a',7))
        before = self.query('SELECT * FROM test_variant ORDER BY set_name,wine_slug')
        self.move()
        self.assertEqual(self.query('SELECT * FROM test_variant ORDER BY set_name,wine_slug'),before)

    def test_a_round_trip_keeps_the_photo_annotations(self):
        before = self.photo('my')
        moved = self.move()
        with sqlite3.connect(self.db) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            answer = TRANSFER.transfer_photo(conn,'target','wine-a',moved['file'],'my',self.digest)
        self.assertEqual(answer['photo'],before)
        self.assertEqual(self.photo('my'),before)


class TransferRoutesTest(unittest.TestCase):
    tearDown = RT.TestsetRoutesTest.tearDown
    request = RT.TestsetRoutesTest.request
    post = RT.TestsetRoutesTest.post
    get_view = RT.TestsetRoutesTest.get_view

    def setUp(self):
        RT.TestsetRoutesTest.setUp(self)
        self.post('/api/testset-new',name='target')
        source = next(row for row in self.get_view()['rows'] if row['slug']=='wine-a')['photos'][0]
        self.digest = source['sha256']

    def move(self, **values):
        return self.post('/api/testset-transfer',**dict({'place':'wine-a','file':'01.jpg',
                         'to_set':'target','sha256':self.digest},**values))

    def test_route_moves_the_entry_and_refreshes_both_views(self):
        source = next(row for row in self.get_view()['rows'] if row['slug']=='wine-a')['photos'][0]
        self.request('/api/testset?set=target')
        status,answer = self.move()
        self.assertEqual(status,200,answer)
        self.assertEqual((answer['set'],answer['from_set'],answer['place']),('target','my','wine-a'))
        self.assertEqual(answer['photo'],source)
        self.assertEqual(answer['source_counts']['photos'],2)
        self.assertEqual(answer['counts']['photos'],1)
        self.assertEqual({row['name']:row['photos'] for row in answer['sets']},{'my':2,'target':1})
        current = next(row for row in self.get_view()['rows'] if row['slug']=='wine-a')['photos']
        self.assertEqual(current,[])
        status,text = self.request('/api/testset?set=target')
        self.assertEqual(status,200)
        target = next(row for row in json.loads(text)['rows'] if row['slug']=='wine-a')['photos']
        self.assertEqual(target,[source])

    def test_route_rejects_stale_requests_and_keeps_the_source(self):
        before = self.get_view()
        status,answer = self.move(sha256='f'*64)
        self.assertEqual(status,409,answer)
        self.assertEqual(self.get_view(),before)

    def test_route_methods_and_missing_values_are_checked(self):
        self.assertEqual(self.request('/api/testset-transfer')[0],405)
        self.assertEqual(self.request('/api/testset-transfer','PUT',b'{}')[0],405)
        self.assertEqual(self.move(sha256=None)[0],400)
        self.assertEqual(self.move(to_set='missing')[0],404)
        self.assertEqual(self.move(to_set='my')[0],400)

    def test_concurrent_requests_cannot_move_the_same_entry_twice(self):
        self.post('/api/testset-new',name='other')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda name:self.move(to_set=name),['target','other']))
        self.assertEqual(sorted(status for status,_ in answers),[200,404])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM test_photo WHERE place=? AND sha256=?',
                                          ('wine-a',self.digest)).fetchone()[0],1)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_the_page_has_the_testset_submenu(self):
        status,page = self.request('/testset')
        self.assertEqual(status,200)
        self.assertIn('Move To testset &gt;',page)
        self.assertIn('id="ctx-testsets"',page)
        self.assertIn('/api/testset-transfer',page)
        self.assertIn('data-to-testset=',page)


if __name__ == '__main__':
    unittest.main()
