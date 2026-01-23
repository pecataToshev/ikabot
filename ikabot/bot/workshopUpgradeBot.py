#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest
from ikabot.function.workshop import fetch_workshop_units_and_ships
from ikabot.helpers.buildings import get_building_info
from ikabot.helpers.gui import addThousandSeparator


class WorkshopUpgradeBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.city = bot_config['city']
        self.building = bot_config['building']
        self.target_units = bot_config['target_units']  # list of unit names to upgrade
        self.notify_on_no_resources = bot_config.get('notify_on_no_resources', False)

    def _get_process_info(self) -> str:
        return 'I upgrade workshop units in {}'.format(self.city['name'])

    def _start(self) -> None:
        while True:
            # Get current workshop data (both units and ships)
            data = get_building_info(self.ikariam_service, self.city['id'], self.building)
            change_view_data = data[1][1][1]
            has_upgrade, units = fetch_workshop_units_and_ships(
                self.ikariam_service, 
                self.city, 
                self.building, 
                change_view_data
            )

            # If an upgrade is in progress, wait for it to complete
            if has_upgrade:
                waiting_time = self.__extract_upgrade_time(change_view_data)
                if waiting_time > 0:
                    self._wait(
                        seconds=waiting_time + 5,
                        info='Upgrade in progress',
                        max_random=30
                    )
                    # Wait additional random time after upgrade completes
                    self._wait(
                        seconds=60,
                        info='Waiting before starting next upgrade',
                        max_random=300  # random time up to 5 minutes
                    )
                continue

            # Filter units to only those we want to upgrade
            target_upgrades = [u for u in units if u['name'] in self.target_units and u['canUpgrade']]

            if len(target_upgrades) == 0:
                # Check if there are units that need resources
                insufficient_resources = [u for u in units if u['name'] in self.target_units and u['insufficientResources']]
                
                if len(insufficient_resources) > 0:
                    if self.notify_on_no_resources:
                        self.telegram.send_message(
                            'Workshop upgrade bot in {} stopped: insufficient resources for remaining upgrades.'.format(
                                self.city['name']
                            )
                        )
                    return
                else:
                    # All target units are fully upgraded
                    self.telegram.send_message(
                        'Workshop upgrade bot in {}: all target units are fully upgraded!'.format(
                            self.city['name']
                        )
                    )
                    return

            # Sort by total resource cost (glass + gold) to get cheapest first
            target_upgrades.sort(key=lambda u: u['glass'] + u['gold'])
            
            # Get the cheapest upgrade
            selected_unit = target_upgrades[0]
            
            # Start the upgrade
            self.__start_upgrade(selected_unit)
            
            self._set_process_info(
                'Started upgrading {} (Glass: {}, Gold: {})'.format(
                    selected_unit['name'],
                    addThousandSeparator(selected_unit['glass']),
                    addThousandSeparator(selected_unit['gold'])
                )
            )

    def __extract_upgrade_time(self, html: str) -> int:
        """Extract remaining time for current upgrade"""
        import re
        timing_str = re.search(r'getProgressBar\((.*?)\);', html, re.DOTALL)
        if timing_str:
            enddate_match = re.search(r'enddate: (\d+)', timing_str.group(1))
            currentdate_match = re.search(r'currentdate: (\d+)', timing_str.group(1))
            if enddate_match and currentdate_match:
                return int(enddate_match.group(1)) - int(currentdate_match.group(1))
        return 0

    def __start_upgrade(self, unit: dict) -> None:
        """Start an upgrade for the specified unit"""
        # Select the correct tab first
        params = unit['unitTabParams'].copy()
        params.update({
            'backgroundView': 'city',
            'currentCityId': self.city['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        })

        self.ikariam_service.post(
            noIndex=True,
            params=params
        )

        # Brief wait to simulate user reviewing the tab before upgrading
        self._wait(
            seconds=1,
            info='Selecting upgrade tab',
            max_random=2
        )

        # Start the improvement
        params = unit['upgradeParams'].copy()
        params.update({
            'activeTab': unit['tab'],
            'templateView': 'workshop',
            'backgroundView': 'city',
            'currentCityId': self.city['id'],
            'actionRequest': actionRequest,
            'ajax': '1'
        })

        self.ikariam_service.post(
            noIndex=True,
            params=params
        )
