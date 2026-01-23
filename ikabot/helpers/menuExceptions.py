#! /usr/bin/env python3
# -*- coding: utf-8 -*-


class ExitFromMenu(Exception):
    """
    Exception raised when user selects 'Exit' (option 0) from a menu.
    This exception propagates up to the main menu loop, allowing graceful
    exit from nested menu operations without requiring None checks everywhere.
    """
    pass
