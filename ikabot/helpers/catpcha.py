import logging
import time

import requests

from ikabot.helpers.database import Database
from ikabot.helpers.ikabotProcessListManager import run
from ikabot.helpers.telegram import Telegram


def resolveCaptcha(db: Database, telegram: Telegram, picture):
    decaptcha_config = db.get_stored_value('decaptcha')
    logging.debug("Decaptcha config: %s", decaptcha_config)

    if decaptcha_config is None or decaptcha_config['name'] == 'default':
        text = run('nslookup -q=txt ikagod.twilightparadox.com ns2.afraid.org')
        parts = text.split('"')
        if len(parts) < 2:
            # the DNS output is not well formed
            return 'Error'
        address = parts[1]

        _url = 'http://{0}'.format(address)
        logging.debug("Sending captcha to %s", _url)

        files = {'upload_file': picture}
        captcha = requests.post(_url, files=files).text
        return captcha
    elif decaptcha_config['name'] == 'custom':
        files = {'upload_file': picture}
        captcha = requests.post('{0}'.format(decaptcha_config['endpoint']), files=files).text
        return captcha
    elif decaptcha_config['name'] == '9kw.eu':
        credits = requests.get("https://www.9kw.eu/index.cgi?action=usercaptchaguthaben&apikey={}".format(decaptcha_config['relevant_data']['apiKey'])).text
        if int(credits) < 10:
            raise Exception('You do not have enough 9kw.eu credits!')
        captcha_id = requests.post("https://www.9kw.eu/index.cgi?action=usercaptchaupload&apikey={}".format(decaptcha_config['relevant_data']['apiKey']), headers={'Content-Type': 'multipart/form-data'}, files={'file-upload-01': picture}).text
        while True:
            captcha_result = requests.get("https://www.9kw.eu/index.cgi?action=usercaptchacorrectdata&id={}&apikey={}".format(captcha_id, decaptcha_config['relevant_data']['apiKey'])).text
            if captcha_result != '':
                return captcha_result.upper()
            time.sleep(5)  # 'Resolving Captcha'
    elif decaptcha_config['name'] == 'telegram':
        return telegram.wait_user_reply(
            msg='Solve captcha',
            picture=picture,
        )




