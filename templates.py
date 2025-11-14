import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Tuple

TEMPLATE_DIR = Path(__file__).parent / 'templates'

class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, np.ndarray] = {}
        # 每个模板的点击中心 (x_ratio, y_ratio)
        self.centers: Dict[str, Tuple[float, float]] = {}

    @staticmethod
    def _compute_center_ratio(img: np.ndarray) -> Tuple[float, float]:
        """使用最初方案：点击格子几何中心 (0.5, 0.5)。"""
        return 0.5, 0.5

    def load_templates(self):
        if not TEMPLATE_DIR.exists():
            TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        for file in TEMPLATE_DIR.glob('*.png'):
            img = cv2.imread(str(file), cv2.IMREAD_COLOR)
            if img is None:
                continue
            self.templates[file.stem] = img
            self.centers[file.stem] = self._compute_center_ratio(img)
        if len(self.templates) < 4:
            print(f"[WARN] 模板数量不足: {len(self.templates)} < 4, 请添加PNG到 {TEMPLATE_DIR}")
        else:
            names = [f"{n}(center=0.50,0.50)" for n in self.templates.keys()]
            print(f"[STEP] 已加载模板: {names}")
        return self.templates

    def match_tile(self, tile_img: np.ndarray) -> Tuple[str, float, Tuple[float,float]]:
        if not self.templates:
            return 'UNKNOWN', 0.0, (0.5, 0.5)
        best_name = 'UNKNOWN'
        best_score = -1.0
        for name, tmpl in self.templates.items():
            h, w = tmpl.shape[:2]
            resized = cv2.resize(tile_img, (w, h))
            res = cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            hist_tile = cv2.calcHist([resized],[0,1,2],None,[8,8,8],[0,256,0,256,0,256])
            hist_tmpl = cv2.calcHist([tmpl],[0,1,2],None,[8,8,8],[0,256,0,256,0,256])
            cv2.normalize(hist_tile, hist_tile)
            cv2.normalize(hist_tmpl, hist_tmpl)
            hist_score = float(cv2.compareHist(hist_tile, hist_tmpl, cv2.HISTCMP_CORREL))
            combined = 0.7*score + 0.3*hist_score
            if combined > best_score:
                best_score = combined
                best_name = name
        center_ratio = self.centers.get(best_name, (0.5, 0.5))
        return best_name, best_score, center_ratio

TEMPLATES = TemplateManager()
