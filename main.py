# Set up pyglet debug options first
import sys
import pyglet
if 'nogldebug' in sys.argv:
    pyglet.options['debug_gl'] = False

# The rest of the imports
import json
from pyglet.window import key
from src.space import SPACE
from src.blocks import (Block, ShieldBlock, EngineBlock, ReactorBlock,
                        CockpitBlock, BlasterBlock, ArmorBlock, ScannerBlock,
                        TractorBlock, AngleLeftBlock, AngleRightBlock,
                        FinLeftBlock, FinRightBlock, ConstructionBlock,
                        BLOCK_SIZE)
from src.materials import COLLISION_TYPES
from src.renderer import inverse_adjust_for_cam
from pymunk.vec2d import Vec2d
import random
from src import settings
from weakref import ref

##############################################################################
# NOTES:
#   * Art assets I am using:
#       * Blocks by Buch:
#           http://opengameart.org/content/spaceship-construction-blocks
#       * Explosion by qubodup:
#           http://opengameart.org/content/bomb-explosion-animation
#       * Music by ERH:
#           http://opengameart.org/content/bluebeat-01-loop-cyberpunk-lab-music
#       * Explode SFX by Michel Baradari:
#           http://opengameart.org/content/2-high-quality-explosions
#           http://opengameart.org/content/rumbleexplosion
#       * Laser SFX by dklon:
#           http://opengameart.org/content/laser-fire
#
##############################################################################

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700

BLOCK_MAP = {'b': Block,
             'a': ArmorBlock,
             's': ShieldBlock,
             'e': EngineBlock,
             'r': ReactorBlock,
             'c': CockpitBlock,
             'l': BlasterBlock,
             'S': ScannerBlock,
             't': TractorBlock,
             'k': AngleLeftBlock,
             'K': AngleRightBlock,
             'f': FinLeftBlock,
             'F': FinRightBlock,
}


def spawn_ship(filename, spawn_location, player_controlled=False):
    """Loads a file with a json definition of a ship."""
    with open('ships/' + filename, 'r') as f:
        lines = f.read()

    data = json.loads(lines)
    whole_ship = []
    controllers = []
    for i, line in enumerate(data['blocks']):
        whole_ship.append([])
        for j, block in enumerate(line):
            dimensions = Vec2d(len(data['blocks']) - 1, len(line) - 1)
            location = (spawn_location +
                        Vec2d(dimensions.x / 2 - j,
                              dimensions.y / 2 - i) * BLOCK_SIZE)
            new = None
            # spawn
            if block != ' ':
                new = BLOCK_MAP[block](location)
                new.direction = int(data['rotation'][i][j])
                # Add in the key bindings and camera lock
                if BLOCK_MAP[block] == CockpitBlock:
                    controllers.append(new)
                    new.temp_slaves = data['keybindings']
                    if player_controlled:
                        SPACE.camera_lock = ref(new)
                        new.ai = False
            whole_ship[i].append(new)
            # weld
            if new and i and whole_ship[i-1][j]:
                new.weld_to(whole_ship[i-1][j])
            if new and j and whole_ship[i][j-1]:
                new.weld_to(whole_ship[i][j-1])

    for b in controllers:
        for binding in b.temp_slaves:
            x, y = binding['position']
            target = whole_ship[y][x]
            target.key = getattr(key, binding['key'])
            target.binding_type = binding['type']
            b.slave_blocks.add(target)
        del b.temp_slaves
        # TODO: pre-activate the 'inverted' bindings
        # TODO: an energy priority system would be quite shiny
        # TODO: in-game ship editor


BACKGROUND = pyglet.image.load('images/blueviolet_nebula.png')
BACKGROUND_SPRITE = pyglet.sprite.Sprite(BACKGROUND)
BACKGROUND_SPRITE.opacity = 128


