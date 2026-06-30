from dataclasses import dataclass


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.hits / self.total) * 100, 2)

    def register_hit(self) -> None:
        self.hits += 1

    def register_miss(self) -> None:
        self.misses += 1

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0

    def snapshot(self) -> dict[str, int | float]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": self.total,
            "hit_rate_percent": self.hit_rate_percent,
        }


cache_metrics = CacheMetrics()
