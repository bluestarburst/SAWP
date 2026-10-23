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

    def print_grid(self):
        xs = [x for x, _ in self._by_position]
        ys = [y for _, y in self._by_position]
        width = max((len(str(ID)) for ID in self.positions), default=1)
        for y in range(min(ys), max(ys) + 1):
            print(" ".join(
                str(self._by_position.get((x, y), "_")).rjust(width)
                for x in range(min(xs), max(xs) + 1)
            ))
