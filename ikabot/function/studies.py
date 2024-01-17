#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from ikabot.config import actionRequest
from ikabot.helpers.getJson import getCity
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.userInput import read


def __get_studies(session):
    html = session.get()
    city = getCity(html)
    city_id = city['id']
    url = 'view=researchAdvisor&oldView=updateGlobalData&cityId={0}&backgroundView=city&currentCityId={0}&templateView=researchAdvisor&actionRequest={1}&ajax=1'.format(city_id, actionRequest)
    resp = session.post(url)
    resp = json.loads(resp, strict=False)
    return resp[2][1]


def __perform_study(session, studies, num_study):
    html = session.get()
    city = getCity(html)
    city_id = city['id']
    research_type = studies['js_researchAdvisorChangeResearchType{}'.format(num_study)]['ajaxrequest'].split('=')[-1]
    url = 'action=Advisor&function=doResearch&actionRequest={}&type={}&backgroundView=city&currentCityId={}&templateView=researchAdvisor&ajax=1'.format(actionRequest, research_type, city_id)
    session.post(url)


def study(ikariam_service, db, telegram):
    """
    Parameters
    ----------
    ikariam_service : ikabot.web.ikariamService.IkariamService
    db: ikabot.helpers.database.Database
    telegram: ikabot.helpers.telegram.Telegram
    """
    banner()
    studies = __get_studies(ikariam_service)
    keys = list(studies.keys())
    num_studies = len([key for key in keys if 'js_researchAdvisorChangeResearchTypeTxt' in key])

    available = []
    for num_study in range(num_studies):
        if 'js_researchAdvisorProgressTxt{}'.format(num_study) in studies:
            available.append(num_study)

    if len(available) == 0:
        print('There are no available studies.')
        enter()
        return

    print('Which one do you wish to study?')
    print('0) None')
    for index, num_study in enumerate(available):
        print('{:d}) {}'.format(index+1, studies['js_researchAdvisorNextResearchName{}'.format(num_study)]))
    choice = read(min=0, max=len(available))

    if choice == 0:
        return

    __perform_study(ikariam_service, studies, available[choice - 1])
    print('Done.')
    enter()
