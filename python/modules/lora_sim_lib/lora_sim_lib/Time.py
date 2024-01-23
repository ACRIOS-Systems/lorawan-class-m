
class Time:
    def __init__(self, ms: float = 0.0, us: float = 0.0) -> None:
        # init time counter (in us)
        self._now = ms * 1000.0 + us

    # property us
    @property
    def us(self) -> float:
        return self._now
    @us.setter
    def us(self, us):
        self._now = us

    @property
    def ms(self) -> float:
        return self._now / 1000.0
    @ms.setter
    def ms(self, ms):
        self._now = ms * 1000

    @property
    def sec(self) -> float:
        return self._now / 1000000.0

    def increment(self) -> None:
        self._now += 1000.0     # 1ms is the step increment

    # operators for this class
    def __add__(self, other: 'Time') -> 'Time':
        return Time(us = self.us + other.us)

    def __sub__(self, other: 'Time') -> 'Time':
        return Time(us = self.us - other.us)

    def __str__(self) -> str:
        return f"{self._now/1000:.3f} ms"

    def __repr__(self) -> str:
        return f"t = {self._now/1000:.3f} ms"

    def __eq__(self, other: 'Time') -> bool:
        return self._now == other._now

    def __lt__(self, other: 'Time') -> bool:
        return self._now < other._now

    def __le__(self, other: 'Time') -> bool:
        return self._now <= other._now

    def __gt__(self, other: 'Time') -> bool:
        return self._now > other._now

    def __ge__(self, other: 'Time') -> bool:
        return self._now >= other._now

    def __ne__(self, other: 'Time') -> bool:
        return self._now != other._now

    # make a copy of this class
    def copy(self) -> 'Time':
        return Time(us = self.us)
    