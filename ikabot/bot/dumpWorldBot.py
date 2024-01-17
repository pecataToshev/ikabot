#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import gzip
import json
import time
from pathlib import Path

from ikabot.bot.bot import Bot
from ikabot.helpers.getJson import getIsland


class DumpWorldBot(Bot):
    def __init__(self, ikariam_service, bot_config):
        super().__init__(ikariam_service, bot_config)
        self.shallow = bot_config['shallow']
        self.start_id = bot_config['start_id']
        self.waiting_time = bot_config['waiting_time']

        self.dump_path = bot_config['dump_path']
        if self.shallow:
            self.dump_path = self.dump_path.replace('.json.gz', '_shallow.json.gz')

    def _get_process_info(self) -> str:
        return 'I dump world'

    def _start(self) -> None:
        self.star_time = time.time()
        world = {
            'name': 's' + str(self.ikariam_service.server_number) + '-' + str(self.ikariam_service.server),
            'self_name': self.ikariam_service.username,
            'dump_start_date': self.star_time,
            'dump_end_date': 0,
            'islands': [],
            'shallow': self.shallow
        }

        shallow_islands = []
        shallow_islands.extend(self.__get_island_data(0, 50, 0, 50, 1))
        shallow_islands.extend(self.__get_island_data(50, 100, 0, 50, 2))
        shallow_islands.extend(self.__get_island_data(0, 50, 50, 100, 3))
        shallow_islands.extend(self.__get_island_data(50, 100, 50, 100, 4))
        # [
        # "58",         //id 0
        # "Phytios",    //name 1
        # "1",          //resource type 2
        # "2",          //type of miracle 3
        # "5",          // ?? 4
        # "4",          // ?? 5
        # "9",          // lumber level  6
        # "12",         // number of people 7
        # 0,            // piracy in range 8
        # "0",          // helios tower 9
        # "0",          // red 10
        # "0"           // blue 11
        # ]

        if self.shallow:
            world['islands'] = shallow_islands
        else:
            # scan each island
            all_island_ids = set([i['id'] for i in shallow_islands])
            world['islands'] = self.__retrieve_islands(all_island_ids)

        self.__dump_to_file(world)

    def __update_status(self, message, percent, percent_total):
        self._set_process_info('{}: {}%; total: {}%'.format(
            message, str(round(percent, 1)), str(round(percent_total, 1))
        ))

    def __get_island_data(self, x_min: int, x_max: int, y_min: int, y_max: int, iteration: int):
        self.__update_status(
            message='Getting ({}-{}, {}-{}) islands'.format(x_min, x_max, y_min, y_max),
            percent=iteration * 25,
            percent_total=iteration * 1.25,
        )
        data = self.ikariam_service.post(
            params={
                'action': 'WorldMap',
                'function': 'getJSONArea',
                'x_min': x_min,
                'x_max': x_max,
                'y_min': y_min,
                'y_max': y_max,
            }
        )
        shallow_islands = []
        for x, val in json.loads(data)['data'].items():
            for y, val2 in val.items():
                shallow_islands.append({
                    'x': x,
                    'y': y,
                    'id': val2[0],
                    'name': val2[1],
                    'resource_type': val2[2],
                    'miracle_type': val2[3],
                    'wood_lvl': val2[6],
                    'players': val2[7]
                })
        return shallow_islands

    def __dump_to_file(self, world):
        self._set_process_info('Saving data to file')
        world['dump_end_date'] = time.time()
        p = Path(self.dump_path).parent
        p.mkdir(exist_ok=True, parents=True)
        with gzip.open(self.dump_path, 'wb') as file:
            json_string = json.dumps(world).encode('utf-8')
            file.write(json_string)

    def __retrieve_islands(self, island_ids):
        islands = []
        world_islands_number = len(island_ids)
        for i, island_id in enumerate(sorted(map(int, island_ids))):
            if int(island_id) < self.start_id:
                continue
            self.__update_status(
                message='Getting island #{}'.format(island_id),
                percent=len(islands) / world_islands_number * 100,
                percent_total=5 + (len(islands) / world_islands_number * 95)
            )
            html = ''
            while len(html) == 0:
                time.sleep(self.waiting_time)
                try:
                    html = self.ikariam_service.get('view=island&islandId=' + str(island_id))
                except Exception:
                    # try again
                    pass
            islands.append(getIsland(html))
        return islands
