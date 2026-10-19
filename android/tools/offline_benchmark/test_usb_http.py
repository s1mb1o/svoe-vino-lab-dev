"""Inject the exact invalid status prefix without an Android device."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch

from usb_http import UsbHttp


PREFIX=b'\x17\x03\x03\x00\x13'+bytes(range(19))


class UsbHttpTest(unittest.TestCase):
    def server(self,faults=(),status=200):
        state=dict(faults=list(faults),posts=[],connections=[],guards=[])
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                payload=b'{"pid":42,"active":false}'
                self.send_response(200);self.send_header('Content-Length',str(len(payload)))
                self.end_headers();self.wfile.write(payload)
            def do_POST(self):
                state['posts'].append(self.rfile.read(int(self.headers['Content-Length'])))
                state['connections'].append(self.headers.get('Connection'))
                fault=state['faults'].pop(0) if state['faults'] else None
                payload=b'{"slug":"wine","pid":42}'
                if fault=='prefix':self.wfile.write(PREFIX)
                self.send_response(status);self.send_header('Content-Length',str(len(payload)))
                self.end_headers()
                if fault=='truncated':payload=payload[:-3]
                if fault=='json':payload=b'x'*len(payload)
                try:self.wfile.write(payload)
                except (BrokenPipeError,ConnectionResetError):pass
                self.close_connection=True
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join()))
        return UsbHttp(server.server_port),state

    def test_binary_prefix_is_rejected_and_retried_on_fresh_socket(self):
        transport,state=self.server(['prefix']);events=[]
        result=transport.post('/v1/match',b'original-image',{},state['guards'].append,events.append)
        self.assertEqual(result,(200,dict(slug='wine',pid=42),2))
        self.assertEqual(state['posts'],[b'original-image']*2)
        self.assertEqual(state['guards'],[False,True])
        self.assertEqual(state['connections'],['close','close'])
        self.assertIn('BadStatusLine',events[0]['transport_error'])
        self.assertEqual(events[1]['attempt'],2)

    def test_retries_are_bounded(self):
        transport,state=self.server(['prefix']*3);events=[]
        with self.assertRaises(http.client.BadStatusLine):
            transport.post('/v1/match',b'image',{},lambda retry:None,events.append)
        self.assertEqual(len(state['posts']),3);self.assertEqual(len(events),3)

    def test_truncated_body_retries(self):
        transport,state=self.server(['truncated'])
        self.assertEqual(transport.post('/v1/match',b'image',{},lambda retry:None)[2],2)
        self.assertEqual(len(state['posts']),2)

    def test_changed_process_prevents_second_post(self):
        transport,state=self.server(['prefix'])
        def guard(retry):
            if retry:raise RuntimeError('Application process changed')
        with self.assertRaisesRegex(RuntimeError,'process changed'):
            transport.post('/v1/match',b'image',{},guard)
        self.assertEqual(len(state['posts']),1)

    def test_model_error_is_not_retried(self):
        transport,state=self.server(status=500)
        self.assertEqual(transport.post('/v1/match',b'image',{},lambda retry:None)[0],500)
        self.assertEqual(len(state['posts']),1)

    def test_invalid_json_is_not_hidden(self):
        transport,state=self.server(['json'])
        with self.assertRaises(json.JSONDecodeError):
            transport.post('/v1/match',b'image',{},lambda retry:None)
        self.assertEqual(len(state['posts']),1)

    def test_health_ignores_proxy_environment_and_urllib_openers(self):
        transport,_=self.server()
        with patch.dict(os.environ,{'http_proxy':'http://invalid.invalid:1',
                                    'HTTP_PROXY':'http://invalid.invalid:1'}), \
             patch('urllib.request.urlopen',side_effect=AssertionError('Do not use urllib')):
            self.assertEqual(transport.health()['pid'],42)


if __name__=='__main__':unittest.main()
