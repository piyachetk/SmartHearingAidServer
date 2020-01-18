import asyncore
import logging
from bluetooth import *
from bthandler import BTClientHandler

logger = logging.getLogger(__name__)


class BTServer(asyncore.dispatcher):
    """Asynchronous Bluetooth Server"""

    data = ""

    def __init__(self, uuid, service_name, port=PORT_ANY, received_callback = None):
        asyncore.dispatcher.__init__(self)

        self._cmds = {}

        if not is_valid_uuid(uuid):
            raise ValueError("uuid {} is not valid".format(uuid))

        self.uuid = uuid
        self.service_name = service_name
        self.port = port

        # Create the server-side BT socket
        self.set_socket(BluetoothSocket(RFCOMM))
        self.bind(("", self.port))
        self.listen(1)

        # Track the client-side handlers with a set
        self.active_client_handlers = set()

        advertise_service(self.socket,
                          self.service_name,
                          service_id=self.uuid,
                          service_classes=[self.uuid, SERIAL_PORT_CLASS],
                          profiles=[SERIAL_PORT_PROFILE]
                          )

        self.port = self.socket.getsockname()[1]
        logger.info("Waiting for connection on RFCOMM channel {}".format(self.port))
        print("Waiting for connection on RFCOMM channel {}".format(self.port))
        self.received_callback = received_callback

    def handle_accept(self):
        # This method is called when an incoming connection request from a client is accept.
        # Get the client-side BT socket
        pair = self.socket.accept()

        if pair is not None:
            client_sock, client_addr = pair
            client_handler = BTClientHandler(socket=client_sock, server=self)
            self.active_client_handlers.add(client_handler)

            logger.info("Accepted connection from {},".format(repr(client_addr[0])) +
                        " number of active connections is {}".format(len(self.active_client_handlers)))
            print("Accepted connection from {},".format(repr(client_addr[0])) +
                  " number of active connections is {}".format(len(self.active_client_handlers)))

    def handle_connect(self):
        # This method is called when the connection is established.
        pass

    def handle_close(self):
        print("Closing server socket")
        # This method is called right before closing the server socket only. For closing a client socket, refer to
        #  'bthandler.py'
        self.close()


if __name__ == '__main__':
    uuid = "6d3eb5f4-7b38-4b3f-a41b-cb47141628f4"
    service_name = "Smart Hearing Aid Server"

    server = BTServer(uuid, service_name)
    asyncore.loop()
