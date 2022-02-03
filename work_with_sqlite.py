import sqlite3
from datetime import datetime, timedelta

from connect import Connect


class sqlite:
    """
    def __init__(self):
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE conversations (id int, mode text)")
        cursor.execute("CREATE TABLE users (user int, username text, score int, "
                       "rank text, dates text, stat text, messages text, marriage text)")
        conn = sqlite3.connect('questions.db')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE questions (id int, quest text)")
        cursor.execute("CREATE TABLE beta_questions (id int, quest text, user_name text)")"""

    VkApi = Connect()

    def update_score(self, score, user_id):
        ranks = self.show_all_in_table('SELECT * FROM ranks', "game_data.db")
        user = self.show_all_in_table('SELECT * FROM users WHERE user=' + str(user_id), "data.db")[0]
        user_score = user[2] + score
        self.update_user('score=' + str(user_score), str(user_id))
        right_rank = 0
        for i in ranks:
            if user_score >= i[4]:
                right_rank = i[0]
            else:
                break
        if user[3] == right_rank:
            return False, None
        else:
            self.update_user("rank='" + right_rank + "'", str(user_id))
            return True, right_rank

    def update_conversation(self, parametr, user):
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        sql = "UPDATE conversations SET " + parametr + "WHERE id = " + user + ""
        cursor.execute(sql)
        conn.commit()

    def update_user(self, settings, user):
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        sql = "UPDATE users SET " + settings + " WHERE user = '" + str(user) + "'"
        cursor.execute(sql)
        conn.commit()

    def check_and_add_user(self, user_id):
        if len(self.show_all_in_table("SELECT * FROM users WHERE user=" + str(user_id), "data.db")) == 0:
            player = self.VkApi.vk_api.users.get(user_id=user_id, name_case='nom')[0]
            player = "*id" + str(user_id) + " (" + player['first_name'] + ")"
            sql = 'INSERT INTO users VALUES (?,?,?,?,?,?,?,?)'
            time_now = datetime.now() + timedelta(hours=3)
            time_now = time_now.strftime('%d.%m.%Y ')
            self.add_in_table(sql, (str(user_id), player, '0', 'здоровый', time_now, "0", "0", 'none'), 'data.db')
            return False
        else:
            return True

    def show_all_users(self):
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        sql = "SELECT * FROM users ORDER BY score"
        cursor.execute(sql)
        return cursor.fetchall()

    def add_in_table(self, sql, data, file):
        conn = sqlite3.connect(file)
        cursor = conn.cursor()
        cursor.executemany(sql, [data])
        conn.commit()

    def show_all_in_table(self, sql, file):
        conn = sqlite3.connect(file)
        cursor = conn.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

    def delete_in_tables(self, sql, file):
        conn = sqlite3.connect(file)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
