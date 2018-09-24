#!/usr/bin/env python3 
import curses
from curses import wrapper
from curses.textpad import Textbox
import socket
import threading
import subprocess
import getpass


import time

user = getpass.getuser()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 8191))
socket_lock = threading.Lock()
scr_lock = threading.Lock()

def print_board(board_window, board_str):
    # board_window.clear()
    scr_lock.acquire(blocking=True)
    board_window.addstr(1, 0, board_str)
    # board_window.border()
    board_window.refresh()
    scr_lock.release()

def print_chat(chat_pad, chat_str, chat_pad_pos):# Very naive implementation
    scr_lock.acquire(blocking=True)
    chat_pad.addstr(0, 0, chat_str)
    chat_pad.refresh(chat_pad_pos, 0, 1, 36, 30, 66)
    scr_lock.release()


# def print_debug_msg(stdscr, BOARD_HEIGHT, msg):

class recvThread(threading.Thread):
    def __init__(self,stdcr):
        threading.Thread.__init__(self)
        self.stdcr = stdcr

    def run(self):
        recv_windows(self.stdcr)

def recv_windows(stdcr):
    scr_lock.acquire(blocking=True)
    BOARD_WINDOW_NLINES = 16
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
    scr_lock.release()

    # HOW TO RECV

    wrap_count = 0
    # time.sleep(25)
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
            chat_string = chat_string + '\n' + msg # https://stackoverflow.com/a/2523020/3754128 link for chat scrolling
            if wrap_count >= 41: # I have literally zero idea why this is the correct number
                chat_pad_pos += 1
            print_chat(chat_pad, chat_string, chat_pad_pos)


def move_curser(pos, move_window):
    scr_lock.acquire(blocking=True)
    move_window.clear()
    move_window.addstr(1, pos, '^')
    move_window.addstr(2, pos, '^')
    move_window.refresh()
    scr_lock.release()

def print_chat_entry(stdscr):
    curses.curs_set(1)
    chat_win = curses.newwin(4,32, 32,35)
    chat_win.addstr(0, 0, "Message (ctrl-g to send)")
    chat_subwin = chat_win.subwin(3, 32, 33, 35)
    chat_win.refresh()
    chat_textbox = curses.textpad.Textbox(chat_subwin)
    chat_textbox.edit()
    message = chat_textbox.gather()
    curses.curs_set(0)
    stdscr.refresh()
    return message

def send_message(message):
    # socket_lock.acquire(blocking=True)
    s.send(('message::' + message).encode('ascii'))
    # socket_lock.release()

def send_move(pos):
    s.send(('move::' + str(pos)).encode('ascii'))

def main(stdscr):
    # username = get_username(stdscr)
    curses.curs_set(0)
    print("Waiting for player 2")
    while True: # Wait for server to ask for username
        response = s.recv(2048).decode('utf-8')
        if response:
            tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter
            # print_board(board_window, msg)
            if (tag == 'name'):
                # print("server asked for name, sending")
                s.send(('name::' + user).encode('ascii'))
                break


    recv_thread = recvThread(stdscr)
    recv_thread.start()

    arrow_pos = 0
    move_window = curses.newwin(4, 32, 7, 0)
    move_curser(arrow_pos, move_window)
    #TODO need to make sure cursor ends up here. Mitigated by using stdscr?
    while True:
        key = stdscr.getkey()
        if key == "KEY_LEFT":
            arrow_pos = (arrow_pos - 4) if arrow_pos > 3 else 24
            move_curser(arrow_pos, move_window)
        elif key == "KEY_RIGHT":
            arrow_pos = (arrow_pos + 4) if arrow_pos < 21 else 0
            move_curser(arrow_pos, move_window)
        elif key == '\n':
            # get selected colomn and send to server
            send_move(int(arrow_pos / 4))
            pass
        elif key == "c":
            send_message(print_chat_entry(stdscr))



    recv_thread.join()
    
wrapper(main)


