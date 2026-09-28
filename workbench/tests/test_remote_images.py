"""Safe server-side fetching for an image dragged from another browser page."""
import base64
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import remote_images as RI  # noqa: E402


PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]


class Response:
    def __init__(self, data, url="https://images.example/photo.webp", length=None):
        self.data = data
        self.url = url
        self.headers = {} if length is None else {"Content-Length": str(length)}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        return self.data[:size]


class Opener:
    def __init__(self, response):
        self.response = response
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request, self.timeout = request, timeout
        return self.response


class RemoteImagesTest(unittest.TestCase):
    def test_fetches_a_public_address_with_a_limit_and_source_name(self):
        opener = Opener(Response(b"picture", length=7))
        with mock.patch.object(RI.socket, "getaddrinfo", return_value=PUBLIC), \
                mock.patch.object(RI.urllib.request, "build_opener", return_value=opener):
            data, name = RI.fetch_image("https://images.example/a%20b.webp", 20)
        self.assertEqual((data, name), (b"picture", "photo.webp"))
        self.assertEqual(opener.timeout, RI.FETCH_TIMEOUT)
        self.assertIn("image/webp", opener.request.get_header("Accept"))
        self.assertEqual(opener.request.get_header("User-agent"), RI.USER_AGENT)

    def test_refuses_non_public_addresses_and_credentials(self):
        for address in ("127.0.0.1", "10.0.0.8", "169.254.1.2", "::1"):
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            answer = [(family, socket.SOCK_STREAM, 6, "", (address, 80))]
            with self.subTest(address=address), \
                    mock.patch.object(RI.socket, "getaddrinfo", return_value=answer), \
                    self.assertRaisesRegex(RI.RemoteImageError, "local host"):
                RI.check_url("http://example.test/image")
        with self.assertRaisesRegex(RI.RemoteImageError, "MUST NOT hold credentials"):
            RI.check_url("https://person:secret@example.test/image")
        with self.assertRaisesRegex(RI.RemoteImageError, "only an http or https"):
            RI.check_url("file:///etc/passwd")

    def test_checks_a_redirect_before_following_it(self):
        request = RI.urllib.request.Request("https://images.example/a")
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
        with mock.patch.object(RI.socket, "getaddrinfo", return_value=private), \
                self.assertRaisesRegex(RI.RemoteImageError, "local host"):
            RI._SafeRedirectHandler().redirect_request(
                request, None, 302, "Found", {}, "http://localhost/private")

    def test_data_images_and_size_limits(self):
        value = "data:image/png;base64," + base64.b64encode(b"png bytes").decode()
        self.assertEqual(RI.fetch_image(value, 20), (b"png bytes", "dropped-image"))
        with self.assertRaisesRegex(RI.RemoteImageError, "larger than 4 bytes"):
            RI.fetch_image(value, 4)

        opener = Opener(Response(b"12345", length=5))
        with mock.patch.object(RI.socket, "getaddrinfo", return_value=PUBLIC), \
                mock.patch.object(RI.urllib.request, "build_opener", return_value=opener), \
                self.assertRaisesRegex(RI.RemoteImageError, "larger than 4 bytes"):
            RI.fetch_image("https://images.example/photo", 4)


if __name__ == "__main__":
    unittest.main()
