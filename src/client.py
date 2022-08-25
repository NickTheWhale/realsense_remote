import threading
import time
from vidgear.gears import NetGear
import dearpygui.dearpygui as dpg
import numpy as np
import socketio


IP_ADDRESS = '10.250.3.29'
VIDEO_PORT = 44444
CONTROLS_PORT = 44443


# ``````````````````````````VIDEO````````````````````````````
video_options = {'address': IP_ADDRESS,
                 'port': VIDEO_PORT,
                 'protocol': 'tcp',
                 'pattern': 2,
                 'logging': True,
                 'receive_mode': True,
                 'jpeg_compression': True,
                 'jpeg_compression_quality': 100}

video_client = NetGear(**video_options)

global frame
frame = None


def recv_video():
    global frame
    while True:
        frame = video_client.recv()


video_thread = threading.Thread(target=recv_video)
video_thread.daemon = True
video_thread.start()

# ````````````````````````CONTROLS```````````````````````
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

    sio.connect(f'http://{IP_ADDRESS}:{CONTROLS_PORT}')
    while True:
        data = input('?: ')
        sio.emit('my_message', data)


controls_thread = threading.Thread(target=send_data)
controls_thread.daemon = True
controls_thread.start()

# `````````````````````````GUI``````````````````````````

dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()


def add_texture(frame: np.ndarray):
    with dpg.texture_registry():
        data = np.flip(frame, 2)
        data = data.ravel()
        data = np.asfarray(data, dtype='f')
        texture_data = np.true_divide(data, 255.0)
        dpg.add_raw_texture(frame.shape[1],
                            frame.shape[0],
                            texture_data,
                            tag='texture_tag',
                            format=dpg.mvFormat_Float_rgb)


def update_texture(frame: np.ndarray):
    data = np.flip(frame, 2)
    data = data.ravel()
    data = np.asfarray(data, dtype='f')
    texture_data = np.true_divide(data, 255.0)
    dpg.set_value('texture_tag', texture_data)


while not isinstance(frame, np.ndarray):
    time.sleep(0.01)
add_texture(frame)

with dpg.window(label='Video'):
    dpg.add_image('texture_tag')

def chat(sender, text):
    sio.emit('my_message', text)

with dpg.window(label='Chat Box'):
    dpg.add_input_text(label='text_box', on_enter=True, callback=chat)

dpg.configure_app(docking=True, docking_space=True, init_file='dpg.ini')
dpg.show_viewport()

while dpg.is_dearpygui_running():
    if isinstance(frame, np.ndarray):
        update_texture(frame)
    dpg.render_dearpygui_frame()

if sio.connected:
    sio.disconnect()

video_client.close()
dpg.destroy_context()
