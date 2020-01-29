from warnings import filterwarnings

filterwarnings("ignore")

from random import randrange
import threading

import json

from btserver import BTServer
from bterror import BTError

from getch import getch

import alsaaudio
import audioop
from scipy.signal import lfilter
import numpy
import spl_lib as spl
import math

import asyncore
from threading import Thread
from time import sleep

CHANNEL = 1  # 1 means mono. If stereo, put 2
RATES = [16000, 44100, 48000]
RATE = RATES[2]

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

INPUT_DEVICE = "hw:1,0"
PERIOD_SIZE = 1600

is_stop = False
multiplier = 5

if __name__ == '__main__':

    inputStream = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, mode=alsaaudio.PCM_NORMAL, device=INPUT_DEVICE)
    inputStream.setchannels(CHANNEL)
    inputStream.setrate(RATE)
    inputStream.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inputStream.setperiodsize(PERIOD_SIZE)

    outputStream = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, mode=alsaaudio.PCM_NORMAL, device='default')
    outputStream.setchannels(CHANNEL)
    outputStream.setrate(RATE)
    outputStream.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    outputStream.setperiodsize(PERIOD_SIZE)


    def received_callback(raw):
        global multiplier
        data = raw.split("\0")[0].strip()
        print(data)
        json_data = json.loads(data)
        if json_data["type"] == "amp":
            multiplier = float(json_data["value"])

    uuid = "6d3eb5f4-7b38-4b3f-a41b-cb47141628f4"
    service_name = "Smart Hearing Aid Server"
    server = BTServer(uuid, service_name, received_callback=received_callback)
    server_thread = Thread(target=asyncore.loop, name="Smart Hearing Aid Server Thread")
    server_thread.daemon = True
    server_thread.start()


    def exit_key():
        global is_stop
        while getch() != 'q':
            continue
        is_stop = True


    exit_key_thread = threading.Thread(target=exit_key)
    exit_key_thread.start()
    print("Press 'q' to stop server")

    block = bytes()
    length = 0

    def amplify():
        global is_stop, multiplier, block, length
        while not is_stop:
            try:
                l, data = inputStream.read()
                amplified = audioop.mul(data, CHANNEL, multiplier)
                outputStream.write(amplified)  # play back audio stream
                block = data
                length = l
            except OSError:
                pass
            except Exception as e:
                print(e)


    amplify_thread = threading.Thread(target=amplify)
    amplify_thread.start()


    def calculate():
        global is_stop
        while not is_stop:
            for client_handler in server.active_client_handlers.copy():
                # Use a copy() to get the copy of the set, avoiding 'set change size during iteration' error
                try:
                    ## Int16 is a numpy data type which is Integer (-32768 to 32767)
                    ## If you put Int8 or Int32, the result numbers will be ridiculous
                    decoded_block = numpy.frombuffer(block, dtype='Int16')
                    ## This is where you apply A-weighted filter
                    y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
                    db = 50 + (20 * numpy.log10(spl.rms_flat(y)))
					
                    msg = json.dumps({ "type": "db", "value": db})
                    client_handler.send(msg.encode())

                except OSError:
                    pass
                except Exception as e:
                    BTError.print_error(handler=client_handler, error=BTError.ERR_WRITE, error_message=repr(e))
                    client_handler.handle_close()
            sleep(0.1)


    calculate_thread = threading.Thread(target=calculate)
    calculate_thread.start()

    while True:
        if is_stop:
            server.handle_close()
            inputStream.close()
            outputStream.close()
            print("Stopping audio service")
            exit(0)
