# -*- coding: utf-8 -*-
"""
В этом файле содержатся методы для работы с режимом отладки
"""
#Подключаем класс для работы с базой данных
from db import DataBase

class Debug:
    def __init__(self, path):
        #Через атрибут self.db работаем с методами для работы с базой данных
        self.db = DataBase(path)

    def check_debug(self):
        """
        Проверяет, включён ли режим отладки, по базе данных
        :return: состояние режима(включен/выключен)
        """
        sql = 'SELECT debug_mode FROM debug'
        result = str(self.db.select_with_fetchone(sql))
        result = result[2:-3:]
        return result

    def activate_debug_mode(self, debug_mode=None):
        """
        Включает/выключает режим отладки
        :param debug_mode: текущее состояние режима, если False - включает режим отладки, если None - то
        сначала проверит базу данных, а потом на основе полученного результата из неё вклюит или выключит режим отладки,
        во всех остальных случаях - выключит режим отладки
        :return: 'debug mod on' - указание, что режим отладки включён, 'debug mod off' - указание,
        что режим отладки выключен
        """
        if debug_mode == None:
            debug_mode = self.check_debug()
        if debug_mode == 'False':
            self.db.query('UPDATE debug SET debug_mode = "True"')
            self.db.query('UPDATE users_info SET user_mode = "default", user_last_message = "None"')
            return "debug mod on"
        else:
            self.db.query('UPDATE debug SET debug_mode = "False"')
            self.db.query('UPDATE users_info SET user_mode = "default", user_last_message = "None"')
            return "debug mod off"