import json
import select
import socket
import threading

from src.rooms import Room, RoomFull, RoomNameAlreadyTaken, RoomNotFound, Rooms


class ThreadedClient(threading.Thread):
    """Threadclient class for each client that connects"""

    def __init__(self, client, room):
        threading.Thread.__init__(self)
        self.event: threading.Event = threading.Event()
        self.client: socket.socket = client
        self.server_room: Room = room
        self.game_room: Rooms = None

    def run(self):
        print(f"{self.client.getsockname()[0]} has connected")
        while not self.event.is_set():
            readable, _, _ = select.select([self.client], [], [], 2) # Type list, list, list
            for obj in readable:
                if obj is self.client:
                    data = self.client.recv(1024)
                    if not data:
                        self.set_event()
                        break

                    try:
                        strings = data.split(b'\0')
                        for msg in strings:
                            if msg != b'':
                                message= json.loads(msg)
                                self.service_data(message)
                    except Exception as e:
                        raise(e)
        print(f"{self.client.getsockname()[0]} has disconnected")

    def service_data(self, data: dict):

        message: dict = {}

        if data['action'] == 'create':
            payload = data['payload']
            try:
                self.server_room.create_room(payload)
                message['message']= f'{payload} created'
            except RoomNameAlreadyTaken:
                message['message'] = 'Error: Room name is already taken'

        if data['action'] == 'join':
            payload = data['payload']
            try:
                self.game_room = self.server_room.join(payload)
                self.game_room.join(self.client)
                message['message']= f'Joined {payload}'
            except RoomNotFound:
                message['message']= 'Error: Room not found'
            except RoomFull:
                message['message']= 'Error: Room is full'

        if data['action'] == 'spectate':
            payload = data['payload']
            try:
                self.game_room = self.server_room.spectate(payload)
                self.game_room.spectate(self.client)
                message['message']= f'Spectating {payload}'
            except RoomNotFound:
                message['message']= 'Error: Room not found'

        if data['action'] == 'get_rooms':
            message['message'] = self.server_room.get_all_rooms()
            print(message['message'])

        if data['action'] == 'leave_room':
            if self.game_room is None:
                message['message'] = f"You aren't in a room"
            else:
                self.game_room.leave(self.client)
                self.game_room = None
                message['message'] = f'You left the room'

        if data['action'] == 'game':
            self.game_room.service_data(data)

        self.client.send((json.dumps(message)+ '\0').encode())

    def set_event(self):
        """Stop the thread"""
        self.event.set()

