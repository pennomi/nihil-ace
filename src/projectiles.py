import math
import pyglet
import pymunk
import random
import settings
from pymunk.vec2d import Vec2d
from materials import COLLISION_TYPES
from space import SPACE
from weakref import ref
from pyglet import gl
from renderer import adjust_for_cam

# TODO: duplicated
BLOCK_SIZE = 16

if settings.SOUND:
    BLASTER_SFX = [
        pyglet.resource.media('sfx/laser1.wav', streaming=False),
        #pyglet.resource.media('sfx/laser2.wav', streaming=False),
        #pyglet.resource.media('sfx/laser3.wav', streaming=False),
    ]

BLASTER_IMAGE = pyglet.image.load('images/blast.png').mipmapped_texture

class Projectile:
    ttl = 100

    def __init__(self, source=None, damage=1):
        # physics
        r = 3
        mass = 0.01
        inertia = pymunk.moment_for_circle(mass, 0, r)
        self._body = pymunk.Body(mass, inertia)
        p = Vec2d(BLOCK_SIZE, 0)
        p.angle = source._body.angle + math.pi / 2 + source.direction * math.pi / 2
        self._body.position = source._body.position + p
        self._body.velocity = source._body.velocity + p * BLOCK_SIZE * 2
        self._shape = pymunk.Circle(self._body, r)
        self._shape.elasticity = 1.0
        self._shape.friction= 0.0
        self._shape.collision_type = COLLISION_TYPES["blaster"]
        self._shape._get_projectile = ref(self)
        SPACE.safe_add(self._body, self._shape)
        SPACE.register_projectile(self)
        # SFX
        if settings.SOUND:
            random.choice(BLASTER_SFX).play()

    def upkeep(self):
        self.ttl -= 1
        if self.ttl < 1:
            SPACE.safe_remove(self._shape, self._body)
            SPACE.remove_projectile(self)

    def draw(self):
        p = adjust_for_cam(self._body.position)

        gl.glEnable(pyglet.gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, BLASTER_IMAGE.id)
        gl.glEnable(gl.GL_POINT_SPRITE)
        gl.glTexEnvi(gl.GL_POINT_SPRITE, gl.GL_COORD_REPLACE, gl.GL_TRUE)
        gl.glPointSize(4 * SPACE.scale)

        gl.glBegin(gl.GL_POINTS)
        # TODO: more optimized to draw as one large batch
        gl.glVertex3f(p.x, p.y, 0)
        gl.glEnd();
