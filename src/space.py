"""Subclass of pymunk.Space so that we can keep track of additional block
updates.
"""
import pymunk


class Space(pymunk.Space):
    blocks = []
    controller_blocks = []
    controllable_blocks = []
    explosions = []
    projectiles = set()
    resources = set()
    camera_lock = None
    last_pos = pymunk.vec2d.Vec2d(0, 0)
    scale = 1
    target_scale = 1

    def __init__(self):
        super(Space, self).__init__()
        self.damping = 0.8
        self.iterations = 100

    def register_block(self, block):
        self.blocks.append(block)
        if hasattr(block, 'ai'):
            self.controller_blocks.append(block)
        if hasattr(block, 'key'):
            self.controllable_blocks.append(block)

    def register_explosion(self, exp):
        self.explosions.append(exp)
SPACE = Space()
