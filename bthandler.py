import asyncore
import logging
from bterror import BTError

logger = logging.getLogger(__name__)


class BTClientHandler(asyncore.dispatcher_with_send):
    """BT handler for client-side socket"""

    def __init__(self, socket, server):
        asyncore.dispatcher_with_send.__init__(self, socket)
        self.server = server
        self.data = ""

    def handle_read(self):
        try:
            self.data = self.recv(1024).decode('UTF-8')
            if self.server.received_callback:
                self.server.received_callback(self.data)
        except Exception as e:
            BTError.print_error(handler=self, error=BTError.ERR_READ, error_message=repr(e))
            self.data = ""
            self.handle_close()

    def handle_close(self):
        print("Closing client socket")

        # flush the buffer
        while self.writable():
            self.handle_write()

        self.server.active_client_handlers.remove(self)
        self.close()
