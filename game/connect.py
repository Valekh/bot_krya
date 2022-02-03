import vk_api
import vk_api.vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id


class Connect:

    # подключение к ВК, где token это полученный токен, а id = айди группы.
    def __init__(self):
        self.vk_session = vk_api.VkApi(
            token='TOKEN')
        self.longpoll = VkBotLongPoll(self.vk_session, 'ID')
        self.vk_api = self.vk_session.get_api()

    def send_message(self, peer, text):
        self.vk_api.messages.send(peer_id=peer, random_id=get_random_id(), message=text, disable_mentions=1)

    def send_message_with_notifications(self, peer, text):
        self.vk_api.messages.send(peer_id=peer, random_id=get_random_id(), message=text)

    # функция ожидания сообщения от конкретного человека (для игр)
    def check_for_one(self, peer):
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW and event.object.id == 0 and event.obj.peer_id == peer:
                return [event.obj.text, event.object.from_id]
