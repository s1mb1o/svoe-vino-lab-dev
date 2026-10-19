"""Strict, proxy-free JSON transport over the owner's ADB loopback forward."""
import http.client
import json
import time


TRANSPORT_ERRORS=(http.client.HTTPException,OSError)


class UsbHttp:
    def __init__(self,port=18088):
        self.port=port

    def request(self,method,path,body=None,headers=None,timeout=15):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Require an origin-relative USB HTTP path')
        # A new plain HTTP socket has no urllib opener, TLS session, proxy, or pool.
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=timeout)
        try:
            connection.request(method,path,body=body,headers={
                'Connection':'close','Accept':'application/json','Accept-Encoding':'identity',
                **(headers or {})})
            response=connection.getresponse()
            length=response.getheader('Content-Length')
            if length is None or not length.isdecimal() or int(length)>8*1024*1024:
                raise ValueError('Invalid USB JSON response length')
            payload=response.read()
            if len(payload)!=int(length):
                raise http.client.IncompleteRead(payload,int(length)-len(payload))
            result=json.loads(payload)
            if not isinstance(result,dict):raise ValueError('Require a JSON response object')
            return response.status,result
        finally:
            connection.close()

    def health(self,record=lambda event:None):
        for attempt in range(1,4):
            try:
                status,body=self.request('GET','/healthz')
                if status!=200:raise ValueError(f'USB health returned HTTP {status}')
                return body
            except TRANSPORT_ERRORS as error:
                record(dict(kind='health',attempt=attempt,transport_error=repr(error)))
                if attempt==3:raise

    def post(self,path,body,headers,guard,record=lambda event:None):
        for attempt in range(1,4):
            guard(attempt>1)
            before=time.monotonic()
            try:
                status,result=self.request('POST',path,body,headers,timeout=600)
            except TRANSPORT_ERRORS as error:
                record(dict(kind='post',attempt=attempt,elapsed_ms=(time.monotonic()-before)*1000,
                    transport_error=repr(error)))
                if attempt==3:raise
            else:
                record(dict(kind='post',attempt=attempt,status=status,
                    elapsed_ms=(time.monotonic()-before)*1000))
                # Model errors are results. Do not turn them into transport retries.
                return status,result,attempt
