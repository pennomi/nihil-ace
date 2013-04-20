'''
Subclass of pymunk.Space so that we can keep track of additional block updates.
'''
import pymunk
from weakref import WeakSet

# TODO: Instead of having a separate implementation for each of these, let's
#       make one remove method that switches them by class.
_OBJECTS_TO_REMOVE = WeakSet()
_OBJECTS_TO_ADD = WeakSet()
_BLOCKS_TO_REMOVE = WeakSet()
_PROJECTILES_TO_REMOVE = WeakSet()
_RESOURCES_TO_REMOVE = WeakSet()

def space_upkeep(space):
    # update scale smoothly
    space.scale += (space.target_scale - space.scale) * .25
    # upkeep on various entities
    for p in space._projectiles.copy():
        p.upkeep()
    for r in space._resources.copy():
        r.upkeep()
    for e in space.explosions:
        e.upkeep()
    # safely add/remove all necessary items
    space._safe_add()
    space._safe_remove()

class Space(pymunk.Space):
    blocks = []
    controller_blocks = []
    controllable_blocks = []
    explosions = []
    camera_lock = None
    last_pos = pymunk.vec2d.Vec2d(0, 0)
    scale = 1
    target_scale = 1
    _projectiles = set()
    _resources = set()

    def __init__(self):
        super(Space, self).__init__()
        self.damping = 0.8
        self.iterations = 100

    def delete_block(self, b):
        _BLOCKS_TO_REMOVE.add(b)

    def remove_projectile(self, b):
        _PROJECTILES_TO_REMOVE.add(b)

    def remove_resource(self, b):
        _RESOURCES_TO_REMOVE.add(b)

    def register_projectile(self, projectile):
        self._projectiles.add(projectile)

    def register_resource(self, res):
        self._resources.add(res)

    def register_block(self, block):
        self.blocks.append(block)
        if hasattr(block, 'ai'):
            self.controller_blocks.append(block)
        if hasattr(block, 'key'):
            self.controllable_blocks.append(block)

    def register_explosion(self, exp):
        self.explosions.append(exp)

    def safe_add(self, *args):
        for a in args:
            _OBJECTS_TO_ADD.add(a)

    def _safe_add(self, *args):
        for a in _OBJECTS_TO_ADD.copy():
            self.add(a)
            _OBJECTS_TO_ADD.remove(a)

    def safe_remove(self, *args):
        for a in args:
            _OBJECTS_TO_REMOVE.add(a)

    def _safe_remove(self, *args):
        for b in _BLOCKS_TO_REMOVE:
            if b in SPACE.blocks:
                SPACE.blocks.remove(b)
            if b in SPACE.controller_blocks:
                SPACE.controller_blocks.remove(b)
            if b in SPACE.controllable_blocks:
                SPACE.controllable_blocks.remove(b)
        for b in _PROJECTILES_TO_REMOVE:
            SPACE._projectiles.remove(b)
        for b in _RESOURCES_TO_REMOVE:
            SPACE._resources.remove(b)

        for a in _OBJECTS_TO_REMOVE:
            try:
                self.remove(a)
            except KeyError:
                print "Error removing:", a
                pass # ignore non-existent stuff, etc.

SPACE = Space()
