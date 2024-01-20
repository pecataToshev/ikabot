#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import base64
import getpass
import json
import logging
import os
import random
import re
import sys
import time
from collections import deque

import requests
from urllib3.exceptions import InsecureRequestWarning

from ikabot import config
from ikabot.config import actionRequest, ConnectionError_wait, user_agent
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import banner, decodeUnicodeEscape, enter
from ikabot.helpers.userInput import read

#blackbox tokens
blackbox_tokens = [ #ch, chi, ffi
    'JVqc1fosb5TG-D2yJJMDaI2_BU2yHpH6aNM8YZPF6hxfxSaSBWqPwQQpW43PO6QSfaLUBitdoMX3KYDpV7sqoRQ5a53C9DdcjsADa91MuR5DdafM_kFmmMoRgO9WwidMfq73Zcj2G01_pNYZSXes0QNGeJ3PEjdpmwBum-IkSXut0gRHbJ7QNJnNAzdszQA0baDQAjJixwAwYZT4L2XIADBpzf84aqABNmfKLmab0TKXzwg8oNcPQnesD3XZDD2f1DlrodM0bZLE9htNkLXnGWDPPqURdpvN_Ua0F0VqnMz0QpjhJW6v2P0vcrMBSJTZ_jBgiNYsdbkCQ2ia3QI0ZLIIUZXeH0R2pu1SmAd53EFmmMgPY7vgEkJzqd8PNGaW6lN4qtoCMqraCjpqnM0FN2CFt-crlAZrzkJ1ueobQHKiGIvqH36u0wU1pRh3rAs7YJLV-ixcoNMXSHmix_krUILF6hxOhbfuUYHnHE2Bue4nYJL2J17D-zFpogY5aqPaEHGj1QprnM0GOG2i2xJ4rhJ23Aw-odIJb9ILbtAAYsP6W5LDJkt9r9QGSW6g0jZv0DZtzi9gxPQkirzsHoO77SZXvSJWj_EqXZHFK2Ga0QU7caTZPqMEOWzRCG3OMZbMBGeYyC5hkcMmicL1KImu4BI3aazdFkh4nc8SQ3On1_wucaPX_C5xlsj6K5HB9FaNxCqO7yJVjMDyJFqL7VKz40d5sBVLf7HkRqzeEHSmCG6j2kClB2qf0jOYzwRmn9UHbaMIPW-iBWiYyu8hU3iq7RJEdqsMPKEHOW_VOXLYPm6n3RNLhOpPsBF1pQk9dtw-dqvgEUl7rRJzqQs-oAU8cNEBM2qj1zpszS5fj_RVueoeT7XaDD5jldj9L2HFKmLE9Vi97U6y6BxSuBt-s-lKf7MVSn7hFUd-4kR12j6i1jpv0QJkm9QHOm_RAjuf0AU4aJn8YMMoWY7yU4a33A5AZZfa_zFjx_8vZJjRNpfKLpDF-Sxelc0yY5fNM2rQADmb0QprngAzlvldviOIwfpejsAjV42_-C2OxPoukMX6L2Wd0gU-pMn7LVKEx_gqXoy87yJZjcD0KmKY0QY5a5DCBSpcjvAihOhLsOQagLkbUIjuU7TmH1W7IFG0F0eA4xxQiepOg7bnG1S27lOHvSBZv_VXje5RhLTkG37hGk-w4xqAtegNP3GWyAs4bqXVC0Fzq-MXPG6x1gg6bJzOAS5fkL3tJXmq3gM2d6fgBTh5qdsJPXOqBClbjbLkJ0x-sBtMuTCfF4L0X5j8auMUjsEiVI32XJXNPqzlGD1vocb4O22k2wAydZrM_i9fhLboDT-Cp9kLYMpCdtcJUrsLeakYfelZittEt-4_cLEZer8BZrH3K6L8U6kNYLX3ZbMIcLcGWYq6BUmT9EaZ0hNtnw9ov_EznvU5arEARYvdQa3uVqz0aKoOZKbZI4_3UaoBVsYfY8oDTpMDZLXmH5noUpvLGYLMQ5kHTcMRe7D4Tsf4Zsr6XpTlXsIKYssMhNI8p9wqbsM8it4vp_Ruv-8URnidzxI3aZvoV9E6phJzmMoQRXOjyPoqUqkSgORTyj1ilMQSZou97R5OfKzRBEZrnc0kjfsxZYq9_yRWhv40aJG26BhZyTmlCmHGKHPcUHWn7SJVjLrtI0h6qtIdZbkGUnep7BFDc99Isxg9b5_mS64ZiLHWCDh741XEMZa77TNklc78LFqKuOgNP2_CI4nqXMXqHGKXygEvYpi97yFGeLvgEkR2ptgLOGmax_cvg7ToDUCBseoPQoOz5RNDc6P9IlSGq90gjgNv2wA1eQ',
    'JVqc1fosb5TG-D2yJJMDaI2_BU2yHpH6aNM8YZPF6hxfxSaSBWqPwQQpW43PO6QSfaLUBitdoMX3KYDpV7sqoRQ5a53C9DdcjsADa91MuR5DdafM_kFmmMoRgO9WwidMfq73Zcj2G01_pNYZSXes0QNGeJ3PEjdpmwBum-IkSXut0gRHbJ7QNJnNAzdszQA0baDQAjJixwAwYZT4L2XIADBpzf84aqABNmfKLmab0TKXzwg8oNcPQnesD3XZDD2f1DlrodM0bZLE9htNkLXnGWDPPqURdpvN_Ua0F0VqnMz0QpjhJW6v2P0vcrMBSJTZ_jBgiNYsdbkCQ2ia3QI0ZLIIUZXeH0R2pu1SmAd53EFmmMgPY7vgEkJzqd8PNGaW6lN4qtoCMqraCjpqnM0FN2CFt-crlAZrzkJ1ueobQHKiGIvqH36u0wU1pRh3rAs7YJLV-ixcoNMXSHmix_krUILF6hxOguNGqg5z1TdpnM8AMGPG_DWaygA3bdAyaJ7QATJqntQMbdMKPJ7O_zZuoNMGOZz_Npf9MJbK_TOXzAJllsctZIm77RJEh6zeEHStDnSrDG2eAjJiyPoqXMH5K2SV-2CUzS9om88DaZ_YD0N5r-IXfOFCd6oPRqsMb9QKQqXWBmyfzwFkxwAzZsfsHlB1p-obVIa22w1QgbHlFTpsr-EVOmyv1AY4ac__MpTLAmjMLWCTyv4wYpjJK5DxIYW37lOJve8ihOocTrLkRqzhGH7jRajdEHHWDUKk3RNFq-FGe63gQ6bWCC1fkbboK1CCtOlKet9Fd60Td7AWfKzlG1GJwiiN7k-z40d7tBp8tOkeT4e561Cx50l83kN6rg8_cajhFXiqC2ydzTKT9yhcjfMYSnyh0xY7bZ8DaKACM5b7K4zwJlqQ9lm88SeIvfFTiLwfU4W8IIKzGHzgFHitD0Ci2RJFeK0PQHndDkN2ptc6ngFml8wwkcT1Gkx-o9UYPW-hBT1totYPdNUIbM4DN2qc0wtwodULcagOPnfZD0ip3D5x1Deb_GHG_ziczP5hlcv9NmvMAjhszgM4baPbEEN84gc5a5DCBTZonMr6LWCXy_4yaKDWD0R3qc4AQ2iazC5gwiaJ7iJYvvdZjsYskfIkXZP5Xo_yVYW-IVqOxyiMwfQlWZL0LJHF-16X_TOVyyyPwvIiWbwfWI3uIVi-8yZLfa_UBkl2rOMTSX-x6SFVeqzvFEZ4qtoMP2ydzvsrY7foHEF0teYWO26v4RdFfa7nQWaYyu8hZIm77ViJ9m3cVL8xnNU5pyBRy_5fkcozmdIKe-kiVXqs3gM1eKrfEzhqrdIENmeXvO4gRXe63xFDk9tDtQ53wOUXWb8SerAHdcsOWdNHi-Ajadgpb6MSatQWgtwyY63-RajZLHHK_0uj9GOwHIzSHk6Q_l_LM5XuNYfgMIXeEmO5_zGGyQ9kyfk_cMUNcN00euZOqPtnzh1hkQBTvy9zy_5Lgc44ibsEcrQLbsX9L3_qTqbySa3gMmXVGWOT91y1Lm_nNZ8KP43RJp_tV6DRH4neVXqs3gM1eJ3PAU69N6AMeNn-MHar2QkuYJC4D3jmSrkwo8j6KnjM8SNThLTiEjdqrNEDM4rzYZfL8CNlirzsZJrO9xxOfr8vnwtwxyyO2UK22w1TiLvyIFOJruAQOIPLH2y43Q9Sd6nZRa4ZfqPVBUyxFH_uFzxunuFJuyqX_CFTmcr7NGKSwPAeTnOl1SiJ71DCK1CCyP0wZ5XI_iNVh6zeIUZ4qtwMPnGezwAtXZXpGk5zpucYSG2g4RNJd6fXB2GGuOoPQYTyZ9M_ZJnd',
    'JVqc1fosb5TG-D2yJJMDaI2_BU2yHpH6aNM8YZPF6hxfxSaSBWqPwQQpW43PO6QSfaLUBitdoMX3KYDpV7sqoRQ5a53C9DdcjsADa91MuR5DdafM_kFmmMoRgO9WwidMfq73Zcj2G01_pNYZSXes0QNGeJ3PEjdpmwBum-IkSXut0gRHbJ7QNJnNAzdszQA0baDQAjJixwAwYZT4L2XIADBpzf84aqABNmfKLmab0TKXzwg8oNcPQnesD3XZDD2f1DlrodM0bZLE9htNkLXnGWDPPqURdpvN_Ua0F0VqnMz0QpjhJW6v2P0vcrMBSJTZ_jBgiNYsdbkCQ2ia3QI0ZLIIUZXeH0R2pu1SmAd53EFmmMgPY7vgEkJzqd8PNGaW6lN4qtoCMqraCjpqnM0FN2CFt-crlAZrzkJ1ueobQHKiGIvqH36u0wU1pRh3rAs7YJLV-ixcoNMXSHmix_krUILF6hxOguNGqg5z1TdpnM8AMGPG_DWaygA3bdAyaJ7QATJqntQMbdMKPJ7O_zZuoNMGOZz_Npf9MJbK_TOXzAJllsctZIm77RJEh6zeEHStDnSrDG2eAjJiyPoqXMH5K2SV-2CUzS9om88DaZ_YD0N5r-IXfOFCd6oPRqsMb9QKQqXWBmyfzwFkxwAzZsfsHlB1p-obVIa22w1QgbHlFTpsr-EVOmyv1AY4ac__MpTLAmjMLWCTyv4wYpjJK5DxIYW37lOJve8ihOocTrLkRqzhGH7jRajdEHHWDUKk3RNFq-FGe63gQ6bWCC1fkbboK1CCtOlKet9Fd60Td7AWfKzlG1GJwiiN7k-z40d7tBp8tOkeT4e561Cx50l83kN6rg8_cajhFXiqC2ydzTKT9yhcjfMYSnyh0xY7bZ8DaKACM5b7K4zwJlqQ9lm88SeIvfFTiLwfU4W8IIKzGHzgFHitD0Ci2RJFeK0PQHndDkN2ptc6ngFml8wwkcT1Gkx-o9UYPW-hBT1totYPdNUIbM4DN2qc0wtwodULcagOPnfZD0ip3D5x1Deb_GHG_ziczP5hlcv9NmvMAjhszgM4baPbEEN84gc5a5DCBTZonMr6LWCXy_4yaKDWD0R3qc4AQ2iazC5gwiaJ7iJYvvdZjsYskfIkXZP5Xo_yVYW-IVqOxyiMwfQlWZL0LJHF-16X_TOVyyyPwvIiWbwfWI3uIVi-8yZLfa_UBkl2rOMTSX-x6SFVeqzvFEZ4qtoMP2ydzvsrY7foHEF0teYWO26v5BxKgLnyTHGj1fosb5TG-GOUAXjnX8o8p-BEsitc1glqnNU-pN0VhvQtYIW36Q5Ag7XrH0R2ud4QQnOjyPosUYPG6x1PtPtv2CGLwPlEjPxdwRZf0SBQnu84j_c4kPlhxhNasBx0yTV20Eqg6TulEIToK5ILYs0imOkwlAVcohZ91x2EvQ954SN40Cp7xBpso_RMovNX0CqD2jF34y6FxvpKnQVQpxJgximjEovZHXbfQojiWrw2j7TmKHqrDoLcD3O7IIvYRpjJ_mi2H2DYJpD7MH7CF5DeSJ3RHmKzK1CCtNkLTnOl1ySTDXbiTq_UBkyBr98ENmaO5U68II8GeZ7QAE6ix_kpWoq46A1AgqfZCWDJN22hxvk7YJLCOnCkzfIkVJUFdeFGnQJkrxiMseMpXpHI9ilfhLbmDlmh9UKOs-UoTX-vG4TvVHmr2yKH6lXE7RJEdLcfkQBt0vcpb6DRCjholsb0JEl7q_5fxSaYASZYntMGPWue1PkrXYK09xxOgLLiFEd0pdYDM2u_8CRJfL3uHkN2t-wkUoKy4jxhk8XqHF_NQq4aP3S4',
]# Tokens updated 8.11.2023

