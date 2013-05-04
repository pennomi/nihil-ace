from pymunk.vec2d import Vec2d
from pyglet import gl
from space import SPACE

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_CENTER = Vec2d(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)
SCREEN_BUFFER = 16

def off_screen(point):
    p = adjust_for_cam(point)
    scale = SPACE.scale
    b = SCREEN_BUFFER * scale

    if (p.x < -b or p.y < -b or
        p.x > SCREEN_WIDTH + b or
        p.y > SCREEN_HEIGHT + b):
        return True
    return False

def adjust_for_cam(point):
    return (point - SPACE.last_pos) * SPACE.scale + SCREEN_CENTER

def inverse_adjust_for_cam(point):
    return (point - SCREEN_CENTER) / SPACE.scale + SPACE.last_pos

def draw_rect(texture, points, direction=0, use_cam=True):
    # Set the texture
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    # Allow alpha blending
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    # draw
    gl.glBegin(gl.GL_QUADS)
    for i, vert in enumerate(points):
        b = (i + direction) % 4 # render according to the direction
        if use_cam:
            x, y = adjust_for_cam(vert)
        else:
            x, y = vert
        texture = b // 2, ((b + 1) // 2) % 2
        gl.glTexCoord2f(*texture)
        gl.glVertex3f(x, y, 0)
    gl.glEnd()

def draw_large_point(texture, p, r):
    draw_rect(texture, [Vec2d(p.x - r, p.y - r),
                        Vec2d(p.x + r, p.y - r),
                        Vec2d(p.x + r, p.y + r),
                        Vec2d(p.x - r, p.y + r),])
