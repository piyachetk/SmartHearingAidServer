import threading
import keyboard

from btserver import BTServer
from bterror import BTError

import pyaudio
import audioop
from scipy.signal import lfilter
import numpy
import spl_lib as spl

import asyncore
from threading import Thread
from time import sleep

''' The following is similar to a basic CD quality
   When CHUNK size is 4096 it routinely throws an IOError.
   When it is set to 8192 it doesn't.
   IOError happens due to the small CHUNK size
   What is CHUNK? Let's say CHUNK = 4096
   math.pow(2, 12) => RATE / CHUNK = 100ms = 0.1 sec
'''
CHUNKS = [4096, 9600]  # Use what you need
CHUNK = CHUNKS[0]
FORMAT = pyaudio.paInt16  # 16 bit
CHANNEL = 1  # 1 means mono. If stereo, put 2

'''
Different mics have different rates.
For example, Logitech HD 720p has rate 48000Hz
'''
RATES = [44300, 48000]
RATE = RATES[1]

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

is_stop = False
multiplier = 2

if __name__ == '__main__':

    '''
    Listen to mic
    '''
    pa = pyaudio.PyAudio()

    stream = pa.open(format=FORMAT,
                     channels=CHANNEL,
                     rate=RATE,
                     input=True,
                     output=True,
                     frames_per_buffer=CHUNK)

    def received_callback(raw):
        global multiplier
        data = raw.strip()
        print(data)
        if data.isnumeric():
            multiplier = float(data)

    # Create a BT server
    uuid = "6d3eb5f4-7b38-4b3f-a41b-cb47141628f4"
    service_name = "Smart Hearing Aid Server"
    server = BTServer(uuid, service_name, received_callback=received_callback)

    # Create the server thread and run it
    server_thread = Thread(target=asyncore.loop, name="Smart Hearing Aid Server Thread")
    server_thread.daemon = True
    server_thread.start()

    def exit_key():
        global is_stop
        keyboard.wait('esc')
        is_stop = True

    exit_key_thread = threading.Thread(target=exit_key)
    exit_key_thread.start()

    def amplify():
        global is_stop, multiplier
        while not is_stop:
            # Amplify and play
            read = stream.read(CHUNK)
            amplified = audioop.mul(read, 1, multiplier)
            stream.write(amplified, CHUNK)  # play back audio stream

    amplify_thread = threading.Thread(target=amplify)
    amplify_thread.start()

    while True:
        for client_handler in server.active_client_handlers.copy():
            if is_stop:
                client_handler.handle_close()
                break

            # Use a copy() to get the copy of the set, avoiding 'set change size during iteration' error

            block = stream.read(CHUNK)

            ## Int16 is a numpy data type which is Integer (-32768 to 32767)
            ## If you put Int8 or Int32, the result numbers will be ridiculous
            decoded_block = numpy.fromstring(block, 'Int16')
            ## This is where you apply A-weighted filter
            y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
            new_decibel = 20 * numpy.log10(spl.rms_flat(y)) + 30

            msg = str(new_decibel) + " dBA"
            # print(msg)

            try:
                client_handler.send(msg.encode())
            except Exception as e:
                BTError.print_error(handler=client_handler, error=BTError.ERR_WRITE, error_message=repr(e))
                client_handler.handle_close()

        if is_stop:
            server.handle_close()
            stream.stop_stream()
            stream.close()
            pa.terminate()
            print("Stopping audio service")
            exit(0)

        # Sleep for 0.1 seconds
        sleep(0.1)
