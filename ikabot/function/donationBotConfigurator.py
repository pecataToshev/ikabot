#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.donationBot import DonationBot
from ikabot.config import materials_names

from ikabot.helpers.database import Database
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.pedirInfo import getIdsOfCities, read

from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def donation_bot_configurator(ikariam_service: IkariamService, db: Database, telegram: Telegram):
    banner()
    (cities_ids, cities) = getIdsOfCities(ikariam_service)
    cities_dict = {}
    initials = [material_name[0] for material_name in materials_names]
    print('Enter how often you want to donate in minutes. (min = 1, default = 1 day)')
    waiting_time = read(min=1, digit=True, default=1 * 24 * 60)
    print(
        'Enter a maximum additional random waiting time between donations in minutes. (min = 0, default = 1 hour)')
    max_random_waiting_time = read(min=0, digit=True, default=1 * 60)
    print("""Which donation method would you like to use to donate automatically? (default = 1)
(1) Donate exceeding percentage of your storage capacity
(2) Donate a percentage of production
(3) Donate specific amount
    """)
    donate_method = read(min=1, max=3, digit=True, default=1)
    for cityId in cities_ids:
        tradegood = cities[cityId]['tradegood']
        initial = initials[int(tradegood)]
        print(
            'In {} ({}), Do you wish to donate to the forest, to the trading good, to both or none? [f/t/b/n]'.format(
                cities[cityId]['name'], initial))
        f = 'f'
        t = 't'
        b = 'b'
        n = 'n'

        rta = read(values=[f, f.upper(), t, t.upper(), b, b.upper(), n, n.upper()])
        if rta.lower() == f:
            donation_type = 'resource'
        elif rta.lower() == t:
            donation_type = 'tradegood'
        elif rta.lower() == b:
            donation_type = 'both'
        else:
            donation_type = None
            percentage = None

        if donation_type is not None and donate_method == 1:
            print(
                'What is the maximum percentage of your storage capacity that you wish to keep occupied? (the resources that exceed it, will be donated) (default: 80%)')
            percentage = read(min=0, max=100, empty=True)
            if percentage == '':
                percentage = 80
            elif percentage == 100:  # if the user is ok with the storage beeing totally full, don't donate at all
                donation_type = None
        elif donation_type is not None and donate_method == 2:
            print(
                'What is the percentage of your production that you wish to donate? (enter 0 to disable donation for the town) (default: 50%)')
            percentage = read(min=0, max=100, empty=True)  # max_random_waiting_time increases inaccuracy
            if percentage == '':
                percentage = 50
            elif percentage == 0:
                donation_type = None
        elif donation_type is not None and donate_method == 3:
            print(
                'What is the amount would you like to donate? (enter 0 to disable donation for the town) (default: 10000)')
            percentage = read(min=0, max=1000000,
                              empty=True)  # no point changing the variable's name everywhere just for this
            if percentage == '':
                percentage = 10000
            elif percentage == 0:
                donation_type = None

        cities_dict[cityId] = {'donation_type': donation_type, 'percentage': percentage}

        print('I will donate every {} minutes.'.format(waiting_time))

    DonationBot(
        ikariam_service=ikariam_service,
        bot_config={
            'cities_ids': cities_ids,
            'cities_dict': cities_dict,
            'waiting_time': waiting_time,
            'max_random_waiting_time': max_random_waiting_time,
            'donate_method': donate_method,
        }
    ).start(
        action='Donations',
        objective='Every {} minutes'.format(waiting_time)
    )

    enter()
