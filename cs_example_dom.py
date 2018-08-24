#!/usr/bin/env python3 
import curses
from curses import wrapper
from curses.textpad import Textbox
import socket
import threading
import subprocess


import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 8191))
socket_lock = threading.Lock()

def get_username(stdscr):
    username_win = curses.newwin(2,32, 0,0)
    username_win.addstr(0, 0, "Please enter your username:")
    username_subwin = username_win.subwin(1, 32, 1, 0)
    username_win.refresh()
    username_textbox = curses.textpad.Textbox(username_subwin)  
    username_textbox.edit()
    username = username_textbox.gather()
    del username_win
    stdscr.refresh() 
    return username 

def print_board(board_window, board_str):
    # board_window.clear()
    board_window.addstr(1, 1, board_str)
    board_window.refresh()

def print_chat(chat_pad, chat_str, chat_pad_pos):# Very naive implementation
    chat_pad.addstr(0, 0, chat_str)
    chat_pad.refresh(chat_pad_pos, 0, 1, 36, 30, 66)

# def print_debug_msg(stdscr, BOARD_HEIGHT, msg):

class recvThread(threading.Thread):
    def __init__(self,stdcr):
        threading.Thread.__init__(self)
        self.stdcr = stdcr

    def run(self):
        recv_windows(self.stdcr)

def recv_windows(stdcr):
    BOARD_WINDOW_NLINES = 32
    BOARD_WINDOW_NCOLS = 32
    board_window = curses.newwin(BOARD_WINDOW_NLINES, BOARD_WINDOW_NCOLS, 0, 0)
    board_window.border()
    board_window.refresh()

    # Literally just here to provide a border for the pad
    CHAT_WINDOW_NLINES = 32
    CHAT_WINDOW_NCOLS = 32
    chat_window = curses.newwin(CHAT_WINDOW_NLINES, CHAT_WINDOW_NCOLS, 0, 35)
    chat_window.border()
    chat_window.refresh()

    chat_string = ''
    chat_pad = curses.newpad(1000, 30)
    chat_pad_pos = 0
    chat_pad.refresh(chat_pad_pos, 0, 1, 36,30,66)

    # HOW TO RECV

    wrap_count = 0

    while True:
        socket_lock.acquire(blocking=True)
        response = s.recv(2048).decode('utf-8')
        socket_lock.release()
        tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter
        if (tag == 'board'):
            board_str = msg
            print_board(board_window, board_str)
        elif (tag == 'message'):
            wrap_count += (len(msg) / 30) + 1
            chat_string = chat_string + '\n' + msg + str(chat_pad_pos) # https://stackoverflow.com/a/2523020/3754128 link for chat scrolling
            if wrap_count >= 41: # I have literally zero idea why this is the correct number
                chat_pad_pos += 1
            print_chat(chat_pad, chat_string, chat_pad_pos)
        time.sleep(.25)


def main(stdscr):
    username = get_username(stdscr)

    while True:
        response = s.recv(2048).decode('utf-8')
        tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter
        print_board(board_window, msg)
        if (tag == 'name'):
            s.send(('name::' + username).encode('ascii'))
        break


    # response = s.recv(2048).decode('utf-8')
    # tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter

    tag = 'name'

    # print_board(board_window, msg)
    # if (tag == 'name'):
    #     s.send(('name::' + username).encode('ascii'))
    recv_thread = recvThread(stdscr)
    recv_thread.start()

    move_window = curses.newwin(4, 32, 35, 0)
    move_window.border()
    move_window.refresh()
    #TODO need to make sure cursor ends up here. Mitigated by using stdscr?
    while True:
        key = stdscr.getkey()
        if key == curses.KEY_LEFT:
            #move indicator left
            pass
        elif key == curses.KEY_RIGHT:
            # move indicator right
            pass
        elif key == curses.KEY_ENTER:
            # get selected colomn and send to server
            pass
        elif key == "c":
            # move focus to chat text box and get input from there. Probably use textbox
            pass


    time.sleep(10)
    recv_thread.join()
    
wrapper(main)

