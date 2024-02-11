#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from ikabot.helpers.gui import banner, Colours, enter
from ikabot.helpers.userInput import read


def importCookie(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()
    print('{}⚠️ INSERTING AN INVALID COOKIE WILL LOG YOU OUT OF YOUR OTHER SESSIONS ⚠️{}\n\n'.format(Colours.Text.Light.YELLOW, Colours.Text.RESET))
    print('Go ahead and export the cookie from another ikabot instance now and then')
    print('type your "ikariam" cookie below:')
    newcookie = read()
    newcookie = newcookie.strip()
    newcookie = newcookie.replace('ikariam=', '')
    cookies = db.get_stored_value('cookies') or {}
    cookies['ikariam'] = newcookie
    if ikariam_service.host in ikariam_service.s.cookies._cookies:
        ikariam_service.s.cookies.set('ikariam', newcookie, domain=ikariam_service.host, path='/')
    else:
        ikariam_service.s.cookies.set('ikariam', newcookie, domain='', path='/')

    html = ikariam_service.s.get(ikariam_service.urlBase).text

    if ikariam_service.isExpired(html):
        print('{}Failure!{} All your other sessions have just been invalidated!'.format(Colours.Text.Light.RED, Colours.Text.RESET))
        enter()
    else:
        print('{}Success!{} This ikabot session will now use the cookie you provided'.format(Colours.Text.Light.GREEN, Colours.Text.RESET))
        cookies = db.get_stored_value('cookies') or {}
        cookies['ikariam'] = newcookie
        db.store_value('cookies', cookies)
        enter()
    ikariam_service.get()


def exportCookie(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()
    ikariam_service.get()  # get valid cookie in case user has logged the bot out before running this feature
    ikariam = (db.get_stored_value('cookies') or {}).get('ikariam')
    print('Use this cookie to synchronise two ikabot instances on 2 different machines\n\n')
    print('ikariam='+ikariam+'\n\n')

    cookie = json.dumps({"ikariam": ikariam})  # get ikariam cookie, only this cookie is invalidated when the bot logs the user out.
    cookies_js = 'cookies={};i=0;for(let cookie in cookies){{document.cookie=Object.keys(cookies)[i]+\"=\"+cookies[cookie];i++}}'.format(cookie)
    print("""To prevent ikabot from logging you out while playing Ikariam do the following:
    1. Be on the "Your session has expired" screen
    2. Open Chrome javascript console by pressing CTRL + SHIFT + J
    3. Copy the text below, paste it into the console and press enter
    4. Press F5
    """)
    print(cookies_js)
    enter()
