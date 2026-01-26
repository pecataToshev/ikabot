#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import math
import re
from decimal import Decimal

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, materials_names
from ikabot.helpers.citiesAndIslands import getCurrentCityId
from ikabot.helpers.gui import addThousandSeparator
from ikabot.helpers.market import execute_market_offer_transfer
from ikabot.helpers.naval import TransportShip, get_transport_ships_size
from ikabot.helpers.planRoutes import waitForAvailableShips


class BuyMarketBot(Bot):
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
                ships_to_use = min(ships_available, 30)
                storage_capacity = ships_to_use * ship_size
                buy_amount = min(self.amount_to_buy, storage_capacity, offer['amountAvailable'])

                self.amount_to_buy -= buy_amount
                offer['amountAvailable'] -= buy_amount
                self.__buy(offer, buy_amount, ship_size, ships_available)
                # start from the beginning again, so that we always buy from the cheapest offers fisrt
                self._wait(5, 'Wait before next batch. Remaining: {}'.format(addThousandSeparator(self.amount_to_buy)), max_random=10)
                break

    def __buy(self, offer, amount_to_buy, ship_size, ships_available):
        ships_used = int(math.ceil((Decimal(amount_to_buy) / Decimal(ship_size))))
        
        # Get price from the takeOffer view
        url = 'view=takeOffer&destinationCityId={}&oldView=branchOffice&activeTab=bargain&cityId={}&position={}&type={}&resource={}&backgroundView=city&currentCityId={}&templateView=branchOffice&actionRequest={}&ajax=1'.format(offer['destinationCityId'], offer['cityId'], offer['position'], offer['type'], offer['resource'], offer['cityId'], actionRequest)
        data = self.ikariam_service.post(url)
        html = json.loads(data, strict=False)[1][1][1]
        
        price = 0
        resource_type = offer['resource']
        
        if resource_type == 'resource': # Wood
            hit = re.search(r'"resourcePrice"\s*value="(\d+)', html)
            if hit:
                price = int(hit.group(1))
        else: # Tradegood
            hits = re.findall(r'"tradegood(\d)Price"\s*value="(\d+)', html)
            for hit in hits:
                if hit[0] == str(resource_type):
                    price = int(hit[1])
                    break
        
        execute_market_offer_transfer(
            session=self.ikariam_service,
            city_id=offer['cityId'],
            destination_city_id=offer['destinationCityId'],
            market_position=self.building_position,
            function_name='buyGoodsAtAnotherBranchOffice',
            resource_type=resource_type,
            amount=amount_to_buy,
            price=price,
            ships_available=ships_available,
            ships_used=ships_used,
            other_player_name=offer['jugadorAComprar'],
            other_city_name=offer['ciudadDestino'],
            offer_type=int(offer['type']),
            action_request=actionRequest
        )
        
        logging.info('I buy %s to %s from %s', addThousandSeparator(amount_to_buy), offer['ciudadDestino'], offer['jugadorAComprar'])
