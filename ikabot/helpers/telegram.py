import logging
import math
import os
import random
import time
from decimal import Decimal

import requests

from ikabot import config
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.userInput import askUserYesNo, read


class Telegram:
    __DB_KEY = 'telegram'
    __BOT_TOKEN = 'botToken'
    __CHAT_ID = 'chatId'

    def __init__(self, db, is_user_attached):
        logging.debug("Setup telegram, isUserAttached: %s", is_user_attached)
        self.__db = db
        self.__is_user_attached = is_user_attached

    def send_message(self, msg, photo=None):
        """
        Sends message to the configured telegram bot. Returns if operation was successful.
        :param msg:
        :param photo:
        :return:
        """
        logging.info('Messaging Telegram bot: %s', msg)
        telegram_data = self.__get_telegram_data()
        if telegram_data is None:
            logging.error('Telegram data is not correct.')
            return False

        return self.__send_message(telegram_data, msg, photo)

    def update_data(self):
        """
        Updates telegram data and returns the new configuration or None if failed.
        :return: dict[]/None
        """
        if not self.__is_user_attached:
            # User is not attached, who will provide the data for us?
            return None

        banner()
        print('You must provide valid credentials to communicate by telegram.')
        print('You are required to provide the token of the bot you are going to use and your chat_id')
        if not askUserYesNo('Will you provide the credentials now'):
            return None

        print('To create your own Telegram Bot, read this: https://core.telegram.org/bots#3-how-do-i-create-a-bot')
        print('Just talk to @botfather in Telegram, send /newbot and then choose the bot\'s name.')
        print('Talk to your new bot and send /start')
        print('Remember to keep the token secret!\n')
        require_bot_token = True

        while True:
            if require_bot_token:
                bot_token = read(msg="Bot's token: ")
                bot_token = bot_token.replace(' ', '')

            messages = self.__get_user_responses({self.__BOT_TOKEN: bot_token})
            if messages is None:
                require_bot_token = True
                if not askUserYesNo('Invalid telegram bot. Do you want to try again'):
                    return None
                continue  # restart the process

            chat_id = self.__get_chat_id(messages)
            if chat_id is None:
                require_bot_token = False
                print('No messages found.')
                print("Please send a random message to the Bot's chat and then click enter")
                enter()
                continue

            telegram_data = {
                self.__BOT_TOKEN: bot_token,
                self.__CHAT_ID: str(chat_id),
            }

            # check if it's actually working
            msg = 'token-' + str(random.randint(0, 9999)).zfill(4)
            self.__send_message(telegram_data, msg)
            if askUserYesNo("I've send you the message {}. Did you receive it".format(msg)):
                self.__db.store_value(self.__DB_KEY, telegram_data)
                return telegram_data

            if not askUserYesNo("Well, probably somthing in the configuration if messed. Do you want to try again"):
                return None

            require_bot_token = True

    def get_user_responses(self):
        """
        Retrieve the messages user sent to the bot on telegram.
        :return: List[dict] | None
        """
        telegram_data = self.__get_telegram_data()
        if telegram_data is None:
            return None

        return self.__get_user_responses(telegram_data)

    def wait_user_reply(self, msg: str, picture=None, max_wait_seconds: int = 60):
        """
        Send message to the user and waits for reply
        :param msg: Describes user options
        :param picture: picture (probably captcha)
        :param max_wait_seconds:
        :return: str | None
        """
        telegram_data = self.__get_telegram_data()
        if telegram_data is None:
            return None

        message_sent = self.__send_message(
            telegram_data=telegram_data,
            msg=f'{msg}\nPlease REPLY to this message with the answer!',
            photo=picture
        )

        sleep_time = 5  # seconds
        for _ in range(math.ceil(Decimal(max_wait_seconds) / sleep_time)):
            responses = self.__get_user_responses(telegram_data)
            if len(responses) > 0:
                for r in responses:
                    if 'reply_to_message' in r and r['reply_to_message']['message_id'] == message_sent['message_id']:
                        return r['text']
            time.sleep(sleep_time)

        return None

    def has_valid_data(self):
        return self.__get_telegram_data() is not None

    def __get_telegram_data(self):
        """
        This function returns stored Telegram data and checks if there is any.
        If there is no data - trying to update the data
        If there is data - returns the data
        :return: dict[]/None
        """
        telegram_data = self.__db.get_stored_value(self.__DB_KEY)
        if self.__is_data_valid(telegram_data):
            return telegram_data

        return self.update_data()

    @staticmethod
    def __get_chat_id(messages):
        for message in messages:
            return message['chat']['id']
        return None

    @staticmethod
    def __get_telegram_url(bot_token, function):
        return 'https://api.telegram.org/bot{}/{}'.format(bot_token, function)

    @staticmethod
    def __is_data_valid(telegram_data):
        return (telegram_data is not None
                and len(telegram_data.get(Telegram.__BOT_TOKEN, '')) > 0
                and len(telegram_data.get(Telegram.__CHAT_ID, '')) > 0)

    @staticmethod
    def __send_message(telegram_data, msg, photo=None):
        """
        Sends message from telegram bot with the given configuration.
        :param telegram_data: dict[]
        :param msg: str
        :param photo: bytes
        :return: bool -> is successful
        """
        msg = 'pid: {}, botName: {}\n{}'.format(os.getpid(), config.BOT_NAME, msg)
        telegram_url = Telegram.__get_telegram_url(telegram_data[Telegram.__BOT_TOKEN], 'sendMessage')

        if photo is None:
            updates = requests.get(
                url=telegram_url,
                params={
                    'chat_id': telegram_data[Telegram.__CHAT_ID],
                    'text': msg
                },
            )
        else:
            # we need to clear the headers here because telegram doesn't like keep-alive,
            # might as well get rid of all headers
            updates = requests.post(
                url=telegram_url,
                files={
                    'document': ('captcha.png', photo)
                },
                data={
                    'chat_id': telegram_data[Telegram.__CHAT_ID],
                    'caption': msg
                }
            )

        updates = updates.json()
        if 'ok' not in updates or updates['ok'] is False:
            return None

        return updates['result']

    @staticmethod
    def __get_user_responses(telegram_data):
        """
        Retrieve the messages user sent to the bot on telegram.
        :param telegram_data: dict[]
        :return:
        """
        updates = requests.get(Telegram.__get_telegram_url(telegram_data[Telegram.__BOT_TOKEN], 'getUpdates')).json()
        if 'ok' not in updates or updates['ok'] is False:
            return None

        return [update['message'] for update in updates['result'] if 'message' in update
                and ('chatId' not in telegram_data
                     or update['message']['chat']['id'] == int(telegram_data['chatId']))]
