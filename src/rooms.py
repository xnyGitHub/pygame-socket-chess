"""Server rooms and room module"""
import socket
import json
from src.game import GameEngine
from src.utils import Singleton


@Singleton
class Room:
    """
    Room class, this object holds an array of rooms objects
    and acts as a bridge allowing the user to join these rooms
    """

    def __init__(self):
        self.game_rooms = {}

    def create_room(self, room_name):
        """Creates a room"""
        if room_name in self.game_rooms:
            raise RoomNameAlreadyTaken()
        self.game_rooms[room_name] = Rooms(room_name)

    def join(self, room_name):
        """Join a room as a player"""
        if room_name not in self.game_rooms:
            raise RoomNotFound()

        if self.game_rooms[room_name].is_full():
            raise RoomFull()

        return self.game_rooms[room_name]

    def spectate(self, room_name):
        """Join as a spectator"""
        if room_name not in self.game_rooms:
            raise RoomNotFound()

        return self.game_rooms[room_name]

    def get_all_rooms(self):
        """Get a list of all the rooms created"""
        if not self.game_rooms:
            return "No Room created"
        return list(self.game_rooms.keys())

    def del_room(self, room_id):
        """Delete a room"""
        del self.game_rooms[room_id]


# ---------------------------------------------


class Rooms:
    """
    The actual room where the clients can player.
    This rooms holds the GameEngine object and services the data sent by the user
    """

    max_spectators: int = 2

    def __init__(self, room_name: str, max_spectator: int = None):
        self.room_name: str = room_name
        self.clients: dict = {"white": None, "black": None}
        self.game = None
        self.players: list = []
        self.spectators: list = []
        self.player_turn: str = "white"

        if max_spectator is not None:
            self.max_spectators = max_spectator

    def join(self, player_address: socket.socket):
        """Join the room"""
        if self.is_full():
            raise RoomFull()
        self.players.append(player_address)

        message = ""
        if self.clients.get("white") is None:
            self.clients["white"] = player_address
            message = json.dumps({"action": "id", "payload": "white"})
        else:
            self.clients["black"] = player_address
            message = json.dumps({"action": "id", "payload": "black"})

        player_address.send((message + "\0").encode())

        if self.is_full():
            self.game = GameEngine()
            for address in self.clients.values():
                message = json.dumps({"action": "game", "sub_action": "start"})
                address.send((message + "\0").encode())
            self.send_players_gamestate()

    def send_players_gamestate(self):
        """Send the players the new gamestate when a move is made"""
        message = {
            "action": "game",
            "sub_action": "update",
            "payload": {"board": self.game.get_board().tolist(), "moves": "", "move_log": self.game.get_move_log()},
        }

        for color, player in self.clients.items():
            if color == "black":
                message["payload"]["moves"] = self.game.get_black_moves()
            if color == "white":
                message["payload"]["moves"] = self.game.get_white_moves()

            dumped = json.dumps(message)
            player.send((dumped + "\0").encode())

    def spectate(self, player_address):
        """Add a spectator to the spectator array"""
        self.spectators.append(player_address)

    def leave(self, player_address):
        """Remove a player from a room"""
        if player_address in self.players:
            self.players.remove(player_address)

        if player_address in self.spectators:
            self.spectators.remove(player_address)

    def service_data(self, data: dict):
        """Service the data sent by the players"""
        if data["sub_action"] == "make_move":
            color = data["payload"]["color"]
            move = data["payload"]["move"]
            if color == self.player_turn:
                self.game.make_move(move)
                self.switch_turns()
            else:
                player_address = self.clients.get(color)
                message = json.dumps({"action": "message", "payload": "'It's not your turn"})
                player_address.send((message + "\0").encode())

        if data["sub_action"] == "undo_move":
            self.game.undo_move()

        self.send_players_gamestate()

    def is_full(self):
        """Check if room is full"""
        if len(self.players) == 2:
            return True
        return False

    def switch_turns(self):
        """Switch the player turns after a move"""
        if self.player_turn == "black":
            self.player_turn = "white"
        elif self.player_turn == "white":
            self.player_turn = "black"


class RoomFull(Exception):
    """If room is full"""


class RoomNotFound(Exception):
    """If room is not found when joining"""


class RoomNameAlreadyTaken(Exception):
    """If room is already name is already taken when creating"""
