import os
import random
import pyglet

# УВАГА: опції треба виставляти ДО створення вікна і ДО імпорту pyglet.gl
pyglet.options['gl_profile'] = 'compatibility'   # щоб уникнути core-profile сюрпризів
# pyglet.options['debug_gl'] = True              # за потреби: детальні GL-логи

from Game.game import Game
from Game.map import Map
from Agents.ghost import Ghost
from Agents.pacman import Pacman


def texture_set_mag_filter_nearest(texture):
    # Викликати ТІЛЬКИ після створення вікна (коли є GL-контекст)
    pyglet.gl.glBindTexture(texture.target, texture.id)
    pyglet.gl.glTexParameteri(texture.target, pyglet.gl.GL_TEXTURE_MAG_FILTER, pyglet.gl.GL_NEAREST)
    pyglet.gl.glBindTexture(texture.target, 0)


def start_game():
    random.seed()

    TILE_SIZE = 22
    MAP_SIZE = 20

    # Коректно виставляємо робочу папку до каталогу зі скриптом
    base_dir = os.path.abspath(os.path.dirname(__file__))
    assets_dir = os.path.join(base_dir, "sprites")

    # 1) СПЕРШУ — СТВОРЮЄМО ВІКНО (щоб уже був GL-контекст)
    #   Розмір коробки поки тимчасовий; після створення об'єктів ми підженемо його, якщо потрібно.
    temp_width = MAP_SIZE * TILE_SIZE
    temp_height = MAP_SIZE * TILE_SIZE
    window = pyglet.window.Window(width=temp_width, height=temp_height, vsync=True, caption="Pacman")
    pyglet.gl.glClearColor(0, 0, 0, 1)

    # 2) ТЕПЕР — ЗАВАНТАЖУЄМО СПРАЙТИ/ТЕКСТУРИ (GL-контекст уже є)
    wall_image = pyglet.image.load(os.path.join(assets_dir, 'wall.png'))
    texture_set_mag_filter_nearest(wall_image.get_texture())

    small_apple_image = pyglet.image.load(os.path.join(assets_dir, 'small_apple.png'))
    texture_set_mag_filter_nearest(small_apple_image.get_texture())

    big_apple_image = pyglet.image.load(os.path.join(assets_dir, 'big_apple.png'))
    texture_set_mag_filter_nearest(big_apple_image.get_texture())

    ghost_sheet = pyglet.image.load(os.path.join(assets_dir, 'ghost_w.png'))
    ghost_images = pyglet.image.ImageGrid(ghost_sheet, 1, 4)
    for image in ghost_images:
        texture_set_mag_filter_nearest(image.get_texture())

    pacman_sheet = pyglet.image.load(os.path.join(assets_dir, 'pacman.png'))
    pacman_images = pyglet.image.ImageGrid(pacman_sheet, 1, 4)
    for image in pacman_images:
        texture_set_mag_filter_nearest(image.get_texture())

    # 3) СТВОРЮЄМО КАРТУ/ГРУ
    game_map = Map(wall_image, small_apple_image, big_apple_image, MAP_SIZE, TILE_SIZE)

    NUMBER_OF_GHOSTS = 4
    GHOST_COLORS = [
        (255, 0, 0),
        (255, 183, 255),
        (0, 255, 255),
        (255, 3, 81),
        (255, 54, 81),
        (12, 183, 81)
    ]

    ghosts = []
    for i in range(NUMBER_OF_GHOSTS):
        ghost_sprites = []
        for j in range(4):
            ghost_image = ghost_images[j]
            ghost_sprite = pyglet.sprite.Sprite(img=ghost_image)
            ghost_sprite.color = GHOST_COLORS[i]
            ghost_sprite.width = TILE_SIZE
            ghost_sprite.height = TILE_SIZE
            ghost_sprites.append(ghost_sprite)
        ghosts.append(Ghost(ghost_sprites, i))

    pacman_sprites = []
    for i in range(4):
        pacman_image = pacman_images[i]
        pacman_sprite = pyglet.sprite.Sprite(img=pacman_image)
        pacman_sprite.width = TILE_SIZE
        pacman_sprite.height = TILE_SIZE
        pacman_sprites.append(pacman_sprite)

    LIVES = 5
    pacman = Pacman(pacman_sprites, LIVES)

    game = Game(game_map, ghosts, pacman)

    # 4) ПІДГОНЯЄМО РОЗМІР ВІКНА ПІД РЕАЛЬНУ КАРТУ (якщо Map має точний size)
    win_w = game.map.size * TILE_SIZE
    win_h = game.map.size * TILE_SIZE
    if (win_w, win_h) != (temp_width, temp_height):
        window.set_size(win_w, win_h)

    # Entity movement seed
    random.seed()

    @window.event
    def on_draw():
        window.clear()
        game.on_draw(TILE_SIZE)

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            window.close()
        elif symbol == pyglet.window.key.R:
            game.restart_game()
        elif symbol == pyglet.window.key.SPACE:
            game.is_updating = not game.is_updating
        elif symbol == pyglet.window.key.P:
            game.show_pacman_costs = not game.show_pacman_costs

    def update(dt):
        if not game.is_updating:
            return
        game.frame += 1
        game.update(dt)

    pyglet.clock.schedule_interval(update, 1/60.0)
    pyglet.app.run()


if __name__ == "__main__":
    start_game()
