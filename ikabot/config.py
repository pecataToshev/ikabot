#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import random


# only use common browsers
if random.randint(0, 1) == 0:
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
else:
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'

update_msg = ''

isWindows = os.name == 'nt'
if isWindows:
    LOG_DIR = os.getenv('temp')
else:
    LOG_DIR = '/tmp'
LOG_DIR = os.path.join(LOG_DIR, 'ikabot')
LOG_FILE = os.path.join(LOG_DIR, 'ikabot.log')

do_ssl_verify = True

BOT_NAME = ''
infoUser = ''

ikaFile = '.ikabot'
DB_FILE = os.path.join(os.path.expanduser("~"), '.ikabot.db')

city_url = 'view=city&cityId='
island_url = 'view=island&islandId='

prompt = ' >>  '

materials_names = ['Wood', 'Wine', 'Marble', 'Cristal', 'Sulfur']
materials_names_tec = ['wood', 'wine', 'marble', 'glass', 'sulfur']
material_img_hash = ['19c3527b2f694fb882563c04df6d8972', 'c694ddfda045a8f5ced3397d791fd064', 'bffc258b990c1a2a36c5aeb9872fc08a', '1e417b4059940b2ae2680c070a197d8c', '9b5578a7dfa3e98124439cca4a387a61']

ConnectionError_wait = 5 * 60
actionRequest = 'REQUESTID'

predetermined_input = []
application_params = {}

MAXIMUM_CITY_NAME_LENGTH = 20
SECONDS_IN_HOUR = 60 * 60
