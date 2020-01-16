import bluetooth
import threading

server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
server_sock.bind(("", bluetooth.PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

uuid = "6d3eb5f4-7b38-4b3f-a41b-cb47141628f4"

bluetooth.advertise_service(server_sock, "Smart Hearing Aid", service_id = uuid,
                            service_classes = [uuid, bluetooth.SERIAL_PORT_CLASS],
                            profiles = [bluetooth.SERIAL_PORT_PROFILE],
                            # protocols=[bluetooth.OBEX_UUID]
                            )

print("Waiting for connection on RFCOMM channel", port)

client_sock, client_info = server_sock.accept()
print("Accepted connection from", client_info)


def receive():
    while True:
        try:
            output = client_sock.recv(1024)
            if not output:
                continue
            print("Received", output)
        except OSError:
            pass


thread_1 = threading.Thread(target=receive)
thread_1.start()

while True:
    try:
        data = input()

        if data == "!exit":
            client_sock.close()
            server_sock.close()
            print("Disconnected.")
            exit(0)
            break
        else:
            client_sock.send(data)

    except OSError:
        pass
