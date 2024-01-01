import time

import requests

from ikabot.helpers.botComm import sendToBot, getUserResponse
from ikabot.helpers.process import run


def resolveCaptcha(session, picture):
    session_data = session.getSessionData()
    if 'decaptcha' not in session_data or session_data['decaptcha']['name'] == 'default':
        text = run('nslookup -q=txt ikagod.twilightparadox.com ns2.afraid.org')
        parts = text.split('"')
        if len(parts) < 2:
            # the DNS output is not well formed
            return 'Error'
        address = parts[1]

        files = {'upload_file': picture}
        captcha = requests.post('http://{0}'.format(address), files=files).text
        return captcha
    elif session_data['decaptcha']['name'] == 'custom':
        files = {'upload_file': picture}
        captcha = requests.post('{0}'.format(session_data['decaptcha']['endpoint']), files=files).text
        return captcha
    elif session_data['decaptcha']['name'] == '9kw.eu':
        credits = requests.get("https://www.9kw.eu/index.cgi?action=usercaptchaguthaben&apikey={}".format(session_data['decaptcha']['relevant_data']['apiKey'])).text
        if int(credits) < 10:
            raise Exception('You do not have enough 9kw.eu credits!')
        captcha_id = requests.post("https://www.9kw.eu/index.cgi?action=usercaptchaupload&apikey={}".format(session_data['decaptcha']['relevant_data']['apiKey']), headers={'Content-Type': 'multipart/form-data'}, files={'file-upload-01': picture}).text
        while True:
            captcha_result = requests.get("https://www.9kw.eu/index.cgi?action=usercaptchacorrectdata&id={}&apikey={}".format(captcha_id, session_data['decaptcha']['relevant_data']['apiKey'])).text
            if captcha_result != '':
                return captcha_result.upper()
            session.wait(5, 'Resolving Captcha')
    elif session_data['decaptcha']['name'] == 'telegram':
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

