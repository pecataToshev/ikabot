#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from ikabot.bot.conductExperimentBot import ConductExperimentBot
from ikabot.helpers.gui import addThousandSeparator, banner, enter
from ikabot.helpers.citiesAndIslands import chooseCity
from ikabot.helpers.userInput import read


def configure_conduct_experiment_bot(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()
       
    # Experiment
    experiments = {}
    total_glass = 0
    found_academy = -1

    banner()
    print('Pick city: ')
    city = chooseCity(ikariam_service)
    total_glass = int(city['availableResources'][3])
    
    # Check if enough glass
    if (total_glass < 300000 ):
        print(f'Not enough glass ({addThousandSeparator(total_glass)}), try another city. Min=300k')
        time.sleep(2)
        enter()
        return
    
    # Search for Academy
    for building in city['position']:
        if building['building'] == 'academy':
            found_academy = building['position']

    if (found_academy < 0):
        print(f'No academy in this town, pick another one')
        time.sleep(2)
        enter()
        return
    
    max_experiments = (total_glass // 300000)
    banner()
    print(f'How many experiments? Min=1, Max={max_experiments}')
    choice = read(min=1, max=max_experiments)

    # Build experiments dict
    experiments['cityID'] = city['id']
    experiments['cityName'] = city['name']
    experiments['academyPosition'] = found_academy
    experiments['numberOfExperiments'] = choice

    ConductExperimentBot(ikariam_service, experiments).start(
        action='Conduct Studies',
        objective=f'Execute {choice} studies',
        target_city=city['name'],
    )
