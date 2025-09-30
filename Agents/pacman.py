from abc import abstractmethod, ABC
import random 

class PacmanState(ABC):
    @abstractmethod
    def move(self, pacman, map):
        pass

    @abstractmethod
    def handle_apple(self, pacman, map):
        pass

class PacmanStateBaseMove(PacmanState):
    def __init__(self) -> None:
        self.prev_position = None
        self.did_move = False

    def move(self, pacman, map):
        current_direction = pacman.current_direction
        direction_map = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        free_neighbours = map.get_free_neighbours(pacman.x, pacman.y)
        if not self.did_move:
            self.did_move = False
            if len(free_neighbours) > 0:
                neighbour_with_best_score = min(free_neighbours, key=lambda x: map.get_pacman_cost(x))
                new_x, new_y = neighbour_with_best_score
                current_direction = -1
                for i, direction in enumerate(direction_map):
                    if direction + (pacman.x, pacman.y) == (new_x, new_y):
                        current_direction = i
                        break
                pacman.current_direction = current_direction
                self.prev_position = (pacman.x, pacman.y)
                pacman.x, pacman.y = new_x, new_y
            else:
                print("PACMAN STUCK")
                pacman.die()
        
        map.pacman_position = (pacman.x, pacman.y)

    def handle_apple(self, pacman, map, apple):
        if apple == 1:
            pacman.score += 10
        elif apple == 2:
            pacman.score += 50
                    

class PacmanStateMove(PacmanStateBaseMove):
    def __init__(self) -> None:
        super().__init__()

    def move(self, pacman, map):
        current_x, current_y = pacman.x, pacman.y
        apple = map.get_best_apple((current_x, current_y), map.get_pacman_cost)
        pacman.current_target = apple
        if apple is not None:
            path = map.dijkstra((current_x, current_y), apple, map.get_pacman_cost)
            if len(path) > 1:
                pacman.path = path[1:]
                pacman.x, pacman.y = path[1]
                self.did_move = True
            else:
                pacman.path = None
                self.did_move = False

        self.prev_position = (current_x, current_y)
        super().move(pacman, map)
    


class Pacman:
    def __init__(self, sprites, lives = 3) -> None:
        self.max_lives = lives
        self.sprites = sprites

        self.restore()

    def restore(self):
        self.restore_without_lives()
        self.lives = self.max_lives
        self.score = 0
        

    def restore_without_lives(self):
        self.x = 0
        self.y = 0
        self.current_direction = 0
        self.state: PacmanState = PacmanStateMove()
        self.did_die = False
        self.current_target = None
        self.path = None

    def move(self, map):
        previous_x, previous_y = self.x, self.y
        self.state.move(self, map)

        apple = map.try_eat_apple(self.x, self.y)
        self.state.handle_apple(self, map, apple)

        if self.y > previous_y:
            self.current_direction = 0
        elif self.x > previous_x:
            self.current_direction = 1
        elif self.y < previous_y:
            self.current_direction = 2
        elif self.x < previous_x:
            self.current_direction = 3
        

    def on_draw(self, tile_size):
        current_sprite = self.sprites[self.current_direction]

        current_sprite.x = self.x * tile_size
        current_sprite.y = self.y * tile_size
        current_sprite.draw()

    def get_score(self):
        return self.score
    
    def get_lives(self):
        return self.lives

    def die(self):
        self.did_die = True
        return self.lives