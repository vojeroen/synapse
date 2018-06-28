# Copyright 2014-2016 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

from OpenSSL import SSL, crypto
from twisted.internet._idna import _idnaBytes
from twisted.internet.ssl import ContextFactory, CertificateOptions
from twisted.internet._sslverify import _defaultCurveName, _tolerateErrors
from twisted.internet.interfaces import IOpenSSLClientConnectionCreator
from zope.interface import implementer

logger = logging.getLogger(__name__)


class ServerContextFactory(ContextFactory):
    """Factory for PyOpenSSL SSL contexts that are used to handle incoming
    connections and to make connections to remote servers."""

    def __init__(self, config):
        self._context = SSL.Context(SSL.SSLv23_METHOD)
        self.configure_context(self._context, config)

    @staticmethod
    def configure_context(context, config):
        try:
            _ecCurve = crypto.get_elliptic_curve(_defaultCurveName)
            context.set_tmp_ecdh(_ecCurve)

        except Exception:
            logger.exception("Failed to enable elliptic curve for TLS")
        context.set_options(SSL.OP_NO_SSLv2 | SSL.OP_NO_SSLv3)
        context.use_certificate_chain_file(config.tls_certificate_file)

        if not config.no_tls:
            context.use_privatekey(config.tls_private_key)

        context.load_tmp_dh(config.tls_dh_params_path)
        context.set_cipher_list("!ADH:HIGH+kEDH:!AECDH:HIGH+kEECDH")

    def getContext(self):
        return self._context


@implementer(IOpenSSLClientConnectionCreator)
class ClientTLSOptions(object):
    """
    Client creator for TLS without certificate identity verification. This is a
    copy of twisted.internet._sslverify.ClientTLSOptions with the identity
    verification left out. For documentation, see the twisted documentation.
    """

    def __init__(self, hostname, ctx):
        self._ctx = ctx
        self._hostname = hostname
        self._hostnameBytes = _idnaBytes(hostname)
        ctx.set_info_callback(
            _tolerateErrors(self._identityVerifyingInfoCallback)
        )

    def clientConnectionForTLS(self, tlsProtocol):
        context = self._ctx
        connection = SSL.Connection(context, None)
        connection.set_app_data(tlsProtocol)
        return connection

    def _identityVerifyingInfoCallback(self, connection, where, ret):
        if where & SSL.SSL_CB_HANDSHAKE_START:
            connection.set_tlsext_host_name(self._hostnameBytes)


class ClientTLSOptionsFactory(object):
    """Factory for Twisted ClientTLSOptions that are used to make connections
    to remote servers for federation."""

    def __init__(self, config):
        # We don't use config options yet
        pass

    def get_options(self, host):
        return ClientTLSOptions(
            unicode(host),
            CertificateOptions(verify=False).getContext()
        )
