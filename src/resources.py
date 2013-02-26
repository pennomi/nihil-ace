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
    ttl = 3600 # 1 minute

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
        SPACE.safe_add(self._body, self._shape)
        SPACE.register_resource(self)

    def draw(self):
        p = adjust_for_cam(self._body.position)

        gl.glEnable(pyglet.gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, RESOURCE_IMAGE.id)
        gl.glEnable(gl.GL_POINT_SPRITE)
        gl.glTexEnvi(gl.GL_POINT_SPRITE, gl.GL_COORD_REPLACE, gl.GL_TRUE)
        gl.glPointSize(8 * SPACE.camera_lock.scale)

        gl.glBegin(gl.GL_POINTS)
        # TODO: more optimized to draw as one large batch
        gl.glVertex3f(p.x, p.y, 0)
        gl.glEnd();
