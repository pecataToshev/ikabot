import datetime
import logging

from ikabot.bot.bot import Bot
from ikabot.config import actionRequest
from ikabot.helpers.botComm import sendToBot
from ikabot.helpers.catpcha import resolveCaptcha
from ikabot.helpers.piracy import convertCapturePoints, getPiracyTemplateData


class AutoPirateBot(Bot):
    __MAXIMUM_PIRATE_MISSION_START_ATTEMPTS = 20

    def __init__(self, session, bot_config):
        super().__init__(session, bot_config)
        self.bot_type = bot_config['type']
        self.city_id = bot_config['cityId']
        self.convert_points = bot_config.get('convertPoints', None)
        self.max_break_time = bot_config['maxBreakTime']

    def _get_process_info(self):
        return '\nI execute {} piracy missions\n'.format(self.bot_config['type'])

    def _start(self):
        if self.bot_type == 'daily':
            self.__execute_piracy_daily_missions()
        else:
            self.__execute_piracy_tasks()

    @staticmethod
    def __get_time_to_sleep_to_next_given_hour(now, given_hour):
        """
        Returns seconds till next time with the given hour.
        :param now: datetime -> current time
        :param given_hour: int -> the wanted hour
        :return: int
        """
        expected_time = now.replace(hour=given_hour,
                                    minute=0, second=0, microsecond=0)
        if expected_time < now:
            expected_time += datetime.timedelta(days=1)

        return (expected_time - now).total_seconds()

    def __execute_piracy_daily_missions(self):
        """
        Performs piracy tasks based on daytime
        :return: void
        """
        day_config = self.bot_config['dailyScheduleConfig']
        night_config = self.bot_config['nightlyScheduleConfig']

        last_mission_type = None
        while True:
            now = datetime.datetime.now()

            if self.__is_config_active(now, day_config):
                logging.debug('Executing daily mission')
                last_mission_type = 'daily'
                self.__execute_piracy_mission(
                    mission_building_level=day_config['missionBuildingLevel'],
                    additional_message='@daily',
                )
                self.__perform_break_between_missions('Daily missions')

            elif self.__is_config_active(now, night_config):
                if last_mission_type == 'nightly':
                    # we've executed one night mission. sleep till day start
                    total_sleep_time = self.__get_time_to_sleep_to_next_given_hour(now, day_config['startHour'])
                    self.session.wait(
                        total_sleep_time,
                        "Sleeping until day start @{}h".format(day_config['startHour'])
                    )
                else:
                    logging.debug('Executing nightly mission')
                    self.__execute_piracy_mission(
                        mission_building_level=night_config['missionBuildingLevel'],
                        additional_message='@nightly'
                    )

                last_mission_type = 'nightly'

            else:
                logging.debug("We're in a config gap")
                # We're in a config gap. Sleep until closest start hour
                seconds_to_day_start = self.__get_time_to_sleep_to_next_given_hour(now, day_config['startHour'])
                seconds_to_night_start = self.__get_time_to_sleep_to_next_given_hour(now, night_config['startHour'])

                if seconds_to_day_start <= seconds_to_night_start:
                    self.session.wait(
                        seconds_to_day_start,
                        "Schedule gap. Sleeping until day start @{}h".format(day_config['startHour'])
                    )
                else:
                    self.session.wait(
                        seconds_to_night_start,
                        "Schedule gap. Sleeping until night start @{}h".format(night_config['startHour'])
                    )

    def __execute_piracy_tasks(self):
        """
        Performs auto pirate number of tasks tasks.
        :return: void
        """
        total_missions = self.bot_config['totalMissions']

        for task_index in range(total_missions):
            self.__execute_piracy_mission(
                mission_building_level=self.bot_config['missionBuildingLevel'],
                additional_message='Mission {}/{}'.format(task_index + 1,
                                                          total_missions)
            )
            self.__perform_break_between_missions(
                'After mission {}/{}'.format(task_index + 1, total_missions)
            )

        logging.info("Successfully executed %d piracy missions",
                     total_missions)

        if self.bot_config['notifyWhenFinished']:
            sendToBot(self.session, "I'm done with pirating")

    def __is_config_active(self, given_time, schedule_config):
        """
        Determines if the config is active in the given time
        :param given_time: datetime.datetime
        :param schedule_config: dict[]
        :return: bool
        """
        current_hour = int(given_time.strftime("%H"))
        _s = schedule_config['startHour']
        _e = schedule_config['endHour']
        return _s < _e and _s <= current_hour <= _e \
            or _s > _e and (current_hour <= _e or _s <= current_hour)

    def __perform_break_between_missions(self, additional_info):
        """
        Performs break between two consecutive piracy missions.
        :param additional_info: str -> additional info message
        :return: void
        """
        if self.max_break_time > 0:
            self.session.wait(
                seconds=1,
                info='Waiting between missions. ' + additional_info,
                max_random=self.max_break_time - 1)

    def __get_template_data_and_wait_ongoing_mission(self):
        """
        Changes view to city and opens the piracy fortress view. Then returns the
        template data of the response
        :return: dict[]
        """
        data = getPiracyTemplateData(self.session, self.city_id)
        if data['hasOngoingMission']:
            self.session.wait(data['ongoingMissionTimeRemaining'],
                              'Found unexpected mission. Waiting it to end.',
                              max_random=5)
            return self.__get_template_data_and_wait_ongoing_mission()

        return data

    def __execute_piracy_mission(
            self,
            mission_building_level,
            additional_message,
            captcha=None,
            remaining_attempts=__MAXIMUM_PIRATE_MISSION_START_ATTEMPTS,
    ):
        """
        Executes piracy mission and handles captcha.
        :param mission_building_level: int -> the building level of the mission
        :param additional_message: str -> additional message in the statuses
        :param captcha: str -> resolved captcha
        :param remaining_attempts: times to try id captcha is not solved
        :return: void
        """
        if remaining_attempts <= 0:
            raise Exception('Failed to start the mission too many times. Terminating')

        data = self.__get_template_data_and_wait_ongoing_mission()
        mission = [p for p in data['pirateCaptureLevels'] if p['buildingLevel'] == mission_building_level][0]

        if mission['buildingLevel'] > data['buildingLevel']:
            _msg = 'This piracy mission ({}) requires {} building level' \
                   'but found {}'.format(mission['name'],
                                         mission['buildingLevel'],
                                         data['buildingLevel'], )
            raise Exception(_msg)

        params = {
            'action': 'PiracyScreen',
            'function': 'capture',
            'buildingLevel': mission['buildingLevel'],
            'view': 'pirateFortress',
            'cityId': self.city_id,
            'position': '17',
            'activeTab': 'tabBootyQuest',
            'backgroundView': 'city',
            'currentCityId': self.city_id,
            'templateView': 'pirateFortress',
            'actionRequest': actionRequest,
            'ajax': '1'
        }
        if captcha is not None:
            params.update({
                'captchaNeeded': '1',
                'captcha': captcha,
            })

        # try to execute the pirate mission
        html = self.session.post(params=params, noIndex=captcha is not None)
        if 'function=createCaptcha' not in html \
                and '"showPirateFortressShip":0' in html:

            time_wait_for_conversion_start = 0
            # Well, it's far more convenient that we're going to execute the conversion right after we've started the new
            # mission rather that waiting the mission to end
            if self.convert_points is not None:
                time_wait_for_conversion_start = self.session.wait(3, 'Simulating user before converting points',
                                                                   max_random=5)
                if self.convert_points == 'mission':
                    convert_points_to_strength = mission['capturePoints']
                else:
                    convert_points_to_strength = int(self.convert_points)
                convertCapturePoints(self.session, self.city_id, convert_points_to_strength)

            # execution is successful, go get some sleep
            self.session.wait(mission['duration'] - time_wait_for_conversion_start,
                              'Executing piracy mission {}. {}'.format(mission['name'], additional_message),
                              max_random=10)

            return

        if 'function=createCaptcha' not in html:
            logging.warning('Mission has not started, but captcha not required. '
                            'Retrying the mission execution')
            return self.__execute_piracy_mission(
                mission_building_level=mission_building_level,
                additional_message=additional_message,
                captcha=None,
                remaining_attempts=remaining_attempts - 1,
            )

        self.session.setProcessInfo('We have to solve some captcha. Let me handle that')
        captcha = None  # well, captcha failed, let's generate a new one
        while (captcha is None or captcha == 'Error') and remaining_attempts > 0:
            remaining_attempts -= 1
            logging.info("Found captcha. Trying to resolve it. "
                         "%d attempts remaining", remaining_attempts)

            picture = self.session.get('action=Options&function=createCaptcha',
                                       fullResponse=True).content
            captcha = resolveCaptcha(self.session, picture)

            logging.info("Resolved captcha to %s", captcha)

        # captcha has been resolved, let's try again.
        # or no more remaining attempts
        return self.__execute_piracy_mission(
            mission_building_level=mission_building_level,
            additional_message=additional_message,
            captcha=captcha,
            remaining_attempts=remaining_attempts,
        )
