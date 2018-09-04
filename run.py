# -*- coding: utf-8 -*-

import datetime
import telebot
from threading import Timer

from config import token, ADMIN_CHATS_ID

bot = telebot.TeleBot(token)

free = True
book_user = ""
book_chat_id = -1
book_start = None
locked = False
lock_user = ""

queue = []

MINUTE = 60
GAME_TIME = 1*MINUTE
GAME_REPEAT_TIME = 1*MINUTE
LOCK_WAIT = 2*MINUTE


def notify(chat_id):
    for i in range(6):
        Timer(GAME_REPEAT_TIME*i,
              lambda num: bot.send_message(chat_id, "Ты еще играешь? Прошло уже "+\
                                           str((GAME_TIME+num*GAME_REPEAT_TIME) / MINUTE) +
                                           " минут, другим тоже хочется... "
                                           "Чтобы отметить, что стол больше не занят, нажми /leave")
              if book_chat_id == chat_id else None).start()

    for admin in ADMIN_CHATS_ID:
        Timer(GAME_REPEAT_TIME*5, lambda: bot.send_message(admin, "Админ, у нас неприятности:(")
                                    if book_chat_id == chat_id else None).start()


def book(user, chat_id):
    global free, locked, lock_user, book_user, book_chat_id, book_start
    if free and (not locked or lock_user == user):
        free = False
        book_user = user
        book_chat_id = chat_id
        book_start = datetime.datetime.now()
        Timer(GAME_TIME, lambda: notify(chat_id) if book_user == user else None).start()
        return True
    else:
        return False


def lock():
    global queue, locked, lock_time, lock_user
    assert len(queue) == 0
    first_user, chat_id = queue.pop(0)
    locked = True
    lock_time = datetime.datetime.now()
    lock_user = first_user
    bot.send_message(chat_id, "Кикер освободился, беги играть! "
                              "У тебя и только у тебя есть возможность "
                              "занять стол в течение двух минут, "
                              "для этого нажми /book."
                              "Если ты не успеешь, то эта возможность "
                              "перейдет к следующему в очереди. "
                              "Если ты не хочешь занимать стол, то нажи /unlock, "
                              "чтобы не задерживать других людей в очереди")
    Timer(LOCK_WAIT, lambda: lock() if lock_user == first_user else None).start()


@bot.message_handler(commands=['check'])
def check(message):
    global free, book_user, locked
    text = ""
    if free and not locked:
        text = "Свободно. Не забудь нажать /book, когда займешь стол."
    else:
        text = u"Занято @"+\
               (book_user+" c "+book_start.strftime("%H:%M")
                if not locked
                else lock_user) + \
               ". " + \
               u"В очереди "+str(len(queue))+u" человек. " + \
               u"Чтобы встать в очередь, нажми /i_will_wait."
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['book'])
def book_command(message):
    if book(message.from_user.username, message.chat.id):
        bot.send_message(message.chat.id, "Успешно")
    else:
        bot.send_message(message.chat.id, "Не удалось")


@bot.message_handler(commands=["leave"])
def leave(message):
    global free
    if len(queue) > 0:
        lock()
        bot.send_message(message.chat.id, "")
    free = True
    bot.send_message(message.chat.id, "Спасибо, что вовремя отметил, что стол освободился!")


@bot.message_handler(commands=["i_will_wait"])
def add_to_queue(message):
    if len(queue) == 0:
        bot.send_message(message.chat.id, "Очередь пуста. Чтобы отметить, что вы заняли стол, нажмите /book.")
    pair = [message.from_user.username, message.chat.id]
    if pair in queue:
        bot.send_message(message.chat.id, "Вы уже в очереди, перед вами "+str(queue.index(pair))+" человек.")
    else:
        queue.append(pair)
        bot.send_message(message.chat.id, "Перед вами "+str(len(queue)-1)+" человек. "+ \
                         "Когда придет ваша очередь, вам придет уведомление")


@bot.message_handler(commands=["unlock"])
def unlock(message):
    global locked
    if message.from_user.username == lock_user:
        if len(queue) > 0:
            lock()
        else:
            locked = False
        bot.send_message(message.chat.id, "Спасибо, что освободил стол для других людей в очереди!")
    else:
        bot.send_message(message.chat.id, "На данный момент стол забронирован за другим человеком :(")


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(message.chat.id, "Привет, любитель кикера! Чтобы забронировать - нажми /book, "
                                      "чтобы проверить доступность стола - нажми /check, "
                                      "чтобы отметить, что стол свободен - нажми /leave.")

@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):
    print message.chat.id
    bot.send_message(message.chat.id, "ой, непонятно :(")

if __name__ == '__main__':
    bot.polling(none_stop=True)