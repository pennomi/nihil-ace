"""Materials hold the physical properties and collision types of all objects.
"""

COLLISION_TYPES = {
    "ship": 1,
    "shield": 2,
    "blaster": 3,
    "explosion": 4,
    "resource": 5,
    "tractor": 6,
    "ghost": 7,
}


class Material(object):
    name = "Base Material"
    density = 1
    hp = 1
    friction = 0.0
    elasticity = 0.0
    collision_type = COLLISION_TYPES['ship']


class NanotubeWeave(Material):
    name = "Nanotube Weave"
    friction = .5
    elasticity = .25
