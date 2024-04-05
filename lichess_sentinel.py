import datetime
import json
import time

from queue import Queue
from threading import Thread

import chess
import requests

from RPLCD.i2c import CharLCD
from gpiozero import Buzzer

buzzer = Buzzer(17)
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2,
              dotsize=8)
lcd.clear()

USERNAME = 'benjamincrom4'
API_TOKEN = ''

GAME_URL_TEMPLATE = 'https://lichess.org/api/board/game/stream/{game_id}'
USER_URL_TEMPLATE = 'https://lichess.org/api/user/{username}'
MOVE_URL_TEMPLATE = (
    'https://lichess.org/api/board/game/{game_id}/move/{move_str}'
)


def display_consumer(display_queue):
    iterations = 0
    white_time_ms = None
    black_time_ms = None
    white_to_move = None
    white_time_delta = None
    black_time_delta = None
    not_initialized = True
    while True:
        if display_queue.empty():
            if not_initialized:
                pass
            else:
                time.sleep(1)
                iterations += 1
                if white_to_move:
                    white_time_delta = datetime.timedelta(
                        milliseconds=white_time_ms - 2000 - (1000 * iterations)
                    )
                else:
                    black_time_delta = datetime.timedelta(
                        milliseconds=black_time_ms - 2000 - (1000 * iterations)
                    )

                white_time_str = str(white_time_delta).split('.', maxsplit=1)[0]
                black_time_str = str(black_time_delta).split('.', maxsplit=1)[0]
                lcd.cursor_pos = (0, 0)
                lcd.write_string(f'{white_time_str}  {black_time_str}')
        else:
            (white_time_ms,
             black_time_ms,
             last_move_str,
             white_to_move,
             white_pieces) = display_queue.get()

            white_time_delta = datetime.timedelta(milliseconds=white_time_ms)
            black_time_delta = datetime.timedelta(milliseconds=black_time_ms)
            white_time_str = str(white_time_delta).split('.', maxsplit=1)[0]
            black_time_str = str(black_time_delta).split('.', maxsplit=1)[0]
            lcd.cursor_pos = (0, 0)
            lcd.write_string(f'{white_time_str}  {black_time_str}')

            if (
                    (white_to_move and white_pieces)
                    or
                    (not white_to_move and not white_pieces)
                ):
                padding = '*' * (15 - len(last_move_str))
            else:
                padding = ' ' * (15 - len(last_move_str))
            if white_to_move:
                full_move_str = f'{padding} {last_move_str}'
            else:
                full_move_str = f'{last_move_str} {padding}'

            lcd.cursor_pos = (1, 0)
            lcd.write_string(full_move_str)

            not_initialized = False
            iterations = 0

def display_producer(display_queue):
    response = requests.get(USER_URL_TEMPLATE.format(username=USERNAME),
                            headers={"Authorization": f"Bearer {API_TOKEN}"},
                            timeout=30)

    game_id, color = response.json()['playing'].split('/')[3:5]

    white_pieces = bool(color == 'white')
    last_move_str = None
    session = requests.Session()

    with session.get(GAME_URL_TEMPLATE.format(game_id=game_id),
                     headers={"Authorization": f"Bearer {API_TOKEN}"},
                     stream=True) as response:
        for line in response.iter_lines():
            if line:
                game_dict = json.loads(line)
                white_to_move = True
                move_number = 1
                move_list_str = ''
                if game_dict['type'] == 'gameState':
                    board = chess.Board()
                    for move_str in game_dict['moves'].split():
                        move = chess.Move.from_uci(move_str)
                        san_str = board.san(move)
                        last_move_str = san_str
                        if white_to_move:
                            move_list_str += f'{move_number}. {san_str} '
                            white_to_move = False
                        else:
                            move_list_str += f'{san_str} '
                            white_to_move = True
                            move_number += 1

                        board.push(move)

                    if (
                            (white_to_move and white_pieces)
                            or
                            (not white_to_move and not white_pieces)
                        ):
                        buzzer.on()
                        time.sleep(0.15)
                        buzzer.off()

                    display_queue.put(
                        (game_dict['wtime'], game_dict['btime'],
                         last_move_str, white_to_move, white_pieces)
                    )

display_queue = Queue()
thread_consumer = Thread(target=display_consumer, args=(display_queue, ))
thread_producer = Thread(target=display_producer, args=(display_queue, ))
thread_consumer.start()
thread_producer.start()
