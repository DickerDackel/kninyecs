import sys

from argparse import ArgumentParser
from collections import defaultdict
from enum import StrEnum, auto
from importlib.resources import files
from math import pi, radians
from random import choice, randint, random
from typing import NamedTuple

import pykraken as kn
import tinyecs as ecs

FPS = 60
PI2 = 2 * pi

CACHE = defaultdict(dict)
ASSETS = files('kninyecs.assets')
SCREEN = kn.Rect(0, 0, 1280, 720)

EMITS_PER_FRAME = 32

cmdline = ArgumentParser(description='Kraken/tinyecs demo')
cmdline.add_argument('-s', '--disable-scaling', action='store_true', default=False, help='Disable scaling effects')
cmdline.add_argument('-r', '--disable-rotation', action='store_true', default=False, help='Disable rotation effects')
cmdline.add_argument('-a', '--disable-alpha', action='store_true', default=False, help='Disable alpha blending')
opts = cmdline.parse_args(sys.argv[1:])


class Comp(StrEnum):
    AUTO_ANGLE = auto()
    AUTO_SCALE = auto()
    LIFETIME = auto()
    MOMENTUM = auto()
    SPRITE_ID = auto()
    TRANSFORM = auto()
    WORLD = auto()


class ZeSprite(NamedTuple):
    texture: kn.Texture
    anchor: kn.Vec2
    pivot: kn.Vec2


def slurp_textures():
    for p in ASSETS.glob('*.png'):
        texture = kn.Texture(str(p))
        center = kn.Vec2(0.5)
        CACHE['sprites'][p.stem] = ZeSprite(texture, anchor=center, pivot=center)


def _timer_to_angle(t):
    return PI2 * t.progress


def _timer_to_scale(timer):
    if timer.progress < 0.5:
        t = 2 * timer.progress
    else:
        t = 1 - (2 * timer.progress - 1)

    return 1.5 * t + 0.5


def mk_thing(sprite_id, position=None):
    auto_angle = kn.Timer(random() * 4.75 + 0.25)
    auto_scale = kn.Timer(random() * 4.75 + 0.25)
    lifetime = kn.Timer(randint(3, 10))
    auto_angle.start()
    auto_scale.start()
    lifetime.start()

    if position is None:
        pos = kn.Vec2(randint(0, int(SCREEN.w)), randint(0, int(SCREEN.h)))
    else:
        pos = kn.Vec2(*position)

    angle = _timer_to_angle(auto_angle)
    scale = _timer_to_scale(auto_scale)
    transform = kn.Transform(pos=pos, angle=angle, scale=scale)

    momentum = kn.Vec2(randint(100, 250), 0)
    momentum.rotate(radians(randint(0, 359)))

    eid = ecs.create_entity()
    ecs.add_component(eid, Comp.SPRITE_ID, CACHE['sprites'][sprite_id])
    ecs.add_component(eid, Comp.TRANSFORM, transform)
    ecs.add_component(eid, Comp.MOMENTUM, momentum)
    ecs.add_component(eid, Comp.AUTO_ANGLE, auto_angle)
    ecs.add_component(eid, Comp.AUTO_SCALE, auto_scale)
    ecs.add_component(eid, Comp.LIFETIME, lifetime)
    ecs.add_component(eid, Comp.WORLD, SCREEN)


def sys_angle(dt, eid, transform, auto_angle):
    transform.angle = _timer_to_angle(auto_angle)
    if auto_angle.done:
        auto_angle.start()


def sys_bounce(dt, eid, transform, momentum, world):
    p = transform.pos
    if p.x < world.left:
        p.x = -p.x
        momentum.x = -momentum.x
    elif p.x > world.right:
        p.x = 2 * world.right - p.x
        momentum.x = -momentum.x
    if p.y < world.top:
        p.y = -p.y
        momentum.y = -momentum.y
    elif p.y > world.bottom:
        p.y = 2 * world.bottom - p.y
        momentum.y = -momentum.y


def sys_lifetime(dt, eid, lifetime):
    if lifetime.done:
        ecs.remove_entity(eid)


def sys_momentum(dt, eid, transform, momentum):
    transform.pos += momentum * dt


def sys_render_with_fade(dt, eid, sprite, transform, lifetime, *, do_fade=True):
    if not do_fade:
        kn.renderer.draw(sprite.texture, transform, sprite.anchor, sprite.pivot)
    else:
        alpha = 1 - lifetime.progress
        bk_alpha = sprite.texture.alpha
        sprite.texture.alpha = alpha
        kn.renderer.draw(sprite.texture, transform, sprite.anchor, sprite.pivot)
        sprite.texture.alpha = bk_alpha


def sys_scale(dt, eid, transform, auto_scale):
    transform.scale = kn.Vec2(_timer_to_scale(auto_scale))
    if auto_scale.done:
        auto_scale.start()


def main():
    kn.init(debug=True)
    kn.time.set_target(FPS)
    kn.window.create('Ze Kraken/tinyecs collab demo example zingy', int(SCREEN.w), int(SCREEN.h))

    slurp_textures()

    for _ in range(50):
        mk_thing(choice(list(CACHE['sprites'])))

    while kn.window.is_open():
        dt = kn.time.get_delta()
        for e in kn.event.poll():
            if e.type == kn.KEY_DOWN:
                if e.key == kn.K_ESC:
                    raise SystemExit

        if kn.mouse.is_pressed(kn.M_LEFT):
            for _ in range(EMITS_PER_FRAME):
                mk_thing(choice(list(CACHE['sprites'])), kn.mouse.get_pos())

        kn.renderer.clear(kn.color.from_hex('#2f4f4f'))

        ecs.run_system(dt, sys_momentum, Comp.TRANSFORM, Comp.MOMENTUM)
        if not opts.disable_rotation:
            ecs.run_system(dt, sys_angle, Comp.TRANSFORM, Comp.AUTO_ANGLE)
        if not opts.disable_scaling:
            ecs.run_system(dt, sys_scale, Comp.TRANSFORM, Comp.AUTO_SCALE)
        ecs.run_system(dt, sys_bounce, Comp.TRANSFORM, Comp.MOMENTUM, Comp.WORLD)
        ecs.run_system(dt, sys_lifetime, Comp.LIFETIME)
        ecs.run_system(dt, sys_render_with_fade, Comp.SPRITE_ID, Comp.TRANSFORM, Comp.LIFETIME, do_fade=not opts.disable_alpha)

        # print(f'Number of sprites left: {len(ecs.eidx)}')

        kn.renderer.present()

    kn.quit()


if __name__ == "__main__":
    main()
