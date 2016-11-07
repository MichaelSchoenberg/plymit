from plymit import Ply, ElementSpecification, ElementProperty, ElementPropertyType, ListProperty, PlyFormatOptions
from collections import namedtuple

p = Ply()
vType = ElementSpecification('vertex')
vType.add_property(ElementProperty('x', ElementPropertyType.FLOAT))
vType.add_property(ElementProperty('y', ElementPropertyType.FLOAT))
vType.add_property(ElementProperty('z', ElementPropertyType.FLOAT))
p.add_element_type(vType)

VertexType = namedtuple('vertex', 'x y z')

p.add_elements('vertex', [VertexType(0, 0, 0), VertexType(0, 0, 1), VertexType(0, 1, 1), VertexType(0, 1, 0),
                          VertexType(1, 0, 0), VertexType(1, 0, 1), VertexType(1, 1, 1), VertexType(1, 1, 0)])

fType = ElementSpecification('face')
fType.add_property(ListProperty('vertex_index', ElementPropertyType.UCHAR, ElementPropertyType.INT))
p.add_element_type(fType)

FaceType = namedtuple('face', 'vertex_index')

p.add_elements('face', [FaceType([0, 1, 2, 3]), FaceType([7, 6, 5, 4]), FaceType([0, 4, 5, 1]),
                        FaceType([1, 5, 6, 2]), FaceType([2, 6, 7, 3]), FaceType([3, 7, 4, 0])])

if __name__ == '__main__':
    for possible_format in PlyFormatOptions:
        print('Validating that writing and reading a ply of format ' + possible_format.friendly_name +
              ' produces the same ply.')
        p.write('test.ply', possible_format)
        p2 = Ply('test.ply')
        assert(p == p2)
    print('Done.')

