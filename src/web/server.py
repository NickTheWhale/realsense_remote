from bottle import route, run


@route('/')
def home():
    return 'home'


@route('/video')
def video():
    return 'video'


run(host='localhost', port=8000, debug=True)
