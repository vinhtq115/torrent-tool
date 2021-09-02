# References: http://bittorrent.org/beps/bep_0003.html
from collections import OrderedDict


class BencodeEncoder:
    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding
        self.ops = {
            int: self.__encode_int,
            str: self.__encode_string,
            dict: self.__encode_dict,
            list: self.__encode_list
        }

    def __encode_int(self, obj: int):
        """
        Integers are represented by an 'i' followed by the number in base 10 followed by an 'e'.
        For example i3e corresponds to 3 and i-3e corresponds to -3. Integers have no size limitation. i-0e is invalid.
        All encodings with a leading zero, such as i03e, are invalid, other than i0e, which of course corresponds to 0.
        :param obj: Integer number
        :return: String of encoded number
        """
        return f'i{obj}e'

    def __encode_dict(self, obj: dict):
        """
        Dictionaries are encoded as a 'd' followed by a list of alternating keys and their corresponding values
        followed by an 'e'. For example, d3:cow3:moo4:spam4:eggse corresponds to {'cow': 'moo', 'spam': 'eggs'} and
        d4:spaml1:a1:bee corresponds to {'spam': ['a', 'b']}. Keys must be strings and appear in sorted order
        (sorted as raw strings, not alphanumerics).
        :param obj:
        :return:
        """
        res = 'd'

        # Convert dictionary's keys to bytes for sorting.
        byte_key_dict = dict()
        for key, value in obj.items():
            byte_key_dict[key.encode(self.encoding, 'strict')] = value

        sorted_byte_key_dict = OrderedDict(sorted(byte_key_dict.items(), key=lambda x: x[0]))

        # Encode
        for key, value in sorted_byte_key_dict.items():
            res += self.__encode_string(key.decode(self.encoding, 'strict')) + self.ops[type(value)](value)

        res += 'e'
        return res

    def __encode_string(self, obj: str):
        """
        Strings are length-prefixed base ten followed by a colon and the string.
        For example 4:spam corresponds to 'spam'.
        :param obj: String
        :return: String of encoded string
        """
        return f'{len(obj)}:{obj}'

    def __encode_list(self, obj: list):
        """
        Lists are encoded as an 'l' followed by their elements (also bencoded) followed by an 'e'.
        For example l4:spam4:eggse corresponds to ['spam', 'eggs'].
        :param obj: List of elements
        :return: String of encoded list
        """
        res = 'l'
        for element in obj:
            assert type(element) in [list, int, dict, str]
            op = self.ops[type(element)]
            res += op(element)
        res += 'e'
        return res

    def encode(self, obj):
        assert type(obj) in [list, int, dict, str]
        op = self.ops[type(obj)]
        res = op(obj).encode(self.encoding)
        return res


if __name__ == '__main__':
    encoder = BencodeEncoder()
    print(encoder.encode({'cow': 'moo', 'spam': 'eggs'}))
    print(encoder.encode({'spam': ['a', 'b']}))
