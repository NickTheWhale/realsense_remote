import threading
import time
from vidgear.gears import NetGear
import cv2
import socketio


IP_ADDRESS = '10.250.3.29'
VIDEO_PORT = 44444
CONTROLS_PORT = 44443


# create client
video_options = {'address': IP_ADDRESS,
                 'port': VIDEO_PORT,
                 'protocol': 'tcp',
                 'pattern': 2,
                 'logging': True,
                 'receive_mode': True,
                 'jpeg_compression': False,
                 'jpeg_compression_quality': 100}

video_client = NetGear(**video_options)


sio = socketio.Client()


def send_data():
    @sio.event
    def connect():
        print('connection established')

    @sio.event
    def my_message(data):
        print('message received with ', data)
        sio.emit('my response', {'response': 'my response'})

    @sio.event
    def disconnect():
        print('disconnected from server')

    data = {
        'time': f'{time.time()}',
        'weather': 'hot',
        'monitor': 'broken',
        'hungry': 'yes',
        'date': '8/24/2022'
    }
    
    sio.connect(f'http://{IP_ADDRESS}:{CONTROLS_PORT}')
    while True:
        # data['time'] = f'{time.time()}'
        data = input('?: ')
        sio.emit('my_message', data)
        # time.sleep(1)


start = time.time()
try:
    client_thread = threading.Thread(target=send_data)
    client_thread.daemon = True
    client_thread.start()

    idx = 0
    while True:
        idx += 1
        start = time.time()
        frame = video_client.recv()

        if frame is None:
            break

        cv2.imshow('video', frame)

        # delta = round((time.time() - start), 5)
        # if delta > 0 and idx > 30:
        #     idx = 0
        #     fps = 1 / delta
        #     msg = f'\rframes/second : {fps:.3f}  |  size : {frame.size}'

        #     sys.stdout.write(msg)
        #     sys.stdout.flush()

        key = cv2.waitKey(1)
        if key == ord('q'):
            break


except (KeyboardInterrupt, RuntimeError):
    pass

if sio.connected:
    sio.disconnect()

cv2.destroyAllWindows()
video_client.close()
