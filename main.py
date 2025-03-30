import random, os
from dotenv import load_dotenv

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

from standart_words import get_random_words_right, get_others_words, conn_close, user_words_write, delete_words_from_tables

load_dotenv()

print('Start telegram bot "English_language_training"')

state_storage = StateMemoryStorage()
token_bot = os.getenv('TG_BOT_TOKEN')
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    user_write_words = State()
    word_for_delete = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = []
    translate, target_word = get_random_words_right()  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = get_others_words(target_word)  # брать из БД
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message): # удалить из БД
    cid = message.chat.id
    bot.send_message(cid, 'напиши пару слов на удаление - русское слово, английское слово')
    bot.set_state(message.from_user.id, MyStates.word_for_delete, cid)

@bot.message_handler(state=MyStates.word_for_delete)
def delete_word_from_user(message):
    cid = message.chat.id
    try:
        rus_word, en_word = map(str.strip, message.text.split(',', 1))
        delete_words_from_tables(rus_word, en_word)
        bot.send_message(cid, 'слова успешно удалены ✅')
    except (ValueError, IndexError):
        bot.send_message(cid, 'формат неверный, попробуй ещё раз через запятую')
    finally:
        bot.delete_state(message.from_user.id, cid)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, 'Напиши пару слов для добавления в следующем формате\n'
                          '"слово на русском", "слово на английском"')
    bot.set_state(message.from_user.id, MyStates.user_write_words, cid)     # сохранить в БД

@bot.message_handler(state=MyStates.user_write_words)
def add_new_word(message):
    cid = message.chat.id
    try:
        rus_word, en_word = map(str.strip, message.text.split(',', 1))
        if not (rus_word.isalpha() and en_word.isalpha()):
            raise ValueError
        user_words_write(rus_word, en_word)
        bot.send_message(cid, f"✅ Слова добавлены:\n🇷🇺 {rus_word} → 🇬🇧 {en_word}")
    except (ValueError, IndexError):

        bot.send_message(cid, "❌ Неверный формат! Попробуй еще раз:\n\"Дом, House\"")
        return
    finally:
        bot.delete_state(message.from_user.id, cid)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)

conn_close()