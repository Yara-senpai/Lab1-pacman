# Agents/ghost.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Dict
import random
import pyglet

# Тип позиції
RC = Tuple[int, int]

# ------------------------------------------------------------
# БАЗОВИЙ СТАН
# ------------------------------------------------------------
class GhostState(ABC):
    @abstractmethod
    def move(self, ghost: "Ghost", map):
        ...

class GhostStateBaseMove(GhostState):
    """Спільний код: м’який анти-реверс, перевірка зіткнень."""
    DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    def __init__(self) -> None:
        self.prev_pos: Optional[RC] = None
        self.should_switch: bool = False

    def _set_dir_from_step(self, ghost: "Ghost", old: RC, new: RC) -> None:
        ox, oy = old
        nx, ny = new
        dx, dy = nx - ox, ny - oy
        for i, (ix, iy) in enumerate(self.DIRS):
            if (ix, iy) == (dx, dy):
                ghost.current_direction = i
                return

    def _collision_check(self, ghost: "Ghost", map) -> bool:
        # зіткнення, якщо відстань мангеттена <= 1
        px, py = map.pacman_position
        return abs(px - ghost.x) + abs(py - ghost.y) <= 0

    def _try_step(self, ghost: "Ghost", map, candidates: List[RC]) -> bool:
        """Зробити крок у перший зі списку кандидатів, якщо він прохідний."""
        if not candidates:
            return False
        # фільтр на прохідність
        walk = [(x, y) for (x, y) in candidates if 0 <= x < map.size and 0 <= y < map.size and map.map[x, y] == 0]
        if not walk:
            return False
        old = (ghost.x, ghost.y)
        new = walk[0]
        self._set_dir_from_step(ghost, old, new)
        ghost.x, ghost.y = new
        return True

    def move(self, ghost: "Ghost", map) -> None:
        # Перед кроком – миттєва перевірка
        if self._collision_check(ghost, map):
            ghost.caught_pacman()
            return
        # Перемикання стану по лічильнику
        if self.should_switch:
            ghost.randomize_state()
            self.should_switch = False
        # Після кроку – ще раз перевірка
        if self._collision_check(ghost, map):
            ghost.caught_pacman()


# ------------------------------------------------------------
# СТАНИ ПОВЕДІНКИ
# ------------------------------------------------------------
class GhostStateWandering(GhostStateBaseMove):
    """Випадкове блукання з легкою відразою до моментального реверсу."""
    def __init__(self, difficulty: int) -> None:
        super().__init__()
        # що вища складність – тим менше привид тиняється
        self.ticks_left = max(10 - difficulty, 4) + random.randint(0, 4)

    def move(self, ghost: "Ghost", map) -> None:
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.should_switch = True

        old = (ghost.x, ghost.y)
        nbrs = map.get_free_neighbours_for_ghost(ghost.x, ghost.y)
        if nbrs:
            # уникаємо реверсу, якщо є альтернатива
            if self.prev_pos in nbrs and len(nbrs) > 1:
                nbrs = [p for p in nbrs if p != self.prev_pos]
            new = random.choice(nbrs)
            self._set_dir_from_step(ghost, old, new)
            ghost.x, ghost.y = new

        self.prev_pos = old
        super().move(ghost, map)


class GhostStateChaseDirect(GhostStateBaseMove):
    """Пряме переслідування: BFS до поточної позиції Pacman (Blinky)."""
    def __init__(self, difficulty: int) -> None:
        super().__init__()
        self.ticks_left = min(5 + difficulty, 9)

    def move(self, ghost: "Ghost", map) -> None:
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.should_switch = True

        old = (ghost.x, ghost.y)
        target = map.pacman_position
        path = map.bfs(old, target, map.get_free_neighbours_for_ghost)
        if len(path) > 1:
            new = path[1]
            self._set_dir_from_step(ghost, old, new)
            ghost.x, ghost.y = new

        self.prev_pos = old
        super().move(ghost, map)


