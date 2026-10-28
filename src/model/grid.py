class GridLayout:
    # Fixed device positions on a grid with neighbor range

    def __init__(self, positions: dict[int, tuple[int, int]]):
        self.positions = positions.copy()
        self._by_position = {position: ID for ID, position in self.positions.items()}
        if len(self._by_position) != len(self.positions):
            raise ValueError("Devices cannot occupy the same position")

    def channel(self, device_id: int) -> int:
        # Return the preferred simulation channel from 0 through 8
        x, y = self.positions[device_id]
        return (x % 3) + 3 * (y % 3)

    def neighbors(self, device_id: int) -> list[int]:
        # Return occupied adjacent cells
        x, y = self.positions[device_id]
        return [
            self._by_position[(x + dx, y + dy)]
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dx or dy) and (x + dx, y + dy) in self._by_position
        ]

    def landmarks(self):
        # Pick the four corners and the center of the layout
        if not self.positions:
            return frozenset()
        xs, ys = zip(*self.positions.values())
        left, right = min(xs), max(xs)
        bottom, top = min(ys), max(ys)
        targets = [(left, bottom), (right, bottom), (left, top), (right, top),
                   ((left + right) / 2, (bottom + top) / 2)]
        # Use the nearest device for gaps and break ties with the lowest ID
        return frozenset(min(self.positions, key=lambda ID: (
            (self.positions[ID][0] - x) ** 2 + (self.positions[ID][1] - y) ** 2, ID))
            for x, y in targets)

    def print_grid(self):
        xs = [x for x, _ in self._by_position]
        ys = [y for _, y in self._by_position]
        width = max((len(str(ID)) for ID in self.positions), default=1)
        for y in range(min(ys), max(ys) + 1):
            print(" ".join(
                str(self._by_position.get((x, y), "_")).rjust(width)
                for x in range(min(xs), max(xs) + 1)
            ))
