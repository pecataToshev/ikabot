#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import math
import re
from decimal import Decimal

from ikabot.bot.bot import Bot
from ikabot.bot.transportGoodsBot import TransportGoodsBot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.gui import addThousandSeparator
from ikabot.helpers.naval import TransportShip, get_transport_ships_size
from ikabot.helpers.planRoutes import waitForAvailableShips


class BuyResourcesBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.offers = bot_config['offers']
        self.amount_to_buy = bot_config['amountToBuy']
        self.building_position = bot_config['buildingPosition']

    def _get_process_info(self) -> str:
        return 'I will buy {} from {} to {}'.format(
            addThousandSeparator(self.bot_config['amountToBuy']),
            materials_names[self.bot_config['resource']],
            self.bot_config['cityName'],
        )

    def _start(self) -> None:
        while True:
            ship_size = get_transport_ships_size(self.ikariam_service, getCurrentCityId(self.ikariam_service), TransportShip.TRANSPORT_SHIP)
            for offer in self.offers:
                if self.amount_to_buy == 0:
                    return
                if offer['amountAvailable'] == 0:
                    continue

                ships_available = waitForAvailableShips(self.ikariam_service, self._wait)
                storage_capacity = ships_available * ship_size
                buy_amount = min(self.amount_to_buy, storage_capacity, offer['amountAvailable'])

                self.amount_to_buy -= buy_amount
                offer['amountAvailable'] -= buy_amount
                self.__buy(offer, buy_amount, ship_size, ships_available)
                # start from the beginning again, so that we always buy from the cheapest offers fisrt
                break

    def __buy(self, offer, amount_to_buy, ship_size, ships_available):
        ships = int(math.ceil((Decimal(amount_to_buy) / Decimal(ship_size))))
        data_dict = {
            'action': 'transportOperations',
            'function': 'buyGoodsAtAnotherBranchOffice',
            'cityId': offer['cityId'],
            'destinationCityId': offer['destinationCityId'],
            'oldView': 'branchOffice',
            'position': self.building_position,
            'avatar2Name': offer['jugadorAComprar'],
            'city2Name': offer['ciudadDestino'],
            'type': int(offer['type']),
            'activeTab': 'bargain',
            'transportDisplayPrice': 0,
            'premiumTransporter': 0,
            'normalTransportersMax': ships_available,
            'capacity': 5,
            'max_capacity': 5,
            'jetPropulsion': 0,
            'transporters': ships,
            'backgroundView': 'city',
            'currentCityId': offer['cityId'],
            'templateView': 'takeOffer',
            'currentTab': 'bargain',
            'actionRequest': actionRequest,
            'ajax': 1
        }
        url = 'view=takeOffer&destinationCityId={}&oldView=branchOffice&activeTab=bargain&cityId={}&position={}&type={}&resource={}&backgroundView=city&currentCityId={}&templateView=branchOffice&actionRequest={}&ajax=1'.format(offer['destinationCityId'], offer['cityId'], offer['position'], offer['type'], offer['resource'], offer['cityId'], actionRequest)
        data = self.ikariam_service.post(url)
        html = json.loads(data, strict=False)[1][1][1]
        hits = re.findall(r'"tradegood(\d)Price"\s*value="(\d+)', html)
        for hit in hits:
            data_dict['tradegood{}Price'.format(hit[0])] = int(hit[1])
            data_dict['cargo_tradegood{}'.format(hit[0])] = 0
        hit = re.search(r'"resourcePrice"\s*value="(\d+)', html)
        if hit:
            data_dict['resourcePrice'] = int(hit.group(1))
            data_dict['cargo_resource'] = 0
        resource = offer['resource']
        if resource == 'resource':
            data_dict['cargo_resource'] = amount_to_buy
        else:
            data_dict['cargo_tradegood{}'.format(resource)] = amount_to_buy
        self.ikariam_service.post(params=data_dict)
        logging.info('I buy %s to %s from %s', addThousandSeparator(amount_to_buy), offer['ciudadDestino'], offer['jugadorAComprar'])
