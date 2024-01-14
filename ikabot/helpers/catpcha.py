import time

import requests

from ikabot.helpers.botComm import getUserResponse, sendToBot
from ikabot.helpers.ikabotProcessListManager import run


def resolveCaptcha(session, picture):
    decaptcha_config = session.db.get_stored_value('decaptcha')
    if decaptcha_config is None or decaptcha_config['name'] == 'default':
        text = run('nslookup -q=txt ikagod.twilightparadox.com ns2.afraid.org')
        parts = text.split('"')
        if len(parts) < 2:
            # the DNS output is not well formed
            return 'Error'
        address = parts[1]

        files = {'upload_file': picture}
        captcha = requests.post('http://{0}'.format(address), files=files).text
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
            session.wait(5, 'Resolving Captcha')
    elif decaptcha_config['name'] == 'telegram':
        sendToBot(session, 'Please solve the captcha', Photo=picture)
        captcha_time = time.time()
        while(True):
            response = getUserResponse(session, fullResponse=True)
            if len(response) == 0:
                time.sleep(5)
                continue
            response = response[-1]
            if response['date'] > captcha_time:
                return response['text']
            time.sleep(5)

