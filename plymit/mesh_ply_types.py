from plymit import ElementSpecification, ElementProperty, ElementPropertyType, ListProperty

VertexType = ElementSpecification('vertex',
                                  ElementProperty('x', ElementPropertyType.FLOAT),
                                  ElementProperty('y', ElementPropertyType.FLOAT),
                                  ElementProperty('z', ElementPropertyType.FLOAT))

FaceType = ElementSpecification('face',
                                ListProperty('vertex_index', ElementPropertyType.UCHAR, ElementPropertyType.INT))

TriangleType = ElementSpecification('triangle',
                                    ElementProperty('i0', ElementPropertyType.UINT),
                                    ElementProperty('i1', ElementPropertyType.UINT),
                                    ElementProperty('i2', ElementPropertyType.UINT))

EdgeType = ElementSpecification('edge',
                                ElementProperty('start', ElementPropertyType.UINT),
                                ElementProperty('end', ElementPropertyType.UINT))
