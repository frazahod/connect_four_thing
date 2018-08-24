import socket
import pickle
import threading
import select
import logging
import sys

# board = [[0 for j in range(6)] for i in range(7)]



turn = ''

MESSAGE = 'message::'
COMMAND = 'command::'
NAME = 'name::'
MOVE = 'move::'
BOARD = 'board::'
QUIT = 'quit::'

def safe_send(socket, message):
    try:
        socket.send(message)
        return None
    except socket.error as err:
        logging.error("Socket error" + err.message)
        return

def accept_connections():
    logging.info('Starting server')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 8191))
    server_socket.listen(5)

    pending_connections = []
    active_games = []

    while True:
        client_connection = server_socket.accept()
        logging.info('Accepted connection')
        # client_connection[0].setblocking(0)
        print('received connection')
        if not pending_connections:
            logging.info('waiting for player2')
            pending_connections.append(client_connection)
            client_connection[0].send((MESSAGE + 'Waiting for other player...').encode('ascii'))
        else:
            logging.info('player2 found')
            pair = (pending_connections[0], client_connection)
            # TODO Handle the logic for this properly later
            if safe_send(pair[0][0], (MESSAGE + 'Game found!').encode('ascii')) or safe_send(pair[1][0], (MESSAGE + 'Game found!').encode('ascii')):
                pending_connections.pop()
            # pair[0][0].send((MESSAGE + 'Game found!').encode('ascii'))
            # pair[1][0].send((MESSAGE + 'Game found!').encode('ascii'))
            game_thread = gameThread(pair)
            logging.info('Starting game Thread')
            game_thread.start()
            active_games.append(game_thread)
            pending_connections = []

class Player():

    def __init__(self, connection, icon):
        logging.info('Player created')
        threading.Thread.__init__(self)
        self.connection = connection
        self.player_lock = threading.Lock()
        self.name = None
        self.icon = icon
        self.message_queue = [] # TODO Use actual queue at some point?

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_connection(self):
        return self.connection[0]

    def get_response(self):
        logging.info('recving')
        return self.connection[0].recv(2048).rstrip().decode("utf-8")

    def get_icon(self):
        return self.icon

    def send_encoded(self, prefix, message):
        logging.info('sending message')
        self.connection[0].send((prefix + message).encode('ascii'))

    def queue_message(self, message):
        self.message_queue.append(message)

    def empty_queue(self):
        for message in self.message_queue:
            self.connection[0].send(message.encode('ascii'))





class gameThread(threading.Thread):
    game_lock = threading.Lock()
    def __init__(self, connections):
        threading.Thread.__init__(self)
        self.connections = connections
        self.board = [[0 for j in range(6)] for i in range(7)]
        self.player1 = Player(connections[0], '0')
        self.player2 = Player(connections[1], '#')
        self.player_map = {
            connections[0][0].fileno(): self.player1,
            connections[1][0].fileno(): self.player2
        }
        self.turn = self.player1
        self.shutting_down = False

    def run(self):
        logging.info('Thread has started')
        self.start_game()

    # TODO This should really be using message queues in order to fully take advantage of the selector. That would be a good next step.
    # Added skeleton for this in Player class. Still need to get client working first though.
    def start_game(self):
        self.player1.send_encoded(NAME, 'username')
        self.player2.send_encoded(NAME, 'username')
        inputs = [self.player1.get_connection(), self.player2.get_connection()]
        outputs = []
        while not self.shutting_down:
            readable, writable, exceptional = select.select(inputs, outputs, [])
            print(self.player_map)
            for con in readable:
                player = self.player_map[con.fileno()]
                response = player.get_response()
                if response:
                    if NAME in response: #TODO don't accept other commands until Names are set
                        logging.info('got name')
                        player.set_name(response.replace(NAME, ''))
                        if self.player1.get_name() and self.player2.get_name():
                            try:
                                self.player2.send_encoded(MESSAGE, 'Connected with ' + self.player1.get_name())
                                self.player1.send_encoded(MESSAGE, 'Connected with ' + self.player2.get_name())
                            except socket.error as err:
                                logging.error("Socket error" + err.message)

                    elif MOVE in response:
                        logging.info('got move')
                        if player == self.turn:
                            position = int(response.replace(MOVE, '')) #TODO check that position is valid
                            add_to_board(self.board, position, player.get_icon())
                            try:
                                self.send_encoded_all(BOARD, self.board)
                            except socket.error as err:
                                logging.error("Socket error" + err.message)
                                player.send_encoded(MESSAGE, "Lost connection with other player. Ending game.")
                                self.shutting_down = True
                            self.turn = self.other(player)
                        else:
                            player.send_encoded(MESSAGE, "Wait your damn turn!")
                    elif MESSAGE in response:
                        logging.info('got message')
                        to_send = response.replace(MESSAGE, player.get_name() + ': ')
                        self.send_encoded_all(MESSAGE, to_send)
                    elif QUIT in response:
                        logging.info('got quit')
                        try:
                            self.send_encoded_all(MESSAGE, player.get_name() + ' gave up........like the pansy they are!')
                        except socket.error as err:
                            logging.error("Socket error" + err.message)
                        self.shutting_down = True
                else:
                    try:
                        player.send_encoded(MESSAGE, self.other(player).get_name() + " closed connection. Ending game.")
                    except socket.error as err:
                        logging.error("Socket error" + err.message)
                    finally:
                        self.shutting_down = True


    def send_encoded_all(self, prefix, message):
        logging.info('Sending to all')
        self.player1.send_encoded(prefix, message)
        self.player2.send_encoded(prefix, message)

    def other(self, player):
        if player.get_connection().fileno() == self.player1.get_connection().fileno():
            return self.player2
        else:
            return self.player1



def add_to_board(board, row, player):
    brow = board[row]
    for idx,item in enumerate(brow):
        if item == 0:
            brow[idx] = player
            break



def stringy(array):
    temp = [0,1,2,3,4,5,6]
    list1 = ''.join(['{:4}'.format(item) for item in temp]) + '\n\n'
    array = reversed(list(zip(*array)))
    return list1 + '\n'.join([''.join(['{:4}'.format(item) for item in row])
      for row in array])

def print_array(array):
    array = reversed(list(zip(*array)))
    print('\n'.join([''.join(['{:4}'.format(item) for item in row])
      for row in array]))

logging.basicConfig(format='%(levelname)s:%(pathname)s:%(lineno)d %(message)s', stream=sys.stdout, level=logging.DEBUG)
accept_connections()


# listen()