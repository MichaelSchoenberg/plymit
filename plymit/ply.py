from enum import Enum, unique
from collections import namedtuple
from typing import Union
import struct


# noinspection PyInitNewSignature
@unique
class ElementPropertyType(Enum):
    CHAR = (1, True, "char")
    UCHAR = (1, False, "uchar")
    SHORT = (2, True, "short")
    USHORT = (2, False, "ushort")
    INT = (4, True, "int")
    UINT = (4, False, "uint")
    FLOAT = (4, True, "float")
    DOUBLE = (8, True, "double")

    def __init__(self, byte_size, signed, friendly_name):
        self.size_in_bytes = byte_size
        self.signed = signed
        self.friendly_name = friendly_name

    def encode_instance_to_bytes(self, obj, byte_order):
        if self == ElementPropertyType.FLOAT or self == ElementPropertyType.DOUBLE:
            format_string = '<' if byte_order == 'little' else '>'
            format_string += 'f' if self == ElementPropertyType.FLOAT else 'd'
            return struct.pack(format_string, obj)
        else:
            return obj.to_bytes(self.size_in_bytes, byteorder=byte_order, signed=self.signed)

    def decode_instance_from_bytes(self, raw_bytes, byte_order):
        if self == ElementPropertyType.FLOAT or self == ElementPropertyType.DOUBLE:
            format_string = '<' if byte_order == 'little' else '>'
            format_string += 'f' if self == ElementPropertyType.FLOAT else 'd'
            return struct.unpack(format_string, raw_bytes)[0]
        else:
            return int.from_bytes(raw_bytes, byteorder=byte_order, signed=self.signed)


# noinspection PyUnusedLocal
def encode_ascii_data(obj, endianness, data_type) -> str:
    return str(obj)


def encode_binary_data(obj, endianness, data_type) -> bytearray:
    return data_type.encode_instance_to_bytes(obj, endianness)


# noinspection PyInitNewSignature
@unique
class PlyFormatOptions(Enum):
    ASCII = ("ascii", "", encode_ascii_data, " ", "\n", "a+", "r")
    BINARY_LITTLE_ENDIAN = ("binary_little_endian", "little", encode_binary_data, b"", b"", "a+b", "rb")
    BINARY_BIG_ENDIAN = ("binary_big_endian", "big", encode_binary_data, b"", b"", "a+b", "rb")

    def __init__(self, friendly_name, byte_order, encoder, sep, linesep, write_filemode, read_filemode):
        self.friendly_name = friendly_name
        self.byte_order = byte_order
        self.encoder = encoder
        self.sep = sep
        self.linesep = linesep
        self.write_filemode = write_filemode
        self.read_filemode = read_filemode

    def concatenate_data(self, elements):
        return self.sep.join(elements)

    def encode_data(self, data, property_type):
        return self.encoder(data, self.byte_order, property_type)


# noinspection PyClassHasNoInit
class ElementProperty(namedtuple('ElementProperty', 'name property_type')):
    """An element property. Each property consists of a name and a type associated with it. Permitted types are
    enumerated in the ElementPropertyType enum above."""
    __slots__ = ()

    def __str__(self):
        return "property " + self.property_type.friendly_name + " " + self.name + "\n"

    def instance_str(self, obj, ply_format) -> Union[str, bytearray]:
        return ply_format.encode_data(getattr(obj, self.name), self.property_type)


# noinspection PyClassHasNoInit
class ListProperty(namedtuple('ListProperty', 'name count_type property_type')):
    """A list property. Each property contains a type describing the count, and a type of the elements."""
    __slots__ = ()

    def __str__(self):
        assert (self.count_type != ElementPropertyType.FLOAT and self.count_type != ElementPropertyType.DOUBLE)
        return str("property list " + self.count_type.friendly_name + " " + self.property_type.friendly_name + " " +
                   self.name + "\n")

    def instance_str(self, obj, ply_format) -> Union[str, bytearray]:
        element_property = getattr(obj, self.name)
        list_data = [ply_format.encode_data(len(element_property), self.count_type)]
        list_data.extend(map(lambda e: ply_format.encode_data(e, self.property_type), element_property))
        return ply_format.concatenate_data(list_data)


