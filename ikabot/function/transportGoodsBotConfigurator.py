#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.transportGoodsBot import TransportGoodsBot, TransportJob
from ikabot.config import materials_names
from ikabot.helpers.database import Database
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.citiesAndIslands import chooseCity
from ikabot.helpers.userInput import askForValue, askUserYesNo
from ikabot.helpers.telegram import Telegram
from ikabot.web.ikariamService import IkariamService


def __plan_route(ikariam_service: IkariamService, routes: list[TransportJob]):
    banner()
    print('Origin city:')
    origin_city = chooseCity(ikariam_service)

    banner()
    print('Destination city')
    target_city = chooseCity(ikariam_service, foreign=True)

    if origin_city['id'] == target_city['id']:
        return None

    resources_left = origin_city['availableResources']
    for route in routes:
        if route.origin_city['id'] == origin_city['id']:
            for i in range(len(materials_names)):
                resources_left[i] -= route.resources[i]

        # the destination city might be from another player
        if target_city['isOwnCity'] and route.target_city['id'] == target_city['id']:
            for i in range(len(materials_names)):
                target_city['freeSpaceForResources'][i] -= route.resources[i]

    print('Available:')
    for i in range(len(materials_names)):
        print('{}:{} '.format(materials_names[i], addThousandSeparator(resources_left[i])), end='')
    print('')

    print('Send:')
    send = []
    for i, material in enumerate(materials_names):
        val = askForValue('{:>10}:'.format(material), resources_left[i])
        send.append(val)

    if sum(send) == 0:
        return None

    return TransportJob(origin_city, target_city, send)


def transport_goods_bot_configurator(ikariam_service: IkariamService, db: Database, telegram:Telegram):
    routes: list[TransportJob] = []
    while True:
        try:
            print('Origin city:')
            try:
                _route = __plan_route(ikariam_service, routes)
            except KeyboardInterrupt:
                _route = None

            if _route is not None:
                banner()
                print('About to send from {} to {}'.format(_route.origin_city['cityName'],
                                                           _route.target_city['cityName']))
                send = _route.resources
                for i in range(len(materials_names)):
                    if send[i] > 0:
                        print('{:>10}: {} '.format(materials_names[i], addThousandSeparator(send[i])))
                print('')

                if askUserYesNo('Proceed'):
                    routes.append(_route)

            if not askUserYesNo('Create another shipment'):
                break
        except KeyboardInterrupt:
            if len(routes) > 0 and askUserYesNo('Do you want to send the configured shipments'):
                break
            return

    if len(routes) == 0:
        print('No shipments to execute')
        enter()
        return

    TransportGoodsBot(
        ikariam_service=ikariam_service,
        bot_config={
            'jobs': routes
        }
    ).start(
        action='Transport Resources',
        objective='Move resources',
    )
