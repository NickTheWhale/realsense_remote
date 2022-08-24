import time
import socketio

sio = socketio.Client()

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


try:
    sio.connect('http://localhost:5000')
    # sio.wait()
    while True:
        data['time'] = f'{time.time()}'
        sio.emit('my_message', data)
        time.sleep(1)

except KeyboardInterrupt:
    sio.disconnect()

except Exception as e:
    print(e)
    sio.disconnect()