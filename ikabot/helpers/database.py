import json
import logging
import sqlite3
from contextlib import closing
from typing import List

from ikabot import config


class Database:
    __bot_name_str = 'botName'
    __bot_name_where = "{} = :{}".format(__bot_name_str, __bot_name_str)

    def __init__(self, bot_name):
        logging.debug('Creating db connection; botName=%s', bot_name)
        self.__bot_name = bot_name
        self.__conn = sqlite3.connect(config.DB_FILE, )

    def close_db_conn(self):
        logging.debug('Closing db connection')
        self.__conn.close()

    def __add_bot_name_to_args(self, args):
        """
        Add account name to the args
        :param args: dict[]
        :return: dict[]
        """
        args = dict(args or {})
        args[self.__bot_name_str] = self.__bot_name
        return args

    def __select(self, table: str, where:List[str]=None, args:dict=None) -> List[dict]:
        """
        Select data from table
        """
        where = " AND ".join([self.__bot_name_where] + (where or []))
        args = self.__add_bot_name_to_args(args)

        with closing(self.__conn.cursor()) as _cursor:
            _cursor.execute(f'SELECT * FROM {table} WHERE {where}', args)
            # Get column names from the cursor description
            columns = [column[0] for column in _cursor.description]
            rows = _cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def __upsert(self, table: str, columns: List[str], data: dict) -> None:
        """
        Inserts data into table
        """
        data = self.__add_bot_name_to_args(data)
        columns = [self.__bot_name_str] + [c for c in columns if c in data]
        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES(:{', :'.join(columns)})"
        with closing(self.__conn.cursor()) as _cursor:
            _cursor.execute(sql, data)
        self.__conn.commit()

    def __delete(self, table: str, args: dict) -> None:
        """
        Deletes data from table
        """
        args = self.__add_bot_name_to_args(args)
        where = " AND ".join(['{} = :{}'.format(c, c) for c in args])
        sql = f"DELETE FROM {table} WHERE {where}"
        with closing(self.__conn.cursor()) as _cursor:
            _cursor.execute(sql, args)
        self.__conn.commit()

    def get_processes(self, filters=None):
        """
        Retrieve processes from the database
        :param filters: list[(column, relation, value)]
        :return:
        """
        where = ['{} {} :{}'.format(f[0], f[1], f[0]) for f in (filters or [])]
        args = {f[0]: f[2] for f in (filters or [])}
        return self.__select('processes', where, args)

    def set_process(self, process):
        self.__upsert(
            'processes',
            [
                "pid",
                "action",
                "status",
                "lastActionTime",
                "nextActionTime",
                "targetCity",
                "objective",
                "info"
            ],
            process
        )

    def delete_process(self, pid):
        self.__delete('processes', {'pid': pid})

    def get_stored_value(self,  key):
        data = self.__select(
            'storage',
            ['storageKey = :storageKey'],
            {'storageKey': key}
        )
        if len(data) == 0:
            return None
        return json.loads(data[0]['data'])

    def store_value(self, key, data):
        self.__upsert(
            'storage',
            ['storageKey', 'data'],
            {'storageKey': key, 'data': json.dumps(data)}
        )
