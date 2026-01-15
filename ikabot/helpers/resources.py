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
    
    # First, navigate to the city view to set the context
    session.get('view=city&cityId={}'.format(city_id), noIndex=True)
    
    # Then, get the global data which includes production information
    data = session.get('view=updateGlobalData&ajax=1', noIndex=True)
    json_data = json.loads(data, strict=False)
    
    logging.debug(f"updateGlobalData response type: {type(json_data)}")
    logging.debug(f"updateGlobalData response: {json_data}")
    
    # Extract headerData from the response
    # The response structure is typically: [[key, {headerData: ..., ...}], ...]
    header_data = None
    
    try:
        if isinstance(json_data, list) and len(json_data) > 0:
            if isinstance(json_data[0], list) and len(json_data[0]) > 1:
                item = json_data[0][1]
                if isinstance(item, dict) and 'headerData' in item:
                    header_data = item['headerData']
                    logging.debug("Found headerData in json_data[0][1]['headerData']")
            
            # If not found in the first position, search through all entries
            if header_data is None:
                for entry in json_data:
                    if isinstance(entry, list) and len(entry) > 1:
                        item = entry[1]
                        if isinstance(item, dict) and 'headerData' in item:
                            header_data = item['headerData']
                            logging.debug(f"Found headerData in entry: {entry[0]}")
                            break
    except (IndexError, KeyError, TypeError) as e:
        logging.error(f"Error extracting header data: {e}")
        logging.error(f"Response structure: {json.dumps(json_data, indent=2)}")
        raise
    
    if header_data is None:
        raise ValueError(f"Could not find headerData in response. Response structure: {json.dumps(json_data, indent=2)}")
    
    wood_production = Decimal(header_data['resourceProduction'])
    luxury_production = Decimal(header_data['tradegoodProduction'])
    luxury_resource_type = int(header_data['producedTradegood'])

    return wood_production, luxury_production, luxury_resource_type
