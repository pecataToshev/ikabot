from ikabot import config
from ikabot.config import prompt


def read(min=None, max=None, digit=False, msg=prompt, values=None, empty=False, additionalValues=None, default=None):  # user input
    """Reads input from user
    Parameters
    ----------
    min : int
        smallest number acceptable as input
    max : int
        greatest number acceptable as input
    digit : bool
        boolean indicating whether or not the input MUST be an int
    msg : str
        string printed before the user is asked for input
    values : list
        list of strings which are acceptable as input
    empty : bool
        a boolean indicating whether or not an empty string is acceptable as input
    additionalValues : list
        list of strings which are additional valid inputs. Can be used with digit = True to validate a string as an input among all digits

    Returns
    -------
    result : int | str
        int representing the user's choice
    """
    try:
        if len(config.predetermined_input) != 0:
            return config.predetermined_input.pop(0)
    except Exception:
        pass

    def _invalid():
        print('\033[1A\033[K', end="")  # remove line
        return read(min, max, digit, msg, values, additionalValues=additionalValues)

    try:
        read_input = input(msg)
    except EOFError:
        return _invalid()

    if additionalValues is not None and read_input in additionalValues:
        return read_input

    if read_input == '' and default is not None:
        return default

    if read_input == '' and empty is True:
        return read_input

    if digit is True or min is not None or max is not None:
        if read_input.isdigit() is False:
            return _invalid()
        else:
            try:
                read_input = eval(read_input)
            except SyntaxError:
                return _invalid()
    if min is not None and read_input < min:
        return _invalid()
    if max is not None and read_input > max:
        return _invalid()
    if values is not None and read_input not in values:
        return _invalid()
    return read_input


def askUserYesNo(question):
    """
    Asks user the yes/no question in the message and returns his response.
    :param question: question
    :return: bool
    """
    return read(
        msg=question + '? (y|N) ',
        values=['y', 'Y', 'n', 'N'],
    ).lower() == 'y'


def askForValue(text, max_val):
    """Displays text and asks the user to enter a value between 0 and max

    Parameters
    ----------
    text : str
        text to be displayed when asking the user for input
    max_val : int
        integer representing the number of input options

    Returns
    -------
    var : int
        integer representing the user's input
        if the user has inputed nothing, 0 will be returned instead
    """
    var = read(msg=text, min=0, max=max_val, default=0, additionalValues=['all', 'half'])
    if var == 'all':
        var = max_val
    elif var == 'half':
        var = max_val // 2
    return var
