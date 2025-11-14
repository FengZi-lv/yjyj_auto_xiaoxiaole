import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Tuple

TEMPLATE_DIR = Path(__file__).parent / 'templates'

class TemplateManager:
    def __init__(self):
        self.templates: Dict[str, np.ndarray] = {}
        # 每个模板的前景中心 (x_ratio, y_ratio)
        self.centers: Dict[str, Tuple[float, float]] = {}

    @staticmethod
    def _compute_center_ratio(img: np.ndarray) -> Tuple[float, float]:
        """使用轮廓法估计模板前景中心。
        步骤：灰度 -> 高斯模糊 -> Otsu 二值(反色) -> 形态学闭操作 -> 最大轮廓 -> 质心。
        若失败则回退到 (0.5, 0.5)。
        """
        h, w = img.shape[:2]
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            # Otsu 阈值，图案通常比背景深，取反得到前景=白
            _, bin_inv = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            # 辅助：用饱和度过滤掉背景
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            sat = hsv[:, :, 1]
            _, sat_mask = cv2.threshold(sat, 30, 255, cv2.THRESH_BINARY)
            mask = cv2.bitwise_and(bin_inv, sat_mask)
            # 形态学闭操作填坑、去噪
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            # 选择最大轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return 0.5, 0.5
            cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(cnt)
            if area < (h * w * 0.01):
                # 面积过小，视为失败
                return 0.5, 0.5
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                return 0.5, 0.5
            cx = M['m10'] / M['m00']
            cy = M['m01'] / M['m00']
            return float(cx / w), float(cy / h)
        except Exception:
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
            names = [f"{n}(cx={self.centers[n][0]:.2f},cy={self.centers[n][1]:.2f})" for n in self.templates.keys()]
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
