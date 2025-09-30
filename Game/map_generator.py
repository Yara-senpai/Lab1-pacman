import numpy as np
import random


class MapGenerator:
    def __init__(self, map_size):
        self.map_size = map_size // 2
        self.original_map_size = map_size
        self.tetris_shapes = [
            np.array([[1, 1, 1, 1]]),
            np.array([[1, 1], [1, 1]]),
            np.array([[1, 1, 0], [0, 1, 1]]),
            np.array([[0, 1, 1], [1, 1, 0]]),
            np.array([[1, 0], [1, 0], [1, 1]]),
            np.array([[0, 1], [0, 1], [1, 1]]),
            np.array([[1, 0], [1, 1], [0, 1]])
        ]

    def generate_map(self, ghost_room_positions):
        map = np.ones((self.original_map_size, self.original_map_size), dtype=int)

        tetris = self.simulate_tetris()
        mirrored = np.concatenate((tetris, np.flip(tetris, axis=1)), axis=1)
        mirrored = np.concatenate((mirrored, np.flip(mirrored, axis=0)), axis=0)

        map -= mirrored

        self.add_ghost_room(map, ghost_room_positions)
        self.add_border(map)

        map = self.join_separated_blocks(map)

        return map

    def join_separated_blocks(self, map):
        visited = np.zeros(map.shape, dtype=bool)
        blocks = []
        for i in range(map.shape[0]):
            for j in range(map.shape[1]):
                if map[i, j] == 0 and not visited[i, j]:
                    block = []
                    self.bfs(map, visited, i, j, block)
                    blocks.append(block)

        if len(blocks) == 1:
            return map

        # sort the blocks by center position
        blocks.sort(key=lambda block: (sum(x for x, _ in block) / len(block),
                                       sum(y for _, y in block) / len(block)))

        # З’єднуємо блоки послідовно L-коридором
        for i in range(1, len(blocks)):
            block1 = blocks[i - 1]
            block2 = blocks[i]

            # знаходимо найближчу пару клітинок (за Манхеттеном)
            min_dist = float('inf')
            min_pair = None
            for a in block1:
                for b in block2:
                    dist = abs(a[0] - b[0]) + abs(a[1] - b[1])
                    if dist < min_dist:
                        min_dist = dist
                        min_pair = (a, b)

            (x1, y1), (x2, y2) = min_pair

            # L-path: спочатку по X, потім по Y (можна й навпаки)
            # Всі клітинки шляху робимо прохідними (0)
            for x in range(min(x1, x2), max(x1, x2) + 1):
                map[x, y1] = 0
            for y in range(min(y1, y2), max(y1, y2) + 1):
                map[x2, y] = 0

        return map

    def add_ghost_room(self, map, ghost_room_positions):
        for x, y in ghost_room_positions:
            map[x, y] = 0

    def add_border(self, map):
        map[0, :] = 1
        map[-1, :] = 1
        map[:, 0] = 1
        map[:, -1] = 1

    def bfs(self, map, visited, i, j, block):
        queue = [(i, j)]
        visited[i, j] = True
        block.append((i, j))

        while queue:
            i, j = queue.pop(0)

            if i > 0 and map[i - 1, j] == 0 and not visited[i - 1, j]:
                queue.append((i - 1, j))
                visited[i - 1, j] = True
                block.append((i - 1, j))
            if i < map.shape[0] - 1 and map[i + 1, j] == 0 and not visited[i + 1, j]:
                queue.append((i + 1, j))
                visited[i + 1, j] = True
                block.append((i + 1, j))
            if j > 0 and map[i, j - 1] == 0 and not visited[i, j - 1]:
                queue.append((i, j - 1))
                visited[i, j - 1] = True
                block.append((i, j - 1))
            if j < map.shape[1] - 1 and map[i, j + 1] == 0 and not visited[i, j + 1]:
                queue.append((i, j + 1))
                visited[i, j + 1] = True
                block.append((i, j + 1))

    def join_separated_blocks(self, map):
        visited = np.zeros(map.shape, dtype=bool)
        blocks = []
        for i in range(map.shape[0]):
            for j in range(map.shape[1]):
                if map[i, j] == 0 and not visited[i, j]:
                    block = []
                    self.bfs(map, visited, i, j, block)
                    blocks.append(block)

        if len(blocks) == 1:
            return map

        # sort the blocks by center position
        blocks.sort(
            key=lambda block: (sum([x[0] for x in block]) / len(block), sum([x[1] for x in block]) / len(block)))

        # join the blocks
        for i in range(1, len(blocks)):
            block1 = blocks[i - 1]
            block2 = blocks[i]

            min_dist = float('inf')
            min_pair = None
            for pair in [(a, b) for a in block1 for b in block2]:
                dist = abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1])
                if dist < min_dist:
                    min_dist = dist
                    min_pair = pair

            x1, y1 = min_pair[0]
            x2, y2 = min_pair[1]

            if x1 == x2:
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    map[x1, y] = 0
            else:
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    map[x, y1] = 0

        return map

    def simulate_tetris(self):
        max_failed_attempts = 10
        failed_attempts = 0
        map_tile = np.zeros((self.map_size, self.map_size), dtype=int)

        while failed_attempts < max_failed_attempts:
            tetris_shape = random.choice(self.tetris_shapes)
            x = 0
            y = random.randint(0, self.map_size - tetris_shape.shape[1])

            placed = self.place_shape(map_tile, tetris_shape, x, y)

            if placed:
                failed_attempts = 0
            else:
                failed_attempts += 1

        return map_tile

    def place_shape(self, map_tile, shape, x, y):
        while x + shape.shape[0] <= self.map_size:
            # check if we can place the shape at the current position
            if self.can_place_shape(map_tile, shape, x, y):
                if x + shape.shape[0] == self.map_size or self.check_collision(map_tile, shape, x + 1, y):
                    # place the shape if it's at the bottom or there's a collision below
                    map_tile[x:x + shape.shape[0], y:y + shape.shape[1]] += shape
                    return True
                else:
                    # move the shape down
                    x += 1
            else:
                # if we can't place the shape at the initial position, return False
                if x == 0:
                    return False
                # place the shape at the previous valid position
                map_tile[x - 1:x - 1 + shape.shape[0], y:y + shape.shape[1]] += shape
                return True
        return False

    def can_place_shape(self, map_tile, shape, x, y):
        if x + shape.shape[0] > self.map_size or y + shape.shape[1] > self.map_size:
            return False
        return np.all((map_tile[x:x + shape.shape[0], y:y + shape.shape[1]] + shape) <= 1)

    def check_collision(self, map_tile, shape, x, y):
        if x + shape.shape[0] > self.map_size:
            return True
        return np.any(map_tile[x:x + shape.shape[0], y:y + shape.shape[1]] * shape)



