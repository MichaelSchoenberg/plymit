from enum import Enum, unique
from collections import namedtuple
from typing import Union
from typing import Generator
import struct

# TODO: This is temporary for testing!
class Vertex:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class Face:
    def __init__(self, vertices):
        self.vertex_index = vertices
# TODO REMOVE ABOVE


# noinspection PyInitNewSignature
@unique
class ElementPropertyType(Enum):
    CHAR = (1, True, "char")
    UCHAR = (1, False,"uchar")
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
        assert(self.count_type != ElementPropertyType.FLOAT and self.count_type != ElementPropertyType.DOUBLE)
        return str("property list " + self.count_type.friendly_name + " " + self.property_type.friendly_name + " " +
                   self.name + "\n")

    def instance_str(self, obj, ply_format) -> Union[str, bytearray]:
        element_property = getattr(obj, self.name)
        list_data = [ply_format.encode_data(len(element_property), self.count_type)]
        list_data.extend(map(lambda e: ply_format.encode_data(e, self.property_type), element_property))
        return ply_format.concatenate_data(list_data)


class ElementSpecification:
    """Specification of an element type. An element type contains an arbitrary list of properties."""

    def __init__(self, name):
        self.name = name
        self.properties = []

    def add_property(self, element_property: Union[ElementProperty, ListProperty]):
        self.properties.append(element_property)

    def instance_str(self, obj, ply_format) -> str:
        elements = list(map(lambda e: e.instance_str(obj, ply_format), self.properties))
        return ply_format.concatenate_data(elements) + ply_format.linesep


def token_stream(file):
    """Word tokenizer. Also breaks on newlines."""
    for line in file:
        for word in line.split(None):
            yield word
        yield '\n'


class PlyHeaderParser:
    """A simple parser to read PLY headers and assemble the information therein."""
    def __init__(self, filename):
        self.ply_format = None
        self.elementData = []
        with open(filename, 'r') as f:
            words_parsed = 0
            found_ply_magic_token = False
            gen = token_stream(f)
            for word in gen:
                if word == "ply":
                    assert(words_parsed == 0)
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
                words_parsed += 1
            assert(found_ply_magic_token is True)
            assert(self.ply_format is not None)
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
        assert(self.ply_format is None)
        format_type = self.parse_next_word(gen)
        for format_option in PlyFormatOptions:
            if format_type == format_option.friendly_name:
                self.ply_format = format_option
                break
        version = self.parse_next_word(gen)
        assert(version == '1.0')

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
        assert(self.currentParsingElement is not None)
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

    def __init__(self, filename=None):
        """Optionally reads a ply file and populates the internal structures of this object to conform to them.
        It is important to note that there is no requirement in the ply spec that a ply file contain more than one line.
        That is, all that is important is that there are separators between the keywords and values."""
        # List of element types, of type ElementSpecification.
        self.elementTypes = []
        # A dictionary keyed by ElementSpecification name containing a list of the actual members of said elements.
        self.elementLists = {}

        if filename is not None:
            parser = PlyHeaderParser(filename)
            with open(filename, parser.ply_format.read_filemode) as f:
                f.seek(parser.body_offset)
                # TODO: Read the elements!

    def add_element_type(self, element_type: ElementSpecification):
        self.elementTypes.append(element_type)
        self.elementLists[element_type.name] = []

    def add_elements(self, type_name, elements):
        try:
            self.elementLists[type_name].extend(elements)
        except TypeError:
            self.elementLists[type_name].append(elements)

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

if __name__ == "__main__":
    p = Ply()
    vType = ElementSpecification('vertex')
    vType.add_property(ElementProperty('x', ElementPropertyType.FLOAT))
    vType.add_property(ElementProperty('y', ElementPropertyType.FLOAT))
    vType.add_property(ElementProperty('z', ElementPropertyType.FLOAT))
    p.add_element_type(vType)

    p.add_elements('vertex', [Vertex(0, 0, 0), Vertex(0, 0, 1), Vertex(0, 1, 1), Vertex(0, 1, 0), Vertex(1, 0, 0),
                              Vertex(1, 0, 1), Vertex(1, 1, 1), Vertex(1, 1, 0)])

    fType = ElementSpecification('face')
    fType.add_property(ListProperty('vertex_index', ElementPropertyType.UCHAR, ElementPropertyType.INT))
    p.add_element_type(fType)

    p.add_elements('face', [Face([0, 1, 2, 3]), Face([7, 6, 5, 4]), Face([0, 4, 5, 1]), Face([1, 5, 6, 2]),
                            Face([2, 6, 7, 3]), Face([3, 7, 4, 0])])

    p.write('test.ply', PlyFormatOptions.BINARY_LITTLE_ENDIAN)
