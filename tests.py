from plymit import Ply, PlyFormatOptions, VertexType, FaceType

p = Ply(None, VertexType, FaceType)
p.add_bulk_elements(VertexType.name, [VertexType(0, 0, 0), VertexType(0, 0, 1), VertexType(0, 1, 1),
                                      VertexType(0, 1, 0), VertexType(1, 0, 0), VertexType(1, 0, 1),
                                      VertexType(1, 1, 1), VertexType(1, 1, 0)])

p.add_elements(FaceType([0, 1, 2, 3]), FaceType([7, 6, 5, 4]), FaceType([0, 4, 5, 1]),
               FaceType([1, 5, 6, 2]), FaceType([2, 6, 7, 3]), FaceType([3, 7, 4, 0]))

assert(len(p.get_elements_of_type(VertexType)) == 8)
assert(len(p.get_elements_of_type(FaceType)) == 6)

if __name__ == '__main__':
    for possible_format in PlyFormatOptions:
        print('Validating that writing and reading a ply of format ' + possible_format.friendly_name +
              ' produces the same ply.')
        p.write('test.ply', possible_format)
        p2 = Ply('test.ply')
        assert(p == p2)
    print('Done.')

