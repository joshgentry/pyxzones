from collections import namedtuple

class Zone(namedtuple('Zone', 'x y width height orientation')):

    def check(self, x, y):
        return (self.x <= x <= self.x + self.width) and (self.y <= y <= self.y + self.height)

    @property
    def corners(self):
        return [
            (self.x, self.y),
            (self.x + self.width, self.y),
            (self.x + self.width, self.y + self.height),
            (self.x, self.y + self.height),
        ]

WorkArea = namedtuple('WorkArea', 'x y width height')
