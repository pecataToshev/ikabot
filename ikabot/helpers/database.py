import json
import sqlite3

from ikabot import config


class Database:
    __account_name_str = 'accountName'
    __account_name_where = "{} = :{}".format(__account_name_str, __account_name_str)

    def __init__(self, account_name):
        self.__account_name = account_name
        self.__conn = sqlite3.connect(config.DB_FILE)
        self.__cursor = self.__conn.cursor()

    def close_db_conn(self):
        self.__cursor.close()
        self.__conn.close()

    def __add_account_name_arg(self, args):
        """
        Add account name to the args
        :param args: dict[]
        :return: dict[]
        """
        args = dict(args or {})
        args[self.__account_name_str] = self.__account_name
        return args

    def __select(self, table, where=None, args=None):
        """
        Select data from table
        :param table: str
        :param where: list[str]
        :param args: dict
        :return:
        """
        where = " AND ".join([self.__account_name_where] + (where or []))
        args = self.__add_account_name_arg(args)
        self.__cursor.execute(f'SELECT * FROM {table} WHERE {where}', args)

        # Get column names from the cursor description
        columns = [column[0] for column in self.__cursor.description]

        rows = self.__cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def __insert(self, table, columns, data):
        """
        Inserts data into table
        :param table: str
        :param columns: list[str]
        :param data: dict
        :return: void
        """
        data = self.__add_account_name_arg(data)
        columns = [self.__account_name_str] + [c for c in columns if c in data]
        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES(:{', :'.join(columns)})"
        self.__cursor.execute(sql, data)
        self.__conn.commit()

    def __delete(self, table, args):
        """
        Deletes data from table
        :param table: str
        :param args: dict
        :return: void
        """
        args = self.__add_account_name_arg(args)
        where = " AND ".join(['{} = :{}'.format(c, c) for c in args])
        sql = f"DELETE FROM {table} WHERE {where}"
        self.__cursor.execute(sql, args)
        self.__conn.commit()

    def get_processes(self, filters=None):
        """
        Retrieve processes from the database
        :param filters: list[[column, relation, value]]
        :return:
        """
        where = ['{} {} :{}'.format(f[0], f[1], f[0]) for f in (filters or [])]
        args = {f[0]: f[2] for f in (filters or [])}
        return self.__select('processes', where, args)

    def set_process(self, process):
        self.__insert(
            'processes',
            [
                "pid",
                "action",
                "status",
                "lastAction",
                "nextAction",
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
        self.__insert(
            'storage',
            ['storageKey', 'data'],
            {'storageKey': key, 'data': json.dumps(data)}
        )
