import time
import random
from math import ceil

from func_timeout import func_timeout, FunctionTimedOut
from vk_api.utils import get_random_id


class Escape:

    def __init__(self, sqlite, connect):
        self.VkApi = connect
        self.sqlite = sqlite

    def selection(self, peer, started, minutes):
        players = [started]
        message = "набор в отряд для побега открыт! время ожидания: " + str(minutes) + " мин." + "\n" + \
                  "\nкоманды: \nвступить, начать/отменить (для запустившего игру), выйти, игроки"
        self.VkApi.send_message(peer, message)
        ready_players = []

        def get_count_for_continue(players):
            if players > 4:
                return ceil(players / 2)
            else:
                return 2

        def wait_for_players():
            count_for_continue = 2
            while True:
                data = self.VkApi.check_for_one(peer)
                data[0] = data[0].lower()
                if data is None:
                    continue

                if data[0] in ('вступить', 'играть', 'войти', 'зайти'):
                    if data[1] in players:
                        message = 'ты уже в игре!'
                    else:
                        players.append(data[1])
                        self.sqlite.check_and_add_user(data[1])
                        user = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(data[1]),
                                                             "data.db")[0][0]
                        count_for_continue = get_count_for_continue(len(players))

                        #  надо будет сменить способ записи игрока

                        message = user + ' вступил(а) в отряд!'
                    self.VkApi.send_message(peer, message)
                elif data[0] in ("начать", "запустить", "бежим", "вперёд", "чайник", "начинаем", "побежали"):
                    if data[1] == started:
                        if len(players) > 0:
                            break
                        else:
                            self.VkApi.send_message(peer, "для побега нужно хотя бы два человека!")
                    else:
                        if data[1] in players:
                            if data[1] in ready_players:
                                message = 'ты уже голосовал за запуск!'
                            else:
                                ready_players.append(data[1])
                                message = "(" + str(len(ready_players)) + "/" + str(count_for_continue) + ")"
                        else:
                            message = "чтобы проголосовать за запуск, нужно быть в отряде"
                        self.VkApi.send_message(peer, message)
                        if len(ready_players) == count_for_continue:
                            break
                elif data[0] == "выйти":
                    if data[1] in players:
                        user = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(data[1]),
                                                             "data.db")[0][0]
                        message = user + " покинул(а) отряд!"
                        if data[1] in ready_players:
                            ready_players.remove(data[1])
                            message += " (" + str(len(ready_players)) + "/" + str(count_for_continue) + ")"
                        players.remove(data[1])
                        count_for_continue = get_count_for_continue(len(players))
                    else:
                        message = 'ты и так не в отряде'
                    self.VkApi.send_message(peer, message)
                elif data[0] in ('игроки', "участники", "отряд"):
                    if len(players) == 0:
                        message = "в отряде никого нет!"
                    else:
                        message = "в отряде:\n"
                        for i in players:
                            user = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + \
                                                                 str(i), "data.db")[0][0]
                            message += user + "; "
                    self.VkApi.send_message(peer, message)
                elif data[0] == "отменить" and data[1] == started:
                    return False
            return True

        try:
            escape = func_timeout(minutes * 60, wait_for_players)
            if escape:
                self.VkApi.send_message(peer, 'побег начинается!')
                self.game(peer, players)
            else:
                self.VkApi.send_message(peer, 'побег отменён!')
                self.sqlite.update_conversation("mode='default'", str(peer))
        except FunctionTimedOut:
            if len(players) > 1:
                self.VkApi.send_message(peer, 'вперёд из дурки!')
                self.game(peer, players)
            else:
                self.VkApi.send_message(peer, 'время кончилось, людей не хватает, побег отменён!')
                self.sqlite.update_conversation("mode='default'", str(peer))

    def game(self, peer, users):
        time.sleep(5)
        players = []
        died = []
        level = 1
        questions = self.sqlite.show_all_in_table("SELECT * FROM questions_for_escape",
                                                  "game_data.db")
        message = "в отряде:\n"
        for player in users:
            user = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(player),
                                                 "data.db")[0][0]
            message += user + "; "
            players.append([player, user, 20, 0, 1, []])  # айди, имя, хп, опыт, уровень, инвентарь
        self.VkApi.send_message(peer, message)

        time.sleep(5)

        while True:
            self.cut_scene(level, players, peer)
            result = self.fight(level, players, peer, questions)
            if len(result[3]) > 0:
                died.append(result[3])
            if result[0] == 1 or level == 9:
                break
            level += 1
            questions = result[1]
            players = result[2]
            self.pause(players, peer, died)
            if len(players) == 0:
                result[0] = 2
                break
        self.reward(result[0], died, players, peer)
        self.sqlite.update_conversation("mode='default'", str(peer))

    def cut_scene(self, level, players, peer):
        sql = "SELECT cut_scenes FROM levels WHERE level=" + str(level)
        cut_scene = self.sqlite.show_all_in_table(sql, "game_data.db")[0][0]
        index = random.randint(0, len(players) - 1)
        random_player = players[index][0]
        random_player = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(random_player),
                                                      "data.db")[0][0]
        cut_scene = cut_scene.replace("{random_name}", random_player)
        cut_scene = cut_scene.split("@")
        for i in cut_scene:
            self.VkApi.send_message(peer, i)
            time.sleep(8)

    def fight(self, level, players, peer, questions):
        sql = "SELECT * FROM levels WHERE level=" + str(level)
        enemy_settings = self.sqlite.show_all_in_table(sql, "game_data.db")[0]
        enemy_health = self.get_the_enemy_hp(len(players), level)

        enemy = []
        died = []
        for i in enemy_settings:
            enemy.append(i)
        enemy.append(enemy_health)

        enemy_talk = []
        for i in range(3, 7):
            enemy_talk.append(enemy[i].split("@"))
        enemy_talk.append(0)

        message = "битва начинается! ваш противник - "
        message += enemy[1] + " (" + str(enemy_health) + " хп)"
        self.VkApi.send_message(peer, message)

        def player_gets_damage(player):
            nonlocal enemy_talk
            damage = round(level * 5 + (5 - len(players) / 2))
            player[2] -= damage
            if player[2] < 0:
                player[2] = 0
            name = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(player[0]),
                                                 "data.db")[0][0]
            talk = self.enemy_talk(3, enemy_talk, enemy, name)
            message = enemy[1] + ": " + talk[0] + "\n\n"
            enemy_talk = talk[1]
            message += enemy[1] + " (" + str(enemy[8]) + " хп) наносит урон [" + str(damage) + "] игроку " + name + \
                       " (" + str(player[2]) + " хп)"
            if player[2] == 0:
                message += ". " + name + " мертв(а)!"
                players.remove(player)
                died.append(player)
            self.VkApi.send_message(peer, message)

        def enemy_gets_damage(player):
            nonlocal enemy_talk
            enemy[8] -= player[4] * 5
            if enemy[8] < 0:
                enemy[8] = 0
            name = self.sqlite.show_all_in_table("SELECT username FROM users WHERE user=" + str(player[0]),
                                                 "data.db")[0][0]
            text = "ответ верный! " + enemy[1] + " (" + str(enemy[8]) \
                   + " хп) получает урон [" + str(player[4] * 5) + "] от игрока " + name + " (" + str(
                player[2]) + " хп)"
            if enemy[8] == 0:
                text += ". победа!"
                talk = self.enemy_talk(7, enemy_talk, enemy, name)
                text += '\n\n' + enemy[1] + " (умирая): " + talk
                if get_medicine():
                    text += '\n\nигроку ' + name + " выпала аптечка! использовать её можно во время паузы"
                    player[5].append('аптечка')
            else:
                talk = self.enemy_talk(2, enemy_talk, enemy, name)
                text += '\n\n' + enemy[1] + ": " + talk[0]
                enemy_talk = talk[1]
            player_app = self.add_score(player)
            player = player_app[1]
            if player_app[0]:
                text += "\n\nлевел ап! " + name + " становится свирепее! (" + str(player[4]) + " лвл)"
            self.VkApi.send_message(peer, text)
            return player

        def get_medicine():
            chance = random.randint(1, 3)
            if chance == 1:
                return True
            else:
                return False

        time.sleep(8)

        while True:
            answer = self.questions(questions, peer, players)
            questions = answer[2]
            index = answer[1]
            if answer[0]:
                players[index] = enemy_gets_damage(players[index])
            else:
                player_gets_damage(players[index])
            time.sleep(8)
            if len(players) == 0:
                return [1, questions, players, died]
            elif enemy[8] == 0:
                return [0, questions, players, died]

    def get_the_enemy_hp(self, x, y):
        result = 20 + 11.1 * (y - 1) + x * (1 + (0.75 * (y - 1)))
        return round(result)

    def questions(self, questions, peer, users):
        players = []
        for player in users:
            players.append(player[0])
        if len(questions) == 0:
            questions = self.sqlite.show_all_in_table("SELECT * FROM questions_for_escape",
                                                      "game_data.db")
        index = random.randint(0, len(questions) - 1)
        message = "ответь правильно на вопрос, чтоб нанести урон (20 сек.):\n\n"
        question = questions[index]
        questions.remove(question)
        message += question[0] + "\n"
        options = question[1].split("@")
        correct_answer = options[int(question[2]) - 1]
        random.shuffle(options)
        correct_answer = options.index(correct_answer) + 1
        for i in range(len(options)):
            message += str(i + 1) + ". " + options[i] + "\n"
        message += "\n"
        self.VkApi.send_message(peer, message)

        try:
            answer = func_timeout(20, self.answer_time, args=(players, peer, options))
            index = players.index(answer[1])
            if answer[0] in (str(correct_answer), options[correct_answer - 1]):
                return True, index, questions
            else:
                return False, index, questions
        except FunctionTimedOut:
            self.VkApi.send_message(peer, 'время вышло!')
            index = random.randint(0, len(players) - 1)
            return False, index, questions

    def answer_time(self, users, peer, options):
        while True:
            data = self.VkApi.check_for_one(peer)
            if (data[1] in users and data[0].isdigit() and 0 < int(data[0]) < 5) or data[0] in options:
                return data

    def add_score(self, player):
        player[3] += 1
        if player[3] == 5 and player[4] != 5:
            player[3] = 0
            player[4] += 1
            player[2] += 10
            return True, player
        else:
            return False, player

    def enemy_talk(self, x, enemy_talk, enemy, player='пидор'):
        mode = 0
        for i in range(len(enemy_talk[0])):
            if enemy[8] <= int(enemy_talk[0][i]):
                mode = i + 1
            else:
                break
        if enemy_talk[4] == mode and enemy[8] > 0:
            if len(enemy_talk[x]) == 0:
                enemy_talk[x] = enemy[x + 3].split("@")
            index = random.randint(0, len(enemy_talk[x]) - 1)
            say = enemy_talk[x][index]
            enemy_talk[x].remove(enemy_talk[x][index])
            say = say.replace("{username}", player)
            return say, enemy_talk
        elif enemy[8] > 0:
            say = enemy_talk[1][mode - 1]
            enemy_talk[4] = mode
            return say, enemy_talk
        else:
            talks = enemy[x].split("@")
            index = random.randint(0, len(talks) - 1)
            say = talks[index]
            return say

    def reward(self, win, died, players, peer):
        if win == 0:
            self.cut_scene(10, players, peer)
        elif win == 1:
            self.VkApi.send_message(peer, "последний шизоид держался как мог, но его победили!")
            time.sleep(8)
        else:
            self.VkApi.send_message(peer, "оставшийся шизоид покончил жизнь самоубийством")
            time.sleep(8)
        message = "спасибо за игру!\n\n"
        if win == 0:
            if len(players) == 1:
                message += "сбежать смог только один шизоид - " + players[0][1] + self.score(players[0]) + "! "
            else:
                message += "сбежали:\n"
                for i in range(len(players)):
                    if i == (len(players) - 1):
                        break
                    message += players[i][1] + self.score(players[i]) + ", "
                message += "и " + players[len(players) - 1][1] + self.score(players[len(players) - 1]) + ". "
            if len(died) == 1 and len(died[0]) == 1:
                message += " а игрок " + died[0][0][1] + self.score(died[0][0]) + " был убит."
            elif len(died) > 0:
                message += "\n\nв процессе побега погибли:\n"
                for i in died:
                    for player in i:
                        message += player[1] + self.score(player) + "; "
        else:
            message += "сбежать пытались:\n"
            for i in died:
                for player in i:
                    message += player[1] + self.score(player) + "; "
        message += "\n\nпосмотреть своё звание и информацию можно командой \"участник\""
        self.VkApi.vk_api.messages.send(peer_id=peer, attachment="photo-190173129_457239052",
                                        message=message, disable_mentions=1, random_id=get_random_id())

    def score(self, player):
        score = player[4] - 1
        if player[4] == 5:
            score += player[3] // 5
        if score == 0:
            return ""
        else:
            message = "(+" + str(score) + ")"
            self.sqlite.update_score(score, player[0])
            return message

    def pause(self, players, peer, died):

        def heal(player):
            player[2] += 10
            max_heal = 10 + (10 * player[4])
            if player[2] > max_heal:
                player[2] = max_heal
                return True, player[2]
            return False, player[2]

        def wait_for_ready():
            ready = 0
            players_in_ready = []
            while ready != count_for_continue:
                data = self.VkApi.check_for_one(peer)
                if data[1] not in users:
                    continue
                elif data[0] in ("готов", "готова"):
                    if data[1] in players_in_ready:
                        message = 'ты уже отмечен как готовый!'
                    else:
                        ready += 1
                        players_in_ready.append(data[1])
                        message = "(" + str(ready) + "/" + str(count_for_continue) + ")"
                    self.VkApi.send_message(peer, message)
                elif data[0] in ('игроки', "отряд", "выжившие"):
                    message = 'в отряде из выживших:\n'
                    for player in players:
                        message += player[1] + " (" + str(player[2]) + " хп); "
                    self.VkApi.send_message(peer, message)
                elif data[0] in ("инвентарь", "вещи"):
                    index = users.index(data[1])
                    count_of_medicine = players[index][5].count('аптечка')
                    if count_of_medicine == 1:
                        message = 'у тебя есть одна аптечка'
                    elif count_of_medicine > 1:
                        message = 'у тебя есть аптечки (' + str(count_of_medicine) + " шт.)"
                    else:
                        message = "твой инвентарь пуст"
                    self.VkApi.send_message(peer, message)
                elif data[0] in ('хил', "аптечка", "подлечиться"):
                    index = users.index(data[1])
                    if 'аптечка' in players[index][5]:
                        player_healing = heal(players[index])
                        players[index][2] = player_healing[1]
                        if player_healing[0]:
                            message = players[index][1] + ' полностью излечил(а) себя! (' + str(players[index][2]) + " хп)"
                        else:
                            message = players[index][1] + ' использовал(а) аптечку! ('
                            max_hp = 10 + (10 * players[index][4])
                            message += str(players[index][2]) + "/" + str(max_hp) + ")"
                        players[index][5].remove('аптечка')
                    else:
                        message = 'у тебя нет аптечки!'
                    self.VkApi.send_message(peer, message)
                elif data[0] in ('самовыпил', "суицид", "суецыд"):
                    index = users.index(data[1])
                    message = players[index][1] + " убивает себя. RIP."
                    died.append([players[index]])
                    players.remove(players[index])
                    users.remove(data[1])
                    if len(players) == 0:
                        message += ' на этом весь побег кончается.'
                        self.VkApi.send_message(peer, message)
                        return
                    self.VkApi.send_message(peer, message)

            self.VkApi.send_message(peer, "игроки готовы, можно двигаться дальше!")

        users = []
        for player in players:
            users.append(player[0])
        count_for_continue = ceil(len(players) / 2)
        message = "\n\nу вас есть минута, чтобы передохнуть. если вы готовы, (0/" + str(count_for_continue) + \
                  ") должны написать готов/готова\n\nкоманды:\nигроки, инвентарь, аптечка, суицид"
        self.VkApi.send_message(peer, message)
        try:
            func_timeout(60, wait_for_ready)
        except FunctionTimedOut:
            self.VkApi.send_message(peer, "больше нет времени прохлаждаться, вперёд!")
        time.sleep(5)
