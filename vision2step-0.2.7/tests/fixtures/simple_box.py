import cadquery as cq

LENGTH = 120.0
WIDTH = 60.0
THICKNESS = 10.0

result = cq.Workplane("XY").box(LENGTH, WIDTH, THICKNESS)
