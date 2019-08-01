import socket
import pickle
import threading
import select
import logging
import sys

turn = ''

MESSAGE = 'message::'
COMMAND = 'command::'
NAME = 'name::'
MOVE = 'move::'
BOARD = 'board::'
QUIT = 'quit::'


def safe_send(the_socket, message):
    try:
        size = len(message)
        while size:
            sent = the_socket.send(message)
            size -= sent
            message = message[:-sent]

    except socket.error as err:
        logging.error("Socket error" + err.message)


def accept_connections():
    logging.info('Starting server')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 8191))
    server_socket.listen(5)

    active_games = []
    waiting_player = None

    while True:
        client_connection = server_socket.accept()  # type: Tuple[socket, address]
        logging.info('Accepted connection')
        print('received connection')
        if not waiting_player:
            logging.info('waiting for player2')
            waiting_player = Player(client_connection, '0')
        else:
            logging.info('player2 found')
            player2 = Player(client_connection, '@')
            pair = (waiting_player, player2)
            game_thread = GameThread(pair)
            logging.info('Starting game Thread')
            game_thread.start()
            active_games.append(game_thread)
            waiting_player = None


class Player:
    # TODO handle socket closure in send and receive
    def __init__(self, connection, icon):
        # type: (Tuple[socket, address], char) -> None
        logging.info('Player created')
        self.connection = connection
        self.player_lock = threading.Lock()
        self.name = None
        self.icon = icon
        self.message_queue = []
        self.resp_buffer = ''

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_connection(self):
        return self.connection[0]

    def get_response(self):
        logging.info('recving')
        while '\r\n' not in self.resp_buffer:
            self.resp_buffer += self.connection[0].recv(2048).decode('utf-8')
        parsed = self.resp_buffer.split('\r\n')
        response = parsed[0]
        self.resp_buffer = parsed[1]
        return response

    def get_icon(self):
        return self.icon

    def queue_message(self, prefix, message):
        self.message_queue.append(prefix + message + '\r\n')

    def empty_queue(self):
        for message in self.message_queue:
            encoded = message.encode('ascii')
            safe_send(self.connection[0], encoded)
        self.message_queue = []


class GameThread(threading.Thread):
    game_lock = threading.Lock()

    def __init__(self, player_pair):
        threading.Thread.__init__(self)
        self.player1, self.player2 = player_pair
        self.board = [['.' for _ in range(6)] for _ in range(7)]
        self.player_map = {
            self.player1.get_connection().fileno(): self.player1,
            self.player2.get_connection().fileno(): self.player2
        }
        self.turn = self.player1
        self.shutting_down = False

    def run(self):
        logging.info('Thread has started')
        self.start_game()

    def start_game(self):
        self.player1.queue_message(NAME, 'username')
        self.player2.queue_message(NAME, 'username')
        inputs = [self.player1.get_connection(), self.player2.get_connection()]
        while not self.shutting_down or self.player1.message_queue or self.player2.message_queue:
            readable, writable, exceptional = select.select(inputs, inputs, inputs)
            for con in readable:
                player = self.player_map[con.fileno()]
                response = player.get_response()
                if response:
                    if NAME in response:  # TODO don't accept other commands until Names are set
                        logging.info('got name')
                        player.set_name(response.replace(NAME, ''))
                        if self.player1.get_name() and self.player2.get_name():
                            self.player1.queue_message(MESSAGE, 'Connected with ' + self.player2.get_name())
                            self.player2.queue_message(MESSAGE, 'Connected with ' + self.player1.get_name())
                            self.send_encoded_all(BOARD, 'Turn: ' + self.turn.name + '\n' + stringy(self.board))

                    elif MOVE in response:
                        logging.info('got move')
                        if player == self.turn:
                            position = int(response.replace(MOVE, ''))  # TODO check that position is valid
                            logging.info('position: ' + str(position))
                            add_to_board(self.board, position, player.get_icon())
                            if self.check_for_win(player.get_icon()):
                                player.queue_message(BOARD, "GAME OVER\nYOU WIN!")
                                self.other(player).queue_message(BOARD, "GAME OVER\n" + player.name + "WINS!\nYOU "
                                                                                                      "LOOSE!")
                                self.shutting_down = True
                            else:
                                self.turn = self.other(player)
                                self.send_encoded_all(BOARD, 'Turn: ' + self.turn.name + '\n' + stringy(self.board))
                        else:
                            player.queue_message(MESSAGE, "Wait your damn turn!")
                    elif MESSAGE in response:
                        logging.info('got message')
                        to_send = response.replace(MESSAGE, player.get_name() + ': ')
                        self.send_encoded_all(MESSAGE, to_send)
                    elif QUIT in response:
                        logging.info('got quit')
                        self.send_encoded_all(MESSAGE, player.get_name() + ' gave up........like the pansy they are!')
                        self.shutting_down = True
                else:
                    self.other(player).queue_message(MESSAGE, player.get_name() + " closed connection. Ending game.")
                    self.shutting_down = True

            for con in writable:
                player = self.player_map[con.fileno()]
                if player.message_queue:
                    logging.info("Writing to player")
                    player.empty_queue()

            for con in exceptional:
                logging.info("Man, I wonder what actually triggers this.")
                player = self.player_map[con.fileno()]
                self.other.queue_message(MESSAGE, player.name + " has disconnected")

        self.player1.get_connection().close()
        self.player2.get_connection().close()

    def try_four_times(self, start, direction, character):
        x, y = start
        p, m = direction
        for i in range(0, 3):
            x += p
            y += m
            try:
                if self.board[x][y] != character:
                    return False
            except IndexError:  # Out of bounds, hahaha this is bad and I should feel bad.
                return False
        return True

    def check_for_win(self, character):
        dir_list = [(1, 1), (1, 0), (0, 1), (1, -1), (0, -1)]
        for x, row in enumerate(self.board):
            for y, col in enumerate(self.board[x]):
                if self.board[x][y] == character:
                    for vector in dir_list:
                        if self.try_four_times((x, y), vector, character):
                            return True
        return False

    def send_encoded_all(self, prefix, message):
        logging.info('Sending to all')
        self.player1.queue_message(prefix, message)
        self.player2.queue_message(prefix, message)

    def other(self, player):
        if player.get_connection().fileno() == self.player1.get_connection().fileno():
            return self.player2
        else:
            return self.player1


def add_to_board(board, row, player):
    brow = board[row]
    for idx, item in enumerate(brow):
        if item == '.':
            brow[idx] = player
            break


def stringy(array):
    array = reversed(list(zip(*array)))
    return '\n'.join([''.join(['{:4}'.format(item) for item in row])
                      for row in array])


def print_array(array):
    array = reversed(list(zip(*array)))
    print('\n'.join([''.join(['{:4}'.format(item) for item in row])
                     for row in array]))


logging.basicConfig(format='%(levelname)s:%(pathname)s:%(lineno)d %(message)s', stream=sys.stdout, level=logging.INFO)
accept_connections()
