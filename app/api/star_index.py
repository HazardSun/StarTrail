"""星表空间索引 - 基于 RA/Dec 的网格索引，替代全量遍历。"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StarRecord:
    name: str
    ra_deg: float
    dec_deg: float
    mag: float
    color: str


class StarIndex:
    """基于 RA/Dec 的简单网格索引。"""

    def __init__(self, cell_size_deg: float = 15.0):
        self._cell_size = cell_size_deg
        self._grid: Dict[Tuple[int, int], List[StarRecord]] = {}
        self._all: List[StarRecord] = []

    def build(self, stars):
        self._grid.clear()
        self._all.clear()
        for s in stars:
            rec = StarRecord(
                name=s[0] if isinstance(s, (list, tuple)) else s.get("name", ""),
                ra_deg=s[1] if isinstance(s, (list, tuple)) else s.get("ra", 0),
                dec_deg=s[2] if isinstance(s, (list, tuple)) else s.get("dec", 0),
                mag=s[3] if isinstance(s, (list, tuple)) else s.get("mag", 99),
                color=s[4] if isinstance(s, (list, tuple)) else s.get("color", "#FFF"),
            )
            self._all.append(rec)
            key = self._cell_key(rec.ra_deg, rec.dec_deg)
            self._grid.setdefault(key, []).append(rec)

    def _cell_key(self, ra, dec):
        return (int(ra // self._cell_size), int(dec // self._cell_size))

    def query_radius(self, ra_deg, dec_deg, radius_deg):
        results = []
        r_cells = range(int((ra_deg - radius_deg) // self._cell_size),
                        int((ra_deg + radius_deg) // self._cell_size) + 1)
        d_cells = range(int((dec_deg - radius_deg) // self._cell_size),
                        int((dec_deg + radius_deg) // self._cell_size) + 1)
        r2 = radius_deg * radius_deg
        for rc in r_cells:
            for dc in d_cells:
                for star in self._grid.get((rc, dc), []):
                    dra = star.ra_deg - ra_deg
                    ddec = star.dec_deg - dec_deg
                    if dra * dra + ddec * ddec <= r2:
                        results.append(star)
        return sorted(results, key=lambda s: s.mag)

    def query_by_mag(self, max_mag=6.0):
        return [s for s in self._all if s.mag <= max_mag]

    @property
    def count(self):
        return len(self._all)
