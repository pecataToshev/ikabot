#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from decimal import Decimal

from ikabot.config import actionRequest


def getAvailableResources(html, num=False):
    """
    Parameters
    ----------
    html : string

    Returns
    -------
    resources_available : list[int] | list[str]
    """
    resources = re.search(r'\\"resource\\":(\d+),\\"2\\":(\d+),\\"1\\":(\d+),\\"4\\":(\d+),\\"3\\":(\d+)}', html)
    if num:
        return [int(resources.group(1)), int(resources.group(3)), int(resources.group(2)), int(resources.group(5)), int(resources.group(4))]
    else:
        return [resources.group(1), resources.group(3), resources.group(2), resources.group(5), resources.group(4)]


def getWarehouseCapacity(html):
    """
    Parameters
    ----------
    html : string
    Returns
    -------
    capacity : int
    """
    capacity = re.search(r'maxResources:\s*JSON\.parse\(\'{\\"resource\\":(\d+),', html).group(1)
    return int(capacity)


def getWineConsumptionPerHour(html):
    """
    Parameters
    ----------
    html : string
    Returns
    -------
    capacity : int
    """
    result = re.search(r'wineSpendings:\s(\d+)', html)
    if result:
        return int(result.group(1))
    return 0


def extract_tradegood(html: str):
    res = re.search(r'producedTradegood:\s"(\d+)",', html)
    if res:
        return int(res.group(1))
    return None


def extract_tradegood_production(html: str):
    res = re.search(r'tradegoodProduction:\s(\d+(\.\d+)?),', html)
    if res:
        return Decimal(res.group(1))
    return Decimal(0)


def extract_resource_production(html: str):
    res = re.search(r'resourceProduction:\s(\d+(\.\d+)?),', html)
    if res:
        return Decimal(res.group(1))
    return Decimal(0)


def getProductionPerSecond(session, city_id):
    """
    Parameters
    ----------
    session : ikabot.web.ikariamService.IkariamService
    city_id : int

    Returns
    -------
    production: tuple[Decimal, Decimal, int]
    """
    import logging
    prod = session.post(params={'action': 'header', 'function': 'changeCurrentCity', 'actionRequest': actionRequest, 'cityId': city_id, 'ajax': '1'})
    prod = json.loads(prod, strict=False)
    
    # Log the response structure for debugging
    logging.debug(f"changeCurrentCity response type: {type(prod)}")
    logging.debug(f"changeCurrentCity response: {prod}")
    
    # Try to extract headerData from the response structure
    # The API can return different structures, so we need to handle multiple cases
    header_data = None
    
    try:
        # Try the original format: prod[0][1]['headerData']
        if isinstance(prod, list) and len(prod) > 0:
            if isinstance(prod[0], list) and len(prod[0]) > 1:
                if isinstance(prod[0][1], dict) and 'headerData' in prod[0][1]:
                    header_data = prod[0][1]['headerData']
                elif isinstance(prod[0][1], list):
                    # Sometimes prod[0][1] is a list, search for headerData in the response
                    for item in prod[0]:
                        if isinstance(item, dict) and 'headerData' in item:
                            header_data = item['headerData']
                            break
            # Sometimes the structure is just prod[0] contains headerData directly
            if header_data is None and isinstance(prod[0], dict):
                for value in prod[0].values():
                    if isinstance(value, dict) and 'headerData' in value:
                        header_data = value['headerData']
                        break
                    elif isinstance(value, dict) and all(k in value for k in ['resourceProduction', 'tradegoodProduction', 'producedTradegood']):
                        header_data = value
                        break
    except (IndexError, KeyError, TypeError) as e:
        logging.error(f"Error extracting header data: {e}")
        logging.error(f"Response structure: {json.dumps(prod, indent=2)}")
        raise
    
    if header_data is None:
        raise ValueError(f"Could not find headerData in response. Response structure: {json.dumps(prod, indent=2)}")
    
    wood_production = Decimal(header_data['resourceProduction'])
    luxury_production = Decimal(header_data['tradegoodProduction'])
    luxury_resource_type = int(header_data['producedTradegood'])

    return wood_production, luxury_production, luxury_resource_type
