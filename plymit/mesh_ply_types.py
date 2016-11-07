from collections import namedtuple

Vertex = namedtuple('Vertex', 'x y z')
Face = namedtuple('Face', 'vertex_index')
Triangle = namedtuple('Triangle', 'i0 i1 i2')
Edge = namedtuple('Edge', 'start end')
