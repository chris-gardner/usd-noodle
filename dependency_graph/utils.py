import os.path

escape_dict = {
    '\7': r'\a',
    '\a': r'\a',
    '\b': r'\b',
    '\c': r'\c',
    '\f': r'\f',
    '\n': r'\n',
    '\r': r'\r',
    '\t': r'\t',
    '\v': r'\v',
    '\'': r'\'',
    '\"': r'\"',
    '\0': r'\0',
    '\1': r'\1',
    '\2': r'\2',
    '\3': r'\3',
    '\4': r'\4',
    '\5': r'\5',
    '\6': r'\6',
    '\8': r'\8',
    '\9': r'\9',
    '\ ': r' ',
}


def raw(text):
    """Returns a raw string representation of text"""
    new_string = r''
    for char in text:
        try:
            new_string += escape_dict[char]
        except KeyError:
            new_string += char
    return new_string

def sanitize_path(in_path):
    """
    Clean the path for consumption
    :param in_path:
    :return:
    """
    in_path = in_path.replace(r'\ ', ' ')
    in_path = raw(in_path)
    in_path = os.path.normpath(in_path)
    in_path = in_path.replace('\\', '/')
    return in_path
