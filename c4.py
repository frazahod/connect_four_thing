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
            client_connection[0].send((MESSAGE + 'Waiting for other player...').encode('ascii')) # TODO: Not this
        else:
            logging.info('player2 found')
            pair = (pending_connections[0], client_connection)
            pending_connections.pop()
            game_thread = gameThread(pair)
            logging.info('Starting game Thread')
            game_thread.start()
            active_games.append(game_thread)
            pending_connections = []

class Player():
    #TODO handle socket closure in send and recieve
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
        try:
            self.connection[0].send((prefix + message).encode('ascii'))
        except socket.error as err:
            return err

    def queue_message(self, prefix, message):
        # logging.info('added message to queue ' + message)
        self.message_queue.append(prefix + message)

    def empty_queue(self):
        for message in self.message_queue:
            self.connection[0].send(message.encode('ascii'))
        self.message_queue = []





class gameThread(threading.Thread):
    game_lock = threading.Lock()
    def __init__(self, connections):
        threading.Thread.__init__(self)
        self.connections = connections
        self.board = [['.' for j in range(6)] for i in range(7)]
        self.player1 = Player(connections[0], '0')
        self.player2 = Player(connections[1], '@')
        self.player_map = {
            connections[0][0].fileno(): self.player1,
            connections[1][0].fileno(): self.player2
        }
        self.turn = self.player1
        self.shutting_down = False

    def run(self):
        logging.info('Thread has started')
        self.start_game()


    def start_game(self):
        #TODO ADD CONTENT LENGTH EQUIVALENT YOU LAZY BASTARD!
        self.player1.queue_message(NAME, 'username')
        self.player2.queue_message(NAME, 'username')
        inputs = [self.player1.get_connection(), self.player2.get_connection()]
        outputs = []
        while not self.shutting_down or self.player1.message_queue or self.player2.message_queue:
            readable, writable, exceptional = select.select(inputs, inputs, inputs)
            # print(self.player_map)
            for con in readable:
                player = self.player_map[con.fileno()]
                response = player.get_response()
                if response:
                    if NAME in response: #TODO don't accept other commands until Names are set
                        logging.info('got name')
                        player.set_name(response.replace(NAME, ''))
                        if self.player1.get_name() and self.player2.get_name():
                            self.player1.queue_message(MESSAGE, 'Connected with ' + self.player2.get_name())
                            self.player2.queue_message(MESSAGE, 'Connected with ' + self.player1.get_name())
                            self.send_encoded_all(BOARD, 'Turn: ' + self.turn.name + '\n' + stringy(self.board))

                    elif MOVE in response:
                        logging.info('got move')
                        if player == self.turn:
                            position = int(response.replace(MOVE, '')) #TODO check that position is valid
                            logging.info('position: ' + str(position))
                            add_to_board(self.board, position, player.get_icon())
                            if self.check_for_win(player.get_icon()):
                                player.queue_message(BOARD, "GAME OVER\nYOU WIN!")
                                self.other(player).queue_message(BOARD, "GAME OVER\n" + player.name + " WINS!\nYOU LOOSE!")
                                self.shutting_down = True
                            else:
                                self.turn = self.other(player)
                                self.send_encoded_all(BOARD, 'Turn: ' + self.turn.name + '\n' + stringy(self.board))
                        else:
                            player.send_encoded(MESSAGE, "Wait your damn turn!")
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
        x,y = start
        p,m = direction
        for i in range(0,3):
            x += p
            y += m
            try: # Oof this is so lazy I am ashamed of it already....but it works!
                if self.board[x][y] != character:
                    return False
            except:
                return False
        return True

    def check_for_win(self, character):
        dir_list = [(1,1), (1,0), (0,1), (1,-1), (0,-1)]
        for x,row in enumerate(self.board):
            for y,col in enumerate(self.board[x]):
                if self.board[x][y] == character:
                    for dir in dir_list:
                        if self.try_four_times((x,y), dir, character):
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
    for idx,item in enumerate(brow):
        if item == '.':
            brow[idx] = player
            break



def stringy(array):
    # temp = [0, 1, 2, 3, 4, 5, 6]
    # list1 = ''.join(['{:4}'.format(item) for item in temp]) + '\n\n'
    array = reversed(list(zip(*array)))
    return '\n'.join([''.join(['{:4}'.format(item) for item in row])
                              for row in array])

def print_array(array):
    array = reversed(list(zip(*array)))
    print('\n'.join([''.join(['{:4}'.format(item) for item in row])
      for row in array]))

logging.basicConfig(format='%(levelname)s:%(pathname)s:%(lineno)d %(message)s', stream=sys.stdout, level=logging.INFO)
accept_connections()


# listen()