def draw_background():
    w = BACKGROUND.width + 1  # +1 so they don't overlap
    # 8.0 is the parallax factor
    offset = -((SPACE.last_pos / 8.0) % w)
    for i in (0, 1):
        for j in (0, 1):
            BACKGROUND_SPRITE.x, BACKGROUND_SPRITE.y = (offset +
                                                        Vec2d(i, j) * w)
            BACKGROUND_SPRITE.draw()


CONSTRUCTION_BLOCK = ConstructionBlock()


def draw_construction_interface():
    # snap to nearest grid position
    mouse = inverse_adjust_for_cam(  # TODO: this offset is wrong when rotated
        MOUSE + Vec2d(BLOCK_SIZE / 2, BLOCK_SIZE / 2) * SPACE.scale)
    if not SPACE.camera_lock():
        return
    cam = SPACE.camera_lock()._body.position
    a = SPACE.camera_lock()._body.angle
    _ = (mouse - cam)
    _.angle -= a
    _ %= Vec2d(BLOCK_SIZE, BLOCK_SIZE)
    _.angle += a
    mouse -= _
    # create a collision object
    CONSTRUCTION_BLOCK._body.position = mouse
    CONSTRUCTION_BLOCK._body.angle = SPACE.camera_lock()._body.angle
    # check if stuff is near it
    valid_welds = []
    for block in SPACE.camera_lock().construction:
        dist = round((block._body.position - mouse).length)
        if dist == 0:
            valid_welds = []
            break
        elif dist == BLOCK_SIZE:
            valid_welds.append(block)
    CONSTRUCTION_BLOCK.valid_welds = valid_welds
    # draw it
    CONSTRUCTION_BLOCK.draw()


def nocollide(space, arbiter):
    return False


def blaster_collision_handler(space, arbiter):
    for s in arbiter.shapes:
        if hasattr(s, '_get_block'):
            s._get_block().take_damage(1)
        else:
            p = s._get_projectile()
            p.ttl = 0
    return False


def explosion_collision_handler(space, arbiter):
    explosion = None
    for s in arbiter.shapes:
        if s.collision_type == COLLISION_TYPES['explosion']:
            explosion = s
            e = explosion._get_explosion()
    for s in arbiter.shapes:
        if hasattr(s, '_get_block'):
            s._get_block().take_damage(e.damage)
        direction = explosion.body.position - s.body.position
        if direction.length:
            direction.length = (explosion._get_explosion().radius -
                                                        direction.length) * 4
            s.body.apply_impulse(direction)
    return False


def tractor_collision_handler(space, arbiter):
    tractor_target = None
    for s in arbiter.shapes:
        if s.collision_type == COLLISION_TYPES['tractor']:
            tractor_target = s.body
    for s in arbiter.shapes:
        if (s.collision_type == COLLISION_TYPES['resource']
                and not (hasattr(s, "target") and s.target())):
            s.target = ref(tractor_target)
    return True

window = pyglet.window.Window(width=SCREEN_WIDTH, height=SCREEN_HEIGHT,
                              vsync=False)

MOUSE = Vec2d(0, 0)


@window.event
def on_mouse_motion(x, y, dx, dy):
    MOUSE.x, MOUSE.y = x, y


@window.event
def on_mouse_scroll(x, y, scroll_x, scroll_y):
    SPACE.target_scale += scroll_y * .05
    SPACE.target_scale = min(max(SPACE.target_scale, 0.25), 5)


@window.event
def on_mouse_press(x, y, button, modifiers):
    try:
        if not SPACE.camera_lock():
            return
        if not CONSTRUCTION_BLOCK or not CONSTRUCTION_BLOCK.valid_welds:
            return
        # TODO: any block type
        new_block = Block(CONSTRUCTION_BLOCK._body.position)
        new_block._body.angle = CONSTRUCTION_BLOCK.valid_welds[0]._body.angle
        for block in CONSTRUCTION_BLOCK.valid_welds:
            new_block.weld_to(block)
        # TODO: link the cockpit as the master block
    except Exception as e:
        print e


@window.event
def on_key_press(symbol, modifiers):
    if SPACE.camera_lock():
        SPACE.camera_lock().on_key_press(symbol)