class ElementSpecification:
    """Specification of an element type. An element type contains an arbitrary list of properties."""

    def __init__(self, name, *properties):
        self.name = name
        self.properties = list(properties)

    def __eq__(self, other):
        if isinstance(other, ElementSpecification):
            return self.name == other.name and self.properties == other.properties
        return False

    def __hash__(self):
        return hash(self.name)

    def add_property(self, element_property: Union[ElementProperty, ListProperty]):
        self.properties.append(element_property)

    def instance_str(self, obj, ply_format) -> str:
        elements = list(map(lambda e: e.instance_str(obj, ply_format), self.properties))
        return ply_format.concatenate_data(elements) + ply_format.linesep

    @property
    def as_named_tuple(self):
        return namedtuple(self.name, list(map(lambda e: e.name, self.properties)))

    def __call__(self, *args):
        tuple_type = self.as_named_tuple
        setattr(tuple_type, 'plymit_type_backreference', self)  # Embed a back-reference to the specification
        result = tuple_type(*args)
        return result


def token_stream(file, break_on_newline=True):
    """Word tokenizer. Also breaks on newlines."""
    while True:
        # Note: Cannot use 'for line in file', because it breaks ftell() due to hidden buffering in Python internals.
        line = file.readline()
        for word in line.split(None):
            yield word
        if break_on_newline:
            yield '\n'


class PlyHeaderParser:
    """A simple parser to read PLY headers and assemble the information therein."""

    def __init__(self, filename):
        self.ply_format = None
        self.elementData = []

        with open(filename, 'r', errors='ignore') as f:
            words_parsed = 0
            found_ply_magic_token = False
            gen = token_stream(f)
            for word in gen:
                if word == "ply":
                    assert (words_parsed == 0)
                    found_ply_magic_token = True
                elif word == "format":
                    self.parse_keyword_format(gen)
                elif word == "comment":
                    self.parse_keyword_comment(gen)
                elif word == "element":
                    self.parse_keyword_element(gen)
                elif word == "property":
                    self.parse_keyword_property(gen)
                elif word == "end_header":
                    break
                elif word != '\n':
                    assert False  # This is not supposed to happen.
                words_parsed += 1
            assert (found_ply_magic_token is True)
            assert (self.ply_format is not None)
            self.body_offset = f.tell()

    CountSpecificationPair = namedtuple('CountSpecificationPair', 'count specification')

    @staticmethod
    def parse_next_word(gen):
        """Skip the newlines the parser provides."""
        word = next(gen)
        while word == '\n':
            word = next(gen)
        return word

    def parse_keyword_format(self, gen):
        assert (self.ply_format is None)
        format_type = self.parse_next_word(gen)
        for format_option in PlyFormatOptions:
            if format_type == format_option.friendly_name:
                self.ply_format = format_option
                break
        version = self.parse_next_word(gen)
        assert (version == '1.0')

    @staticmethod
    def parse_keyword_comment(gen):
        word = ""
        while word is not '\n':
            word = next(gen)

    def parse_keyword_element(self, gen):
        element_name = self.parse_next_word(gen)
        element_count = int(self.parse_next_word(gen))
        specification = ElementSpecification(element_name)
        self.elementData.append(PlyHeaderParser.CountSpecificationPair(element_count, specification))

    def parse_keyword_property(self, gen):
        assert (len(self.elementData) > 0)
        next_word = self.parse_next_word(gen)
        if next_word == "list":
            count_property_type = self.get_property_type(self.parse_next_word(gen))
            property_type = self.get_property_type(self.parse_next_word(gen))
            property_name = self.parse_next_word(gen)
            self.elementData[-1].specification.add_property(ListProperty(property_name, count_property_type,
                                                                         property_type))
        else:
            property_type = self.get_property_type(next_word)
            property_name = self.parse_next_word(gen)
            self.elementData[-1].specification.add_property(ElementProperty(property_name, property_type))

    @staticmethod
    def get_property_type(property_type_str):
        for property_type in ElementPropertyType:
            if property_type.friendly_name == property_type_str:
                return property_type


