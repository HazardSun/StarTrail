import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".startrail"
CONFIG_FILE = CONFIG_DIR / "config.json"

class Config:
    def __init__(self):
        self.mode: str = "beginner"
        self.latitude: float = 39.9042
        self.longitude: float = 116.4074
        self.city_name: str = "北京"
        self.api_keys: dict = {"nasa": "", "openweather": ""}
        self.light_pollution: str = "城市"
        self.pro_settings: dict = {
            "show_ra_dec_grid": True,
            "show_dso": True,
            "show_iss_track": True,
            "auto_refresh": False,
            "units": "metric",
            "gl_renderer": True,
        }
        self._load()

    def _ensure_dirs(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self):
        self._ensure_dirs()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self):
        self._ensure_dirs()
        data = {
            "mode": self.mode,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city_name": self.city_name,
            "api_keys": self.api_keys,
            "light_pollution": self.light_pollution,
            "pro_settings": self.pro_settings
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def is_pro(self) -> bool:
        return self.mode == "professional"

config = Config()
