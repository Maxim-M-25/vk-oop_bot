# -*- coding: utf-8 -*-
"""Этот файл является связующим звеном между управляющим
файлом(server_manager.py) и файлом логики(обработчиком(commander.py))
Его суть в следующем: Этот файл запускается файлом server_manager.py и принимает запросы из вк,
затем он перенаправляет этот запрос в обработчик(commander.py) и тот уже решает, что делать, и
возвращает текст ответа + клавиатуру(в случае если клавиатура не требуется, вернётся только текст,
а клавиатура будет = None), после чего, на основе текста, который вернул обработчик(commander.py), этот файл
выполнит либо отправку сообщения которое пришло из commander.py, либо, если пришел текст, означающий действие,
то выполнит действие указанное в этом тексте. Например: commander.py вернул 'hello' - server.py просто
отправит это сообщение либо в беседу, либо в личные сообщения группы. Пример 2: из commander.py пришел ответ 'off' -
server.py вернёт этот текст в server_manager.py, и тот остановит бота. Пример 3: из commander.py пришел
текст 'get_logs' - server.py запустит функцию get_document, и она вышлет логи на указанный id в вк.
!!!ВАЖНО!!! Бот работает по принципу:
1.Слушаю longpoll канал
2.пришло сообщение
3.извлекаю из базы данных информацию о пользователе который прислал это сообщение(далее такой пользователь будет
называться 'текущий пользователь' ('current user')
4.передаю на обработку в commander.py - на основе его 'ответа' отправляю сообщение или выполняю действие пришедшее
    из ответа
5.Возвращаюсь этап 1"""

#Импорт библиотек
import vk_api.vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import time
import logging
import traceback
import requests

#Подключаем классы из других файлов:
#Подключили класс для работы с базой данных
from db import DataBase

#Подключили класс для обработки команд
from commander import Handler

#Подключили класс для загрузки клавиатур бота
from keyboard import Keyboards

#Подключили класс для работы с режимом  отладки(о нём будет рассказано в файле debug_mode.py
from debug_mode import Debug