class Ply:
    """A simple wrapper containing the data from a Ply file. Ply files contain a list of element types, with a count
    associated with each, and a list of those elements laid out in the order they are specified. Please consult Greg
    Turk's page containing the full specification here:

        http://www.dcs.ed.ac.uk/teaching/cs4/www/graphics/Web/ply.html
    """

    # noinspection PyUnusedLocal
    @staticmethod
    def _parse_body_ascii_element(file, property_type, ply_format, ascii_word_gen):
        word = next(ascii_word_gen)
        if property_type == ElementPropertyType.FLOAT or property_type == ElementPropertyType.DOUBLE:
            return float(word)
        else:
            return int(word)

    @staticmethod
    def _parse_body_binary_element(file, property_type, ply_format):
        raw_bytes = file.read(property_type.size_in_bytes)
        return property_type.decode_instance_from_bytes(raw_bytes, ply_format.byte_order)

    def _parse_body(self, file, header):
        if header.ply_format == PlyFormatOptions.ASCII:
            ascii_word_gen = token_stream(file, break_on_newline=False)
            parse_function = lambda f, prop, pf: self._parse_body_ascii_element(f, prop, pf, ascii_word_gen)
        else:
            parse_function = self._parse_body_binary_element

        for count_element_pair in header.elementData:
            count, element_type = (count_element_pair.count, count_element_pair.specification)
            self.elementLists[element_type.name] = []
            element_tuple_type = namedtuple(element_type.name, map(lambda x: x.name, element_type.properties))
            for element_id in range(count):
                raw_data = []
                for pt in element_type.properties:
                    if isinstance(pt, ListProperty):
                        new_list = []
                        num_elements_in_list = parse_function(file, pt.count_type, header.ply_format)
                        for list_element in range(num_elements_in_list):
                            new_list.append(parse_function(file, pt.property_type, header.ply_format))
                        raw_data.append(new_list)
                    else:
                        raw_data.append(parse_function(file, pt.property_type, header.ply_format))
                self.elementLists[element_type.name].append(element_tuple_type(*raw_data))

    def __init__(self, filename=None):
        """Creates a new ply object. Optionally reads a ply file and populates the internal structures of this object
        to conform to the input file.
        It is important to note that there is no requirement in the ply spec that a ply file contain more than one line.
        That is, all that is important is that there are separators between the keywords and values.
        Note also that this format guarantees that each type is defined only once, but does not guarantee the order
        of type definitions in the ply header."""
        # List of element types, of type ElementSpecification.
        self.elementTypes = set()
        # A dictionary keyed by ElementSpecification name containing a list of the actual members of said elements.
        self.elementLists = {}

        if filename is not None:
            parser = PlyHeaderParser(filename)
            self.elementTypes = self.elementTypes.union(set(map(lambda x: x.specification, parser.elementData)))
            with open(filename, parser.ply_format.read_filemode) as f:
                f.seek(parser.body_offset)
                self._parse_body(f, parser)

    def __eq__(self, other):
        if isinstance(other, Ply):
            return self.elementTypes == other.elementTypes and self.elementLists == other.elementLists
        return False

    def add_element_type(self, *element_type):
        """Add support to this ply file for any number of element types."""
        for i in element_type:
            self.elementTypes.add(i)
            if i.name not in self.elementLists:
                self.elementLists[i.name] = []

    def add_elements(self, *elements):
        """Adds any number of elements of any known type."""
        for i in elements:
            self.add_element_type(i.plymit_type_backreference)
            self.elementLists[i.__class__.__name__].append(i)

    def add_bulk_elements(self, elements):
        """Adds any number of elements of the same type."""
        if len(elements) > 0:
            element_type = elements[0].plymit_type_backreference
            self.add_element_type(element_type)
            try:
                self.elementLists[element_type.name].extend(elements)
            except TypeError:
                self.elementLists[element_type.name].append(elements)

    def get_elements_of_type(self, element_type):
        return self.elementLists[element_type.name]

    def write_header(self, filename, ply_format: PlyFormatOptions):
        with open(filename, 'w') as f:
            f.write("ply\n")
            f.write("format " + ply_format.friendly_name + " 1.0\n")
            f.write("comment written by plymit\n")
            for et in self.elementTypes:
                num_such_elements = len(self.elementLists[et.name])
                f.write("element " + et.name + " " + str(num_such_elements) + "\n")
                for pt in et.properties:
                    f.write(str(pt))
            f.write("end_header\n")

    def write(self, filename, ply_format):
        self.write_header(filename, ply_format)
        with open(filename, ply_format.write_filemode) as f:
            for et in self.elementTypes:
                for element in self.elementLists[et.name]:
                    f.write(et.instance_str(element, ply_format))
