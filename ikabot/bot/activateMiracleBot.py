import json
import logging

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest


class ActivateMiracleBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.already_activated = 0
        self.target_activations_number = bot_config['targetActivationNumber']
        self.island = bot_config['island']
        self.wonder_name = self.island['wonderName']

    def _get_process_info(self) -> str:
        return 'I activate {} times the miracle {} on {}'.format(
            self.target_activations_number, self.wonder_name, self.island['id']
        )

    def _start(self) -> None:
        island = self.island
        while self.already_activated < self.target_activations_number:
            self.__wait_for_miracle(island)
            self.already_activated += 1
            success, waiting_time = self.__activate_miracle_http_call(island)

            if not success:
                msg = 'The miracle {} on {} could not be activated. #{}/{}'.format(
                    island['wonderName'], island['id'], self.already_activated, self.target_activations_number)
                logging.error(msg)
                self.telegram.send_message(msg)
                return

            logging.info('Miracle %s onn %s successfully activated #%s/%s',
                         island['wonderName'], island['id'], self.already_activated, self.target_activations_number)

    def __wait_for_miracle(self, island):
        logging.info('Waiting for miracle %s on island %s #%s/%s',
                     island['wonderName'], island['id'], self.already_activated, self.target_activations_number)
        while True:
            self._set_process_info('Checking if miracle {} on {} can be activated'.format(island['wonderName'],
                                                                                          island['id']))

            temple_response = self.ikariam_service.post(
                params={
                    "view": "temple",
                    "cityId": island['ciudad']['id'],
                    "position": island['ciudad']['pos'],
                    "backgroundView": "city",
                    "currentCityId": island['ciudad']['id'],
                    "actionRequest": actionRequest,
                    "ajax": "1"
                }
            )
            temple_response = json.loads(temple_response, strict=False)
            temple_response = temple_response[2][1]

            for elem in temple_response:
                if 'countdown' in temple_response[elem]:
                    end_time = temple_response[elem]['countdown']['enddate']
                    current_time = temple_response[elem]['countdown']['currentdate']
                    wait_time = end_time - current_time
                    break
            else:
                available = temple_response['js_WonderViewButton']['buttonState'] == 'enabled'
                if available:
                    return
                else:
                    wait_time = 60

            self._wait(
                seconds=wait_time + 5,
                info='Recovering ({} remaining)'.format(self.target_activations_number - self.already_activated),
                max_random=20
            )

    def __activate_miracle_http_call(self, island):
        """
        Activates miracle
        :param island: dict[]
        :return: bool, int -> successfully activated, waiting time
        """
        logging.info("Trying to activate the miracle %s on %s", island['wonderName'], island['id'])
        response = self.ikariam_service.post(
            params={
                'action': 'CityScreen',
                'cityId': island['ciudad']['id'],
                'function': 'activateWonder',
                'position': island['ciudad']['pos'],
                'backgroundView': 'city',
                'currentCityId': island['ciudad']['id'],
                'templateView': 'temple',
                'actionRequest': actionRequest,
                'ajax': '1'
            }
        )
        response = json.loads(response, strict=False)
        if response[1][1][0] == 'error':
            return False, -1

        return True, ActivateMiracleBot.get_waiting_time(response)

    @staticmethod
    def get_waiting_time(activate_miracle_response):
        """
        Returns waiting time for the miracle from response
        :param activate_miracle_response: dict[]
        :return: int -> seconds to wait
        """
        temple_response = activate_miracle_response[2][1]
        for elem in temple_response:
            if 'countdown' in temple_response[elem]:
                end_time = temple_response[elem]['countdown']['enddate']
                current_time = temple_response[elem]['countdown']['currentdate']
                return end_time - current_time
        return 0