class Server:
    def __init__(self, api_token, group_id):
        """Назначаем атрибуты, необходимые для работы с vk api при создании объекта 'server1' по этому классу"""

        # Для Long Poll
        self.vk = vk_api.VkApi(token=api_token)

        # Для использования Long Poll API
        self.long_poll = VkBotLongPoll(self.vk, group_id)

        # Для вызова методов vk_api
        self.vk_api = self.vk.get_api()

        #Здесь храним токен сообщества, он нам потребуется при обработки исключения requests.exceptions.ReadTimeout
        self.vk_token = api_token

        #По этим же причинам храним id сообщества, с которым работаем
        self.group_id = group_id

        #В этих атрибутах хранятся данные о текущем пользователе:
        #Его id в вк
        self.from_id = 0

        #peer_id с которого пришло сообщение
        self.peer_id = 0

        #Текст из сообщения
        self.msg = ''

        #Имя пользователя в вк
        self.user_name = ''

        #Фамилия пользователя в вк
        self.user_last_name = ''

        #Роль пользователя
        self.user_role = ''

        #id владельца бота
        self.ROOT_owner_id = 000000000 #'000000000 замените id владельца(нужно передать тип данных int(integer))'

        #Через этот атрибут выполняются методы для работы с базой данных
        self.db = DataBase('dbs/main_db.db')

        #Через этот атрибут выполняются методы для работы с режимом отладки
        self.debug = Debug('dbs/main_db.db')

        #Через этот атрибут обращаемся к методам из commander.py
        self.handler = Handler(self.group_id, self.ROOT_owner_id)

        #Через этот атрибут обращаемся к методу для получения клавиатуры бота
        self.kb = Keyboards()

        #В этих атрибутах хранятся клавиатуры, для каждой роли своя клавиатура
        self.ROOT_kb = self.kb.get_keyboard('root_kb')
        self.ADMIN_kb = self.kb.get_keyboard('admin_kb')
        self.Editor_kb = self.kb.get_keyboard('editor_kb')
        self.user_kb = self.kb.get_keyboard('user_kb')

        #Это пустая клавиатура, она доступна абсолютно всем, и высылается когда текущий
        #пользователь хочет скрыть клавиатуру
        self.empty_kb = self.kb.get_keyboard('empty_kb')

        #Флаг, показывает, выдан ли боту мут: True - выдан, False - не выдан
        self.bot_mute = False

        #Этот атрибут хранит предупреждение, которое высылается текущему пользователю,
        #когда бот находится в режиме отладки. !!! На пользователей с ролью 'ROOT' оно не действует
        self.debug_warn = 'В данный момент бот находится в режиме отладки и не может ' \
                          'отвечать на команды, когда отладка закончится, бот ' \
                          'продолжит функционировать. Приносим извинения за ' \
                          'предоставленные неудобства'

        #Флаг, показывает, находится ли бот в режиме отладки: True - находится, False - не находится
        self.debug_mode = False

        logging.info('Запуск файла бота...')

    def get_user_name(self):
        """
        Эта функция узнаёт имя текущего пользователя по его id в вк
        :return: user_name
        :rtype: str
        """
        result = self.vk.method('users.get', {'user_ids': self.from_id})
        user_name = result[0]['first_name']
        return user_name

    def get_user_last_name(self):
        """
        Эта функция узнаёт фамилию текущего пользователя по его id в вк
        :return: user_name
        :rtype: str
        """
        result = self.vk.method('users.get', {'user_ids': self.from_id})
        last_name = result[0]['last_name']
        return last_name

    def get_document(self, path, type='doc', title='Пустой заголовок'):
        """
        Эта функция загружает указанный документ на сервера вк. По полученной строке,
        файл можно прикрепить только к личному сообщению
        :param path: Путь до документа
        :param type: Тип вложения - по умолчанию doc - документ
        :param title: Заголовок документа
        :return: Строка, которая помещается в список attachment при отправке сообщения
        """
        upload_url = self.vk_api.docs.getMessagesUploadServer(type=type, peer_id=self.peer_id)['upload_url']
        response = requests.post(upload_url, files={'file': open(path, 'rb')}).json()
        result = response['file']
        save = self.vk.method('docs.save', {'file': result, 'title': title})
        owner_id = save['doc']['owner_id']
        media_id = save['doc']['id']
        document = f'{type}{owner_id}_{media_id}'
        return document

    def download_doc(self, url, name='error_file', db=False):
        """
        Эта функция скачивает документ из личного сообщения в вк
        :param url: url адрес файла
        :param name: Имя, под которым будет сохранён файл
        :param db: Флаг, True - Скачается файл в формате .db, False - файл будет сохранён как .txt
        :return: None
        """
        self.message_distributor('Скачивание файла...')
        logging.info(f'Скачивание файла | имя файла: {name} | db {str(db)} |id: {self.from_id} | peer_id {self.peer_id} | '
                     f'ник: {self.user_name} {self.user_last_name} | режим: {self.user_mode} | права: {self.user_role}')
        try:
            response = requests.get(url)
            if db:
                with open('db.db', 'wb') as dbf:
                    dbf.write(response.content)
            else:
                with open(f'{name}.txt', 'wb') as f:
                    f.write(response.content)
            self.message_distributor('Файл скачан!')
        except Exception:
            dwld_file_error_msg = traceback.format_exc()
            logging.error(f'Ошибка при загрузке файла: {dwld_file_error_msg}')

    def check_user_in_db(self):
        """
        Эта функция проверяет наличие текущего пользователя в базе данных, по его id в вк
        :return: Список найден пользователей по id в вк текущего пользователя
        """
        sql = 'SELECT user_id FROM users_info WHERE user_id = %d' % self.from_id
        result = self.db.select_with_fetchone(sql)
        if result is None:
            return result
        result = result[1:-2:]
        return result

    def add_user_in_db(self):
        """
        Эта функция добавляет пользователя в базу данных, будет добавлен пользователь с ролью 'user',
        режимом 'default' и последним сообщением(столбец user_last_message в базе данных) = 'None'
        :return: True - пользователь добавлен, True в этой версии нигде не используется
        """
        sql = "INSERT INTO users_info (user_id, user_name, user_last_name) VALUES (%d , '%s', '%s')" % \
              (self.from_id, self.user_name, self.user_last_name)
        self.db.query(sql)
        return True

    def send_msg(self, peer_id, message, attachment: list = [], keyboard=None, spam=False):
        """
        Эта функция отправляет сообщение пользователю в вк
        :param peer_id: peer_id на который нужно отправить сообщение, можно передать обычный id пользователя,
            но это не тестировалось!
        :param message: Текст сообщения
        :param attachment: Список медиа вложений
        :param keyboard: Клавиатура бота, высылается текущему пользователю,
            !!!При отправке в беседу клавиатура станет у всех одинаковой!!!
        :param spam: Флаг, True - в лог файл запишется, что функция вызвана рассылкой,
            False - обычная отправка сообщения
        :return: None
        """
        try:
            self.vk.method('messages.send', {'peer_id': peer_id, 'message': message, 'keyboard': keyboard,
                                             'attachment': attachment, 'random_id': 0})
            if not spam:
                logging.info(f'id: {self.from_id} | peer_id: {self.peer_id} | ник: {self.user_name} '
                             f'{self.user_last_name} | роль: {self.user_role} | режим: {self.user_mode} | '
                             f'Функция send_message отправила '
                             f'сообщение: {message}')
            else:
                logging.info(f'id: {self.from_id} | spam_id: {self.peer_id} | Функция send_spam отправила '
                             f'сообщение: {message}')
        except Exception:
            error_send_msg = traceback.format_exc()
            logging.error(f'Функия send_msg() не отправила сообщение, т.к. произошла ошибка: {error_send_msg}')

    def error_report(self, msg):
        """
        Эта функция отправляет сообщения только владельцу бота, вызывается в основном из файла server_manager.py
        :param msg: Текст сообщения
        :return: None
        """
        self.vk.method('messages.send', {'peer_id': self.ROOT_owner_id, 'message': msg, 'random_id': 0})

    def message_distributor(self, response_text = 'Пустой текст', response_kb = None, attachment: list = [], user_id = 0, peer_id = 0):
        """
        Эта функция решает куда будет отправлено сообщение и с каким текстом, если входящее сообщение из беседы,
            то ответ на него будет отправлен в беседу, с упоминанием изначального отправителя
        :param response_text: Текст который будет отправлен
        :param response_kb: Клавиатура которая будет отправлена
        :param attachment: Список вложений
        :param user_id: если передан - отправка идёт по id текущего пользователя
        :param peer_id: если передан - отправка идёт по peer_id
        !!!Если переданы и id и peer_id - то пойдёт обычная отправка, и если id текущего пользователя = peer_id,
             то отправка идёт в личные сообщения группы
        :return:
        """
        if user_id != 0:
            self.send_msg(user_id, response_text,
                          keyboard=self.determine_keyboard(response_kb), attachment=attachment)
        elif peer_id != 0:
            self.send_msg(peer_id, response_text,
                          keyboard=self.determine_keyboard(response_kb), attachment=attachment)
        else:
            if self.from_id == self.peer_id:
                self.send_msg(self.from_id, response_text,
                              keyboard=self.determine_keyboard(response_kb), attachment=attachment)
            else:
                self.send_msg(self.peer_id, self.get_mention(response_text),
                              keyboard=self.determine_keyboard(response_kb), attachment=attachment)


    def get_user_data(self):
        """
        Эта функция вытягивает информацию о текущем пользователе из базы данных, по id в вк текущего пользователя.
        Принцып работы: Сначала получается информация о пользователе из базы данных(result), затем,
        в цикле for, собирается словарь data_array. Это работает так: Функция берёт значение по
        индексу i(индекс обновляется на каждой итерации цикла) и присоединяет к нему элемент по этому же индексу из keys.
        Таким образом, мы склеиваем значения из ячеек(они хранятся в result) с именем столбца(они хранятся в списке
        keys) из базы данных
        :return: Словарь с информацией о пользователе, вида: {'Имя столбца из БД' : 'Значение из ячейки в этом столбце'}
        """
        sql = 'SELECT * FROM users_info WHERE user_id = "%s"' % self.from_id
        result = self.db.select_with_fetchone(sql)
        keys = ['id', 'user_id', 'user_name', 'user_last_name', 'user_mode', 'user_role', 'user_last_message']
        data_array = {}
        i = 0
        for key in keys:
            data_array.update({key: result[i]})
            i += 1
        return data_array

    def send_spam(self):
        """
        Эта функция рассылает сообщения всем пользователям, которые есть в базе данных, при условии, что их id в вк
        является корректным и пользователь разрешил сообществу отправлять себе сообщения. В сообщение рассылки будет
        подставлена информация о инициализаторе рассылки(текущий пользователь)
        :return: True - рассылка выполнена, True в этой версии нигде не используется
        """
        logging.warning(f'Запущена рассылка | from_id: {self.from_id}')
        sql = "SELECT user_id FROM users_info"
        users_ids = [x[0] for x in self.db.select_with_fetchall(sql)]
        spam_sql = "SELECT user_last_message FROM users_info WHERE user_id = %d" % self.from_id
        spam_msg = str(self.db.select_with_fetchone(spam_sql))
        spam_msg = spam_msg[2:-3:]
        if spam_msg == '':
            return self.send_msg(self.from_id, 'Сообщение для рассылки не может быть пустым!')
        for id in users_ids:
            try:
                if id < 0:
                    continue
                self.send_msg(id, f'Рассылка создана: {self.user_name} {self.user_last_name}\n\n{spam_msg}', spam=True)
                time.sleep(1)
            except Exception:
                spam_error_msg = traceback.format_exc()
                logging.error(f'Произошла ошибка при рассылке: {spam_error_msg}')
                time.sleep(1)
        sql_rewrite_last_msg = "UPDATE users_info SET user_last_message = 'ожидание сообщения' WHERE user_id = %d" % \
                               self.from_id
        self.db.query(sql_rewrite_last_msg)
        self.send_msg(self.from_id, 'Разослано!')
        logging.warning('Рассылка выполнилась!')
        return True

    def get_mention(self, message):
        """
        Генерирует упоминание текущего пользователя и подставляет его в сообщение.
        Используется при отправке сообщений в беседу
        :return: Строка с сообщением + упоминание текущего пользователя
        """
        msg = f'[id{self.from_id}|{self.user_name} {self.user_last_name}],\n{message}'
        return msg

    def get_user_mode(self, user_id):
        """
        Эта функция вытягивает информацию о режиме текущего пользователя из базы данных
        :param user_id: id в вк, по которому нужно получить информацию
        :return: Возвращает режим текущего пользователя
        """
        sql = "SELECT user_mode FROM users_info WHERE user_id = %d" % user_id
        user_mode = str(self.db.select_with_fetchone(sql))
        user_mode = user_mode[2:-3:]
        return user_mode

    def get_user_role(self, user_id):
        """
        Эта функция вытягивает информацию о роли текущего пользователя из базы данных
        :param user_id: id в вк, по которому нужно получить информацию
        :return: Возвращает роль текущего пользователя
        """
        sql = "SELECT user_role FROM users_info WHERE user_id = '%s'" % user_id
        result = str(self.db.select_with_fetchone(sql))
        result = result[2:-3:]
        return str(result)

    def get_last_message(self):
        """
        Эта функция вытягивает информацию о последнем сообщении(столбец user_last_message)
            текущего пользователя из базы данных
        :return: Возвращает последнее сообщение текущего пользователя
        """
        sql = "SELECT user_last_message FROM users_info WHERE user_id = %d" % self.from_id
        result = self.db.select_with_fetchone(sql)[0]
        return result

    def determine_keyboard(self, path):
        """
        Эта функция определяет клавиатуру, подставляемую в сообщение, в зависимости от роли текущего пользователя
        :param path: Имя клавиатуры
        :return: Вернёт клавиатуру, либо None(когда клавиатура не найдена)
        """
        if path == 'main_kb':
            if self.user_role == "user":
                return self.user_kb
            elif self.user_role == 'Editor':
                return self.Editor_kb
            elif self.user_role == 'ADMIN':
                return self.ADMIN_kb
            elif self.user_role == 'ROOT':
                return self.ROOT_kb
            else:
                return
        elif path == 'empty_kb':
            return self.empty_kb
        else:
            return

    def start(self):
        """
        Это основной цикл бота, сюда попадают сообщения и выполняются их отправка обратно в вк, либо выполняется
            действие полученное от commander.py
        :return: Возвращает в файл server_manager.py команду от commander.py
        """
        logging.info('Запущен основной цикл')
        try:
            # print('Запуск основного цикла')
            #Слушаем longpoll канал( в event попадёт событие)
            for event in self.long_poll.listen():
                #Если событие - новое сообщение:
                if event.type == VkBotEventType.MESSAGE_NEW:
                    #Извлекаем данные о текущем пользователе в соответствующие атрибуты
                    self.from_id = event.obj['message']['from_id']
                    self.peer_id = event.obj['message']['peer_id']
                    self.msg = event.obj['message']['text']
                    # if self.msg == '/help':
                    #     self.message_distributor('Эта команда находится в разработке!')
                    #     continue
                    self.user_name = self.get_user_name()
                    self.user_last_name = self.get_user_last_name()
                    self.user_mode = self.get_user_mode(self.from_id)
                    self.user_role = self.get_user_role(self.from_id)
                    self.debug_mode = self.debug.check_debug()
                    self.user_last_message = self.get_last_message()
                    logging.info(f'Входящий запрос | from_id: {self.from_id} | peer_id: {self.peer_id} | '
                                 f'ник: {self.user_name} '
                                 f'{self.user_last_name} | роль: {self.user_role} | режим: {self.user_mode} | '
                                 f'сообщение: {self.msg}')
                    #Если это команды для обновления файлов бота:
                    if self.msg.lower() == 'group_server' or self.msg.lower() == 'commander' or \
                            self.msg.lower() == 'group_db' or self.msg.lower() == 'db':
                        #Приводим текст сообщения к нижнему регистру
                        self.msg = self.msg.lower()
                        #Если сообщение пришло с id владельца
                        if self.from_id == self.ROOT_owner_id:
                            #Забираем в self.attach список вложений из сообщения
                            self.attch = event.obj['message']['attachments']
                            #Если количество сообщений не равно 1 - высылаем предупреждение, что передан не 1 документ
                            if len(self.attch) != 1:
                                self.message_distributor(f'Должен быть прикреплён ровно 1 документ!\n'
                                                         f'Прикреплёно {len(self.attch)} документов!')
                                continue
                            #Иначе:
                            else:
                                #В переменную url извлекаем url прикреплённого документа
                                url = self.attch[0]['doc']['url']
                                #Если в сообщении не содержит db(означает что нужно скачать файл в формате .db)
                                if self.msg != 'db':
                                    #Скачиваем файл в формате .txt
                                    self.download_doc(url, self.msg)
                                    continue
                                elif self.msg == 'db':
                                    #Скачиваем файл в формате .db
                                    self.download_doc(url, self.msg, db=True)
                        #Если не с id владельца, то высылаем предупреждение, что у текущего
                        #пользователя нет доступа к этой команде
                        else:
                            self.message_distributor('Ошибка доступа!')
                            continue
                    #Если сообщение начинается с этих имён команд, то не приводим текст к нижнему регистру
                    if self.msg.startswith('/sqlq') or self.msg.startswith('/sqlo') or self.msg.startswith('/sqla') or \
                            self.msg.startswith('/msg') or self.msg.startswith('/delete_file'):
                        pass
                    #Если пользователь находясь в режиме рыссылки отправил текст для рассылки,
                    #то сохраняем регистр символов
                    elif self.user_mode == 'рассылка' and self.user_last_message == 'ожидание сообщения':
                        pass
                    #Иначе, приводим текст сообщения в нижний регистр
                    else:
                        self.msg = self.msg.lower()
                    #Проверяем, есть ли текущий пользователь в базе данных
                    if self.check_user_in_db() is None:
                        #Если нет - добавляем его в базу данных
                        self.add_user_in_db()
                    # print(self.msg)
                    # raise requests.exceptions.ReadTimeout
                    #Если эта команды для обновления - говорим что они доступны только владельцу бота
                    if self.msg.lower().startswith('/update_') and self.from_id != self.ROOT_owner_id:
                        self.message_distributor('Эта функция доступна только разработчикам!')
                        continue
                    #Передаём на обработку в commander.py данные из базы данных о текущем пользователе,
                    #и получившийся текст сообщения
                    response = self.handler.msg_handler(self.get_user_data(), self.msg)
                    #Если response = False - значит сообщение не команда, бот не реагирует на него
                    if response == False:
                        continue
                    #Если из commander.py пришел кортеж - значит передана клавиатура, и записываем текст с
                    #клавиатурой в соответствующие переменные
                    if isinstance(response, tuple):
                        # print('array')
                        response_text = response[0]
                        response_kb = response[1]
                    #Иначе - делаем клавиатуру равной None
                    else:
                        response_text = response
                        response_kb = None
                    #Если commander.py ответил 'off', передаём эту команду в server_manager.py
                    if response_text == 'off':
                        return 'off'
                    #Если пришла команда 'get_logs' - высылаем логи
                    if response_text == 'get_logs':
                        self.message_distributor(response_text='Логи',
                                                 attachment=self.get_document('bot_log_files/main_log.log',
                                                                              'doc', 'Лог_файл'))
                        continue
                    #Если пришла команда mute_false - устанавливаем флаг self.bot_mute равным False
                    elif response_text == 'mute_false':
                        self.bot_mute = False
                        self.message_distributor('Бот размучен!')
                        continue
                    #Если пришла команда mute_true - устанавливаем флаг self.bot_mute равным True
                    elif response_text == 'mute_true':
                        self.bot_mute = True
                        self.message_distributor('Бот замучен!')
                        continue
                    #Если пришла команда 'debug mod on' - включаем режим отладки
                    elif response_text == 'debug mod on':
                        self.send_msg(self.from_id, 'Режим отладки включен')
                        logging.warning(f'id: {self.from_id} | peer_id: {self.peer_id} |'
                                        f' ник: {self.user_name} {self.user_last_name} | права: {self.user_role} | режим: {self.user_mode}'
                                        f' | Режим отладки включен')
                        self.debug_mode = True
                        continue
                    #Если пришла команда 'debug mod off' - выключаем режим отладки
                    elif response_text == 'debug mod off':
                        self.send_msg(self.from_id, 'Режим отладки выключен')
                        logging.warning(f'id: {self.from_id} | peer_id: {self.peer_id} |'
                                        f' ник: {self.user_name} {self.user_last_name} | права: {self.user_role} | режим: {self.user_mode}'
                                        f' | Режим отладки выключен')
                        self.debug_mode = False
                        continue
                    #Если пришедший текст начинается с 'msg' - то выполняем отправку сообщения по переданным параметрам
                    elif response_text.startswith('msg'):
                        params = response_text.split('&')
                        id = int(params[1])
                        text = params[2]
                        self.send_msg(id, text)
                        continue
                    #Если сообщение начинается с 'restart&' - говорим server_manager.py перезапустить бота
                    elif response_text.startswith('restart&'):
                        params = response_text.split('&')
                        restart_message = params[1]
                        sql = "SELECT user_id FROM users_info WHERE user_role = 'ROOT' OR user_role = 'ADMIN'"
                        result = [x[0] for x in self.db.select_with_fetchall(sql)]
                        for i in result:
                            self.message_distributor(restart_message, user_id=i)
                            time.sleep(1)
                        return 'restart'
                    #Если сообщение начинается с 'update_module&' - запускаем обновление указанного модуля
                    elif response_text.startswith('update_module&'):
                        self.message_distributor('Запуск обновления...')
                        return response_text
                    #Если сообщение = 'update_db' - запускаем обновление базы данных
                    elif response_text == 'update_db':
                        self.message_distributor('База данных обновляется...')
                        self.db.disconnect()
                        return 'update_db'
                    #В других случаях:
                    else:
                        #Если бот в режиме отладки:
                        if self.debug_mode == 'True':
                            #Если роль текущего пользователя = ROOT - ничего не делаем
                            if self.user_role == 'ROOT':
                                continue
                            # Если ответ 'Невозможна смена режима' - говорим что нельзя сменить режим, т.к. бот на отладке
                            if response_text == 'Невозможна смена режима':
                                self.message_distributor(
                                    'Бот находится в режиме отладки, нельзя менять режим в этот момент')
                                continue
                            #Иначе, высылаем текст из self.debug_warn
                            self.message_distributor(self.debug_warn)
                        #Если боту не выдан мут или роль текущего пользователя - ROOT или сообщение пришло от владельца бота:
                        if self.bot_mute is False or self.user_role == 'ROOT' or self.from_id == self.ROOT_owner_id:
                            #Если ответ 'spam' - запускаем функцию рассылки
                            if response_text == 'spam':
                                self.send_spam()
                                continue
                    #Если боту выдан мут и роль текущего пользователя не = ROOT - ничего не делаем
                    if self.bot_mute and self.user_role != 'ROOT':
                        continue
                    #Высылаем сообщение
                    self.message_distributor(response_text, response_kb)

        except requests.exceptions.ReadTimeout:
            """Если время сессии истекла - переподключаемся и ждём 15 секунд"""
            del self.vk
            self.vk = vk_api.VkApi(token=self.vk_token)
            self.long_poll = VkBotLongPoll(self.vk, self.group_id)
            self.vk_api = self.vk.get_api()
            error_msg = traceback.format_exc()
            logging.error(f'Ошибка подключения: {error_msg}')
            time.sleep(15)
        except Exception:
            """Если случилась какая-то ошибка - записываем её в файл лога, и ждём 5 секунд"""
            error_msg = traceback.format_exc()
            # print(f'Произошла ошибка в файле бота:\n    {error_msg}\nПерезапуск...')
            logging.error(f'Произошла ошибка в файле бота: {error_msg}')
            logging.info('Перезапуск...')
            time.sleep(5)