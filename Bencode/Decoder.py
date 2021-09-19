from collections import OrderedDict


class DecodeError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


class BencodeDecoder:
    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding
        self.ops = {
            list: self.decode_list,
            int: self.decode_int,
            dict: self.decode_dictionary,
            bytes: self.decode_string_bytes
        }
        self.__char_i = 'i'.encode(self.encoding)[0]
        self.__char_l = 'l'.encode(self.encoding)[0]
        self.__char_d = 'd'.encode(self.encoding)[0]
        self.__char_e = 'e'.encode(self.encoding)[0]
        self.__char_0 = '0'.encode(self.encoding)[0]
        self.__char_9 = '9'.encode(self.encoding)[0]
        self.__char_colon = ':'.encode(self.encoding)[0]
        self.__char_hyphen = '-'.encode(self.encoding)[0]

    def decode_int(self, inp: bytes):
        """
        Integers are represented by an 'i' followed by the number in base 10 followed by an 'e'.
        For example i3e corresponds to 3 and i-3e corresponds to -3. Integers have no size limitation. i-0e is invalid.
        All encodings with a leading zero, such as i03e, are invalid, other than i0e, which of course corresponds to 0.
        :param inp: Input bytes string
        :return: Decoded integer
        """
        if inp[0] != self.__char_i or inp[-1] != self.__char_e:
            raise DecodeError(f'To decode integer, input must begin with \'i\' and end with \'e\'. '
                              f'Input: {inp}.')

        try:
            result = int(inp[1: -1])
        except ValueError:
            raise DecodeError(f'Integer must be encoded in base ten ASCII. '
                              f'Input: {inp}.')

        if result == 0 and inp[1] == self.__char_hyphen:
            raise DecodeError(f'Negative zero is not permitted. Input: {inp}.')

        if result != 0 and ((inp[1] == self.__char_hyphen and inp[2] == self.__char_0)
                            or (inp[1] == self.__char_0)):
            raise DecodeError(f'Leading zeros are not allowed. Input: {inp}.')

        return result

    def decode_string_bytes(self, inp: bytes):
        """
        Strings are length-prefixed base ten followed by a colon and the string.
        For example 4:spam corresponds to 'spam'.
        :param inp: Input bytes string
        :return: Decoded bytes string
        """
        colon_pos = inp.find(self.__char_colon)

        if colon_pos == -1:
            raise DecodeError(f'String must contain colon \':\'. Input: {inp}.')

        try:
            string_length = int(inp[:colon_pos])
            if string_length <= 0:
                raise ValueError
        except ValueError:
            raise DecodeError(f'Prefixed string before colon must be an integer and higher than 0. Input: \'{inp}\'')

        if string_length != len(inp[colon_pos + 1:]):
            raise DecodeError(f'String length and predefined length do not match. '
                              f'String length: {string_length}, predefined length: {len(inp[colon_pos + 1:])}. '
                              f'Input: \'{inp}\'')

        return inp[colon_pos + 1:]

    def decode_list(self, inp: bytes):
        """
        Lists are encoded as an 'l' followed by their elements (also bencoded) followed by an 'e'.
        For example l4:spam4:eggse corresponds to ['spam', 'eggs'].
        :param inp: Input bytes string
        :return: Decoded list
        """
        if inp[0] != self.__char_l or inp[-1] != self.__char_e:
            raise DecodeError(f'To decode list, input must begin with \'l\' and end with \'e\'. '
                              f'Input: {inp}.')

        results = list()
        idx = 1

        while idx < len(inp) - 1:
            if inp[idx] == self.__char_i:  # Decode integer
                ending_e = inp.find(self.__char_e, idx + 1)
                inp_ = inp[idx: ending_e + 1]
                try:
                    result = self.decode_int(inp_)
                    idx = ending_e + 1
                except DecodeError:
                    raise DecodeError(f'Cannot decode integer from {inp_}.')
            elif inp[idx] == self.__char_l:  # Decode list
                ending_e = inp.find(self.__char_e, idx + 1)
                if ending_e == -1:
                    raise DecodeError(f'Cannot decode list from index {idx}.')
                while ending_e != -1:
                    inp_ = inp[idx: ending_e + 1]
                    try:
                        result = self.decode_list(inp_)
                        idx = ending_e + 1
                        break
                    except DecodeError:
                        ending_e = inp.find(self.__char_e, ending_e + 1)
                    if ending_e == -1:
                        raise DecodeError(f'Cannot decode list from {inp_}.')

            elif inp[idx] == self.__char_d:  # Decode dictionary
                ending_e = inp.find(self.__char_e, idx + 1)
                if ending_e == -1:
                    raise DecodeError(f'Cannot decode dictionary from index {idx}.')
                while ending_e != -1:
                    inp_ = inp[idx: ending_e + 1]
                    try:
                        result = self.decode_dictionary(inp_)
                        idx = ending_e + 1
                        break
                    except DecodeError:
                        ending_e = inp.find(self.__char_e, ending_e + 1)
                    if ending_e == -1:
                        raise DecodeError(f'Cannot decode dictionary from index {idx}.')
            elif self.__char_0 <= inp[idx] <= self.__char_9:  # Decode string
                colon = inp.find(self.__char_colon, idx + 1)
                try:
                    str_len = int(inp[idx: colon])
                    if str_len <= 0:
                        raise ValueError
                except ValueError:
                    raise DecodeError(f'Prefixed string before colon must be an integer and higher than 0. '
                                      f'Input: {inp}.')

                inp_ = inp[idx: colon + str_len + 1]
                try:
                    result = self.decode_string_bytes(inp_)
                    idx = colon + str_len + 1
                except DecodeError:
                    raise DecodeError(f'Cannot decode string from {inp_}.')
            else:
                raise DecodeError(f'Cannot infer type from character {inp[idx]} '
                                  f'at index {idx} in input {inp}.')
            results.append(result)

        return results

    def decode_dictionary(self, inp: bytes):
        """
        Dictionaries are encoded as a 'd' followed by a list of alternating keys and their corresponding values
        followed by an 'e'. For example, d3:cow3:moo4:spam4:eggse corresponds to {'cow': 'moo', 'spam': 'eggs'} and
        d4:spaml1:a1:bee corresponds to {'spam': ['a', 'b']}. Keys must be strings and appear in sorted order
        (sorted as raw strings, not alphanumerics).
        :param inp: Input bytes string
        :return: Decoded dictionary
        """
        if inp[0] != self.__char_d or inp[-1] != self.__char_e:
            raise DecodeError(f'To decode dictionary, input must begin with \'d\' and end with \'e\'. '
                              f'Input: {inp}.')

        results = OrderedDict()
        keys = []
        idx = 1

        while idx < len(inp) - 2:
            # Extract key (string)
            if not self.__char_0 <= inp[idx] <= self.__char_9:
                raise DecodeError(f'Dictionary key must conform to string specification. '
                                  f'Found {inp[idx]} at index {idx}. Input: {inp}.')

            colon = inp.find(self.__char_colon, idx + 1)
            try:
                str_len = int(inp[idx: colon])
                if str_len <= 0:
                    raise ValueError
            except ValueError:
                raise DecodeError(
                    f'Prefixed string before colon must be an integer and higher than 0. Input: {inp}.')
            inp_ = inp[idx: colon + str_len + 1]
            idx = colon + str_len + 1
            try:
                key = self.decode_string_bytes(inp_)
            except DecodeError:
                raise DecodeError(f'Cannot decode string from {inp_}.')

            # Extract value
            if inp[idx] == self.__char_i:  # Decode integer
                ending_e = inp.find(self.__char_e, idx + 1)
                inp_ = inp[idx: ending_e + 1]
                idx = ending_e + 1
                try:
                    value = self.decode_int(inp_)
                except DecodeError:
                    raise DecodeError(f'Cannot decode integer from {inp_}.')
            elif inp[idx] == self.__char_l:  # Decode list
                ending_e = inp.find(self.__char_e, idx + 1)
                inp_ = inp[idx: ending_e + 1]
                idx = ending_e + 1
                try:
                    value = self.decode_list(inp_)
                except DecodeError:
                    raise DecodeError(f'Cannot decode list from {inp_}.')
            elif inp[idx] == self.__char_d:  # Decode dictionary
                ending_e = inp.find(self.__char_e, idx + 1)
                if ending_e == -1:
                    raise DecodeError(f'Cannot decode dictionary from index {idx}.')
                while ending_e != -1:
                    inp_ = inp[idx: ending_e + 1]
                    try:
                        value = self.decode_dictionary(inp_)
                        idx = ending_e + 1
                        break
                    except DecodeError:
                        # raise DecodeError(f'Cannot decode dictionary from {inp_}.')
                        ending_e = inp.find(self.__char_e, ending_e + 1)
                    if ending_e == -1:
                        raise DecodeError(f'Cannot decode dictionary from index {idx}.')
            elif self.__char_0 <= inp[idx] <= self.__char_9:  # Decode string
                colon = inp.find(self.__char_colon, idx + 1)
                try:
                    str_len = int(inp[idx: colon])
                    if str_len <= 0:
                        raise ValueError
                except ValueError:
                    raise DecodeError(
                        f'Prefixed string before colon must be an integer and higher than 0. Input: {inp}.')

                inp_ = inp[idx: colon + str_len + 1]
                idx = colon + str_len + 1
                try:
                    value = self.decode_string_bytes(inp_)
                except DecodeError:
                    raise DecodeError(f'Cannot decode string from {inp_}.')
            else:
                raise DecodeError(f'Cannot infer type from character \'{inp[idx]}\' '
                                  f'at index {idx} in input {inp}.')

            results[key] = value
            keys.append(key)

        if keys != sorted(keys):
            raise DecodeError(f'Keys must be strings and appear in sorted order '
                              f'(sorted as raw strings, not alphanumerics).')

        return results