class GhostStateAmbush(GhostStateBaseMove):
    """Перехоплення: ціль – 2 клітинки попереду напряму Pacman (Pinky)."""
    def __init__(self, difficulty: int) -> None:
        super().__init__()
        self.ticks_left = min(4 + difficulty, 8)

    def _ahead_of_pac(self, map, k: int = 2) -> RC:
        px, py = map.pacman_position
        d = getattr(map, "pacman_direction", 0)  # 0:R,1:D,2:L,3:U
        dxdy = [(0, 1), (1, 0), (0, -1), (-1, 0)][d]
        ax, ay = px + k * dxdy[0], py + k * dxdy[1]
        # якщо стіна – посуньмося ближче до Pacman
        k2 = k
        while not (0 <= ax < map.size and 0 <= ay < map.size) or map.map[ax, ay] == 1:
            k2 -= 1
            if k2 <= 0:
                return (px, py)
            ax, ay = px + k2 * dxdy[0], py + k2 * dxdy[1]
        return (ax, ay)

    def move(self, ghost: "Ghost", map) -> None:
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.should_switch = True

        old = (ghost.x, ghost.y)
        target = self._ahead_of_pac(map, 2)
        path = map.bfs(old, target, map.get_free_neighbours_for_ghost)
        if len(path) > 1:
            new = path[1]
            self._set_dir_from_step(ghost, old, new)
            ghost.x, ghost.y = new

        self.prev_pos = old
        super().move(ghost, map)


class GhostStateCutOff(GhostStateBaseMove):
    """Перерізання шляху: намагаємось зайняти клітинку між Pacman і найближчим 'вузлом' (Inky-лайт)."""
    def __init__(self, difficulty: int) -> None:
        super().__init__()
        self.ticks_left = min(4 + difficulty, 8)

    def _pick_cut(self, map) -> RC:
        """Вибрати точку 'попереду' Pacman за його напрямом, але трохи далі, ніж у Ambush."""
        px, py = map.pacman_position
        d = getattr(map, "pacman_direction", 0)
        dxdy = [(0, 1), (1, 0), (0, -1), (-1, 0)][d]
        # шукаємо перший перетин (місце де розгалуження >1) у напрямі руху
        cx, cy = px, py
        for _ in range(1, 6):
            nx, ny = cx + dxdy[0], cy + dxdy[1]
            if not (0 <= nx < map.size and 0 <= ny < map.size) or map.map[nx, ny] == 1:
                break
            cx, cy = nx, ny
            # розгалуження
            if len(map.get_free_neighbours_for_ghost(cx, cy)) >= 3:
                return (cx, cy)
        return (cx, cy)

    def move(self, ghost: "Ghost", map) -> None:
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.should_switch = True

        old = (ghost.x, ghost.y)
        target = self._pick_cut(map)
        path = map.bfs(old, target, map.get_free_neighbours_for_ghost)
        if len(path) > 1:
            new = path[1]
            self._set_dir_from_step(ghost, old, new)
            ghost.x, ghost.y = new

        self.prev_pos = old
        super().move(ghost, map)


class GhostStateShy(GhostStateBaseMove):
    """Сором’язливий (Clyde): якщо близько до Pacman — тікає у свій куток, якщо далеко — блукає/трохи женеться."""
    CORNERS = ("tl", "tr", "bl", "br")

    def __init__(self, difficulty: int, corner: str = "bl") -> None:
        super().__init__()
        self.ticks_left = min(5 + difficulty, 9)
        self.corner = corner if corner in self.CORNERS else "bl"

    def _corner_target(self, map) -> RC:
        h = w = map.size
        corners = {
            "tl": (1, 1),
            "tr": (1, w - 2),
            "bl": (h - 2, 1),
            "br": (h - 2, w - 2),
        }
        tx, ty = corners[self.corner]
        # якщо стіна — посуваємось до центру, поки не стане прохідно
        cx, cy = tx, ty
        while not (0 <= cx < map.size and 0 <= cy < map.size) or map.map[cx, cy] == 1:
            if cx > map.size // 2: cx -= 1
            if cy > map.size // 2: cy -= 1
            if cx < 0 or cy < 0: break
        return (max(0, min(cx, map.size - 1)), max(0, min(cy, map.size - 1)))

    def move(self, ghost: "Ghost", map) -> None:
        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.should_switch = True

        old = (ghost.x, ghost.y)
        px, py = map.pacman_position
        d = abs(px - old[0]) + abs(py - old[1])

        if d <= 4:
            target = self._corner_target(map)
        else:
            # коли далеко — або блукаємо, або трохи переслідуємо
            if random.random() < 0.5:
                target = map.pacman_position
            else:
                nbrs = map.get_free_neighbours_for_ghost(old[0], old[1])
                if nbrs:
                    new = random.choice(nbrs)
                    self._set_dir_from_step(ghost, old, new)
                    ghost.x, ghost.y = new
                    self.prev_pos = old
                    super().move(ghost, map)
                    return
                target = map.pacman_position

        path = map.bfs(old, target, map.get_free_neighbours_for_ghost)
        if len(path) > 1:
            new = path[1]
            self._set_dir_from_step(ghost, old, new)
            ghost.x, ghost.y = new

        self.prev_pos = old
        super().move(ghost, map)


