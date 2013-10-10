import math
import pyglet
import pymunk
import random
from pymunk.vec2d import Vec2d
from materials import COLLISION_TYPES
from space import SPACE
from weakref import ref
from pyglet import gl
from renderer import adjust_for_cam

# TODO: duplicated
BLOCK_SIZE = 16

RESOURCE_IMAGE = pyglet.image.load('images/iron.png').mipmapped_texture


class Resource(object):
    # represents the halflife of the resource object
    decay_chance = 0.00125

    def __init__(self, source=None):
        # physics
        r = 4
        mass = 0.01
        inertia = pymunk.moment_for_circle(mass, 0, r)
        self._body = pymunk.Body(mass, inertia)
        p = Vec2d(random.uniform(0, BLOCK_SIZE), 0)
        p.rotate(random.uniform(0, 2 * math.pi))
        self._body.position = source._body.position
        self._body.velocity = source._body.velocity + p
        self._shape = pymunk.Circle(self._body, r)
        self._shape.elasticity = 1.0
        self._shape.friction= 0.0
        self._shape.collision_type = COLLISION_TYPES["resource"]
        self._shape._get_resource = ref(self)
        self._shape.sensor = True
        SPACE.add(self._body, self._shape)
        SPACE.resources.add(self)

    def upkeep(self):
        if self.decay_chance > random.random():
            SPACE.remove(self._shape, self._body)
            SPACE.resources.remove(self)
        if hasattr(self._shape, "target") and self._shape.target():
            b = self._shape
            direction = b.target().position - b.body.position
            if direction.length < BLOCK_SIZE / 2:
                block = b.target()._get_block()
                if block:
                    block.resource_count += 1
                SPACE.resources.remove(self)
            # TODO: 160 is the radius of the field...
            #       let's get that dynamically
            direction.length = max(0.1, (160 - direction.length) / 160)
            b.body.apply_impulse(direction)
            # TODO: http://chipmunk-physics.net/forum/viewtopic.php?f=1&t=2912

    def draw(self):
        p = adjust_for_cam(self._body.position)

        gl.glEnable(pyglet.gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, RESOURCE_IMAGE.id)
        gl.glEnable(gl.GL_POINT_SPRITE)
        gl.glTexEnvi(gl.GL_POINT_SPRITE, gl.GL_COORD_REPLACE, gl.GL_TRUE)
        gl.glPointSize(8 * SPACE.scale)

        gl.glBegin(gl.GL_POINTS)
        # TODO: more optimized to draw as one large batch
        gl.glVertex3f(p.x, p.y, 0)
        gl.glEnd()
