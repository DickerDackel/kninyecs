from collections import defaultdict
from enum import StrEnum, auto
from importlib.resources import files
from math import pi, radians
from os import environ
from random import choice, randint, random
from typing import NamedTuple

import pykraken as kn
import tinyecs as ecs

from pgcooldown import Cooldown, LerpThing, LTRepeat

if 'XDG_SESSION_TYPE' in environ and environ['XDG_SESSION_TYPE'] == 'wayland':
    environ['SDL_VIDEODRIVER'] = 'wayland'


FPS = 60

CACHE = defaultdict(dict)
ASSETS = files('kninyecs.assets')
SCREEN = kn.Rect(0, 0, 1280, 720)

EMITS_PER_FRAME = 5


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


def mk_thing(sprite_id, position=None):
    if choice((0, 1)):
        lt_angle = LerpThing(0, 2 * pi, random() * 4.75 + 0.25, repeat=LTRepeat.LOOP)
    else:
        lt_angle = LerpThing(2 * pi, random() * 4.75 + 0.25, 0, repeat=LTRepeat.LOOP)
    lt_scale = LerpThing(0.5, 2, random() * 4.75 + 0.25, repeat=LTRepeat.BOUNCE)
    lifetime = Cooldown(randint(3, 10))

    if position is None:
        pos = kn.Vec2(randint(0, int(SCREEN.w)), randint(0, int(SCREEN.h)))
    else:
        pos = kn.Vec2(*position)

    angle = lt_angle()
    scale = lt_scale()
    transform = kn.Transform(pos=pos, angle=angle, scale=scale)

    momentum = kn.Vec2(randint(100, 250), 0)
    momentum.rotate(radians(randint(0, 359)))

    eid = ecs.create_entity()
    ecs.add_component(eid, Comp.SPRITE_ID, CACHE['sprites'][sprite_id])
    ecs.add_component(eid, Comp.TRANSFORM, transform)
    ecs.add_component(eid, Comp.MOMENTUM, momentum)
    ecs.add_component(eid, Comp.AUTO_ANGLE, lt_angle)
    ecs.add_component(eid, Comp.AUTO_SCALE, lt_scale)
    ecs.add_component(eid, Comp.LIFETIME, lifetime)
    ecs.add_component(eid, Comp.WORLD, SCREEN)


def sys_angle(dt, eid, transform, auto_angle):
    transform.angle = auto_angle()


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
    if lifetime.cold():
        ecs.remove_entity(eid)


def sys_momentum(dt, eid, transform, momentum):
    transform.pos += momentum * dt


def sys_render(dt, eid, sprite, transform):
    kn.renderer.draw(sprite.texture, transform, sprite.anchor, sprite.pivot)


def sys_scale(dt, eid, transform, auto_scale):
    transform.scale = kn.Vec2(auto_scale())


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

        if kn.mouse.is_pressed(1):
            for _ in range(EMITS_PER_FRAME):
                mk_thing(choice(list(CACHE['sprites'])), kn.mouse.get_pos())

        kn.renderer.clear(kn.color.from_hex('#2f4f4f'))

        ecs.run_system(dt, sys_render, Comp.SPRITE_ID, Comp.TRANSFORM)
        ecs.run_system(dt, sys_momentum, Comp.TRANSFORM, Comp.MOMENTUM)
        ecs.run_system(dt, sys_angle, Comp.TRANSFORM, Comp.AUTO_ANGLE)
        ecs.run_system(dt, sys_scale, Comp.TRANSFORM, Comp.AUTO_SCALE)
        ecs.run_system(dt, sys_bounce, Comp.TRANSFORM, Comp.MOMENTUM, Comp.WORLD)
        ecs.run_system(dt, sys_lifetime, Comp.LIFETIME)

        print(f'Number of sprites left: {len(ecs.eidx)}')

        kn.renderer.present()

    kn.quit()


if __name__ == "__main__":
    main()
