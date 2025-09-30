import numpy as np
import pyglet
from Game.map_generator import MapGenerator
import random 

class MapImages:
    def __init__(self, wall_image, small_apple_image, big_apple_image):
        self.wall_image = wall_image
        self.small_apple_image = small_apple_image
        self.big_apple_image = big_apple_image

class Map:
    def __init__(self, wall_image, small_apple_image, big_apple_image, size, tile_size):
        self.map_images = MapImages(wall_image, small_apple_image, big_apple_image)

        self.ghosts_positions = []
        self.pacman_position = 0

        self.map = np.zeros((size, size))
        self.apple_map = np.zeros((size, size))

        self.tile_size = tile_size
        self.size = size
        self.generate()

        self.map_copy = self.map.copy()
        self.apple_map_copy = self.apple_map.copy()


        self.init_sprites(tile_size, size)

    def _is_fully_connected(self) -> bool:
        """Чи вся множина нулів (проходів) у одній компоненті?"""
        import collections
        h, w = self.map.shape
        # знайдемо першу прохідну клітинку
        start = None
        for i in range(h):
            for j in range(w):
                if self.map[i, j] == 0:
                    start = (i, j)
                    break
            if start:
                break
        if start is None:
            return False  # немає жодної прохідної клітинки

        seen = set([start])
        q = collections.deque([start])
        while q:
            x, y = q.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < h and 0 <= ny < w and self.map[nx, ny] == 0 and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))

        # перевіряємо, що всі нулі досяжні
        total_open = int((self.map == 0).sum())
        return len(seen) == total_open

    def init_sprites(self, tile_size, size):
        self.wall_sprites_batch = pyglet.graphics.Batch()
        self.small_apple_sprites_batch = pyglet.graphics.Batch()
        self.big_apple_sprites_batch = pyglet.graphics.Batch()
        
        wall_image, small_apple_image, big_apple_image = self.map_images.wall_image, self.map_images.small_apple_image, self.map_images.big_apple_image

        self.wall_sprites = []
        self.small_apple_sprites = []
        self.big_apple_sprites = []
        self.apple_sprites = [[None] * size for _ in range(size)]

        for x, row in enumerate(self.map):
            for y, tile in enumerate(row):
                if tile == 1:
                    wall_sprite = pyglet.sprite.Sprite(img=wall_image, batch=self.wall_sprites_batch)
                    wall_sprite.x = x * tile_size
                    wall_sprite.y = y * tile_size
                    wall_sprite.width, wall_sprite.height = tile_size, tile_size
                    self.wall_sprites.append(wall_sprite)

        for x, row in enumerate(self.apple_map):
            for y, tile in enumerate(row):
                if tile == 1:
                    apple_sprite = pyglet.sprite.Sprite(img=small_apple_image, batch=self.small_apple_sprites_batch)
                    apple_sprite.x = x * tile_size
                    apple_sprite.y = y * tile_size
                    apple_sprite.width, apple_sprite.height = tile_size, tile_size
                    self.apple_sprites[x][y] = apple_sprite
                elif tile == 2:
                    apple_sprite = pyglet.sprite.Sprite(img=big_apple_image, batch=self.big_apple_sprites_batch)
                    apple_sprite.x = x * tile_size
                    apple_sprite.y = y * tile_size
                    apple_sprite.width, apple_sprite.height = tile_size, tile_size
                    self.apple_sprites[x][y] = apple_sprite


    def restore_map(self):
        self.ghosts_positions = []
        self.pacman_position = None

        self.map = self.map_copy.copy()
        self.apple_map = self.apple_map_copy.copy()

        self.init_sprites(self.tile_size, self.size)

    def get_ghost_room_positions(self):
        center = self.size // 2 - 1
        offsets = [(0,0), (1,0), (0,1), (1,1)]
        return [(center + offset[0], center + offset[1]) for offset in offsets]

    def get_random_empty_space(self):
        x = random.randint(0, self.size - 1)
        y = random.randint(0, self.size - 1)
        while self.map[x, y] == 1 or (x, y) in self.ghosts_positions or (x, y) == self.pacman_position:
            x = random.randint(0, self.size - 1)
            y = random.randint(0, self.size - 1)
        return x, y

    def try_eat_apple(self, x, y):
        apple = self.apple_map[x, y]
        self.apple_map[x, y] = 0
        if self.apple_sprites[x][y]:
            self.apple_sprites[x][y].delete()
            self.apple_sprites[x][y] = None
        return apple

    def generate(self):
        # кілька спроб з різними випадковими станами
        MAX_TRIES = 8
        for attempt in range(MAX_TRIES):
            self.map = np.zeros((self.size, self.size))
            room_positions = self.get_ghost_room_positions()

            gen = MapGenerator(self.size)
            # випадковий сид для різноманітності між спробами
            random.seed()  # або random.seed(time.time_ns())
            candidate = gen.generate_map(room_positions)

            self.map = candidate
            self.apple_map = np.abs(np.ones((self.size, self.size)) - self.map)

            dead_ends = self.find_dead_ends()
            if dead_ends:
                big_apple_positions = random.choices(dead_ends, k=max(1, len(dead_ends) // 4))
                for x, y in big_apple_positions:
                    self.apple_map[x, y] = 2

            # ПРОВІРКА З’ЄДНАНОСТІ
            if self._is_fully_connected():
                break
        else:
            # якщо всі спроби провалились — останній варіант залишаємо як є
            print("[Map] Warning: failed to build fully connected map after", MAX_TRIES, "tries")

    def find_dead_ends(self):
        dead_ends = []
        for x in range(self.size):
            for y in range(self.size):
                if self.map[x, y] == 0:
                    free_neighbours = self.get_free_neighbours(x, y)
                    if len(free_neighbours) == 1:
                        dead_ends.append((x, y))

        return dead_ends

    def get_free_neighbours(self, x, y):
        neighbours = []
        if x > 0 and self.map[x-1, y] == 0:
            neighbours.append((x-1, y))
        if x < self.size - 1 and self.map[x+1, y] == 0:
            neighbours.append((x+1, y))
        if y > 0 and self.map[x, y-1] == 0:
            neighbours.append((x, y-1))
        if y < self.size - 1 and self.map[x, y+1] == 0:
            neighbours.append((x, y+1))

        for ghost_x, ghost_y in self.ghosts_positions:
            if (ghost_x, ghost_y) in neighbours:
                neighbours.remove((ghost_x, ghost_y))

        if self.pacman_position in neighbours:
            neighbours.remove(self.pacman_position)
        
        return neighbours
    
    def get_free_neighbours_for_ghost(self, x, y):
        neighbours = []
        if x > 0 and self.map[x-1, y] == 0:
            neighbours.append((x-1, y))
        if x < self.size - 1 and self.map[x+1, y] == 0:
            neighbours.append((x+1, y))
        if y > 0 and self.map[x, y-1] == 0:
            neighbours.append((x, y-1))
        if y < self.size - 1 and self.map[x, y+1] == 0:
            neighbours.append((x, y+1))
        
        return neighbours
    
    def on_draw(self, tile_size):
        self.wall_sprites_batch.draw()
        self.small_apple_sprites_batch.draw()
        self.big_apple_sprites_batch.draw()

    def get_bfs_apples(self, position):
        depth = 5
        queue = [position]
        visited = np.zeros((self.size, self.size))
        visited[position] = 1
        apples = []
        for i in range(depth):
            new_queue = []
            for current in queue:
                for neighbour in self.get_free_neighbours(*current):
                    if visited[neighbour] == 0:
                        visited[neighbour] = 1
                        new_queue.append(neighbour)
                        if self.apple_map[neighbour] == 1:
                            apples.append(neighbour)
                        elif self.apple_map[neighbour] == 2:
                            apples.append(neighbour)
            queue = new_queue
        
        return apples

    def get_ghosts_nearby(self, position, radius):
        ghosts = []
        for ghost_position in self.ghosts_positions:
            if abs(ghost_position[0] - position[0]) + abs(ghost_position[1] - position[1]) <= radius:
                ghosts.append(ghost_position)
        return ghosts

    def get_best_apple(self, position, cost_function):
        los_apples = self.get_bfs_apples(position)
        if len(los_apples) > 0:
            best_apple = tuple(min(los_apples, key=lambda x: abs(x[0] - position[0]) + abs(x[1] - position[1]) + cost_function(x) * 2))
            return best_apple
        
        apples = np.argwhere(self.apple_map == 1)
        big_apples = np.argwhere(self.apple_map == 2)
        merged_apples = np.concatenate((apples, big_apples), axis=0)

        normalized_distance = lambda x: (abs(x[0] - position[0]) + abs(x[1] - position[1])) / self.size

        return tuple(min(merged_apples, key=lambda x: (cost_function(x) * normalized_distance(x))))


    def get_pacman_cost(self, position):
        cost = 0

        # if wall then inf
        if self.map[position[0], position[1]] == 1:
            return 100000000

        # how close is the position to ghosts
        for ghost_position in self.ghosts_positions:
            cost += 2 / (abs(ghost_position[0] - position[0]) + abs(ghost_position[1] - position[1]) + 1)

        nearby_ghosts = self.get_ghosts_nearby(position, 2)
        cost += 10 * len(nearby_ghosts)
            

        # how open is the position and ghost is near
        is_dangerous_position = len(self.get_ghosts_nearby(position, 2)) > 0 
        free_neighbours = self.get_free_neighbours(*position)
        cost += 0.5 / (len(free_neighbours) + 1) if is_dangerous_position else 0
        
        apples = self.get_bfs_apples(position)

        # how many apples
        cost += 1 / (len(apples) + 1)

        contains_apple = self.apple_map[position[0], position[1]]
        # if position contains an apple
        if contains_apple == 1:
            cost /= 1.25
        elif contains_apple == 2:
            cost /= 1.5

        

        return cost

    def is_apple_map_empty(self):
        return sum(sum(self.apple_map)) == 0
    
    def is_position_near_or_inside_pacman(self, position):
        return abs(self.pacman_position[0] - position[0]) + abs(self.pacman_position[1] - position[1]) <= 1

    def bfs(self, start, finish, neighbours_function=None):
        queue = [start]
        visited = np.zeros((self.size, self.size))
        visited[start] = 1
        parent = np.zeros((self.size, self.size, 2))

        while len(queue) > 0:
            current = tuple(queue.pop(0))
            if current == finish:
                path = []
                while current != start:
                    path.append(current)
                    current = tuple(parent[current[0], current[1]].astype(int))
                path.append(start)
                return path[::-1]

            for neighbour in neighbours_function(*current):
                if visited[neighbour] == 0:
                    visited[neighbour] = 1
                    parent[neighbour[0], neighbour[1]] = current
                    queue.append(neighbour)

        return []

    def dijkstra(self, start, finish, cost_function=None):
        open_set = {start}
        closed_set = set()
        came_from = {}
        g_score = {start: 0}

        while open_set:
            current = min(open_set, key=lambda x: g_score[x])

            if current == finish:
                path = []
                while current != start:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            open_set.remove(current)
            closed_set.add(current)

            for neighbour in self.get_free_neighbours(*current):
                if neighbour in closed_set:
                    continue

                if cost_function:
                    tentative_g = g_score[current] + 1 + cost_function(neighbour)
                else:
                    tentative_g = g_score[current] + 1

                if neighbour not in g_score or tentative_g < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g
                    if neighbour not in open_set:
                        open_set.add(neighbour)

        print("No path found")
        print(f"Start: {start}, Finish: {finish}")
        print(f"Explored {len(closed_set)} nodes")
        return []