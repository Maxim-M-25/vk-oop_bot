# -*- coding: utf-8 -*-
"""
Этот файл занимается 'сложной' обработкой команд, сюда приходит сообщение из server.py,
здесь оно обрабатывается, и возвращается обратно в server.py
"""

#Подключаем модули
import logging
import datetime
import os
import traceback

#Подключаем класс для работы с базой данных
from db import DataBase
#Подключаем класс для работы с режимом отладки
from debug_mode import Debug

class Handler:
    def __init__(self, group_id, ROOT_owner_id):
        self.user_id = 0
        self.peer_id = 0
        self.msg = ''

        #Через self.debug обращаемся к методам для работы с режимом отладки
        self.debug = Debug('dbs/main_db.db')
        #Через self.db обращаемся к методам для работы с базой данных
        self.db = DataBase('dbs/main_db.db')

        #Сюда кладём id сообщества, через которое работает бот
        self.group_id = group_id
        #Сюда кладём id владельца бота
        self.ROOT_owner_id = ROOT_owner_id

        #Эти атрибуты хранят информацию о уровне доступа для ролей, команд и режимов соответственно.
        #В каждом из ник лежит словарь, вида {'роль/команда/режим' : 'уровень доступа'}
        self.roles_info = self.get_roles()
        self.commands_info = self.get_commands()
        self.modes_info = self.get_modes()

    def get_roles(self):
        """
        Генерирует информацию о ролях для атрибута self.roles_info
        :return: словарь, вида: {'роль' : 'уровень доступа'}
        """
        sql = "SELECT * FROM roles"
        query = [x for x in self.db.select_with_fetchall(sql)]
        roles = {}
        for i in query:
            roles.update({i[0]: i[1]})
        return roles

    def get_commands(self):
        """
        Генерирует информацию о командах для атрибута self.commands_info
        :return: словарь, вида: {'команда' : 'уровень доступа'}
        """
        sql = "SELECT command_name, command_access FROM commands"
        query = [x for x in self.db.select_with_fetchall(sql)]
        commands = {}
        for i in query:
            commands.update({i[0]: i[1]})
        return commands

    def get_modes(self):
        """
        Генерирует информацию о режимах для атрибута self.modes_info
        :return: словарь, вида: {'режим' : 'уровень доступа'}
        """
        sql = "SELECT mode_name, mode_access FROM modes"
        query = [x for x in self.db.select_with_fetchall(sql)]
        mods = {}
        for i in query:
            mods.update({i[0]: i[1]})
        return mods

    def get_commands_and_mods(self):
        """
        Генерирует список команд и режимов для текущего пользователя на основе его роли
        :return: Сгенерированный список команд и режимов (str(string))
        """
        user_access = self.roles_info[self.user_role]
        c_sql = "SELECT * FROM commands WHERE command_access <= %d" % user_access
        с_query = [x for x in self.db.select_with_fetchall(c_sql)]
        m_sql = "SELECT * FROM modes WHERE mode_access <= %d" % user_access
        m_query = [x for x in self.db.select_with_fetchall(m_sql)]
        line = ''
        for i in с_query:
            line = line + f'– {i[0]}{i[1]}\n'
        line = line + '––––––––––––––––––––––––––––\n'
        for i in m_query:
            line = line + f'– {i[0]}{i[1]}\n'
        line = 'Доступные команды и режимы:\n\n' + line
        return line

    def get_profile(self):
        """
        Генерирует информацию о профиле текущего пользователя(Уровень доступа, текущий режим, Имя и фамилия в системе)
        :return: Сгенерированная строка(str(string)) с информацией о пользователе
        """
        line = f'Информация о профиле:\n\n– Уровень доступа: {self.user_role}\n– Текущий режим: {self.user_mode}' \
               f'\n– Имя в системе: {self.user_name}' \
               f'\n– Фамилия в системе: {self.user_last_name}\n\nСписок всех доступных команд: /help'
        return line

    def get_all_users(self):
        """
        Генерирует список, содержащий текущее состояние всех спользователей из таблицы users_info
        :return: Сгенерированный список (str(string))
        """
        sql = "SELECT * FROM users_info WHERE 1"
        result = [x for x in self.db.select_with_fetchall(sql)]
        line = ''
        for i in result:
            id = i[0]
            user_id = i[1]
            user_name = i[2]
            user_last_name = i[3]
            user_mode = i[4]
            user_role = i[5]
            user_last_message = i[6]
            line = line + f'{id} | {user_id} | {user_name} | {user_last_name} | {user_mode} | {user_role} | ' \
                          f'{user_last_message}\n'
        return line

    def sqlq(self):
        """
        Выполняет UPDATE, DELETE, INSERT запросы к базе данных
        :return: сообщение об выполнении запроса
        """
        sql = self.command_text
        try:
            self.db.query(sql)
            return 'Запрос выполнен!'
        except:
            return 'Ошибка при выполнении запроса!'

    def sqlo(self):
        """
        Выполняет SELECT запросы к базе данных, методом fetchone
        :return: сообщение об ошибке/результат выполнения запроса
        """
        try:
            sql = self.command_text
            result = [x for x in self.db.select_with_fetchone(sql)]
        except:
            return 'Ошибка при выполнении запроса!'
        return str(result)

    def sqla(self):
        """
        Выполняет SELECT запросы к базе данных, методом fetchall
        :return: сообщение об ошибке/результат выполнения запроса
        """
        try:
            sql = self.command_text
            result = [x for x in self.db.select_with_fetchall(sql)]
        except:
            return 'Ошибка при выполнении запроса!'
        return str(result)

    def say_hello(self):
        """
        Отправляет ответ на нажатие кнопки 'Начать' при старте диалога
        :return: вернёт сообщение 'Привет!' и имя клавиатуры для сообщение, в данном случае - main_kb
        """
        return 'Привет!', 'main_kb'

    def send_msg(self, param):
        """
        Генерирует строку, содержащую параметры для выполнения отправки сообщения по переданным тексту
        и id получателя
        :param param: строка вида: 'id назначения&текст сообщения'
        :return: строка, содержащая параметры для выполнения отправки сообщения по переданным тексту
        и id получателя
        """
        params = param.split('&')
        if len(params) != 2:
            return 'Команда некорректна!'
        id = params[0]
        try:
            id = int(id)
        except:
            return 'id не является числом!'
        text = params[1]
        line = f'msg&{id}&{text}'
        return line

    def check_spam(self):
        """
        Проверяет, есть ли в данный момент кто-то в режиме рассылки
        :return: True - есть, False - нет
        """
        sql = 'SELECT user_mode FROM users_info WHERE user_mode == "рассылка"'
        result = self.db.select_with_fetchall(sql)
        if result != []:
            return True
        return False

    def check_restart(self):
        """
        Проверяет, насколько давно был последний перезапуск. Если перезапуск был меньше 3 минут назад -
        запретит перезапуск сейчас
        :return: True - можно перезапускаться, False - перезапускаться нельзя
        """
        now = datetime.datetime.today()
        sql = "SELECT last_restart FROM restart_bot"
        result = self.db.select_with_fetchone(sql)
        try:
            last_restart = datetime.datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f')
        except:
            if result is None:
                add_sql = "INSERT INTO restart_bot VALUES ('%s')" % now
                self.db.query(add_sql)
                return True
            else:
                return 'Ошибка!'
        delta = now - last_restart
        if delta.seconds <= 180:
            return False
        n_sql = "UPDATE restart_bot SET last_restart = '%s'" % now
        self.db.query(n_sql)
        return True

    def delete_file(self, file_path):
        """
        Удаляет файл по переданному пути
        :param file_path: путь до файла/папки
        :return: Результат удаления
        """
        try:
            os.remove(file_path)
            logging.warning(f'Удалено: {file_path} | id: {self.user_id} | ник: {self.user_name} {self.user_last_name}')
            return f'{file_path} - удалено!'
        except Exception:
            remove_file_error_msg = traceback.format_exc()
            logging.error(f'При удалении {file_path} произошла ошибка: {remove_file_error_msg}')
            return 'При удалении произошла ошибка!'

    def get_dir(self, path):
        """
        Возвращает список файлов и папок по переданному пути
        :param path: Путь до директории
        :return: Список доступных файлов и папок по переданному пути
        """
        try:
            path = str(path)
        except:
            return 'Не удалось преобразовать путь к строке!'
        if path == '':
            path = '.'
        try:
            files = os.listdir(path)
        except:
            return 'Ошибка в пути!'
        line = ''
        for file in files:
            if '.' in file:
                if file.startswith('.'):
                    line = line + f'!> {file}\n'
                else:
                    line = line + f'{file}\n'
            else:
                line = line + f'> {file}\n'
        return line

    def check_user_ban(self, ban_id):
        """
        Проверяет, выдан ли пользователю бан
        :param ban_id: id в вк по которому нужно проверить
        :return: True - пользователь заблокирован, False - пользователь разблокирован
        """
        sql = 'SELECT user_id FROM users_ban WHERE user_id = %d' % ban_id
        result = self.db.select_with_fetchone(sql)
        if result is None:
            return False
        return True

    def take_ban(self, ban_id):
        """
        Выдаёт бан по переданному id в вк
        :param ban_id: id в вк, по которму нужно выдать бан
        :return: True - пользователь заблокирован, в этой версии нигде не используется
        """
        sql = 'INSERT INTO users_ban VALUES (%d)' % ban_id
        self.db.query(sql)
        return True

    def un_ban(self, ban_id):
        """
        Снимает бан с пользователя по переданному id в вк
        :param ban_id: id в вк, по которму нужно снять блокировку
        :return: True - пользователь разблокирован, в этой версии нигде не используется
        """
        sql = 'DELETE FROM users_ban WHERE user_id = %d' % ban_id
        self.db.query(sql)
        return True

    def check_ban_access(self, ban_id):
        """
        Проверяет, может ли текущий пользователь выдать бан по переданному id в вк
        :param ban_id: id в вк, который требуется заблокировать
        :return: True - текущий пользователь может забанить переданный id в вк,
        False - у текущего пользователя недостаточно прав, чтобы банить переданный id
        """
        sql = 'SELECT user_role FROM users_info WHERE user_id = %d' % ban_id
        result = str(self.db.select_with_fetchone(sql))
        if result == 'None':
            return 'Нет пользователя в бд!'
        result = result[2:-3:]
        if result == 'ROOT' and self.user_role == 'ADMIN':
            return False
        if result == self.user_role:
            return False
        return True

    def ban_manager(self, ban_id):
        """
        Управляет блокировкой пользователей
        :param ban_id: id в вк который нужно заблокировать
        :return: Заблокирует/Разблокирует пользователя по переданному id в вк
        """
        logging.warning(f'id: {self.user_id} | ban_id: {ban_id}'
                        f' ник: {self.user_name} {self.user_last_name} | права: {self.user_role} | режим: {self.user_mode}'
                        f' | Запущена функция ban_manager()')
        try:
            ban_id = int(ban_id)
        except:
            return 'id не является числом!'
        access = self.check_ban_access(ban_id)
        if access == 'Нет пользователя в бд!' or ban_id == 0:
            return 'Такого пользователя нет в базе данных!'
        if access == False:
            return 'Нельзя банить пользователей с такой же ролью и выше!', 'main'
        result = self.check_user_ban(ban_id)
        if result == False:
            self.take_ban(ban_id)
            return f'Пользователь {ban_id} заблокирован'
        else:
            self.un_ban(ban_id)
            return f'Пользователь {ban_id} разблокирован'

    def msg_handler(self, user_data, command):
        """
        Обработчик команд
        :param user_data: словарь c информацией о текущем пользователе, пришедший из файла server.py
        :param command: текст пришедшего сообщения
        :return: текст ответа/команда, для выплнения в файле(ах) server.py(server.py и server_manager.py)
        """
        #Сюда записываем исходный текст команды
        self.command = command
        #Сюда попадут параметры команды, либо если их нет - то сама команда
        self.command_text = ''
        #Распаковка user_data в соответствующие атрибуты
        self.id = user_data['id']
        self.user_id = user_data['user_id']
        self.user_name = user_data['user_name']
        self.user_last_name = user_data['user_last_name']
        self.user_mode = user_data['user_mode']
        self.user_role = user_data['user_role']
        self.user_last_message = user_data['user_last_message']
        #Флаг, отвечает за активность режима отладки(true - включен/false - выключен)
        self.debug_mode = self.debug.check_debug()
        #Флаг, True - текущий пользователь заблокирован, False - текущий пользователь разблокирован
        self.user_ban = self.check_user_ban(self.user_id)

        #Если кнопку нажали в беседе, убираем упоминание сообщества
        if self.command.startswith(f'[club{self.group_id}|@упоминание сообщества]'):
            #!!!ВАЖНО!!! В нашем случае, чтобы в self.command попала чистая команда, пришлось срезать первые 30 символов
            #от всего текста сообщения, в вашем случае, она может отличаться!!!
            self.command = self.command[30::]
        #Если нажата кнопка начать при старте диалога с сообществом:
        if self.command == 'начать':
            #Возвращаем в server.py результат выполнения метода say_hello
            return self.say_hello()
        #Если текст всего сообщение начинается с '//' - то это означает, что текущий пользователь хочет переключиться
        #в другой режим
        if self.command.startswith('//'):
            #Если пользователь заблокирован И (роль текущего пользователя не ROOT ИЛИ написал не владелец бота):
            #Сообщаем пользователю, что он заблокирован
            if self.user_ban and (self.user_role != "ROOT" or self.user_id != self.ROOT_owner_id):
                return 'Вы были заблокированы, по вопросам обращайтесь к администрации!'
            #params содержит: ['//Имя_режима_в_который_переключиться', 'набор параметров для команды']
            params = self.command.split(' ', maxsplit=1)
            #Сюда попадает имя_режима_в_который_переключиться
            self.command = params[0][2::]
            try:
                #Если есть параметры - записываем их в атрибут self.command_text
                self.command_text = params[1]
            except:
                #Иначе, self.command_text = самой команде
                self.command_text = self.command
            #Если пришедший режим есть в списке режимов:
            if self.command_text in self.modes_info:
                #Если уровень доступа текущего пользователя строго меньше уровня доступа режима(например:
                #уровень роли Editor - 1, уровень команды '/logs' - 3, то 1<3, 1=/=3) И пишет не владелец бота:
                if self.modes_info[self.command_text] > self.roles_info[self.user_role] and self.user_id != self.ROOT_owner_id:
                    return 'Недостаточно прав для переключения в этот режим!'
                #Иначе - продолжаем обработку команды
                else:
                    #Вызываем переключение режима
                    return self.change_mode(self.command)
            #Иначе:
            else:
                return 'Неизвестный режим!'
        #Если текст начинается с '/' - то это команда
        #Схема обработки уровня доступа такая же как и выше
        elif self.command.startswith('/'):
            if self.user_ban and (self.user_role != "ROOT" or self.user_id != self.ROOT_owner_id):
                return 'Вы были заблокированы, по вопросам обращайтесь к администрации!'
            params = self.command.split(' ', maxsplit=1)
            self.command = params[0][1::]
            try:
                self.command_text = params[1]
            except:
                self.command_text = self.command
            if self.command in self.commands_info:
                if self.commands_info[self.command] > self.roles_info[self.user_role] and self.user_id != self.ROOT_owner_id:
                    return 'Недостаточно прав для выполнения команды!'
                else:
                    #Вызываем ядро для обработки команды
                    return self.core()
            else:
                return 'Неизвестная команда!'
        #Если текущий пользователь находится в режиме рассылки и последнее сообщение = 'ожидание сообщения' -
        #Значит пришел текст, который будет разослан, запускаем ядро и сохраняем пришедший текст как
        #последнее сообщение(столбец user_last_message в таблице users_info)
        elif self.user_mode == 'рассылка' and self.user_last_message == 'ожидание сообщения':
            return self.core()
        #Если вышеперечисленное не подошло - значит сообщение не команда, не реагируем
        else:
            return False

    def core(self):
        """
        Это ядро. Оно обрабатывает команду после проверки доступа.
        :return: либо текст, либо ('текст', 'имя клавиатуры')
        """
        #Если режим - default
        if self.user_mode == 'default':
            #Реакции на команды
            if self.command == 'main_kb':
                return 'Включена главная клавитура', 'main_kb'
            elif self.command == 'clear':
                return 'Клавиатура отчищена!', 'empty_kb'
            elif self.command == 'help':
                return self.get_commands_and_mods()
            elif self.command == 'profile':
                return self.get_profile()
            elif self.command == 'disable':
                return 'mute_true'
            elif self.command == 'on':
                return 'mute_false'
            elif self.command == 'off':
                return 'off'
            elif self.command == 'logs':
                return 'get_logs'
            elif self.command == 'dir':
                return self.get_dir(self.command_text)
            elif self.command == 'update_db':
                return 'update_db'
            elif self.command.startswith('update_module'):
                return f'update_module&{self.command_text}'
            elif self.command == 'restart':
                response = self.check_restart()
                if response == True:
                    return 'restart&Перезапуск...'
                elif response == 'Ошибка!':
                    return 'Ошибка при перезапуске!'
                else:
                    return 'Перезапускаться можно раз в три минуты!'
            elif self.command == 'delete_file':
                return self.delete_file(self.command_text)
            elif self.command.startswith('sqlq'):
                return self.sqlq()
            elif self.command.startswith('sqlo'):
                return self.sqlo()
            elif self.command.startswith('sqla'):
                return self.sqla()
            elif self.command == 'get_all_users':
                return self.get_all_users()
            elif self.command == 'debug':
                result = self.debug.activate_debug_mode()
                return result
            elif self.command.startswith('msg'):
                return self.send_msg(self.command_text)
            elif self.command.startswith('ban'):
                return self.ban_manager(self.command_text)
            elif self.command == 'начать':
                return self.say_hello()
            else:
                return 'Команда не поддерживается в этом режиме!'
        #Если режим - рассылка
        elif self.user_mode == 'рассылка':
            if self.command == 'создать_рассылку':
                sql = "UPDATE users_info SET user_last_message = 'ожидание сообщения' WHERE user_id = %d" % self.user_id
                self.db.query(sql)
                return 'Введи текст для рассылки:'
            elif self.user_last_message == 'ожидание сообщения':
                sql = "UPDATE users_info SET user_last_message = '%s' WHERE user_id = %d" % (self.command, self.user_id)
                self.db.query(sql)
                return 'Текст сохранён!'
            elif self.command == 'очистить_текст':
                if self.user_last_message != 'ожидание сообщения':
                    sql = "UPDATE users_info SET user_last_message = 'ожидание сообщения' WHERE user_id = %d" % (self.user_id)
                    self.db.query(sql)
                    return 'Текст очищен!'
                else:
                    return 'Ты ещё не создал(а) рассылку!'
            elif self.command == 'разослать':
                if self.user_last_message == 'ожидание сообщения':
                    return 'Нет сохранённого текста!'
                else:
                    return 'spam'
            elif self.command == 'profile':
                return self.get_profile()
            else:
                return 'Команда некорректна или не поддерживается в этом режиме!'
        #Иначе - сообщение об ошибке
        else:
            return 'Вы находитесь в несуществующем режиме!'

    def change_mode(self, mode):
        """
        Меняет режим пользователя
        :param mode: режим в который нужно переключиться
        :return: Сообщение о выполнении переключения
        """
        #Если режим отладки выключен:
        if self.debug_mode == 'False':
            #Если текущий режим = пришедшему
            if mode == self.user_mode:
                return 'Ты уже в этом режиме'
            elif mode == 'default':
                sql = "UPDATE users_info SET user_mode = 'default', user_last_message = 'None' WHERE user_id = %d" % self.user_id
                self.db.query(sql)
                return 'Режим обновлён!'
            elif mode == 'рассылка':
                if self.check_spam():
                    return 'Кто-то уже находится в режиме рассылке, попробуй чуть позже!'
                sql = "UPDATE users_info SET user_mode = 'рассылка' WHERE user_id = '%s'" % self.user_id
                self.db.query(sql)
                return 'Режим обновлён!'
        #Иначе:
        else:
            return 'Невозможна смена режима', 'None'