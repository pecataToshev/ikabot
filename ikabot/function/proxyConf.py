#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import requests

import ikabot.config as config
from ikabot.helpers.gui import banner, enter
from ikabot.helpers.pedirInfo import read


def show_proxy(session):
    proxy_data = session.db.get_stored_value('proxy')
    msg = 'using proxy:'
    if proxy_data is not None and proxy_data['set'] is True:
        curr_proxy = proxy_data['conf']['https']
        if test_proxy(proxy_data['conf']) is False:
            proxy_data['set'] = False
            session.db.store_value('proxy', proxy_data)
            sys.exit('the {} proxy does not work, it has been removed'.format(curr_proxy))
        if msg not in config.update_msg:
            # add proxy message
            config.update_msg += '{} {}\n'.format(msg, curr_proxy)
        else:
            # delete old proxy message
            config.update_msg = config.update_msg.replace('\n'.join(config.update_msg.split('\n')[-2:]), '')
            # add new proxy message
            config.update_msg += '{} {}\n'.format(msg, curr_proxy)
    elif msg in config.update_msg:
        # delete old proxy message
        config.update_msg = config.update_msg.replace('\n'.join(config.update_msg.split('\n')[-2:]), '')


def test_proxy(proxy_dict):
    try:
        requests.get('https://lobby.ikariam.gameforge.com/', proxies=proxy_dict, verify=config.do_ssl_verify)
    except Exception:
        return False
    return True


def read_proxy():
    print('Enter the proxy (examples: socks5://127.0.0.1:9050, https://45.117.163.22:8080):')
    proxy_str = read(msg='proxy: ')
    proxy_dict = {'http': proxy_str, 'https': proxy_str}
    if test_proxy(proxy_dict) is False:
        print('The proxy does not work.')
        enter()
        return None
    print('The proxy works and it will be used for all future requests.')
    enter()
    return proxy_dict


def proxyConf(session, event, stdin_fd, predetermined_input):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    try:
        banner()
        print('Warning: The proxy does not apply to the requests sent to the lobby!\n')

        proxy_data = session.db.get_stored_value('proxy')
        if proxy_data is None or proxy_data['set'] is False:
            print('Right now, there is no proxy configured.')
            proxy_dict = read_proxy()
            if proxy_dict is None:
                event.set()
                return
            proxy_data = {
                'conf': proxy_dict,
                'set': True,
            }
        else:
            curr_proxy = proxy_data['conf']['https']
            print('Current proxy: {}'.format(curr_proxy))
            print('What do you want to do?')
            print('0) Exit')
            print('1) Set a new proxy')
            print('2) Remove the current proxy')
            rta = read(min=0, max=2)

            if rta == 0:
                event.set()
                return
            if rta == 1:
                proxy_dict = read_proxy()
                if proxy_dict is None:
                    event.set()
                    return
                proxy_data['conf'] = proxy_dict
                proxy_data['set'] = True
            if rta == 2:
                proxy_data['set'] = False
                print('The proxy has been removed.')
                enter()

        session.db.store_value('proxy', proxy_data)
        event.set()
    except KeyboardInterrupt:
        event.set()
        return
