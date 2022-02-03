from threading import Thread

from func_timeout import func_timeout, FunctionTimedOut


class MenuOfGame:

    def __init__(self, vk_connect, sqlite):
        self.VkBot = vk_connect
        self.work_with_sql = sqlite

    def treatment(self, data):
        text, peer, from_id = data
        words = text.split()
        if text == 'обучение':
            Thread(target=self.training, args=(peer,)).start()
            return
        elif words[0] == 'побег':
            name = 'уже идёт игра!'
            self.VkBot.send_message(peer, name)

    def training(self, peer):
        sql = "SELECT * FROM conversations WHERE id=" + str(peer)
        conversation_mode = self.work_with_sql.show_all_in_table(sql, "data.db")[0][1]
        if conversation_mode == 'training':
            self.VkBot.send_message(peer, 'обучение уже открыто, нажми 0 и я снова покажу список')
            return
        else:
            sql = "mode='training'"
            self.work_with_sql.update_conversation(sql, str(peer))

        def wait_for_answer():
            while True:
                text = self.VkBot.check_for_one(peer)[0]
                if text.isdigit() and -1 < int(text) < 3:
                    return int(text)

        text = 'что тебя интересует?\n'
        list_of_training = "0. показать список ещё раз\n1. как начать игру?\n2. что нужно делать?"
        self.VkBot.send_message(peer, text + list_of_training)
        while True:
            try:
                number = func_timeout(30, wait_for_answer)
            except FunctionTimedOut:
                sql = "mode='default'"
                self.work_with_sql.update_conversation(sql, str(peer))
                return
            if number == 0:
                answer = list_of_training
            elif number == 1:
                answer = "чтобы начать игру, нужно написать \"побег\". если вы хотите выбрать время набора игроков," + \
                         " то добавляйте циферку. например \"побег 4\" - 4 минуты. максимум - 10."
            elif number == 2:
                answer = 'отвечать правильно на вопросы, и тем самым наносить урон противнику. неправильный ответ' + \
                         " влечёт за собой получение пиздыx`."
            else:
                answer = "э?"
            self.VkBot.send_message(peer, answer)
