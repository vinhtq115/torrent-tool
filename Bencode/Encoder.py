# References: http://bittorrent.org/beps/bep_0003.html
from collections import OrderedDict


class EncodeError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


class BencodeEncoder:
    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding
        self.ops = {
            int: self.encode_int,
            str: self.encode_string,
            bytes: self.encode_string,
            dict: self.encode_dict,
            list: self.encode_list
        }

    def encode_int(self, obj: int) -> bytes:
        """
        Integers are represented by an 'i' followed by the number in base 10 followed by an 'e'.
        For example i3e corresponds to 3 and i-3e corresponds to -3. Integers have no size limitation. i-0e is invalid.
        All encodings with a leading zero, such as i03e, are invalid, other than i0e, which of course corresponds to 0.
        :param obj: Integer number
        :return: Bytes string of encoded number
        """
        return f'i{obj}e'.encode(self.encoding)

    def encode_string(self, obj: str or bytes) -> bytes:
        """
        Strings are length-prefixed base ten followed by a colon and the string.
        For example 4:spam corresponds to 'spam'.
        :param obj: String or byte string
        :return: Bytes string of encoded string
        """
        if type(obj) is str:
            obj = obj.encode(self.encoding)

        return f'{len(obj)}:'.encode(self.encoding) + obj

    def encode_dict(self, obj: dict) -> bytes:
        """
        Dictionaries are encoded as a 'd' followed by a list of alternating keys and their corresponding values
        followed by an 'e'. For example, d3:cow3:moo4:spam4:eggse corresponds to {'cow': 'moo', 'spam': 'eggs'} and
        d4:spaml1:a1:bee corresponds to {'spam': ['a', 'b']}. Keys must be strings and appear in sorted order
        (sorted as raw strings, not alphanumerics).
        :param obj: Dictionary
        :return: Bytes string of encoded dictionary
        """
        res = 'd'.encode(self.encoding)

        # Convert dictionary's keys to bytes for sorting.
        byte_key_dict = dict()
        for key, value in obj.items():
            byte_key_dict[key.encode(self.encoding, 'strict')] = value

        sorted_byte_key_dict = OrderedDict(sorted(byte_key_dict.items(), key=lambda x: x[0]))

        # Encode
        for key, value in sorted_byte_key_dict.items():
            res += self.encode_string(key) + self.ops[type(value)](value)

        res += 'e'.encode(self.encoding)
        return res

    def encode_list(self, obj: list) -> bytes:
        """
        Lists are encoded as an 'l' followed by their elements (also bencoded) followed by an 'e'.
        For example l4:spam4:eggse corresponds to ['spam', 'eggs'].
        :param obj: List of elements
        :return: String of encoded list
        """
        res = 'l'.encode(self.encoding)
        for element in obj:
            print(element)
            if type(element) not in [list, int, dict, str, bytes]:
                raise EncodeError(f'Unsupported element type \'{type(element)}\' of element \'{element}\'.')

            op = self.ops[type(element)]
            res += op(element)
        res += 'e'.encode(self.encoding)
        return res

    def encode(self, obj) -> bytes:
        if type(obj) not in [list, int, dict, str, bytes]:
            raise EncodeError(f'Unsupported object type \'{type(obj)}\' of object \'{obj}\'.')

        op = self.ops[type(obj)]
        res = op(obj)
        return res
