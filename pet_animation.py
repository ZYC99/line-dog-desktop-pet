import os, random
from collections import defaultdict
from PySide6.QtGui import QMovie
from PySide6.QtCore import QObject, Signal
from config import ASSETS_DIR

class PetAnimation(QObject):
    """管理所有 GIF 素材的加载和播放"""
    animation_done = Signal()  # 非循环动画播完

    def __init__(self):
        super().__init__()
        self._movies: dict[str, list[QMovie]] = defaultdict(list)
        self._current_category = "idle"
        self._current_movie: QMovie = None
        self._load_all()

    def _load_all(self):
        """扫描 assets/gif/ 下所有文件夹，加载 GIF"""
        if not os.path.isdir(ASSETS_DIR):
            return
        for category in sorted(os.listdir(ASSETS_DIR)):
            cat_path = os.path.join(ASSETS_DIR, category)
            if not os.path.isdir(cat_path):
                continue
            gifs = sorted(
                [f for f in os.listdir(cat_path) if f.lower().endswith('.gif')]
            )
            for gif in gifs:
                path = os.path.join(cat_path, gif)
                movie = QMovie(path)
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self._movies[category].append(movie)

    def has_category(self, category: str) -> bool:
        return len(self._movies.get(category, [])) > 0

    def get_random(self, category: str) -> QMovie | None:
        """获取指定分类的随机 GIF（循环播放）"""
        pool = self._movies.get(category, [])
        if not pool:
            return None
        movie = random.choice(pool)
        movie.jumpToFrame(0)
        self._current_category = category
        self._current_movie = movie
        return movie

    def get_walk(self, direction: int) -> QMovie | None:
        """
        获取走路 GIF，根据方向选奇数(右)或偶数(左)
        direction: 1=右, -1=左, 0=上(jump)
        """
        if direction == 0:
            return self.get_random("jump")
        pool = self._movies.get("walk", [])
        if not pool:
            return None
        # 按文件名数字排序，奇数=右，偶数=左
        target_parity = 1 if direction > 0 else 0
        matching = [
            m for m in pool
            if self._file_parity(m) == target_parity
        ]
        if not matching:
            return random.choice(pool)
        movie = random.choice(matching)
        movie.jumpToFrame(0)
        self._current_category = "walk"
        self._current_movie = movie
        return movie

    def _file_parity(self, movie: QMovie) -> int:
        """从文件名提取编号奇偶性"""
        name = os.path.basename(movie.fileName())
        digits = ''.join(c for c in name if c.isdigit())
        if digits:
            return int(digits) % 2
        return 0

    def stop(self):
        if self._current_movie:
            self._current_movie.stop()

    def categories(self) -> list[str]:
        return list(self._movies.keys())
