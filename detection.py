import json
import time
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import mss
from config import CONFIG
from templates import TEMPLATES

CONFIG_FILE = Path(__file__).parent / 'config.json'

class RegionManager:
    def __init__(self):
        self.board_region: Optional[Tuple[int,int,int,int]] = None
        self.score_region: Optional[Tuple[int,int,int,int]] = None
        self.serial_port: Optional[str] = None
        self.load_regions()

    def load_regions(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
                self.board_region = tuple(data.get('board_region')) if data.get('board_region') else None
                self.score_region = tuple(data.get('score_region')) if data.get('score_region') else None
                self.serial_port = data.get('serial_port') or None
                print('[INFO] 已加载配置文件 config.json')
            except Exception as e:
                print(f'[WARN] 加载区域文件失败: {e}')
        else:
            print('[INFO] 未找到配置文件，请使用热键记录并选择串口')

    def save_config(self):
        data = {
            'board_region': self.board_region,
            'score_region': self.score_region,
            'serial_port': self.serial_port,
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'[STEP] 配置已保存到 {CONFIG_FILE}')

    def set_board_start(self, x, y):
        if self.board_region:
            _, _, right, bottom = self.board_region
            self.board_region = (x, y, right, bottom)
        else:
            self.board_region = (x, y, x, y)
        print(f'[STEP] 记录棋盘左上: ({x},{y})')

    def set_board_end(self, x, y):
        if not self.board_region:
            print('[ERROR] 尚未记录棋盘左上')
            return
        left, top, _, _ = self.board_region
        self.board_region = (left, top, x, y)
        print(f'[STEP] 记录棋盘右下: ({x},{y})')
        self.save_config()

    def set_score_start(self, x, y):
        if self.score_region:
            _, _, right, bottom = self.score_region
            self.score_region = (x, y, right, bottom)
        else:
            self.score_region = (x, y, x, y)
        print(f'[STEP] 记录分数区左上: ({x},{y})')

    def set_score_end(self, x, y):
        if not self.score_region:
            print('[ERROR] 尚未记录分数区左上')
            return
        left, top, _, _ = self.score_region
        self.score_region = (left, top, x, y)
        print(f'[STEP] 记录分数区右下: ({x},{y})')
        self.save_config()

    def set_serial_port(self, port: str):
        self.serial_port = port
        print(f'[STEP] 记录串口: {port}')
        self.save_config()

    @staticmethod
    def _is_region_valid(region: Optional[Tuple[int,int,int,int]]) -> bool:
        if not region:
            return False
        left, top, right, bottom = region
        return (right - left) > 3 and (bottom - top) > 3

    def board_ready(self) -> bool:
        return self._is_region_valid(self.board_region)

    def score_ready(self) -> bool:
        return self._is_region_valid(self.score_region)

    def ready(self) -> bool:
        return self.board_ready() and self.score_ready()

REGIONS = RegionManager()

class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()

    def grab_region(self, region):
        if not region:
            return None
        left, top, right, bottom = region
        monitor = {
            'left': int(left),
            'top': int(top),
            'width': int(right - left),
            'height': int(bottom - top)
        }
        shot = self.sct.grab(monitor)
        return np.array(shot)[:, :, :3]

CAPTURE = ScreenCapture()

class BoardRecognizer:
    def __init__(self):
        self.prev_board: Optional[np.ndarray] = None
        self.center_ratios: Optional[np.ndarray] = None  # shape (rows, cols, 2)

    def recognize_board(self):
        region = REGIONS.board_region
        if not REGIONS.board_ready():
            print('[ERROR] 棋盘区域未设置')
            return None
        board_img = CAPTURE.grab_region(region)
        if board_img is None:
            print('[ERROR] 截图失败')
            return None
        left, top, right, bottom = region
        tile_w = (right - left) / CONFIG.cols
        tile_h = (bottom - top) / CONFIG.rows
        board = []
        confs = []
        centers = []
        for r in range(CONFIG.rows):
            row = []
            c_row = []
            centers_row = []
            for c in range(CONFIG.cols):
                x1 = int(c * tile_w)
                y1 = int(r * tile_h)
                x2 = int((c + 1) * tile_w)
                y2 = int((r + 1) * tile_h)
                tile = board_img[y1:y2, x1:x2]
                name, score, (crx, cry) = TEMPLATES.match_tile(tile)
                if score < CONFIG.min_confidence and self.prev_board is not None:
                    print(f'[WARN] 低置信度 {score:.2f}@({r},{c}) -> 重试')
                    retry = 0
                    while retry < CONFIG.retry_low_conf:
                        time.sleep(0.05)
                        board_img_retry = CAPTURE.grab_region(region)
                        if board_img_retry is None:
                            print('[WARN] 重试截图失败，跳过本次重试')
                            retry += 1
                            continue
                        tile_retry = board_img_retry[y1:y2, x1:x2]
                        name_retry, score_retry, (crx_retry, cry_retry) = TEMPLATES.match_tile(tile_retry)
                        if score_retry >= CONFIG.min_confidence:
                            name, score = name_retry, score_retry
                            crx, cry = crx_retry, cry_retry
                            break
                        retry += 1
                    if score < CONFIG.min_confidence:
                        print('[WARN] 重试仍失败，使用上一帧值降级')
                        name = self.prev_board[r][c]
                        score = CONFIG.min_confidence
                        # 无法确定中心，使用居中
                        crx, cry = 0.5, 0.5
                row.append(name)
                c_row.append(score)
                centers_row.append((crx, cry))
            board.append(row)
            confs.append(c_row)
            centers.append(centers_row)
        board = np.array(board)
        confs = np.array(confs)
        centers = np.array(centers)
        self.prev_board = board
        self.center_ratios = centers
        return board, confs

BOARD_RECOGNIZER = BoardRecognizer()

class ScoreStabilityChecker:
    def __init__(self):
        pass

    @staticmethod
    def avg_diff(a, b):
        if a.shape != b.shape:
            return 9999
        return float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32))))

    def wait_stable(self):
        region = REGIONS.score_region
        if not REGIONS.score_ready():
            time.sleep(CONFIG.wait_score_stable_seconds)
            return
        start = time.time()
        frames = []
        while True:
            img = CAPTURE.grab_region(region)
            if img is None:
                time.sleep(CONFIG.poll_interval)
                continue
            frames.append(img)
            if len(frames) >= CONFIG.score_stable_checks:
                diffs = [self.avg_diff(frames[i], frames[i-1]) for i in range(1, len(frames))]
                avgd = sum(diffs)/len(diffs)
                if avgd < CONFIG.score_diff_threshold:
                    print(f'[STEP] 分数区域稳定 diff={avgd:.2f}')
                    return
                else:
                    frames.pop(0)
            if time.time() - start > CONFIG.wait_score_stable_seconds * 5:
                print('[WARN] 分数区域长时间未稳定，强制继续')
                return
            time.sleep(CONFIG.poll_interval)

SCORE_CHECKER = ScoreStabilityChecker()