# def main(stdscr):
#     stdscr.addstr(0, 0, "Enter IM message: (hit Ctrl-G to send)")
#
#     editwin = curses.newwin(5,30, 2,1)
#     rectangle(stdscr, 1,0, 1+5+1, 1+30+1)
#     stdscr.refresh()
#
#     box = Textbox(editwin)
#
#     # Let the user edit until Ctrl-G is struck.
#     box.edit()
#
#     # Get resulting contents
#     message = box.gather()
#
# def main(stdscr):
#     # Clear screen
#     stdscr.clear()
#     stdscr.addstr(0, 0, "Current mode: Typing mode",
#                           curses.A_REVERSE)
#     stdscr.refresh()
#     # pad = curses.newpad(100, 100)
#     # These loops fill the pad with letters; addch() is
#     # explained in the next section
#     # for y in range(0, 99):
#     #     for x in range(0, 99):
#     #         pad.addch(y,x, ord('a') + (x*x+y*y) % 26)
#     #         # Displays a section of the pad in the middle of the screen.
#     #         # (0,0) : coordinate of upper-left corner of pad area to display.
#     #         # (5,5) : coordinate of upper-left corner of window area to be filled
#     #         #         with pad content.
#     #         # (20, 75) : coordinate of lower-right corner of window area to be
#     #         #          : filled with pad content.
#     #         pad.refresh( 0,0, 5,5, 20,75)
#     
#     
#     time.sleep(2)



# This raises ZeroDivisionError when i == 10. SHOWS HOW ON ERROR CURSES EXISTS PROPERLY
# for i in range(0, 11):
#     v = i-10
#     stdscr.addstr(i, 0, '10 divided by {} is {}'.format(v, 10/v))
# stdscr.refresh()
# stdscr.getkey()

# NOT NEEDED .. let curses wrapper() take care of the initialization
# def startup():
#     # initialize curses -- stdscr is a window obj representing the screen
#     stdscr = curses.initscr()
#     # disable automatic key echoing
#     curses.noecho()
#     # don't require enter for key presses
#     curses.cbreak()
#     # enable function keys (including arrow keys)
#     stdscr.keypad(1)
#    
# def on_exit():
#     # revert settings on_exit
#     curses.nocbreak(); 
#     stdscr.keypad(0); 
#     curses.echo()
#     curses.endwin()

################################################################################
# import curses.textpad
# import time
# from curses import wrapper
# import threading
# import socket
# from curses.textpad import Textbox, rectangle
# scr_lock = threading.Lock()
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect(('localhost', 8191))
#
# def isInt(s):
#     try:
#         int(s)
#         return True
#     except ValueError:
#         return False
#
# def get_input(stdscr):
#     editwin = curses.newwin(3,30, 0,35)
#     while True:
#         editwin.addstr(0, 0, "Enter column: ")
#         c = editwin.getch(1,0)
#         if c == ord('q'):
#             break
#         elif chr(c) == 'r' or isInt(chr(c)) and int(chr(c)) in range(0,6):
#             editwin.addstr(2,0,"Column " + chr(c))
#             s.send(chr(c).encode('ascii'))
#         editwin.refresh()
#
#
#
# class inputThread(threading.Thread):
#     def __init__(self, stdscr):
#         threading.Thread.__init__(self)
#         self.stdscr = stdscr
#     def run(self):
#         get_input(self.stdscr)
#
# def stringy(array):
#     temp = [0,1,2,3,4,5,6]
#     list1 = ''.join(['{:4}'.format(item) for item in temp]) + '\n\n'
#     array = reversed(list(zip(*array)))
#     return list1 + '\n'.join([''.join(['{:4}'.format(item) for item in row])
#       for row in array]) + '\n'
#
# def input_loop(stdscr):
#     while True:
#         scr_lock.acquire(blocking=True)
#         stdscr.addstr(10, 0, "Enter command:")
#         c = stdscr.getch(11,0)
#         if c == ord('p'):
#             stdscr.addstr(12, 0, "Poop")
#         elif c == ord('q'):
#             stdscr.refresh()
#             scr_lock.release()
#             break
#         scr_lock.release()
#
#
# def main(stdscr):
#
#     curses.echo()
#     input_thread = inputThread(stdscr)
#     input_thread.start()
#
#     board = [[0 for j in range(6)] for i in range(7)]
#     boardstr = stringy(board)
#
#     # Clear screen
#     win = curses.newwin(30, 30, 0, 0)
#     while True:
#         scr_lock.acquire(blocking=True)
#         bytes = s.recv(2048).decode('utf-8')
#         win.clear()
#         win.addstr(0, 0, bytes)
#         # win.addstr(0, 0, boardstr)
#         win.refresh()
#         scr_lock.release()
#
#     input_thread.join()
#     # This raises ZeroDivisionError when i == 10.
#     # for i in range(0, 9):
#     #     v = i-10
#     #     #time.sleep(1)
#     #     stdscr.addstr(i, 0, '10 divided by {} is {}'.format(v, 10/v))
#
#
# wrapper(main)
#
# #stdscr = curses.initscr()
#


#curses.noecho()
#curses.echo()
#stdscr.addstr("Pretty text", curses.color_pair(1))
#stdscr.refresh()

#begin_x = 20
#begin_y = 7
#height = 5
#width = 40
#win = curses.newwin(height, width, begin_y, begin_x)


#hw = "Hello world!"


#curses.endwin()
