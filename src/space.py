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
    # Check for physics damage
    # TODO: This takes a REALLY LONG TIME. Optimize then replace.
    #for block in space.blocks:
    #    block.take_physics_damage()
    # tick down all projectiles
    for p in space._projectiles.copy():
        p.ttl -= 1
        if p.ttl < 1:
            space.safe_remove(p._shape, p._body)
            space.remove_projectile(p)
    for r in space._resources.copy():
        r.ttl -= 1
        if r.ttl < 1:
            space.safe_remove(r._shape, r._body)
            space.remove_resource(r)
        if hasattr(r._shape, "target") and r._shape.target():
            b = r._shape
            direction = b.target().position - b.body.position
            if direction.length < 16 / 2: # TODO: hardcoded block size
                block = b.target()._get_block()
                if block:
                    block.resource_count += 1
                space.remove_resource(r)
            # TODO: 160 is the radius of the field...
            #       let's get that dynamically
            direction.length = max(0.1, (160 - direction.length) / (160))
            b.body.apply_impulse(direction)
    for e in space.explosions:
        e.upkeep()

    # Safely add/remove all necessary items
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
