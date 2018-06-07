from io import BytesIO

import attr
from six import text_type

from mock import Mock
from synapse.api.ratelimiting import Ratelimiter
from synapse.http.site import SynapseRequest
from synapse.server import HomeServer
from synapse.util import Clock


@attr.s
class FakeChannel(object):

    result = attr.ib(factory=dict)

    def writeHeaders(self, version, code, reason, headers):
        self.result["version"] = version
        self.result["code"] = code
        self.result["reason"] = reason
        self.result["headers"] = headers

    def write(self, content):
        if "body" not in self.result:
            self.result["body"] = b""

        self.result["body"] += content

    def requestDone(self, _self):
        self.result["done"] = True

    def getPeer(self):
        return None

    def getHost(self):
        return None

    @property
    def transport(self):
        return self


class FakeSite:

    server_version_string = b"1"
    site_tag = "test"

    @property
    def access_logger(self):
        class FakeLogger:
            def info(self, *args, **kwargs):
                pass

        return FakeLogger()


def default_config():
    m = Mock()
    m.enable_registration = True
    m.password_providers = []
    m.signing_key = [b"A"]
    m.server_name = "testserver"
    return m


@attr.s
class FakeHomeserver(HomeServer):

    _reactor = attr.ib()
    hostname = attr.ib(default="localhost")
    _building = attr.ib(default=attr.Factory(dict))
    ratelimiter = attr.ib(default=attr.Factory(Ratelimiter))
    config = attr.ib(default=attr.Factory(default_config))
    version_string = b"1"
    distributor = ""
    tls_server_context_factory = None

    def get_clock(self):
        return Clock(self._reactor)

    def get_pusherpool(self):
        m = Mock()
        return m


def make_request(method, path, content=b""):

    if isinstance(content, text_type):
        content = content.encode('utf8')

    site = FakeSite()
    channel = FakeChannel()

    req = SynapseRequest(site, channel)
    req.process = lambda: b""
    req.content = BytesIO(content)
    req.requestReceived(method, path, b"1.1")

    return req, channel


def wait_until_result(clock, channel, timeout=100):
    """
    Wait until the channel has a result.
    """
    x = 0

    while not channel.result:
        x += 1
        if x > timeout:
            raise Exception("Timed out waiting for request to finish.")
        clock.advance(0.1)
