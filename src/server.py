import threading
import time
import socketio
import eventlet
from vidgear.gears import VideoGear
from vidgear.gears import NetGear
import numpy as np
import cv2
import opcua
from opcua import Node, ua
import logging as log


OPC_IP = 'opc.tcp://localhost:4840'
VIDEO_IP = '172.16.0.36'
VIDEO_PORT = 44444
CONTROLS_PORT = 44443

ROI_DEPTH_NODE = 'ns=2;i=2'
ROI_INVALID_NODE = 'ns=2;i=3'
ROI_DEVIATION_NODE = 'ns=2;i=4'
ROI_SELECT_NODE = 'ns=2;i=5'
STATUS_NODE = 'ns=2;i=6'
ALIVE_NODE = 'ns=2;i=8'


global running
running = True
global flip
flip = False
global text
text = ''

# `````````````````````````CONTROLS`````````````````````````


def start_controls_server():

    sio = socketio.Server()
    app = socketio.WSGIApp(sio)

    @sio.event
    def connect(sid, environ):
        global running
        running = True
        print('connect')

    @sio.event
    def command(sid, command: str):
        print('message ', command)
        global running
        global flip
        global text
        if command == 'stop':
            running = False
        elif command == 'start':
            running = True
        elif command == 'flip':
            print('GOT FLIP')
            flip = not flip
            print(flip)
        elif command.startswith('text'):
            text = command[4:]
        elif command.startswith('depth'):
            try:
                global opc_client
                opc_client.write_node(opc_client.get_node(ROI_DEPTH_NODE), int(command[5:]), ua.VariantType.Float)
            except Exception as e:
                print('failed to write node:', e)

    @sio.event
    def disconnect(sid):
        global running
        running = False
        print('disconnect')

    eventlet.wsgi.server(eventlet.listen((VIDEO_IP, CONTROLS_PORT)), app)


# ``````````````````````````VIDEO`````````````````````````
# create camera stream
stream = VideoGear(source=0).start()

# create server
video_options = {'address': VIDEO_IP,
                 'port': VIDEO_PORT,
                 'protocol': 'tcp',
                 'pattern': 2,
                 'logging': True,
                 'jpeg_compression': True,
                 'jpeg_compression_quality': 100}

video_server = NetGear(**video_options)


def send_video():
    global running
    while True:
        if running:
            frame: np.ndarray = stream.read()

            if frame is not None:
                global flip
                global text
                if flip:
                    frame = cv2.flip(frame, int(flip))
                frame = cv2.resize(frame, (960, 540))
                frame = frame[14:491, 122:838]
                if text != '':
                    cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                1, (255, 255, 255), 1, cv2.LINE_AA, False)
                video_server.send(frame)

        else:
            time.sleep(0.1)


# ````````````````````````OPC`````````````````````````
def setup():
    log.getLogger().setLevel(log.DEBUG)
    log.getLogger(opcua.__name__).setLevel(log.WARNING)
    opc_client = opcua.Client(OPC_IP)
    opc_client.connect()
    return opc_client


class OpcClient:
    def __init__(self, client: opcua.Client):
        self._client = client

        self._nodes = self.get_nodes()
        self._running = True

    def run(self) -> None:
        """main loop"""
        log.info('Running')
        try:
            while self._running:
                self.read_nodes()
                self.write_node(self._nodes['alive'], True, ua.VariantType.Boolean)
                time.sleep(1)
        except Exception as e:
            log.error(e)

    def write_node(self, node: Node, value, type: ua.VariantType) -> bool:
        """write value to node

        :param node: node
        :type node: Node
        :param value: write value
        :type value: any
        :param type: value type to convert value to
        :type type: ua.VariantType
        """
        try:
            dv = ua.DataValue(ua.Variant(value, type))
            node.set_value(dv)
        except (ua.UaError, TimeoutError) as e:
            log.error(f'Failed to set "{node.get_browse_name()}" to "{value}": {e}')
            return False
        return True

    def read_node(self, node: Node) -> None:
        """get node value"""
        try:
            return node.get_value()
        except ua.UaError as e:
            log.error(f'Failed to get "{node.get_browse_name()}": {e}')

    def read_nodes(self) -> None:
        """log node values"""
        longest = max([len(x) for x in self._nodes])

        for node in self._nodes:
            val = self.read_node(self._nodes[node])
            current = len(node)
            spaces = ' ' * (longest - current)
            log.info(f'"{node}":{spaces} {val}')
        print()

    def get_nodes(self) -> None:
        """retrieve nodes from opc server"""
        try:
            self._nodes = {
                'roi_depth': self.get_node(ROI_DEPTH_NODE),
                'roi_invalid': self.get_node(ROI_INVALID_NODE),
                'roi_deviation': self.get_node(ROI_DEVIATION_NODE),
                'roi_select': self.get_node(ROI_SELECT_NODE),
                'status': self.get_node(STATUS_NODE),
                'alive': self.get_node(ALIVE_NODE)
            }
        except Exception as e:
            log.error(f'Failed to retrieve nodes from server: {e}', False)
            self.stop()
        else:
            return self._nodes

    def get_node(self, nodeid: str) -> Node:
        """retrieve node from opc server"""
        return self._client.get_node(nodeid)

    def close(self) -> None:
        """disconnect client and exit"""
        try:
            self._client.disconnect()
        except RuntimeError:
            pass


try:
    controls_thread = threading.Thread(target=start_controls_server)
    controls_thread.daemon = True
    controls_thread.start()

    video_thread = threading.Thread(target=send_video)
    video_thread.daemon = True
    video_thread.start()

    try:
        client = setup()
    except Exception as e:
        print(e)
        while True:
            time.sleep(1)
    else:
        global opc_client
        opc_client = OpcClient(client)
        opc_client.run()


except (KeyboardInterrupt, RuntimeError):
    pass
try:
    opc_client.close()
except:
    pass
stream.stop()
video_server.close()
