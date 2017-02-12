from plymit import Ply, PlyFormatOptions, VertexType, FaceType
from plymit import ElementSpecification, ElementProperty, ElementPropertyType

# Create an empty ply object
p = Ply()

# Add a bunch of vertex elements. This is a faster way to add elements of the same type in bulk.
p.add_bulk_elements([VertexType(0, 0, 0), VertexType(0, 0, 1), VertexType(0, 1, 1),
                     VertexType(0, 1, 0), VertexType(1, 0, 0), VertexType(1, 0, 1),
                     VertexType(1, 1, 1)])

# Add the last vertex and a bunch of face elements. add_elements adds any number of elements of any type.
p.add_elements(VertexType(1, 1, 0), FaceType([0, 1, 2, 3]), FaceType([7, 6, 5, 4]), FaceType([0, 4, 5, 1]),
               FaceType([1, 5, 6, 2]), FaceType([2, 6, 7, 3]), FaceType([3, 7, 4, 0]))

assert(len(p.get_elements_of_type(VertexType)) == 8)
assert(len(p.get_elements_of_type(FaceType)) == 6)

# For demonstration purposes, here's how you define a new type for the ply to know about. See mesh_ply_types.py for more
# examples.
QuadType = ElementSpecification('triangle',
                                ElementProperty('i0', ElementPropertyType.UINT),
                                ElementProperty('i1', ElementPropertyType.UINT),
                                ElementProperty('i2', ElementPropertyType.UINT),
                                ElementProperty('i3', ElementPropertyType.UINT))

# Even if you don't use the type, you can guarantee it is written into the ply header by adding it to the ply type list.
p.add_element_type(QuadType)

if __name__ == '__main__':
    for possible_format in PlyFormatOptions:
        print('Validating that writing and reading a ply of format ' + possible_format.friendly_name +
              ' produces the same ply.')
        p.write('test.ply', possible_format)
        p2 = Ply('test.ply')
        assert(p == p2)
    print('Done.')

