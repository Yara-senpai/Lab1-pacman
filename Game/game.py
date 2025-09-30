from Game.map import Map
from typing import List
from Agents.ghost import Ghost
from Agents.pacman import Pacman
import pyglet
import math

class Game:
    def __init__(self, map: Map, ghosts: List[Ghost], pacman: Pacman):
        self.is_updating = False
        self.difficulty = 5

        self.map: Map = map
        self.pacman = pacman
        self.ghosts = ghosts

        self.show_pacman_costs = False

        self.start_game()

    def reset_positions(self):
        ghost_room_positions = self.map.get_ghost_room_positions()
        for i, ghost in enumerate(self.ghosts):
            ghost.x, ghost.y = ghost_room_positions[i]

        self.pacman.x, self.pacman.y = self.map.get_random_empty_space()

        self.map.ghosts_positions = [(ghost.x, ghost.y) for ghost in self.ghosts]
        self.map.pacman_position = (self.pacman.x, self.pacman.y)
        self.map.pacman_direction = getattr(self.pacman, "current_direction", 0)

    def start_game(self):
        self.reset_positions()

        self.frame = 0

        self.is_updating = True

    def restart_game(self):
        self.is_updating = False
        self.map.restore_map()
        self.pacman.restore()
        for ghost in self.ghosts:
            ghost.difficulty = self.difficulty
            ghost.restore()
        self.start_game()

    def next_level(self):
        self.difficulty += 1
        self.restart_game()

    def get_free_neighbours(self, x, y):
        neighbours = self.map.get_free_neighbours(x, y)

        for ghost in self.ghosts:
            if (ghost.x, ghost.y) in neighbours:
                neighbours.remove((ghost.x, ghost.y))

        neighbours.remove((self.pacman.x, self.pacman.y))

    def on_draw(self, tile_size):
        self.map.on_draw(tile_size)
        for ghost in self.ghosts:
            ghost.on_draw(tile_size)
        self.pacman.on_draw(tile_size)

        if self.show_pacman_costs:
            for x, row in enumerate(self.map.map):
                for y, tile in enumerate(row):
                    if tile == 0:
                        pacman_cost = round(self.map.get_pacman_cost((x, y)), 2)
                        pyglet.text.Label(f"{pacman_cost}",
                                        font_name='Arial',
                                        font_size=8,
                                        x=x * tile_size, y=y * tile_size).draw()
            if self.pacman.path is not None:
                for p in self.pacman.path:
                    x, y = p
                    pyglet.shapes.Circle(x * tile_size + tile_size // 2, y * tile_size + tile_size // 2, 5, color=(255, 0, 0)).draw()

        if self.pacman.current_target is not None:
            x, y = self.pacman.current_target
            pyglet.shapes.Circle(x * tile_size + tile_size // 2, y * tile_size + tile_size // 2, 5, color=(0, 255, 0)).draw()

        score = pyglet.text.Label(f"Score: {self.pacman.score}",
                                  font_name='Arial',
                                  font_size=16,
                                  x=0, y=self.map.size * tile_size,
                                  anchor_x='left', anchor_y='top')

        lives = pyglet.text.Label(f"Lives: {self.pacman.lives}",
                                  font_name='Arial',
                                  font_size=16,
                                  x=self.map.size * tile_size, y=self.map.size * tile_size,
                                  anchor_x='right', anchor_y='top')

        pacman_state_type = pyglet.text.Label(f"Pacman state: {self.pacman.state.__class__.__name__}",
                                    font_name='Arial',
                                    font_size=10,
                                    x=0, y=self.map.size * tile_size - 18,
                                    anchor_x='left', anchor_y='top')

        difficulty = pyglet.text.Label(f"Difficulty: {self.difficulty}",
                                    font_name='Arial',
                                    font_size=10,
                                    x=0, y=self.map.size * tile_size - 36,
                                    anchor_x='left', anchor_y='top')

        for ghost in self.ghosts:
            ghost_state = pyglet.text.Label(f"Ghost {ghost.n} state: {ghost.state.__class__.__name__}",
                                    font_name='Arial',
                                    font_size=10,
                                    x=self.map.size * tile_size, y=self.map.size * tile_size - 18 * (ghost.n + 1),
                                    anchor_x='right', anchor_y='top')
            ghost_state.draw()


        score.draw()
        lives.draw()
        pacman_state_type.draw()
        difficulty.draw()

    def update(self, dt):
        if not self.is_updating:
            return

        if self.frame % (60 // ((self.difficulty * 2)+5)) == 0:
            for i, ghost in enumerate(self.ghosts):
                ghost.move(self.map)
                self.map.ghosts_positions[i] = (ghost.x, ghost.y)
                if ghost.did_catch_pacman:
                    self.pacman.die()
                    ghost.did_catch_pacman = False
                    return

        if self.frame % (60 // 20) == 0:
            self.pacman.move(self.map)
            self.map.pacman_position = (self.pacman.x, self.pacman.y)
            self.map.pacman_direction = getattr(self.pacman, "current_direction", 0)

            if self.map.is_apple_map_empty():
                self.next_level()
                return
            if self.pacman.did_die:
                self.pacman.lives -= 1
                if self.pacman.lives == 0:
                    self.restart_game()
                else:
                    self.pacman.restore_without_lives()
                    for ghost in self.ghosts:
                        ghost.restore()
                    self.reset_positions()


