import math
import pyglet
import pymunk
from renderer import adjust_for_cam, off_screen, draw_rect, draw_large_point
from space import SPACE
from materials import Material, COLLISION_TYPES
from pyglet.window import key
from pymunk import PivotJoint, GearJoint
from pymunk.vec2d import Vec2d
from weakref import ref, WeakSet
from explosion import Explosion
from projectiles import Projectile
from resources import Resource
from pyglet.sprite import Sprite
import random

BLOCK_SIZE = 16

CACHED_IMAGES = {}
def load_image(filename, anchor=Vec2d(0, 0)):
    if filename in CACHED_IMAGES:
        return CACHED_IMAGES[filename]
    else:
        img = pyglet.image.load(filename)
        img.anchor_x, img.anchor_y = int(anchor.x), int(anchor.y)
        CACHED_IMAGES[filename] = img.mipmapped_texture
        return CACHED_IMAGES[filename]


class ConstructionBlock():
    ''' THIS REALLY ISN'T A BLOCK!
    It's a ghost object that is used to display to the user where their mouse
    is going to place a block on their ship. '''
    direction = 0 # 0-3 for the cardinal directions
    image = 'basic'
    image_anchor = Vec2d(BLOCK_SIZE / 2, BLOCK_SIZE / 2)

    def __init__(self):
        # load images
        base_path = "images/blocks/{}.png".format(self.image)
        self.img = load_image(base_path, self.image_anchor)
        w = h = BLOCK_SIZE
        inertia = pymunk.moment_for_box(1, w, h)
        self._body = pymunk.Body(1, inertia)
        self._body.position = Vec2d(0, 0)
        self._shape = pymunk.Poly.create_box(self._body, (w, h))
        self._shape.collision_type = COLLISION_TYPES['ghost']
        self._shape.sensor = True
        self._shape._get_block = ref(self)
        SPACE.add(self._body, self._shape)

    def draw(self):
        draw_rect(self.img.id, self._shape.get_points(),
                  direction=self.direction)


