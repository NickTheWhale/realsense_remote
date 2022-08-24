import eventlet
import socketio

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

@sio.event
def disconnect(sid):
    print('disconnect ', sid)
    print()

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)