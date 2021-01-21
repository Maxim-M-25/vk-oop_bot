# -*- coding: utf-8 -*-
"""
––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
version/версия: 1.0.0 - release | Автор: Максим Токарев | Бесплатный хостинг для бота: pythonanywhere
Наш ютуб канал с разборкой этого бота(там ещё не весь на 21.01.2021):
https://www.youtube.com/channel/UChhQu3BybjxzOwYnmMslVPA смотрите в разделе 'python'
––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
Это главный файл бота. Чтобы включить бота - нужно запустить этот файл.
Здесь идёт управление файлом server.py, сначала он запускается от сюда, а затем,
server_manager.py ждёт пока ему что-то вернётся из метода start в файле server.py, и затем,
на основе пришедших данных, либо выключает бота, либо обновляет модуль, либо перезапускает бота и т.д.
"""
#Подключение модулей
import time
import logging
import traceback
import os

#Импортируем токен сообщества
from config import api_main_token

#Настройка логирования
logging.basicConfig(filename='bot_log_files/main_log.log', filemode='a',
                    format=u'%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logging.info('Запуск бота...')

#Флаг, используется при обновлении файлов бота. В случае успешного обновления - True, неудачного - False,
#None - бот только что запущен, а значит нет информации об обновлении
success_update = None

try:
    """Главный цикл бота"""
    while True:
        #Импортируем класс Server из файла server.py
        from server import Server
        try:
            #Создаём объект server1 по классу Server, передаём токен сообщества и id сообщества из которого работает бот
            server1 = Server(api_main_token, 000000000) #000000000 - замените эти цифры своим id сообщества
            #Если нет информации об обновлении - ничего не делаем
            if success_update is None:
                pass
            #Если обновление успешно - высылаем сообщение владельцу, что бот успешно обновился
            elif success_update is True:
                server1.error_report('Бот обновлён!')
                #Сбрасываем флаг
                success_update = None
            #Если при обновлении произошла ошибка - высылаем уведомление об этом владельцу
            else:
                server1.error_report('Обновление не удалось!')
                # Сбрасываем флаг
                success_update = None
            #В переменную response попадает ответ из метода start, файла server.py
            response = server1.start()
            #Если ответ 'off' - прерываем главный цикл, и скрипт выключается
            if response == 'off':
                logging.warning('Бот выключен')
                break
            #Если ответ 'restart' - удаляем server1, и переходим на новую итерацию цикла
            elif response == 'restart':
                del server1
                logging.warning('Бот перезапускается...')
                continue
            #Если ответ начинается с 'update_module' - обновляем модуль
            elif response.startswith('update_module'):
                #В params содержатся ['название команды', 'имя обновляемого модуля']
                params = response.split('&')
                module_name = params[1]
                #Список имён файлов, доступных для обновления
                modules = ['commander', 'group_server', 'db']
                #Если запрошенный для обновления файл есть в списке modules:
                if module_name in modules:
                    logging.warning(f'Обновляется модуль {module_name}')
                    #Удаляем server1
                    del server1
                    # cwd = os.getcwd()
                    #Переименовываем файл модуля по принципу module_name.py -> module_name_old.py,
                    #где _old - временный постфикс, нужен, чтобы в случае ошибки при обновлении,
                    #по нему можно было восстановить файл, который был до обновления
                    os.rename(f'{module_name}.py', f'{module_name}_old.py')
                    #Есть ли .txt файл с кодом и именем обновляемого файла
                    #(то которое было до переименования(без постфикса '_old'))
                    file_there = os.path.isfile(f'{module_name}.txt')
                    #Если этот файл обнаружен:
                    if file_there:
                        try:
                            #Переименовываем файл, содержащий свежий код, по принципу module_name.txt -> module_name.py
                            os.rename(f'{module_name}.txt', f'{module_name}.py')
                            #Если предыдущий шаг выполнен, удаляем файл со старым кодом, к его имени мы добавили
                            #постфикс _old
                            os.remove(f'{module_name}_old.py')
                            #Устанавливаем флаг = True, т.к. при обновлении файла ошибок не произошло
                            success_update = True
                            continue
                        except Exception:
                            #Если произошла ошибка - записываем её в логи
                            update_error_msg = traceback.format_exc()
                            logging.error(f'Ошибка при обновлении модуля {module_name}: {update_error_msg}')
                            #Убираем временный постфикс '_old', тем мамым восстанавливая тот файл,
                            #который был до обновления
                            os.rename(f'{module_name}_old.py', f'{module_name}.py')
                            success_update = False
                            continue
                    #Иначе, удаляем постфикс
                    else:
                        logging.error(f'Ошибка при обновлении модуля {module_name}: файл {module_name}.txt не найден!')
                        #Удаляем временный постфикс '_old'
                        os.rename(f'{module_name}_old.py', f'{module_name}.py')
                        #Устанавливаем флаг = False, т.к. не нашли .txt файл
                        success_update = False
                #Если файла нет в списке разрешенных, записываем в логи, что файл с таким именем не найден
                else:
                    logging.warning(f'При обновлении произошла ошибка! {module_name} - модуль не найден!')
                    success_update = False
                continue
            #Здесь используется таже самая схема что и при обновлении модулей,
            #только нам заранее известно что обновляем файл базы данных
            elif response == 'update_db':
                logging.warning('Обновляется база данных')
                del server1
                os.rename('dbs/main_db.db', 'dbs/group_db_old.db')
                db_there = os.path.isfile('db.db')
                if db_there:
                    try:
                        os.replace('db.db', 'dbs/main_db.db')
                        os.remove('dbs/group_db_old.db')
                        success_update = True
                        continue
                    except Exception:
                        update_db_error_msg = traceback.format_exc()
                        logging.error(f'При обновлении базы данных произошла ошибка: {update_db_error_msg}')
                        os.rename('dbs/group_db_old.db', 'dbs/main_db.db')
                        success_update = False
                        continue
                else:
                    logging.error('Ошибка при обновлении базы данных: файл db.db не найден!')
                    os.rename('dbs/group_db_old.db', 'dbs/main_db.db')
                    success_update = False
                    continue

        except:
            #Если случилась ошибка - пишем её в логи, ждём 15 секунд, и перезапускаемся
            error_msg = traceback.format_exc()
            # print(f'Произошла неожиданная ошибка:\n    {error_msg}\n Перезапуск...')
            logging.error(f'Произошла неожиданная ошибка: {error_msg}')
            logging.info('Перезапуск...')
            time.sleep(15)
except:
    logging.warning('Выключение...')
finally:
    #В случае какой-то серьёзной ошибки, блок 'finally' вышлет уведомление владельцу(если сможет конечно),
    #в котором укажет случившуюся ошибку
    error_msg = traceback.format_exc()
    server1.error_report(f'!!!Сработал блок except!!!\nОшибка:\n{error_msg}')
    logging.error(f'Сработал блок finally!!! Ошибка: {error_msg}')
    logging.fatal('Бот выключен')

logging.info('Скрипт завершен')