import sqlite3
import requests
from threading import Thread
import time

from vk_api.bot_longpoll import VkBotEventType
import vk_api
from vk_api.utils import get_random_id

from connect import Connect
from game import Game
from menu import MenuOfGame
from escape1 import Escape
from work_with_sqlite import sqlite


class Bot:
    def __init__(self):
        self.sqlite = sqlite()
        self.data = []
        self.ChatBot = Connect()
        self.menu = MenuOfGame(self.ChatBot, self.sqlite)
        self.Game = Game(self.sqlite, self.ChatBot)
        self.Escape = Escape(self.sqlite, self.ChatBot)

    # функция, обрабатывающая полученные события от VK (напр., сообщения)
    def check(self):
        while True:
            try:
                for event in self.ChatBot.longpoll.listen():
                    if event.type == VkBotEventType.MESSAGE_NEW and event.object.id == 0:
                        self.who(event.obj.text.lower(), event.obj.peer_id, event.object.from_id)
            except requests.exceptions.ReadTimeout:
                print('Ошибка тайм-аута')
                continue
            except vk_api.exceptions.ApiError as error:
                print(error)
                continue
            except:
                continue

    # сюда поступают полученные приложения, где бот их сортирует: от других ботов в мусорку, от остальных
    # на рассмотрение
    def who(self, text, peer, from_id):
        if from_id < 0 or len(text) < 1:
            return
        self.data = [text, peer, from_id]
        if len(self.sqlite.show_all_in_table('SELECT * FROM conversations WHERE id=' + str(peer), "data.db")) == 0:
            data = [(str(peer), "default")]
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()
            cursor.executemany("INSERT INTO conversations VALUES (?,?)", data)
            conn.commit()
            self.ChatBot.vk_api.messages.send(peer_id=peer,
                                              attachment="photo-190173129_457239053", random_id=get_random_id(),
                                              message='добро пожаловать в "Дурка онлайн".\nобучение - чтоб я рассказал'
                                                      ' об игре \nигра/побег - чтоб запустить игру'
                                                      '\n\nдля того, чтоб я работал, мне нужно выдать права админа')
        self.treatment()

    # после приветствия (в случае необходимости) игроков, бот считывает их сообщения
    def treatment(self):
        text = self.data[0]
        words = text.split()
        conversation_data = self.sqlite.show_all_in_table('SELECT * FROM conversations WHERE id=' + str(self.data[1]),
                                                          "data.db")[0][1]
        if words[0] in ("игра", "побег") and conversation_data == "game":
            self.ChatBot.send_message(self.data[1], 'нельзя. игра идёт!')
        elif words[0] in ('игра', "побег"):
            self.start_game()
        else:
            self.menu.treatment(self.data)

    # игра начинается и передаёт в другой модуль количество указанных игроком минут для ожидания других
    def start_game(self):
        words = self.data[0].split()
        if len(words) > 1:
            if words[1].isdigit():
                if 0 < int(words[1]) < 11:
                    time_in_minutes = int(words[1])
                else:
                    time_in_minutes = 2
            else:
                return
        else:
            time_in_minutes = 2
        self.sqlite.update_conversation("mode='game'", str(self.data[1]))
        self.sqlite.check_and_add_user(self.data[2])
        Thread(target=self.Escape.selection, args=(self.data[1], self.data[2], time_in_minutes)).start()


VkBot = Bot()
time.sleep(3)
VkBot.check()
