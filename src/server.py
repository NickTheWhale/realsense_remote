import threading
import time
import socketio
import eventlet
from vidgear.gears import VideoGear
from vidgear.gears import NetGear


IP_ADDRESS = '10.250.3.29'
VIDEO_PORT = 44444
CONTROLS_PORT = 44443


# create camera stream
stream = VideoGear(source=0).start()

# create server
video_options = {'address': IP_ADDRESS,
                 'port': VIDEO_PORT,
                 'protocol': 'tcp',
                 'pattern': 2,
                 'logging': True,
                 'jpeg_compression': True,
                 'jpeg_compression_quality': 100}

video_server = NetGear(**video_options)

global running
running = True

def start_controls_server():
    sio = socketio.Server()
    app = socketio.WSGIApp(sio)

    @sio.event
    def connect(sid, environ):
        print('connect ', sid)
        print()

    @sio.event
    def my_message(sid, data):
        print('message ', data)
        print()
        global running
        if data == 'stop':
            running = False
        elif data == 'start':
            running = True
            

    @sio.event
    def disconnect(sid):
        print('disconnect ', sid)
        print()
        
    eventlet.wsgi.server(eventlet.listen((IP_ADDRESS, CONTROLS_PORT)), app)
    
def send_video():
    global running
    while True:
        if running:
            frame = stream.read()

            if frame is None:
                break

            video_server.send(frame)

try:
    controls_thread = threading.Thread(target=start_controls_server)
    controls_thread.daemon = True
    controls_thread.start()
    
    video_thread = threading.Thread(target=send_video)
    video_thread.daemon = True
    video_thread.start()
        
    while True:
        print('doing stuff here')
        time.sleep(1)

except (KeyboardInterrupt, RuntimeError):
    pass


stream.stop()
video_server.close()
