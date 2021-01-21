# -*- coding: utf-8 -*-
"""
Это файл для работы с базой данных. Здесь содержатся методы для выполнения разных запросов
"""
import sqlite3

class DataBase:
    def __init__(self, path):
        """
        Этот метод принимает путь до файла базы данных, подключается к ней,
         и позволяет проводить операции с базой данных
        :param path: Путь до файла базы данных. Путь должен вести на конкретный файл.
        """
        #Подключаемся
        self.conn = sqlite3.connect(path)
        #Создаём курсор, позволяющий работать с базой данных
        self.c = self.conn.cursor()

    def select_with_fetchone(self, cmd):
        """
        Этот метод выполняет SELECT запросы методом fetchone
        :param cmd: SQL запрос (str)
        :return: список с выборкой
        """
        self.c.execute(cmd)
        result = self.c.fetchone()
        return result

    def select_with_fetchall(self, cmd):
        """
        Этот метод выполняет SELECT запросы методом fetchall
        :param cmd: SQL запрос (str)
        :return: список с выборкой
        """
        self.c.execute(cmd)
        result = self.c.fetchall()
        return result

    def query(self, cmd):
        """
        Этот метод выполняет UPDATE, DELETE, INSERT запросы
        :param cmd: SQL запрос (str)
        :return: None
        """
        self.c.execute(cmd)
        self.conn.commit()

    def disconnect(self):
        """
        Этот метод прерывает соединение с базой данных
        :return: None
        """
        self.conn.close()