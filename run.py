# -*- coding: utf-8 -*-

import datetime
import telebot
from telebot import types
from threading import Timer
import pytz

from config import token, ADMIN_CHATS_ID

bot = telebot.TeleBot(token, threaded=False)

free = True
book_user = ""
book_chat_id = -1
book_start = None

wait_user = None
wait_user_booked = None

waiting_leave_chat_id = None

queue = []

MINUTE = 60
GAME_TIME = 30*MINUTE
GAME_REPEAT_TIME = 5*MINUTE
LOCK_WAIT = 2*MINUTE


def remind(chat_id):
    for i in range(6):
        Timer(GAME_REPEAT_TIME*i,
              lambda: bot.send_message(chat_id, "Ты еще играешь? Прошло уже больше"+\
                                       str(GAME_TIME / MINUTE) +
                                       " минут, другим тоже хочется... "
                                       "Чтобы отметить, что стол больше не занят, нажми /leave")
              if book_chat_id == chat_id else None).start()

    for admin in ADMIN_CHATS_ID:
        Timer(GAME_REPEAT_TIME*5, lambda: bot.send_message(admin, "Админ, у нас неприятности:(")
                                    if book_chat_id == chat_id else None).start()


def book(chat_id, user, time):
    global free, book_chat_id, book_user, book_start
    free = False
    book_chat_id = chat_id
    book_user = user
    book_start = time


def unbook(chat_id, send_message=True):
    global free, book_user, book_chat_id, book_start, wait_user, wait_user_booked
    if len(queue) > 0:
        first_user, first_chat_id = queue.pop(0)
        book(first_chat_id, first_user, datetime.datetime.now(pytz.timezone('Europe/Moscow')))
        bot.send_message(first_chat_id,
                         "Кикер освободился, беги играть! "
                         "У тебя и только у тебя есть возможность "
                         "занять стол в течение двух минут, "
                         "для этого нажми /book."
                         "Если ты не успеешь, то эта возможность "
                         "перейдет к следующему в очереди. "
                         "Если ты не хочешь занимать стол, то нажи /unlock, "
                         "чтобы не задерживать других людей в очереди")
        wait_user = first_user
        wait_user_booked = False
        Timer(LOCK_WAIT, lambda: unbook(first_chat_id, send_message=False) if not wait_user_booked else None).start()
    else:
        free = True
        book_user = None
        book_chat_id = None
        book_start = None

    if send_message:
        bot.send_message(chat_id, "Спасибо, что вовремя отметил, что стол освободился!")


@bot.message_handler(commands=['check'])
def check(message):
    global free, book_user
    text = ""
    if free:
        text = "Свободно. Не забудь нажать /book, когда займешь стол."
    else:
        text = u"Занято @"+book_user+" c "+book_start.strftime("%H:%M")+". " + \
               u"В очереди "+str(len(queue))+u" человек. " + \
               u"Чтобы встать в очередь, нажми /i_will_wait."
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['book'])
def book_command(message):
    global free, book_user, book_chat_id, book_start, wait_user_booked
    if free:
        book(message.chat.id, message.from_user.username, datetime.datetime.now(pytz.timezone('Europe/Moscow')))
        Timer(GAME_TIME, lambda: remind(message.chat.id) if book_user == message.from_user.username else None).start()
        bot.send_message(message.chat.id, "Успешно")
    else:
        if wait_user == message.from_user.username:
            wait_user_booked = True
            bot.send_message(message.chat.id, "Молодец, беги играть!")
        else:
            bot.send_message(message.chat.id, u"Не удалось, стол занят. "+\
                                              u"В очереди "+str(len(queue))+u" человек. Чтобы встать в очередь, нажми /i_will_wait.")
    print "CMD: book"
    print "free:", free, "book_user:", book_user, "book_chat_id:", book_chat_id


@bot.message_handler(commands=["leave"])
def leave(message):
    global free, waiting_leave_chat_id, book_user
    if free:
        bot.send_message(message.chat.id, "В данный момент стол свободен.")
    else:
        if book_user != message.from_user.username:
            keyboard = types.InlineKeyboardMarkup()
            callback_button = types.InlineKeyboardButton(text="Да", callback_data="leave_for_sure")
            keyboard.add(callback_button)
            bot.send_message(message.chat.id, u"Ты хочешь освободить стол, "+\
                                              u"который занят в данный момент @"+\
                                              book_user+u", ты уверен?", reply_markup=keyboard)
            waiting_leave_chat_id = message.chat.id
        else:
            unbook(message.chat.id)
    print "CMD: leave"
    print "free: ", free, " book_user: ", book_user 




@bot.callback_query_handler(func=lambda call: True)
def test_callback(call):
    global book_chat_id, waiting_leave_chat_id
    if call.data == "leave_for_sure":
        if call.message.chat.id == waiting_leave_chat_id:
            book_chat_id_rem = book_chat_id
            unbook(call.message.chat.id)
            print "book chat id:", book_chat_id
            bot.send_message(book_chat_id_rem, u"Вашу бронь отменили. "+\
                                           u"Вероятно, вы забыли вовремя отметить доступность стола. Не надо так :(")
            waiting_leave_chat_id = None
        else:
            bot.send_message(call.message.chat.id, "Уже отменено")

@bot.message_handler(commands=["i_will_wait"])
def add_to_queue(message):
    global free
    if free and len(queue) == 0:
        bot.send_message(message.chat.id, "Очередь пуста. Чтобы отметить, что вы заняли стол, нажмите /book.")
        return

    pair = [message.from_user.username, message.chat.id]
    if pair in queue:
        bot.send_message(message.chat.id, "Вы уже в очереди, перед вами "+str(queue.index(pair))+" человек.")
    else:
        if book_user != message.from_user.username:
            queue.append(pair)
            bot.send_message(message.chat.id, "Перед вами "+str(len(queue)-1)+" человек. "+ \
                             "Когда придет ваша очередь, вам придет уведомление")
        else:
            bot.send_message(message.chat.id, "Вы уже заняли стол, вам не нужно вставать очередь, играйте на здровье!")


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
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print e
