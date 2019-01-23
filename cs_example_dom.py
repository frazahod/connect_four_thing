#!/usr/bin/env python3
import curses
from curses import wrapper
from curses.textpad import Textbox
import socket
import threading
import subprocess
import getpass
import signal
import time
import sys
import textwrap


user = getpass.getuser()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('fxdeva11', 8191))
socket_lock = threading.Lock()
scr_lock = threading.Lock()


def handler(signum, frame):
    print('signal handler called')
    s.send(('quit::' + 'SIGTERM').encode('ascii'))
    sys.exit(0)

def print_board(board_window, board_str):
    scr_lock.acquire(blocking=True)
    board_window.clear()
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
    BOARD_WINDOW_NLINES = 8
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
    resp_buffer = ''
    while True:
        socket_lock.acquire(blocking=True)
        while '\r\n' not in resp_buffer:
            resp_buffer += s.recv(2048).decode('utf-8')
        parsed = resp_buffer.split('\r\n')
        response = parsed[0]
        resp_buffer = parsed[1]
        # response = s.recv(2048).decode('utf-8')
        socket_lock.release()
        if response and '::' in response:
            tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter
            if tag == 'board':
                board_str = msg
                print_board(board_window, board_str)
            elif tag == 'message':
                msg = textwrap.fill(msg, 30)
                wrap_count += (len(msg) / 30) + 1
                chat_string = chat_string + '\n' + msg # https://stackoverflow.com/a/2523020/3754128 link for chat scrolling
                if wrap_count >= 41: # I have literally zero idea why this is the correct number
                    chat_pad_pos += 1
                print_chat(chat_pad, chat_string, chat_pad_pos)
        else:
            return


def move_curser(pos, move_window):
    scr_lock.acquire(blocking=True)
    move_window.clear()
    move_window.addstr(1, pos, '^')
    move_window.addstr(2, pos, '^')
    move_window.refresh()
    scr_lock.release()

def print_chat_entry(stdscr):
    scr_lock.acquire(blocking=True)
    curses.curs_set(1)
    chat_win = curses.newwin(4,32, 12,0)
    chat_win.addstr(0, 0, "Message (ctrl-g to send)")
    chat_subwin = chat_win.subwin(3, 32, 13, 0)
    chat_win.refresh()
    chat_textbox = curses.textpad.Textbox(chat_subwin)
    chat_textbox.edit()
    message = chat_textbox.gather()
    curses.curs_set(0)
    stdscr.refresh()
    scr_lock.release()
    return message.replace('\n', '')

def send_message(message):
    # socket_lock.acquire(blocking=True)
    s.send(('message::' + message + '\r\n').encode('ascii')) # POSIX something something, atomic something something.
    # socket_lock.release()

def send_move(pos):
    s.send(('move::' + str(pos) + '\r\n').encode('ascii'))

def main(stdscr):
    curses.curs_set(0)
    print("Waiting for player 2")
    resp_buffer = ''
    while True: # Wait for server to ask for username
        while '\r\n' not in resp_buffer:
            resp_buffer += s.recv(2048).decode('utf-8')
        parsed = resp_buffer.split('\r\n')
        response = parsed[0]
        resp_buffer = parsed[1]
        if response and '::' in response:
            tag, msg = response.split('::', 1)  # Only splits on first instance of delimiter
            if tag == 'name':
                s.send(('name::' + user + '\r\n').encode('ascii'))
                break


    recv_thread = recvThread(stdscr)
    recv_thread.start()

    arrow_pos = 0
    move_window = curses.newwin(4, 32, 8, 0)
    move_curser(arrow_pos, move_window)
    #TODO need to make sure cursor ends up here. Mitigated by using stdscr?
    while True:
        if not recv_thread.is_alive(): return
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
            message = print_chat_entry(stdscr)
            if '!quit' in message:
                s.send(('quit::' + 'SIGTERM').encode('ascii'))
                recv_thread.join()
                return
            else:
                send_message(message)


    recv_thread.join()
    
wrapper(main)


