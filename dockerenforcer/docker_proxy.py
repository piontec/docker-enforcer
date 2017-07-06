# Adapted from http://stackoverflow.com/a/15645169/221061
class ServerProtocol(protocol.Protocol):
    def __init__(self):
        self.buffer = None
        self.client = None

    def connectionMade(self):
        factory = protocol.ClientFactory()
        factory.protocol = ClientProtocol
        factory.server = self

        reactor.connectTCP(SERVER_ADDR, SERVER_PORT, factory)

    # Client => Proxy
    def dataReceived(self, data):
        if self.client:
            self.client.write(data)
        else:
            self.buffer = data

    # Proxy => Client
    def write(self, data):
        self.transport.write(data)


class ClientProtocol(protocol.Protocol):
    def connectionMade(self):
        self.factory.server.client = self
        self.write(self.factory.server.buffer)
        self.factory.server.buffer = ''

    # Server => Proxy
    def dataReceived(self, data):
        self.factory.server.write(data)

    # Proxy => Server
    def write(self, data):
        if data:
            self.transport.write(data)


def main():
    factory = protocol.ServerFactory()
    factory.protocol = ServerProtocol

    reactor.listenTCP(LISTEN_PORT, factory)
    reactor.run()


if __name__ == '__main__':
    main()

# https://stackoverflow.com/questions/15640640/python-twisted-man-in-the-middle-implementation/15645169#15645169
# import sys
# from twisted.internet import reactor
# from twisted.internet.protocol import ServerFactory, ClientFactory, Protocol
# from twisted.protocols import basic
# from twisted.python import log
#
# LISTEN_PORT = 2593
# SERVER_PORT = 1234
#
#
# class ServerProtocol(Protocol):
#     def connectionMade(self):
#         reactor.connectTCP('localhost', SERVER_PORT, MyClientFactory(self))
#
#     def dataReceived(self, data):
#         self.clientProtocol.transport.write(data)
#
# class ClientProtocol(Protocol):
#     def connectionMade(self):
#         # Pass ServerProtocol a ref. to ClientProtocol
#         self.serverProtocol.clientProtocol = self;
#
#     def dataReceived(self, data):
#         self.serverProtocol.transport.write(data)
#
# class MyServerFactory(ServerFactory):
#     protocol = ServerProtocol
#     def buildProtocol(self, addr):
#         # Create ServerProtocol
#         p = ServerFactory.buildProtocol(self, addr)
#         return p
#
# class MyClientFactory(ClientFactory):
#     protocol = ClientProtocol
#     def __init__(self, serverProtocol_):
#         self.serverProtocol = serverProtocol_
#
#     def buildProtocol(self, addr):
#         # Create ClientProtocol
#         p = ClientFactory.buildProtocol(self,addr)
#         # Pass ClientProtocol a ref. to ServerProtocol
#         p.serverProtocol = self.serverProtocol
#         return p
#
# def main():
#     log.startLogging(sys.stdout)
#
#     reactor.listenTCP(LISTEN_PORT, MyServerFactory())
#     reactor.run()
#
# if __name__ == '__main__':
#     main()