#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from decimal import Decimal

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest, city_url, materials_names
from ikabot.helpers.getJson import parse_int
from ikabot.helpers.gui import addThousandSeparator
from ikabot.helpers.market import (execute_market_offer_transfer, getMarketInfo,
                                   onSellInMarket, storageCapacityOfMarket)
from ikabot.helpers.naval import TransportShip, get_transport_ships_size
from ikabot.helpers.planRoutes import waitForAvailableShips


class SellMarketWithOwnOfferBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
# ... (SellResourcesWithOwnOfferBot remains unchanged inheritance-wise as it was Bot) ...
        self.amount_to_sell = bot_config['amount_to_sell']
        self.price = bot_config['price']
        self.resource_type = bot_config['resource_type']
        self.sell_market_capacity = bot_config['sell_market_capacity']
        self.city = bot_config['my_offering_market_city']

    def _get_process_info(self) -> str:
        return 'I sell {} of {} in {}'.format(
            addThousandSeparator(self.amount_to_sell),
            materials_names[self.resource_type],
            self.city['name']
        )

    def _start(self) -> None:
        initial_amount_to_sell = self.amount_to_sell
        html = getMarketInfo(self.ikariam_service, self.city)
        previous_on_sell = onSellInMarket(html)[self.resource_type]
        while True:
            html = getMarketInfo(self.ikariam_service, self.city)
            currently_on_sell = onSellInMarket(html)[self.resource_type]
            # if there is space in the store
            if currently_on_sell < storageCapacityOfMarket(html):
                # add our new offer to the free space
                free_space = self.sell_market_capacity - currently_on_sell
                offer = min(self.amount_to_sell, free_space)
                self.amount_to_sell -= offer
                new_offer = currently_on_sell + offer

                payloadPost = {
                    'cityId': self.city['id'],
                    'position': self.city['marketPosition'],
                    'action': 'CityScreen',
                    'function': 'updateOffers',
                    'resourceTradeType': '444',
                    'resource': '0',
                    'resourcePrice': '10',
                    'tradegood1TradeType': '444',
                    'tradegood1': '0',
                    'tradegood1Price': '11',
                    'tradegood2TradeType': '444',
                    'tradegood2': '0',
                    'tradegood2Price': '12',
                    'tradegood3TradeType': '444',
                    'tradegood3': '0',
                    'tradegood3Price': '17',
                    'tradegood4TradeType': '444',
                    'tradegood4': '0',
                    'tradegood4Price': '5',
                    'backgroundView': 'city',
                    'currentCityId': self.city['id'],
                    'templateView': 'branchOfficeOwnOffers',
                    'currentTab': 'tab_branchOfficeOwnOffers',
                    'actionRequest': actionRequest,
                    'ajax': '1'
                }
                if self.resource_type == 0:
                    payloadPost['resource'] = new_offer
                    payloadPost['resourcePrice'] = self.price
                else:
                    payloadPost['tradegood{:d}'.format(self.resource_type)] = new_offer
                    payloadPost['tradegood{:d}Price'.format(self.resource_type)] = self.price
                self.ikariam_service.post(params=payloadPost)

                # if we don't have any more to add to the offer, leave the loop
                if self.amount_to_sell == 0:
                    break

            # sleep for 2 hours
            self._wait(60 * 60 * 2, 'Waiting someone to buy the offer')

        # wait until the last of our offer is actualy bought, and let the user know
        while True:
            html = getMarketInfo(self.ikariam_service, self.city)
            currently_on_sell = onSellInMarket(html)[self.resource_type]
            if currently_on_sell <= previous_on_sell:
                self.telegram.send_message('{} of {} was sold at {:d}'.format(
                    addThousandSeparator(initial_amount_to_sell),
                    materials_names[self.resource_type],
                    self.price
                ))
                return

            # sleep for 2 hours
            self._wait(60 * 60 * 2, 'Waiting all offers to be bought')


class SellMarketToOfferBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.left_to_sell = bot_config['left_to_sell']
        self.amount_to_sell = bot_config['amount_to_sell']
        self.offers = bot_config['offers']
        self.resource_type = bot_config['resource_type']
        self.city_to_buy_from = bot_config['city_to_buy_from']

    def _get_process_info(self) -> str:
        return "I sell {} of {} in {}".format(
            addThousandSeparator(self.amount_to_sell),
            materials_names[self.resource_type],
            self.city_to_buy_from['name']
        )

    def _start(self) -> None:
        ship_size = get_transport_ships_size(self.ikariam_service, self.city_to_buy_from['id'], TransportShip.TRANSPORT_SHIP)
        for offer in self.offers:
            cityname, username, amount, precio, dist, destination_city_id = offer
            cityname = cityname.strip()
            amount_to_buy = parse_int(amount)
            while True:
                amount_to_sell = min(amount_to_buy, self.left_to_sell)
                ships_available = waitForAvailableShips(self.ikariam_service, self._wait, additional='; Resources left: {}'.format(addThousandSeparator(self.left_to_sell)))
                ships_needed = math.ceil((Decimal(amount_to_sell) / Decimal(ship_size)))
                ships_used = min(ships_available, ships_needed, 30)
                if ships_needed > ships_used:
                    amount_to_sell = ships_used * ship_size
                self.left_to_sell -= amount_to_sell
                amount_to_buy -= amount_to_sell

                self.ikariam_service.get(city_url + self.city_to_buy_from['id'], noIndex=True)
                
                execute_market_offer_transfer(
                    session=self.ikariam_service,
                    city_id=self.city_to_buy_from['id'],
                    destination_city_id=destination_city_id,
                    market_position=self.city_to_buy_from['marketPosition'],
                    function_name='sellGoodsAtAnotherBranchOffice',
                    resource_type=self.resource_type,
                    amount=amount_to_sell,
                    price=precio,
                    ships_available=ships_available,
                    ships_used=ships_used,
                    other_player_name=username,
                    other_city_name=cityname,
                    offer_type='333',
                    action_request=actionRequest
                )

                if self.left_to_sell == 0:
                    return
                if amount_to_buy == 0:
                    break
                self._wait(5, 'Wait before next batch. Remaining: {}'.format(addThousandSeparator(self.left_to_sell)), max_random=10)
