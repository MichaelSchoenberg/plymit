from enum import Enum, unique
from collections import namedtuple
from typing import Union

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


@unique
class ElementPropertyType(Enum):
    CHAR = (1, "char")
    UCHAR = (1, "uchar")
    SHORT = (2, "short")
    USHORT = (2, "ushort")
    INT = (4, "int")
    UINT = (4, "uint")
    FLOAT = (4, "float")
    DOUBLE = (8, "double")

    def __init__(self, byte_size, friendly_name):
        self.size_in_bytes = byte_size
        self.friendly_name = friendly_name

@unique
class PlyFormatOptions(Enum):
    ASCII = "ascii"
    BINARY_LITTLE_ENDIAN = "binary_little_endian"
    BINARY_BIG_ENDIAN = "binary_big_endian"


class ElementProperty(namedtuple('ElementProperty', 'name property_type')):
    """An element property. Each property consists of a name and a type associated with it. Permitted types are
    enumerated in the ElementPropertyType enum above."""
    __slots__ = ()

    def __str__(self):
        return "property " + self.property_type.friendly_name + " " + self.name + "\n"

    def instance_str(self, obj) -> str:
        return str(getattr(obj, self.name))


class ListProperty(namedtuple('ListProperty', 'name count_type property_type')):
    """A list property. Each property contains a type describing the count, and a type of the elements."""
    __slots__ = ()

    def __str__(self):
        assert(self.count_type != ElementPropertyType.FLOAT and self.count_type != ElementPropertyType.DOUBLE)
        assert(self.property_type != ElementPropertyType.FLOAT and self.property_type != ElementPropertyType.DOUBLE)
        return str("property list " + self.count_type.friendly_name + " " + self.property_type.friendly_name + " " +
                   self.name + "\n")

    def instance_str(self, obj) -> str:
        element_property = getattr(obj, self.name)
        return str.rstrip(str(len(element_property)), ' ') + "".join(str(e) for e in element_property)


class ElementSpecification:
    """Specification of an element type. An element type contains an arbitrary list of properties."""

    def __init__(self, name):
        self.name = name
        self.properties = []

    def add_property(self, element_property: Union[ElementProperty, ListProperty]):
        self.properties.append(element_property)

    def instance_str(self, obj) -> str:
        return "".join(e.instance_str(obj) for e in self.properties)


class Ply:
    """A simple wrapper containing the data from a Ply file. Ply files contain a list of element types, with a count
    associated with each, and a list of those elements laid out in the order they are specified. Please consult Greg
    Turk's page containing the full specification here:

        http://www.dcs.ed.ac.uk/teaching/cs4/www/graphics/Web/ply.html
    """

    def __init__(self):
        # List of element types, of type ElementSpecification.
        self.elementTypes = []
        # A dictionary keyed by ElementSpecification name containing a list of the actual members of said elements.
        self.elementLists = {}

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
            f.write("format " + ply_format.value + " 1.0\n")
            f.write("comment written by plymit\n")
            for et in self.elementTypes:
                num_such_elements = len(self.elementLists[et.name])
                f.write("element " + et.name + " " + str(num_such_elements) + "\n")
                for pt in et.properties:
                    f.write(str(pt))
            f.write("end_header\n")

    def write(self, filename, ply_format):
        self.write_header(filename, ply_format)
        with open(filename, 'a+') as f:
            for et in self.elementTypes:
                for element in self.elementLists[et.name]:
                    f.write(" ".join(et.instance_str(element)) + "\n")

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

    p.write('test.ply', PlyFormatOptions.ASCII)
