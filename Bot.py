import os
import sqlite3
import pybase64

import telebot
from telebot import types

import Config
from KandinskyAPI import KandinskyAPI
from YandexArtAPI import YandexArtAPI


# Создание базы данных и таблиц с запросами пользователей
def create_data_base():
    connect = sqlite3.connect('kandinsky_generation_db.db')
    cursor = connect.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        chat_id TEXT NOT NULL
        )
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS API_PROMPTS (
        id INTEGER PRIMARY KEY,
        prompt TEXT,
        image TEXT,
        user TEXT NOT NULL,
        FOREIGN KEY (user) REFERENCES STAFF (Users_chat_id)
        )
        ''')
    connect.commit()
    connect.close()


# Добавление новых пользователей в таблицу пользователей
def insert_user_to_db(username, chat_id):
    db_connect = sqlite3.connect('kandinsky_generation_db.db')
    db_cursor = db_connect.cursor()
    db_cursor.execute(f'SELECT username FROM Users WHERE chat_id = {chat_id}')
    user = db_cursor.fetchall()
    if not user:
        db_cursor.execute('INSERT INTO Users (username, chat_id) VALUES (?, ?)', (username, chat_id))
        db_connect.commit()
    db_connect.close()
    
    
# Добавление ответов от API на запросы пользователей
def insert_response_to_db(prompt, str_image, chat_id):
    db_connect = sqlite3.connect('kandinsky_generation_db.db')
    db_cursor = db_connect.cursor()
    db_cursor.execute('INSERT INTO API_PROMPTS (prompt, image, user) VALUES (?, ?, ?)',
                      (prompt, str_image,
                       f'{chat_id}'))
    db_connect.commit()
    db_connect.close()
    
    
# Определение глобальных переменных
bot = telebot.TeleBot(Config.BOT_TOKEN)
generation_model = {'model': ''}
kandinskyAPI = KandinskyAPI()
yaAPI = YandexArtAPI()
create_data_base()


# Функция отслеживания команды /start
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    username = message.from_user.username
    if not username:
        username = f'user_{message.chat.id}'
    if not os.path.isdir('Generated_images'):
        os.mkdir(f'Generated_images')
    if not os.path.isdir(f'Generated_images/{username}_{message.chat.id}'):
        os.mkdir(f'Generated_images/{username}_{message.chat.id}')
        
    insert_user_to_db(username, message.chat.id)

    text = 'Добро пожаловать!\nНапишу картину по вашему запросу'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row(types.KeyboardButton('Кандинский'), types.KeyboardButton('Другая русская нейросеть'))
    bot.send_message(message.chat.id, text, reply_markup=markup)


# Kandinsky generation handlers
# Установка стиля генерации
def set_style_images(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for style in kandinskyAPI.styles:
            btn = types.KeyboardButton(style['title'])
            markup.add(btn)
        bot.send_message(message.chat.id, 'В каком стиле будем рисовать?', reply_markup=markup)
        bot.register_next_step_handler(message, set_resolution)


# установка разрешения готового изображения
def set_resolution(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        for st in kandinskyAPI.styles:
            if message.text == st['title']:
                kandinskyAPI.style = st
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(types.KeyboardButton('512x512'), types.KeyboardButton('1024x1024'))
        markup.row(types.KeyboardButton('1024x682'), types.KeyboardButton('682x1024'))
        bot.send_message(message.chat.id, 'Что с размером?', reply_markup=markup)
        bot.register_next_step_handler(message, set_prompt)


# установка запроса для генерации
def set_prompt(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        if message.text == '512x512':
            kandinskyAPI.set_size(512, 512)
        elif message.text == '1024x1024':
            kandinskyAPI.set_size(1024, 1024)
        elif message.text == '1024x682':
            kandinskyAPI.set_size(1024, 682)
        elif message.text == '682x1024':
            kandinskyAPI.set_size(682, 1024)
        bot.send_message(message.chat.id, 'Что должно быть на картине?')
        bot.register_next_step_handler(message, set_negative_prompt)


# Установка негативного промпта или что не нужно использовать при генерации
def set_negative_prompt(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        # api.prompt = message.text
        kandinskyAPI.set_query(message.text)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(types.KeyboardButton('Использовать все!'))
        bot.send_message(message.chat.id, 'Что не исопльзовать при генерации(яркие цвета)?', reply_markup=markup)
        bot.register_next_step_handler(message, generate_image)


# Отправка запроса на генерацию изображения
def generate_image(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        bot.send_message(message.chat.id, 'Пишем картину, скоро будет готова')
        if message.text == 'Использовать все!':
            kandinskyAPI.set_negative_prompt('')
        else:
            kandinskyAPI.set_negative_prompt(message.text)
        images = kandinskyAPI.generate()
        if images == 'error':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'))
            bot.send_message(message.chat.id, 'Попробуйте заново с другим запросом?',
                             reply_markup=markup)
            return
        else:
            image_data = pybase64.b64decode(images[0])
            username = message.from_user.username
            if not username:
                username = f'user_{message.chat.id}'
            photo = open(f'Generated_images/{username}_{message.chat.id}/generatedImage{message.message_id}.jpeg', 
                         'wb+')
            photo.write(image_data)
            photo.seek(0, 0)
            bot.send_photo(message.chat.id, photo)
            photo.close()
            bot.clear_step_handler_by_chat_id(message.chat.id)

            insert_response_to_db(kandinskyAPI.query, images[0], message.chat.id)

            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
            bot.send_message(message.chat.id, 'Повторим("ещё одну?"), дополним запрос или напишем другую("/start")?', 
                             reply_markup=markup)


# Ya generation handlers
# Установка соотношения сторон готового изображения
def set_yandex_ratio(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        yaAPI.update_iamtoken()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(types.KeyboardButton('1x1'), types.KeyboardButton('2x1'))
        markup.row(types.KeyboardButton('1x2'), types.KeyboardButton('3x4'))
        bot.send_message(message.chat.id, 'Выберите соотношение сторон', reply_markup=markup)
        bot.register_next_step_handler(message, set_yandex_prompt)


# Установка запроса для генерации
def set_yandex_prompt(message):

    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
        return 
    else:
        if message.text == '1x1':
            yaAPI.set_ratio(1, 1)
        elif message.text == '2x1':
            yaAPI.set_ratio(2, 1)
        elif message.text == '1x2':
            yaAPI.set_ratio(1, 2)
        elif message.text == '3x4':
            yaAPI.set_ratio(3, 4)
        bot.send_message(message.chat.id, 'Введите запрос. Чем подробнее запрос, тем лучше будет картина')
        bot.register_next_step_handler(message, yandex_generate)


# Отправка запроса генерации изображения
def yandex_generate(message):
    if message.text == '/start':
        bot.clear_step_handler_by_chat_id(message.chat.id)
        start_handler(message)
    else:
        bot.send_message(message.chat.id, 'Генерим картинку, скоро будет готова')
        yaAPI.seed_update()
        yaAPI.set_text(message.text)
        image = yaAPI.generate()
        if image == 'error':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'))
            bot.send_message(message.chat.id, 'Попробуйте заново с другим запросом?',
                             reply_markup=markup)
            return
        else:
            image_data = pybase64.b64decode(image)
            username = message.from_user.username
            if not username:
                username = f'user_{message.chat.id}'
            photo = open(f'Generated_images/{username}_{message.chat.id}/generatedImage{message.message_id}.jpeg', 
                         'wb+')
            photo.write(image_data)
            photo.seek(0, 0)
            bot.send_photo(message.chat.id, photo)
            photo.close()
            bot.clear_step_handler_by_chat_id(message.chat.id)

            insert_response_to_db(yaAPI.text, image, message.chat.id)

            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
            bot.send_message(message.chat.id, 'Повторим("ещё одну?"), дополним запрос или напишем другую("/start")?',
                             reply_markup=markup)


# Обработчик введенных текстов
@bot.message_handler(content_types=['text'])
def text_hendler(message):
    # Для повторения генерации по тому же запросу
    if (message.text == 'Еще одну') and (generation_model['model'] != ''):
        bot.send_message(message.chat.id, 'Пишем картину, скоро будет готова')
        image = ''
        if generation_model['model'] == 'Kandinsky':
            images = kandinskyAPI.generate()
            image = images[0]
        elif generation_model['model'] == 'YandexArt':
            yaAPI.seed_update()
            image = yaAPI.generate()
        if image == 'error':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'))
            bot.send_message(message.chat.id, 'Попробуйте заново с другим запросом?',
                             reply_markup=markup)
            return
        else:
            image_data = pybase64.b64decode(image)
            username = message.from_user.username
            if not username:
                username = f'user_{message.chat.id}'
            photo = open(f'Generated_images/{username}_{message.chat.id}/generatedImage{message.message_id}.jpeg',
                         'wb+')
            photo.write(image_data)
            photo.seek(0, 0)
            bot.send_photo(message.chat.id, photo)
            photo.close()

            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup = types.ReplyKeyboardMarkup()
            markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
            bot.send_message(message.chat.id, 'Повторим("ещё одну?"), дополним запрос или напишем другую("/start")?',
                             reply_markup=markup)
        return
    # для определения модели через которую будет происходить генерация
    elif message.text == 'Кандинский':
        generation_model['model'] = 'Kandinsky'
        set_style_images(message)
        return
    elif message.text == 'Другая русская нейросеть':
        generation_model['model'] = 'YandexArt'
        set_yandex_ratio(message)
        return
    # Для дополнения предыдущего запроса генерации новым промптом
    if generation_model['model'] == 'Kandinsky':
        if (kandinskyAPI.query != '') and (len(kandinskyAPI.query) + len(message.text) < 1000):
            kandinskyAPI.query += ', ' + message.text
            bot.send_message(message.chat.id, 'Пишем картину, скоро будет готова')
            images = kandinskyAPI.generate()
            if images == 'error':
                bot.clear_step_handler_by_chat_id(message.chat.id)
                markup = types.ReplyKeyboardMarkup()
                markup.row(types.KeyboardButton('/start'))
                bot.send_message(message.chat.id, 'Попробуйте заново с другим запросом?',
                                 reply_markup=markup)
                return
            else:
                image_data = pybase64.b64decode(images[0])
                username = message.from_user.username
                if not username:
                    username = f'user_{message.chat.id}'
                photo = open(f'Generated_images/{username}_{message.chat.id}/generatedImage{message.message_id}.jpeg',
                             'wb+')
                photo.write(image_data)
                photo.seek(0, 0)
                bot.send_photo(message.chat.id, photo)
                photo.close()
                
                insert_response_to_db(kandinskyAPI.query, images[0], message.chat.id)

                bot.clear_step_handler_by_chat_id(message.chat.id)
                markup = types.ReplyKeyboardMarkup()
                markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
                bot.send_message(message.chat.id, 
                                 'Повторим("ещё одну?"), дополним запрос или напишем другую("/start")?',
                                 reply_markup=markup)
            return
        # обработчик превышения допустимого количества символов в запросе
        elif (kandinskyAPI.query != '') and (len(message.text) >= 1000):
            markup = types.ReplyKeyboardMarkup()
            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
            bot.send_message(message.chat.id, 
                             'Cлишком большой запрос, придется начать сначала, или повторить', 
                             reply_markup=markup)
            return
    # Для дополнения предыдущего запроса генерации новым промптом
    elif generation_model['model'] == 'YandexArt':
        if (yaAPI.text != '') and (len(message.text)+len(yaAPI.text) <= 500):
            bot.send_message(message.chat.id, 'Генерим картинку, скоро будет готова')
            yaAPI.seed_update()
            yaAPI.text += f' {message.text}'
            image = yaAPI.generate()
            if image == 'error':
                bot.clear_step_handler_by_chat_id(message.chat.id)
                markup = types.ReplyKeyboardMarkup()
                markup.row(types.KeyboardButton('/start'))
                bot.send_message(message.chat.id, 'Попробуйте заново с другим запросом?',
                                 reply_markup=markup)
                return
            else:
                image_data = pybase64.b64decode(image)
                username = message.from_user.username
                if not username:
                    username = f'user_{message.chat.id}'
                photo = open(f'Generated_images/{username}_{message.chat.id}/generatedImage{message.message_id}.jpeg',
                             'wb+')
                photo.write(image_data)
                photo.seek(0, 0)
                bot.send_photo(message.chat.id, photo)
                photo.close()
                
                insert_response_to_db(yaAPI.text, image, message.chat.id)

                bot.clear_step_handler_by_chat_id(message.chat.id)
                markup = types.ReplyKeyboardMarkup()
                markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
                bot.send_message(message.chat.id, 
                                 'Повторим("ещё одну?"), дополним запрос или напишем другую("/start")?', 
                                 reply_markup=markup)
                return
        # обработчик превышения допустимого количества символов в запросе
        elif (yaAPI.text != '') and (len(message.text)+len(yaAPI.text) > 500):
            markup = types.ReplyKeyboardMarkup()
            bot.clear_step_handler_by_chat_id(message.chat.id)
            markup.row(types.KeyboardButton('/start'), types.KeyboardButton('Еще одну'))
            bot.send_message(message.chat.id,
                             'Cлишком большой запрос, придется начать сначала!, или повторить',
                             reply_markup=markup)
            return 
