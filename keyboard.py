# -*- coding: utf-8 -*-
"""
Этот файл используется для получения кода клавиатур бота
"""
class Keyboards:
    def  __init__(self):
        pass

    def get_keyboard(self, path):
        """
        Этот метод считает файл клавиатуры, и вернёт его содержимое
        :param path: имя клавиатуры, в случае вложенных папок(например:
        Имеем такую структуру файлов
        –––––––––––––––––––––––––––
        |keyboards
        |    main_kb.json
        |    roots
        |    |    root_kb.json
        |    admins
        |    |    admin_kb.json
        |    |    more_kb
        |    |    |    spam_kb.json
        –––––––––––––––––––––––––––
        Тогда, чтобы получить spam_kb.json, нужно будет передать в path следующее: 'admins/more_kb/spam_kb',
        а чтобы получить, например main_kb, достаточно передать в path следующее: 'main_kb')
        !!!ВАЖНО!!! дописовать в конце имени/пути '.json' не надо, метод сделает это сам!!!
        :return: Считанная клавиатура
        """
        with open(f'keyboards/{path}.json', 'r', encoding="UTF-8") as kb:
            return kb.read()