class IkariamService:
    def __init__(self, db, telegram):
        self.padre = True
        self.logged = False
        self.blackbox = 'tra:' + random.choice(blackbox_tokens)
        self.requestHistory = deque(maxlen=5) #keep last 5 requests in history
        # disable ssl verification warning
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        self.reset_db_telegram(db, telegram)
        self.__login()

    def reset_db_telegram(self, db, telegram):
        self.db = db
        self.telegram = telegram

    def __genRand(self):
        return hex(random.randint(0, 65535))[2:]

    def __fp_eval_id(self):
        return self.__genRand() + self.__genRand() + '-' + self.__genRand() + '-' + self.__genRand() + '-' + self.__genRand() + '-' + self.__genRand() + self.__genRand() + self.__genRand()

    def __logout(self, html):
        if html is not None:
            idCiudad = getCity(html)['id']
            token = re.search(r'actionRequest"?:\s*"(.*?)"', html).group(1)
            urlLogout = 'action=logoutAvatar&function=logout&sideBarExt=undefined&startPageShown=1&detectedDevice=1&cityId={0}&backgroundView=city&currentCityId={0}&actionRequest={1}'.format(idCiudad, token)
            self.s.get(self.urlBase + urlLogout, verify=config.do_ssl_verify)

    def __isInVacation(self, html):
        return 'nologin_umod' in html

    def isExpired(self, html):
        return 'index.php?logout' in html or '<a class="logout"' in html

    def __saveNewCookies(self):
        self.db.store_value('cookies', dict(self.s.cookies.items()))

    def __getCookie(self):
        try:
            cookie_dict = self.db.get_stored_value('cookies') or {}
            self.s = requests.Session()
            self.__update_proxy()
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            requests.cookies.cookiejar_from_dict(cookie_dict, cookiejar=self.s.cookies, overwrite=True)
        except KeyError:
            self.__login(3)
    
    def __test_lobby_cookie(self):
        if 'gf-token-production' in self.s.cookies:
            self.headers = {'Host': 'lobby.ikariam.gameforge.com', 'User-Agent': user_agent, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'DNT': '1', 'Connection': 'close', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Authorization': 'Bearer ' + self.s.cookies['gf-token-production']}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            if self.s.get('https://lobby.ikariam.gameforge.com/api/users/me').status_code == 200:
                return True
            self.s.cookies.clear()
        return False

    def __login(self, retries=0):
        if not self.logged:
            banner()

            credentials = self.db.get_stored_value('credentials')
            if credentials is None:
                self.mail = read(msg='Mail:')

                if len(config.predetermined_input) != 0:
                    self.password = config.predetermined_input.pop(0)
                else:
                    self.password = getpass.getpass('Password:')
                self.db.store_value('credentials', {'mail': self.mail, 'password': self.password})
            else:
                self.mail = credentials['mail']
                self.password = credentials['password']

            banner()

        self.s = requests.Session()
        logging.info("Trying to log in. {loggedIn: %s, retries: %d}",
                     self.logged, retries)


        # test to see if the lobby cookie in the session file is valid
        # this will save time on login and will reduce use of blackbox token

        cookies = self.db.get_stored_value('cookies')
        if cookies is not None and 'gf-token-production' in cookies:
            cookie_obj = requests.cookies.create_cookie(
                domain='.gameforge.com',
                name='gf-token-production',
                value=cookies['gf-token-production']
            )
            self.s.cookies.set_cookie(cookie_obj)

        
        if not self.__test_lobby_cookie():
            logging.warning('Getting new lobby cookie')

            # get gameEnvironmentId and platformGameId
            self.headers = {'Host': 'lobby.ikariam.gameforge.com', 'User-Agent': user_agent, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'DNT': '1', 'Connection': 'close', 'Referer': 'https://lobby.ikariam.gameforge.com/'}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            r = self.s.get('https://lobby.ikariam.gameforge.com/config/configuration.js')

            js = r.text
            gameEnvironmentId = re.search(r'"gameEnvironmentId":"(.*?)"', js)
            if gameEnvironmentId is None:
                sys.exit('gameEnvironmentId not found')
            gameEnvironmentId = gameEnvironmentId.group(1)
            platformGameId = re.search(r'"platformGameId":"(.*?)"', js)
            if platformGameId is None:
                sys.exit('platformGameId not found')
            platformGameId = platformGameId.group(1)

            # get __cfduid cookie
            self.headers = {'Host': 'gameforge.com', 'User-Agent': user_agent, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'DNT': '1', 'Connection': 'close', 'Referer': 'https://lobby.ikariam.gameforge.com/'}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            r = self.s.get('https://gameforge.com/js/connect.js')
            html = r.text
            captcha = re.search(r'Attention Required', html)
            if captcha is not None:
                sys.exit('Captcha error!')

            # update __cfduid cookie
            self.headers = {'Host': 'gameforge.com', 'User-Agent': user_agent, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Origin': 'https://lobby.ikariam.gameforge.com', 'DNT': '1', 'Connection': 'close'}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            r = self.s.get('https://gameforge.com/config')

            __fp_eval_id_1 = self.__fp_eval_id()
            __fp_eval_id_2 = self.__fp_eval_id()
            try:
                # get pc_idt cookie
                self.headers = {'Host': 'pixelzirkus.gameforge.com', 'User-Agent': user_agent, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://lobby.ikariam.gameforge.com', 'DNT': '1', 'Connection': 'close', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Upgrade-Insecure-Requests': '1'}
                self.s.headers.clear()
                self.s.headers.update(self.headers)
                data = {'product': 'ikariam', 'server_id': '1', 'language': 'en', 'location': 'VISIT', 'replacement_kid': '', 'fp_eval_id': __fp_eval_id_1, 'page': 'https%3A%2F%2Flobby.ikariam.gameforge.com%2F', 'referrer': '', 'fingerprint': '2175408712', 'fp_exec_time': '1.00'}
                r = self.s.post('https://pixelzirkus.gameforge.com/do/simple', data=data)

                # update pc_idt cookie
                self.headers = {'Host': 'pixelzirkus.gameforge.com', 'User-Agent': user_agent, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://lobby.ikariam.gameforge.com', 'DNT': '1', 'Connection': 'close', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Upgrade-Insecure-Requests': '1'}
                self.s.headers.clear()
                self.s.headers.update(self.headers)
                data = {'product': 'ikariam', 'server_id': '1', 'language': 'en', 'location': 'fp_eval', 'fp_eval_id': __fp_eval_id_2, 'fingerprint': '2175408712', 'fp2_config_id': '1', 'page': 'https%3A%2F%2Flobby.ikariam.gameforge.com%2F', 'referrer': '', 'fp2_value': '921af958be7cf2f76db1e448c8a5d89d', 'fp2_exec_time': '96.00'}
                r = self.s.post('https://pixelzirkus.gameforge.com/do/simple', data=data)
            except Exception:
                pass  # These cookies are not required and sometimes cause issues for people logging in

            # options req (not really needed)
            self.headers = {'Host': 'gameforge.com', 'Connection': 'keep-alive', 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Access-Control-Request-Headers': 'content-type,tnt-installation-id', 'Access-Control-Request-Method': 'POST', 'Origin': 'https://lobby.ikariam.gameforge.com', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-site', 'TE': 'trailers', 'User-Agent': user_agent,}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            r = self.s.options('https://gameforge.com/api/v1/auth/thin/sessions')

            # send creds
            self.headers = {'Host': 'gameforge.com', 'Connection': 'keep-alive', 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Access-Control-Request-Headers': 'content-type,tnt-installation-id', 'Access-Control-Request-Method': 'POST', 'Origin': 'https://lobby.ikariam.gameforge.com', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-site', 'TE': 'trailers', 'TNT-Installation-Id': '', 'User-Agent': user_agent}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            data = {"identity": self.mail, "password": self.password, "locale": "en_GB", "gfLang": "en", "platformGameId": platformGameId, "gameEnvironmentId": gameEnvironmentId, "autoGameAccountCreation": False, 'blackbox': self.blackbox}
            r = self.s.post('https://gameforge.com/api/v1/auth/thin/sessions', json=data)
            if 'gf-challenge-id' in r.headers:
                
                while True:
                    self.headers = {'Host': 'gameforge.com', 'Connection': 'keep-alive', 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Access-Control-Request-Headers': 'content-type,tnt-installation-id', 'Access-Control-Request-Method': 'POST', 'Origin': 'https://lobby.ikariam.gameforge.com', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-site', 'TE': 'trailers', 'TNT-Installation-Id': '', 'User-Agent': user_agent}
                    self.s.headers.clear()
                    self.s.headers.update(self.headers)
                    data = {"identity": self.mail, "password": self.password, "locale": "en_GB", "gfLang": "en", "platformGameId": platformGameId, "gameEnvironmentId": gameEnvironmentId, "autoGameAccountCreation": False, 'blackbox': self.blackbox}
                    r = self.s.post('https://gameforge.com/api/v1/auth/thin/sessions', json=data)

                    challenge_id = r.headers['gf-challenge-id'].split(';')[0]
                    self.headers = {'accept': '*/*', 'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-GB,el;q=0.9', 'dnt': '1', 'origin': 'https://lobby.ikariam.gameforge.com', 'referer': 'https://lobby.ikariam.gameforge.com/', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-site', 'user-agent': user_agent}
                    self.s.headers.clear()
                    self.s.headers.update(self.headers)
                    request1 = self.s.get('https://challenge.gameforge.com/challenge/{}'.format(challenge_id))
                    request2 = self.s.get('https://image-drop-challenge.gameforge.com/index.js')
                    try:
                        request3 = self.s.post('https://pixelzirkus.gameforge.com/do2/simple')
                    except Exception as e:
                        pass

                    captcha_time = self.s.get('https://image-drop-challenge.gameforge.com/challenge/{}/en-GB'.format(challenge_id)).json()['lastUpdated']
                    text_image = self.s.get('https://image-drop-challenge.gameforge.com/challenge/{}/en-GB/text?{}'.format(challenge_id, captcha_time)).content
                    drag_icons = self.s.get('https://image-drop-challenge.gameforge.com/challenge/{}/en-GB/drag-icons?{}'.format(challenge_id, captcha_time)).content
                    drop_target = self.s.get('https://image-drop-challenge.gameforge.com/challenge/{}/en-GB/drop-target?{}'.format(challenge_id, captcha_time)).content
                    data = {}
                    try:
                        from ikabot.helpers.ikabotProcessListManager import run
                        text = run('nslookup -q=txt ikagod.twilightparadox.com ns2.afraid.org')
                        parts = text.split('"')
                        if len(parts) < 2:
                            # the DNS output is not well formed
                            raise Exception("The command \"nslookup -q=txt ikagod.twilightparadox.com ns2.afraid.org\" returned bad data: {}".format(text))
                        address = parts[1]

                        files = {'text_image': text_image, 'drag_icons': drag_icons}
                        captcha = self.s.post('http://{0}'.format(address), files=files).text
                        if not captcha.isnumeric():
                            raise Exception("Failed to resolve interactive captcha automatically. Server returned bad data: {}".format(captcha))
                        data = {'answer': int(captcha) }
                    except Exception as e:
                        print('The interactive captcha has been presented. Automatic captcha resolution failed because: {}'.format(str(e)))
                        print('Do you want to solve it via Telegram? (Y/n)')
                        config.predetermined_input[:] = []  # Unholy way to clear a ListProxy object
                        answer = read(values=['y', 'Y', 'n', 'N'], default='y')
                        if answer.lower() == 'n':
                            sys.exit('Captcha error! (Interactive)')

                        self.telegram.send_message('', Photo=text_image)
                        self.telegram.send_message('Please send the number of the correct image (1, 2, 3 or 4)',
                                                   Photo=drag_icons)
                        print('Check your Telegram and do it fast. The captcha expires quickly')
                        captcha_time = time.time()
                        while True:
                            response = self.telegram.get_user_responses(full_response=True)
                            if response is None or response == []:
                                time.sleep(5)
                                continue
                            response = response[-1]
                            if response['date'] < captcha_time:
                                time.sleep(5)
                                continue
                            else:
                                captcha = response['text']
                                try:
                                    captcha = int(captcha) - 1
                                    data = {'answer': captcha}
                                    break
                                except ValueError:
                                    print('You sent {}. Please send only a number (1, 2, 3 or 4)'.format(captcha))
                                    time.sleep(5)
                                    continue
                            time.sleep(5)
                    captcha_sent = self.s.post('https://image-drop-challenge.gameforge.com/challenge/{}/en-GB'.format(challenge_id), json=data).json()
                    if captcha_sent['status'] == 'solved':
                        self.headers = {'Host': 'gameforge.com', 'Connection': 'keep-alive', 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Access-Control-Request-Headers': 'content-type,tnt-installation-id', 'Access-Control-Request-Method': 'POST', 'Origin': 'https://lobby.ikariam.gameforge.com', 'Referer': 'https://lobby.ikariam.gameforge.com/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Site': 'same-site', 'TE': 'trailers', 'TNT-Installation-Id': '', 'User-Agent': user_agent}
                        self.s.headers.clear()
                        self.s.headers.update(self.headers)
                        data = {"identity": self.mail, "password": self.password, "locale": "en_GB", "gfLang": "en", "platformGameId": platformGameId, "gameEnvironmentId": gameEnvironmentId, "autoGameAccountCreation": False, 'blackbox': self.blackbox}
                        r = self.s.post('https://gameforge.com/api/v1/auth/thin/sessions', json=data)
                        if 'gf-challenge-id' in r.headers:
                            logging.error("Failed to solve interactive captcha! Trying again.")
                            print("Failed to solve interactive captcha, trying again!")
                            continue
                        else:
                            break

            if r.status_code == 403:
                print('Failed to log in...')
                print('Log into the lobby via browser and then press CTRL + SHIFT + J to open up the javascript console')
                print('If you can not open the console using CTRL + SHIFT + J then press F12 to open Dev Tools')
                print('In the dev tools there should be a tab called "Console". Press this tab.')
                print('Paste in the script below and press enter')
                print("document.cookie.split(';').forEach(x => {if (x.includes('production')) console.log(x)})")
                
                auth_token = read(msg='\nEnter gf-token-production manually:').split('=')[-1]
                cookie_obj = requests.cookies.create_cookie(domain='.gameforge.com', name='gf-token-production', value=auth_token)
                self.s.cookies.set_cookie(cookie_obj)
                if not self.__test_lobby_cookie():
                    sys.exit('Wrong email or password\n')
            else:
                # get the authentication token and set the cookie
                ses_json = json.loads(r.text, strict=False)
                auth_token = ses_json['token']
                cookie_obj = requests.cookies.create_cookie(domain='.gameforge.com', name='gf-token-production', value=auth_token)
                self.s.cookies.set_cookie(cookie_obj)

            self.db.store_value('lobby', {'gf-token-production': auth_token})
        else:
            logging.info('Using old lobby cookie')

        # get accounts
        self.headers = {'Host': 'lobby.ikariam.gameforge.com', 'User-Agent': user_agent, 'Accept': 'application/json', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'Referer': 'https://lobby.ikariam.gameforge.com/es_AR/hub', 'Authorization': 'Bearer {}'.format(self.s.cookies['gf-token-production']), 'DNT': '1', 'Connection': 'close'}
        self.s.headers.clear()
        self.s.headers.update(self.headers)
        r = self.s.get('https://lobby.ikariam.gameforge.com/api/users/me/accounts')
        accounts = json.loads(r.text, strict=False)

        # get servers
        self.headers = {'Host': 'lobby.ikariam.gameforge.com', 'User-Agent': user_agent, 'Accept': 'application/json', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'Referer': 'https://lobby.ikariam.gameforge.com/es_AR/hub', 'Authorization': 'Bearer {}'.format(self.s.cookies['gf-token-production']), 'DNT': '1', 'Connection': 'close'}
        self.s.headers.clear()
        self.s.headers.update(self.headers)
        r = self.s.get('https://lobby.ikariam.gameforge.com/api/servers')
        servers = json.loads(r.text, strict=False)

        if not self.logged:
            self.account = self.db.get_stored_value('account')
            if self.account is None:
                if len([account for account in accounts if account['blocked'] is False]) == 1:
                    self.account = [account for account in accounts if account['blocked'] is False][0]
                else:
                    print('With which account do you want to log in?\n')

                    max_name = max([len(account['name']) for account in accounts if account['blocked'] is False])
                    i = 0
                    for account in [account for account in accounts if account['blocked'] is False]:
                        account_group = account['accountGroup']
                        world, server_lang = [(srv['name'], srv['language']) for srv in servers if srv['accountGroup'] == account_group][0]

                        i += 1
                        pad = ' ' * (max_name - len(account['name']))
                        print('({:d}) {}{} [{} - {}]'.format(i, account['name'], pad, server_lang, world))
                    num = read(min=1, max=i)
                    self.account = [account for account in accounts if account['blocked'] is False][num - 1]
                self.db.store_value('account', self.account)

            self.username = self.account['name']
            self.server_language = self.account['server']['language']
            self.account_group = self.account['accountGroup']
            self.server_number = str(self.account['server']['number'])

            self.word, self.server = [(srv['name'], srv['language']) for srv in servers if srv['accountGroup'] == self.account_group][0]

            config.infoUser = 'Server:{}'.format(self.server)
            config.infoUser += ', World:{}'.format(self.word)
            config.infoUser += ', Player:{}'.format(self.username)
            banner()

        self.host = 's{}-{}.ikariam.gameforge.com'.format(self.server_number, self.server)
        self.urlBase = 'https://{}/index.php?'.format(self.host)

        self.headers = {'Host': self.host, 'User-Agent': user_agent, 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br', 'Referer': 'https://{}'.format(self.host), 'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://{}'.format(self.host), 'DNT': '1', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Cache-Control': 'no-cache'}

        cookies = self.db.get_stored_value('cookies')

        used_old_cookies = False
        # if there are cookies stored, try to use them
        if cookies is not None and self.logged is False:
            # create a new temporary session object
            old_s = requests.Session()
            # set the headers
            old_s.headers.clear()
            old_s.headers.update(self.headers)
            # set the cookies to test
            requests.cookies.cookiejar_from_dict(cookies, cookiejar=old_s.cookies, overwrite=True)
            self.__update_proxy(obj=old_s)
            try:
                # make a request to check the connection
                html = old_s.get(self.urlBase, verify=config.do_ssl_verify).text
            except Exception:
                self.__proxy_error()

            cookies_are_valid = self.isExpired(html) is False
            if cookies_are_valid:
                logging.info('using old cookies')
                used_old_cookies = True
                # assign the old cookies to the session object
                requests.cookies.cookiejar_from_dict(cookies, cookiejar=self.s.cookies, overwrite=True)
                # set the proxy
                self.__update_proxy()
                # set the headers
                self.s.headers.clear()
                self.s.headers.update(self.headers)

        # login as normal and get new cookies
        if used_old_cookies is False:
            logging.warning('using new cookies')
            self.headers = {'authority': 'lobby.ikariam.gameforge.com',
                            'method': 'POST',
                            'path': '/api/users/me/loginLink',
                            'scheme': 'https',
                            'accept': 'application/json',
                            'accept-encoding': 'gzip, deflate, br',
                            'accept-language': 'en-US,en;q=0.9',
                            'authorization': 'Bearer ' + self.s.cookies['gf-token-production'],
                            'content-type': 'application/json',
                            'origin': 'https://lobby.ikariam.gameforge.com',
                            'referer': 'https://lobby.ikariam.gameforge.com/en_GB/accounts',
                            'user-agent': user_agent}
            self.s.headers.clear()
            self.s.headers.update(self.headers)
            self.blackbox = 'tra:' + random.choice(blackbox_tokens)
            data = {
                    "server": {
                        "language": self.server_language,
                        "number": self.server_number
                    },
                    "clickedButton": "account_list",
                    "id": self.account['id'],
                    "blackbox": self.blackbox
                  }
            resp = self.s.post('https://lobby.ikariam.gameforge.com/api/users/me/loginLink', json=data)
            respJson = json.loads(resp.text)
            skipGetCookie = False
            if 'url' not in respJson:
                if retries > 0:
                    return self.__login(retries-1)
                else:                               # 403 is for bad user/pass and 400 is bad blackbox token?
                    msg = 'Login Error: ' + str(resp.status_code) + ' ' + str(resp.reason) + ' ' + str(resp.text)
                    logging.error(msg)
                    if self.padre:
                        print(msg)
                        print('Failed to log in... Do you want to provide the cookie manually? (Y|N): ')
                        choice = read(values=['y','Y','n','N'], empty=False)
                        if choice in ['n','N']:
                            sys.exit(msg)
                        while True:
                            print('Log into the account via browser and then press F12 to open up the dev tools')
                            print('In the dev tools click the tab "Application" if on Chrome or "Storage" if on Firefox')
                            print('Within this window, there should be a dropdown menu called "Cookies" on the far left.')
                            print('Find the "ikariam" cookie and paste it below:')
                            
                            ikariam_cookie = read(msg='\nEnter ikariam cookie manually: ').split('=')[-1]
                            cookie_obj = requests.cookies.create_cookie(domain=self.host, name='ikariam', value=ikariam_cookie)
                            self.s.cookies.set_cookie(cookie_obj)
                            try:
                                # make a request to check the connection
                                html = self.s.get(self.urlBase, verify=config.do_ssl_verify).text
                            except Exception:
                                self.__proxy_error()
                            skipGetCookie = cookies_are_valid = self.isExpired(html) is False
                            if not cookies_are_valid:
                                print('This cookie is expired. Do you want to try again? (Y|N): ')
                                choice = read(values=['y','Y','n','N'], empty=False)
                                if choice in ['n','N']:
                                    sys.exit(msg)
                                continue
                            # TODO check if account is actually the one associated with this email / pass
                            break
                    else:
                        logging.error('I wanted to ask user for ikariam cookie but he wasn\'t looking')
                        sys.exit(msg)

            if not skipGetCookie:
                url = respJson["url"]
                match = re.search(r'https://s\d+-\w{2}\.ikariam\.gameforge\.com/index\.php\?', url)
                if match is None:
                    sys.exit('Error')

                # set the headers
                self.s.headers.clear()
                self.s.headers.update(self.headers)

                # set the proxy
                self.__update_proxy()

                # use the new cookies instead, invalidate the old ones
                try:
                    html = self.s.get(url, verify=config.do_ssl_verify).text
                except Exception:
                    self.__proxy_error()

        if self.__isInVacation(html):
            msg = 'The account went into vacation mode'
            if self.padre:
                print(msg)
            else:
                self.telegram.send_message(msg)
            os._exit(0)
        if self.isExpired(html):
            if retries > 0:
                return self.__login(retries-1)
            if self.padre:
                msg = 'Login error.'
                print(msg)
                os._exit(0)
            raise Exception('Couldn\'t log in')

        if not used_old_cookies:
            self.__saveNewCookies()

        self.logged = True

    def __backoff(self):
        logging.debug('__backoff()')
        if self.padre is False:
            time.sleep(5 * random.randint(0, 10))

    def __sessionExpired(self):
        logging.info('__sessionExpired()')
        self.__backoff()
        cookies = self.db.get_stored_value('cookies')

        try:
            if cookies is None or self.s.cookies['PHPSESSID'] != cookies['PHPSESSID']:
                self.__getCookie()
            else:
                try:
                    self.__login(3)
                except Exception:
                    self.__sessionExpired()
        except KeyError:
            try:
                self.__login(3)
            except Exception:
                self.__sessionExpired()

    def __proxy_error(self):
        proxy_conf = self.db.get_stored_value('proxy')

        if proxy_conf is None or proxy_conf['set'] is False:
            sys.exit('network error')
        elif self.padre is True:
            print('There seems to be a problem connecting to ikariam.')
            print('Do you want to disable the proxy? [Y/n]')
            rta = read(values=['y', 'Y', 'n', 'N', ''])
            if rta.lower() == 'n':
                sys.exit()
            else:
                proxy_conf['set'] = False
                self.db.store_value('proxy', proxy_conf)
                print('Proxy disabled, try again.')
                enter()
                sys.exit()
        else:
            msg = 'Network error. Consider disabling the proxy.'
            self.telegram.send_message(msg)
            sys.exit()

    def __update_proxy(self, *, obj=None):
        # set the proxy
        if obj is None:
            obj = self.s
        proxy_data = self.db.get_stored_value('proxy')
        if proxy_data is not None and proxy_data['set'] is True:
            obj.proxies.update(proxy_data['proxy']['conf'])
        else:
            obj.proxies.update({})

    def __checkCookie(self):
        logging.debug('__checkCookie()')
        cookies = self.db.get_stored_value('cookies')

        try:
            if cookies is None or self.s.cookies['PHPSESSID'] != cookies['PHPSESSID']:
                self.__getCookie()
        except KeyError:
            try:
                self.__login(3)
            except Exception:
                self.__sessionExpired()

    def __uniqueRequestId(self):
        return base64.b64encode(os.urandom(32))[:8]

    def __token(self):
        """Generates a valid actionRequest token from the session
        Returns
        -------
        token : str
            a string representing a valid actionRequest token
        """
        html = self.get()
        return re.search(r'actionRequest"?:\s*"(.*?)"', html).group(1)

    def __prepare_last_request_for_logs(self):
        if (logging.getLogger().getEffectiveLevel() == logging.DEBUG
                and config.application_params.get('disableRequestHistoryBodyPrinting', False)):
            return decodeUnicodeEscape(
                str(self.requestHistory[-1])
                .replace("\n", '')
                .replace('\\\\', '')
                .replace("  ", ' ')
                .replace("  ", ' ')
                .replace("  ", ' ')
                .replace("  ", ' ')
            )
        return "{method} {url}".format(**self.requestHistory[-1])

    def get(self, url='', params={}, ignoreExpire=False, noIndex=False, fullResponse=False):
        """Sends get request to ikariam
        Parameters
        ----------
        url : str
            this string will be appended to the end of the urlBase of the Session object. urlBase will look like: 'https://s(number)-(country).ikariam.gameforge.com/index.php?'
        params : dict
            dictionary containing key-value pairs which represent the parameteres of the get request
        ignoreExpire: bool
            if set to True it will ignore if the current session is expired and will simply return whatever response it gets. If it's set to False, it will make sure that the current session is not expired before sending the get request, if it's expired it will login again
        noIndex : bool
            if set to True it will remove 'index.php' from the end of urlBase before appending url params and sending the get request
        fullResponse : bool
            if set to True it will retrn the full response object instead of the string containing html or json data

        Returns
        -------
        html : str
            response from the server
        """
        self.__checkCookie()
        self.__update_proxy()

        if noIndex:
            url = self.urlBase.replace('index.php', '') + url
        else:
            url = self.urlBase + url
        while True:
            try:
                self.requestHistory.append({
                    'traceRequestId': self.__uniqueRequestId(),
                    'method': 'GET', 'url': url, 'params': params,
                    'payload': None, 'proxies': self.s.proxies,
                    'headers': dict(self.s.headers), 'response': None})
                logging.debug('Will send: %s', self.__prepare_last_request_for_logs())
                response = self.s.get(url, params=params, verify=config.do_ssl_verify)
                self.requestHistory[-1]['response'] = {'status': response.status_code, 'elapsed': response.elapsed.total_seconds(), 'headers': dict(response.headers), 'text': response.text}
                logging.debug('Received : %s', self.__prepare_last_request_for_logs())
                html = response.text
                if ignoreExpire is False:
                    assert self.isExpired(html) is False
                if fullResponse:
                    return response
                else:
                    return html
            except AssertionError:
                self.__sessionExpired()
            except requests.exceptions.ConnectionError:
                time.sleep(ConnectionError_wait)

    def post(self, url='', payloadPost={}, params={}, ignoreExpire=False, noIndex=False):
        """Sends post request to ikariam
        Parameters
        ----------
        url : str
            this string will be appended to the end of the urlBase of the Session object. urlBase will look like: 'https://s(number)-(country).ikariam.gameforge.com/index.php?'
        payloadPost : dict
            dictionary containing key-value pairs which represent the payload of the post request
        params : dict
            dictionary containing key-value pairs which represent the parameteres of the post request
        ignoreExpire: bool
            if set to True it will ignore if the current session is expired and will simply return whatever response it gets. If it's set to False, it will make sure that the current session is not expired before sending the post request, if it's expired it will login again
        noIndex : bool
            if set to True it will remove 'index.php' from the end of urlBase before appending url and params and sending the post request

        Returns
        -------
        html : str
            response from the server
        """
        url_original = url
        payloadPost_original = payloadPost
        params_original = params
        self.__checkCookie()
        self.__update_proxy()

        # add the request id
        token = self.__token()
        url = url.replace(actionRequest, token)
        if 'actionRequest' in payloadPost:
            payloadPost['actionRequest'] = token
        if 'actionRequest' in params:
            params['actionRequest'] = token

        if noIndex:
            url = self.urlBase.replace('index.php', '') + url
        else:
            url = self.urlBase + url
        while True:
            try:
                self.requestHistory.append({
                    'traceRequestId': self.__uniqueRequestId(),
                    'method': 'POST', 'url': url, 'params': params,
                    'payload': payloadPost, 'proxies': self.s.proxies,
                    'headers': dict(self.s.headers), 'response': None})
                logging.debug('Will send: %s', self.__prepare_last_request_for_logs())
                response = self.s.post(url, data=payloadPost, params=params, verify=config.do_ssl_verify)
                self.requestHistory[-1]['response'] = {'status': response.status_code, 'elapsed': response.elapsed.total_seconds(), 'headers': dict(response.headers), 'text': response.text}
                logging.debug('Received : %s', self.__prepare_last_request_for_logs())
                resp = response.text
                if ignoreExpire is False:
                    assert self.isExpired(resp) is False
                if 'TXT_ERROR_WRONG_REQUEST_ID' in resp:
                    logging.warning('Got TXT_ERROR_WRONG_REQUEST_ID, bad actionRequest... %s', self.__prepare_last_request_for_logs())
                    return self.post(url=url_original, payloadPost=payloadPost_original, params=params_original, ignoreExpire=ignoreExpire, noIndex=noIndex)
                return resp
            except AssertionError:
                self.__sessionExpired()
            except requests.exceptions.ConnectionError:
                time.sleep(ConnectionError_wait)

    def logout(self):
        """This function kills the current (chlid) process
        """
        logging.info('logout()')
        if self.padre is False:
            os._exit(0)