class Block(object):
    # TODO: let's make blocks that can be more than a single fixed size
    material = Material()
    bindings = []
    direction = 0 # 0-3 for the cardinal directions
    health = 3
    damage = 0
    has_exploded = False

    # sprites
    image = 'basic'
    # TODO: calculate this based on individual block size
    image_anchor = Vec2d(BLOCK_SIZE / 2, BLOCK_SIZE / 2)

    def __init__(self, point):
        self._joints = WeakSet()
        self._adjacent_blocks = WeakSet()
        # load images
        base_path = "images/blocks/{}.png".format(self.image)
        damaged_path = "images/blocks/{}_damaged.png".format(self.image)
        destroyed_path = "images/blocks/{}_destroyed.png".format(self.image)
        self.img = load_image(base_path, self.image_anchor)
        self.img_damaged = load_image(damaged_path, self.image_anchor)
        self.img_destroyed = load_image(destroyed_path, self.image_anchor)

        w = h = BLOCK_SIZE
        # using (density * 1 ** 2) for these because our units are BLOCK_SIZE
        inertia = pymunk.moment_for_box(self.material.density, w, h)
        self._body = pymunk.Body(self.material.density, inertia)
        self._body.position = point
        self._shape = pymunk.Poly.create_box(self._body, (w, h))
        self._shape.elasticity = self.material.elasticity
        self._shape.friction = self.material.friction
        self._shape.collision_type = self.material.collision_type
        self._shape._get_block = ref(self)
        SPACE.add(self._body, self._shape)
        SPACE.register_block(self)

    def weld_to(self, block):
        pj = PivotJoint(self._body, block._body,
                              (self._body.position + block._body.position) / 2)
        gj = GearJoint(self._body, block._body, 0, 1)
        SPACE.add(pj, gj)
        # add weak references to each other
        block._adjacent_blocks.add(self)
        self._adjacent_blocks.add(block)
        # and to the joint
        self._joints.add(pj)
        block._joints.add(pj)
        self._joints.add(gj)
        block._joints.add(gj)

    def draw(self):
        if off_screen(self._body.position):
            return
        if self.damage >= self.health:
            tex = self.img_destroyed.id
        elif self.damage > 0:
            tex = self.img_damaged.id
        else:
            tex = self.img.id
        draw_rect(tex, self._shape.get_points(), direction=self.direction)

    def take_physics_damage(self):
        for joint in self._joints.copy():
            self.take_damage(joint.impulse // 250)

    def take_damage(self, amount):
        self.damage += amount
        if self.damage >= self.health and not self.has_exploded:
            # create an explosion
            self.has_exploded = True
            Explosion(self._body.position, BLOCK_SIZE,
                      velocity=self._body.velocity)
            # remove joints
            SPACE.safe_remove(*self._joints)
            self._joints = WeakSet()
            # remove ties to the construction
            for block in self._adjacent_blocks:
                block._adjacent_blocks.remove(self)
            self._adjacent_blocks = WeakSet()
        elif self.damage >= self.health * 2:
            Explosion(self._body.position, BLOCK_SIZE,
                      velocity=self._body.velocity)
            for i in range(random.randint(1,5)):
                Resource(self)
            SPACE.safe_remove(self._body, self._shape)
            SPACE.delete_block(self)

    @property
    def construction(self):
        c = WeakSet()
        c.add(self)
        self._build_construction(c)
        return c

    def _build_construction(self, current_set):
        for block in self._adjacent_blocks:
            if block not in current_set:
                current_set.add(block)
                block._build_construction(current_set)


class AngleLeftBlock(Block):
    image = 'angle_left'


class AngleRightBlock(Block):
    image = 'angle_right'


class FinLeftBlock(Block):
    image = 'fin_left'


class FinRightBlock(Block):
    image = 'fin_right'


class ArmorBlock(Block):
    health = 6
    image = 'armor'


class ReactorBlock(Block):
    power_generated = 3
    power_used = 0
    image = 'reactor'
    big_explosion = False

    def take_damage(self, amount):
        super(ReactorBlock, self).take_damage(amount)
        if self.damage >= self.health and not self.big_explosion:
            self.big_explosion = True
            Explosion(self._body.position, BLOCK_SIZE * 1.5,
                      velocity=self._body.velocity, damage=2)


class CockpitBlock(Block):
    image = 'cockpit'
    ai = True

    def __init__(self, point):
        super(CockpitBlock, self).__init__(point)
        self.slave_blocks = WeakSet()
        self.shieldsup = False

    def on_key_press(self, key):
        [b.on_key_down() for b in self.slave_blocks if b.key == key]

    def on_key_release(self, key):
        [b.on_key_up() for b in self.slave_blocks if b.key == key]

    def enemy_ai_update(self):
        # TODO: This is pretty stupid AI. We'll have to work on that later.
        # ALWAYS TURN ON SHIELDS
        if not self.shieldsup:
            [b.on_key_down() for b in self.slave_blocks if isinstance(b, ShieldBlock)]
            self.shieldsup = True

        # ALWAYS FLY TOWARDS PLAYER
        if not SPACE.camera_lock(): # they win and quit moving
            [b.on_key_up() for b in self.slave_blocks]
            return
        target = SPACE.camera_lock # this is naive, but works for now
        target_dir = target()._body.position - self._body.position
        ang = (self._body.angle - target_dir.angle + math.pi / 2) % (math.pi * 2)
        general_direction = abs((ang) % (math.pi * 2)) < math.pi / 8
        ang += self._body.angular_velocity
        if ang > 0 and abs(ang) <= math.pi:
            best_direction = "ccw"
        elif ang > 0 and abs(ang) > math.pi:
            best_direction = "cw"
        elif ang < 0 and abs(ang) <= math.pi:
            best_direction = "cw"
        elif ang < 0 and abs(ang) > math.pi:
            best_direction = "ccw"
        if self._body.angular_velocity > math.pi / 2:
            [b.on_key_up() for b in self.slave_blocks if b.key == key.LEFT]
            [b.on_key_down() for b in self.slave_blocks if b.key == key.RIGHT]
        elif self._body.angular_velocity < -math.pi / 2:
            [b.on_key_up() for b in self.slave_blocks if b.key == key.RIGHT]
            [b.on_key_down() for b in self.slave_blocks if b.key == key.LEFT]
        # TODO: If moving very fast relative to the target, slow down
        elif best_direction == "cw":
            [b.on_key_up() for b in self.slave_blocks if b.key == key.RIGHT]
            [b.on_key_down() for b in self.slave_blocks if b.key == key.LEFT]
        else:
            [b.on_key_up() for b in self.slave_blocks if b.key == key.LEFT]
            [b.on_key_down() for b in self.slave_blocks if b.key == key.RIGHT]

        # SHOOT AT PLAYER IF CLOSE
        ang = self._body.angle - target_dir.angle + math.pi / 2
        if (target_dir.length <= BLOCK_SIZE * 50 and general_direction):
            [b.on_key_down() for b in self.slave_blocks if isinstance(b, BlasterBlock)]
        else:
            [b.on_key_up() for b in self.slave_blocks if isinstance(b, BlasterBlock)]


class ControllableBlock(Block):
    power_requirement = 1
    key = None
    binding_type = "toggle" # also use "mirror" or "inverted"
    _active = False # True if it is currently running
    on = False # True if the "switch" is on. It *may* actually be active.
    powered = False

    def on_key_down(self):
        if self.binding_type == "toggle":
            self.on = not self.on
        elif self.binding_type == "mirror":
            self.on = True
        elif self.binding_type == "inverted":
            self.on = False

    def on_key_up(self):
        if self.binding_type == "toggle":
            pass
        elif self.binding_type == "mirror":
            self.on = False
        elif self.binding_type == "inverted":
            self.on = True

    def _upkeep(self):
        if self.powered and self.on and not self._active:
            self.activate()
            self._active = True
        elif not (self.on and self.powered) and self._active:
            self.deactivate()
            self._active = False

    def _power_upkeep(self):
        if not self.on:
            return True
        self.powered = False
        c = self.construction
        power_blocks = [b for b in c if isinstance(b, ReactorBlock)]
        for b in power_blocks:
            if b.power_used + self.power_requirement <= b.power_generated:
                b.power_used += self.power_requirement
                self.powered = True
                return True # successfully powered
        return False # no more power

    def activate(self):
        pass

    def deactivate(self):
        pass


class BlasterBlock(ControllableBlock):
    image = 'blaster'

    cooldown = 10
    cooldown_counter = 0

    def shoot(self):
        self.cooldown_counter = self.cooldown
        Projectile(source=self, damage=1)

    def _upkeep(self):
        super(BlasterBlock, self)._upkeep()
        self.cooldown_counter -= 1
        if self._active and self.cooldown_counter <= 0:
            self.shoot()


SHIELD_IMAGE = load_image('images/shield_bubble.png')
class ShieldBlock(ControllableBlock):
    magnitude = 500
    image = 'shield'
    _shield_body = None
    _shield_shape = None
    _shield_link = None
    radius = BLOCK_SIZE * 2

    def activate(self):
        density = 0.01
        mass = density
        inertia = pymunk.moment_for_circle(mass, 0, self.radius)
        self._shield_body = pymunk.Body(mass, inertia)
        self._shield_body.position = self._body.position
        self._shield_shape = pymunk.Circle(self._shield_body, self.radius)
        self._shield_shape.elasticity = 0.5
        self._shield_shape.friction= 0.0
        self._shield_shape.collision_type = COLLISION_TYPES["shield"]
        self._shield_link = PivotJoint(self._body, self._shield_body,
                                                                (0, 0), (0, 0))
        SPACE.add(self._shield_body, self._shield_shape, self._shield_link)

    def deactivate(self):
        SPACE.remove(self._shield_link, self._shield_body, self._shield_shape)
        self._shield_body = self._shield_link = self._shield_shape = None

    def draw(self):
        super(ShieldBlock, self).draw()
        if self._active and not off_screen(self._shield_body.position):
            draw_large_point(SHIELD_IMAGE.id, self._shield_body.position, self.radius)


class TractorBlock(ControllableBlock):
    magnitude = 500
    image = 'shield'
    _tractor_body = None
    _tractor_shape = None
    _tractor_link = None
    radius = BLOCK_SIZE * 10
    resource_count = 0 # this will eventually be storage blocks?

    def activate(self):
        density = 0.01
        mass = density
        inertia = pymunk.moment_for_circle(mass, 0, self.radius)
        self._tractor_body = pymunk.Body(mass, inertia)
        self._tractor_body.position = self._body.position
        self._tractor_body._get_block = ref(self)
        self._tractor_shape = pymunk.Circle(self._tractor_body, self.radius)
        self._tractor_shape.collision_type = COLLISION_TYPES["tractor"]
        self._tractor_shape.sensor = True
        self._tractor_link = PivotJoint(self._body, self._tractor_body,
                                                                (0, 0), (0, 0))
        SPACE.add(self._tractor_body, self._tractor_shape, self._tractor_link)

    def deactivate(self):
        SPACE.remove(self._tractor_link, self._tractor_body, self._tractor_shape)
        self._tractor_body = self._tractor_link = self._tractor_shape = None

    def draw(self):
        super(TractorBlock, self).draw()
        if self._active and not off_screen(self._tractor_body.position):
            draw_large_point(SHIELD_IMAGE.id, self._tractor_body.position, self.radius)


class ScannerBlock(ControllableBlock):
    magnitude = BLOCK_SIZE * 1000
    image = 'scanner'

    ARROW = load_image('images/arrow.png')
    ARROW.anchor_x = 16
    ARROW.anchor_y = 16
    _arrow_sprite = Sprite(ARROW)

    def draw(self):
        super(ScannerBlock, self).draw()
        if not self._active:
            return
        for b in SPACE.blocks:
            if not isinstance(b, ReactorBlock) or b.has_exploded:
                continue
            v = b._body.position - self._body.position
            d = v.length
            if d > BLOCK_SIZE * 5 and d < self.magnitude:
                v.length = BLOCK_SIZE * 5
                pos = adjust_for_cam(self._body.position + v)
                self._arrow_sprite._x, self._arrow_sprite._y = pos.x, pos.y
                self._arrow_sprite.rotation = -(v.angle / math.pi * 180)
                self._arrow_sprite.scale = (self.magnitude - d) / self.magnitude
                self._arrow_sprite.draw()


ENGINE_FIRE = load_image('images/fire.png')

class EngineBlock(ControllableBlock):
    magnitude = 500
    image = 'engine'

    def _upkeep(self):
        super(EngineBlock, self)._upkeep()
        self._body.reset_forces()
        if self._active:
            v1 = Vec2d(0, self.magnitude)
            v1.rotate(self._body.angle + float(self.direction) / 2 * math.pi)
            self._body.apply_force(v1)

    def deactivate(self):
        self._body.reset_forces()

    def draw(self):
        super(EngineBlock, self).draw()
        if self._active and not off_screen(self._body.position):
            offset = Vec2d(0, -BLOCK_SIZE)
            offset.rotate(self._body.angle + float(self.direction) / 2 * math.pi)
            points = [p + offset for p in self._shape.get_points()]
            draw_rect(ENGINE_FIRE.id, points, direction=self.direction)