@window.event
def on_key_release(symbol, modifiers):
    if SPACE.camera_lock():
        SPACE.camera_lock().on_key_release(symbol)

FPS_DISPLAY = pyglet.clock.ClockDisplay()


@window.event
def on_draw():
    window.clear()
    draw_background()
    [b.draw() for b in SPACE.blocks]
    [p.draw() for p in SPACE._projectiles]
    [r.draw() for r in SPACE._resources]
    [e.draw() for e in SPACE.explosions]
    draw_construction_interface()
    FPS_DISPLAY.draw()


def update(dt):
    [b._upkeep() for b in SPACE.controllable_blocks]
    # update scale smoothly
    SPACE.scale += (SPACE.target_scale - SPACE.scale) * .25
    # upkeep on various entities
    for p in SPACE._projectiles.copy():
        p.upkeep()
    for r in SPACE._resources.copy():
        r.upkeep()
    for e in SPACE.explosions:
        e.upkeep()
    # Run the simulation
    SPACE.step(dt)
    # Update the camera's last valid position
    if SPACE.camera_lock():
        SPACE.last_pos = Vec2d(SPACE.camera_lock()._body.position)
pyglet.clock.schedule_interval(update, 1.0 / 60.0)


def tick_ai(dt):
    [b.enemy_ai_update() for b in SPACE.controller_blocks if b.ai]
pyglet.clock.schedule_interval(tick_ai, 1.0 / 60.0)


def tick_power(dt):
    reactors = [b for b in SPACE.blocks if isinstance(b, ReactorBlock)]
    for r in reactors:
        r.power_used = 0
    random.shuffle(SPACE.controllable_blocks)
    [b._power_upkeep() for b in SPACE.controllable_blocks]
pyglet.clock.schedule_interval(tick_power, 1.0 / 5.0)


# INITIALIZE SPACE
def collide(t1, t2, func):
    SPACE.add_collision_handler(COLLISION_TYPES[t1], COLLISION_TYPES[t2],
                                begin=func)

collide('shield', 'ship', nocollide)
collide('explosion', 'explosion', nocollide)
collide('blaster', 'explosion', nocollide)
collide('blaster', 'blaster', nocollide)
collide('shield', 'explosion', nocollide)
collide('ship', 'blaster', blaster_collision_handler)
collide('ship', 'explosion', explosion_collision_handler)
collide('tractor', 'resource', tractor_collision_handler)


def main():
    if 'nosound' in sys.argv:
        settings.SOUND = False

    # MUSIC
    if settings.SOUND:
        player = pyglet.media.Player()
        player.queue(pyglet.resource.media('music/ERH_BlueBeat_01.ogg'))
        player.eos_action = pyglet.media.Player.EOS_LOOP
        player.play()

    # CREATE THE SHIP
    spawn_ship('fighter.ship', Vec2d(0, 0), player_controlled=True)
    for i in range(5):
        spawn = 3000
        #spawn_ship('frigate.ship', Vec2d(random.randint(-spawn, spawn),
        #                                 random.randint(-spawn, spawn)))
        #spawn_ship('trident.ship', Vec2d(random.randint(-spawn, spawn),
        #                                random.randint(-spawn, spawn)))
        #spawn_ship('lander.ship', Vec2d(random.randint(-spawn, spawn),
        #                                random.randint(-spawn, spawn)))
        spawn_ship('mini.ship', Vec2d(random.randint(-spawn, spawn),
                                        random.randint(-spawn, spawn)))
    for i in range(5):
        spawn = 3000
        spawn_ship('asteroid.ship', Vec2d(random.randint(-spawn, spawn),
                                          random.randint(-spawn, spawn)))

    # RUN REACTOR
    pyglet.app.run()

if __name__ == '__main__':
    if 'profile' in sys.argv:
        import cProfile, pstats
        cProfile.run('main()', 'nihil_ace.prof')
        p = pstats.Stats('nihil_ace.prof')
        p.strip_dirs().sort_stats('time').print_stats(20)
    else:
        main()