# ------------------------------------------------------------
# САМИЙ ПРИВИД
# ------------------------------------------------------------
class Ghost:
    """
    role:
      - "blinky" (червоний)  : пряме переслідування
      - "pinky"  (рожевий)   : перехоплення попереду Pacman
      - "inky"   (блакитний) : перерізання шляху
      - "clyde"  (помаранч.) : сором’язливий
    Якщо role не передали — призначимо по n % 4.
    """
    ROLE_BY_INDEX = {0: "blinky", 1: "pinky", 2: "inky", 3: "clyde"}

    def __init__(self, sprites, n: int, role: Optional[str] = None) -> None:
        self.sprites = sprites
        self.n = n
        self.role = (role or self.ROLE_BY_INDEX.get(n % 4, "blinky")).lower()
        self.difficulty = 1
        self.current_direction = 0
        self.did_catch_pacman = False
        self.x = 0
        self.y = 0
        self.state: GhostState = GhostStateWandering(self.difficulty)

    # -------- API гри --------
    def restore(self):
        self.current_direction = 0
        self.did_catch_pacman = False
        self.state = GhostStateWandering(self.difficulty)
        # координати виставляє Game.reset_positions()

    def randomize_state(self):
        """Перемикання стану з огляду на роль і складність (ймовірності)."""
        d = max(1, int(self.difficulty))

        # Ваги станів за роллю
        if self.role == "blinky":
            # здебільшого пряме переслідування
            weights = [
                ("chase", 3 + d),     # ChaseDirect
                ("ambush", 1 + d//2), # інколи перехоплення
                ("cutoff", 1 + d//2), # інколи перерізання
                ("wander", max(1, 5 - d)),
            ]
        elif self.role == "pinky":
            weights = [
                ("ambush", 3 + d),
                ("chase", 1 + d//2),
                ("wander", max(1, 5 - d)),
                ("cutoff", 1 + d//2),
            ]
        elif self.role == "inky":
            weights = [
                ("cutoff", 3 + d),
                ("ambush", 1 + d//2),
                ("chase", 1 + d//2),
                ("wander", max(1, 5 - d)),
            ]
        else:  # clyde
            weights = [
                ("shy", 3 + d),
                ("wander", max(1, 5 - d)),
                ("chase", 1 + d//2),
                ("ambush", 1),
            ]

        bag: List[str] = []
        for name, w in weights:
            bag.extend([name] * max(1, int(w)))
        choice = random.choice(bag)

        if choice == "chase":
            self.state = GhostStateChaseDirect(d)
        elif choice == "ambush":
            self.state = GhostStateAmbush(d)
        elif choice == "cutoff":
            self.state = GhostStateCutOff(d)
        elif choice == "shy":
            # кут для Clyde оберемо за n, щоб розвести привидів
            corner = ["tl", "tr", "bl", "br"][self.n % 4]
            self.state = GhostStateShy(d, corner=corner)
        else:
            self.state = GhostStateWandering(d)

    def move(self, map):
        oldx, oldy = self.x, self.y
        self.state.move(self, map)
        # якщо таки зрушили — напрямок вже виставлено у стані
        # (залишимо «на випадок» коли хтось пересунувся зовні)
        if (self.x, self.y) == (oldx, oldy):
            # не зрушив — збережемо напрямок як був
            pass

    def on_draw(self, tile_size):
        current_sprite = self.sprites[self.current_direction]
        current_sprite.x = self.x * tile_size
        current_sprite.y = self.y * tile_size
        number = pyglet.text.Label(
            str(self.n), font_name='Times New Roman', font_size=12,
            x=self.x * tile_size, y=self.y * tile_size
        )
        current_sprite.draw()
        number.draw()

    def caught_pacman(self):
        self.did_catch_pacman = True
        print(f"GHOST {self.n} ({self.role}) CAUGHT PACMAN")
