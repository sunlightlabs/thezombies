SOCKET_NAMESPACE = '/com'

@socketio.on('connect', namespace=SOCKET_NAMESPACE)
def test_connect():
    send('Connection established with server')

@socketio.on('message', namespace=SOCKET_NAMESPACE)
def handle_message(message):
    print('received message: ' + repr(message))
    send('Message received')
