import pymunk
import pyglet
import random
from pymunk.vec2d import Vec2d
from materials import COLLISION_TYPES
from space import SPACE
from weakref import ref
import settings
from pyglet import gl
from renderer import adjust_for_cam, off_screen

if settings.SOUND:
    EXPLOSION_SFX = [
        pyglet.resource.media('sfx/explode1.wav', streaming=False),
        pyglet.resource.media('sfx/explode2.wav', streaming=False),
        pyglet.resource.media('sfx/explode3.flac', streaming=False),
    ]

BLOCK_SIZE = 16 # TODO: this is duplicated

EXPLOSION_ANIM = pyglet.image.load('images/explosion2.png').mipmapped_texture
ANIM_ROWS = 4.0
ANIM_COLUMNS = 8.0
ANIM_FRAMES = 3 * 8 # last row is empty

FRAME_POSITIONS = []
for i in xrange(ANIM_FRAMES):
    FRAME_POSITIONS.append(((i % ANIM_COLUMNS / ANIM_COLUMNS), (i // ANIM_COLUMNS) / ANIM_ROWS))


class Explosion:
    ticks = 20

    # sprites
    image = 'images/explosion2.png'
    image_anchor = Vec2d(32, 32)

    def __init__(self, point, radius, velocity=Vec2d(0, 0), damage=0):
        self.radius = radius
        self.damage = damage

        inertia = pymunk.moment_for_circle(pymunk.inf, 0, radius)
        self._body = pymunk.Body(pymunk.inf, inertia)
        self._body.position = point
        self._body.velocity = velocity
        self._shape = pymunk.Circle(self._body, radius)
        self._shape.collision_type = COLLISION_TYPES['explosion']
        self._shape._get_explosion = ref(self)
        SPACE.safe_add(self._body, self._shape)
        SPACE.register_explosion(self)

        # play SFX
        if settings.SOUND:
            sound = random.choice(EXPLOSION_SFX)
            # TODO: 3D sound
            #volume = (500 - (SPACE.camera_lock._body.position - self._body.position).length) / 500
            #if volume > 0:
            #    print volume
            #    sound.volume = random.choice([1.0, .5, .25])
            sound.play()

    def upkeep(self):
        self.ticks -= 1
        if self.ticks <= 0:
            SPACE.explosions.remove(self)
            SPACE.safe_remove(self._body, self._shape)

    def draw(self):
        # TODO: Let's use particles. Way more fun.

        p = adjust_for_cam(self._body.position)

        if off_screen(self._body.position):
            return

        gl.glEnable(gl.GL_TEXTURE_2D) # enables texturing, without it everything is white
        gl.glBindTexture(gl.GL_TEXTURE_2D, EXPLOSION_ANIM.id)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA);

        # TODO: more optimized to draw as one large batch
        gl.glBegin(gl.GL_QUADS)

        r = (self.radius + BLOCK_SIZE) * SPACE.camera_lock.scale
        for i, vert in enumerate([Vec2d(p.x - r, p.y - r),
                                  Vec2d(p.x + r, p.y - r),
                                  Vec2d(p.x + r, p.y + r),
                                  Vec2d(p.x - r, p.y + r),]):

            # TODO: This is really ugly, and a lot of shared code with the
            #       blocks. Let's write a draw_rect function to handle this
            #       with an optional animation option.

            x = (i // 2)
            if x == 0:
                x = FRAME_POSITIONS[int((20 - self.ticks) / 20. * ANIM_FRAMES)][0]
            else:
                x = FRAME_POSITIONS[int((20 - self.ticks) / 20. * ANIM_FRAMES)][0] + 1 / ANIM_COLUMNS
            y = ((i + 1) // 2) % 2
            if y == 0:
                y = FRAME_POSITIONS[int((20 - self.ticks) / 20. * ANIM_FRAMES)][1]
            else:
                y = FRAME_POSITIONS[int((20 - self.ticks) / 20. * ANIM_FRAMES)][1] + 1 / ANIM_ROWS

            gl.glTexCoord2f(x, y)
            gl.glVertex3f(vert.x, vert.y, 0)

        gl.glEnd()
