import time
import pyautogui
import serial
from serial import SerialException
from serial.tools import list_ports
from config import CONFIG
from detection import REGIONS, BOARD_RECOGNIZER

class MouseActions:
    def __init__(self):
        self.ser = None
        self._open_serial()

    def _open_serial(self):
        # 列出端口供选择
        ports = list(list_ports.comports())
        if not ports:
            print('[WARN] 未发现任何串口设备，无法使用Arduino移动')
            self.ser = None
            return
        print('[INFO] 可用串口列表:')
        for idx, p in enumerate(ports, start=1):
            print(f'  {idx}. {p.device} - {p.description}')
        selected = None
        while True:
            inp = input(f'请选择串口编号(1-{len(ports)})，或直接回车使用已有配置: ').strip()
            if inp == '' and REGIONS.serial_port:
                selected = REGIONS.serial_port
                print(f'[STEP] 使用已保存串口 {selected}')
                break
            try:
                num = int(inp)
                if 1 <= num <= len(ports):
                    selected = ports[num-1].device
                    print(f'[STEP] 选择串口 {selected}')
                    REGIONS.set_serial_port(selected)
                    break
                else:
                    print('[WARN] 编号超出范围')
            except ValueError:
                print('[WARN] 请输入有效数字或直接回车')
        if not selected:
            print('[WARN] 未选择串口，使用本机点击备用方案')
            self.ser = None
            return
        try:
            self.ser = serial.Serial(selected, CONFIG.serial_baud, timeout=0.1)
            time.sleep(0.5)
            print(f"[STEP] 已连接 Arduino 串口 {selected} @ {CONFIG.serial_baud}")
        except SerialException as e:
            print(f"[WARN] 串口 {selected} 打开失败: {e}")
            self.ser = None

    def _arduino_click(self):
        if self.ser and self.ser.is_open:
            try:
                msg = (CONFIG.serial_click_char + "\n").encode('ascii')
                self.ser.write(msg)
                self.ser.flush()
                return True
            except SerialException as e:
                print(f"[WARN] 串口写入失败: {e}，尝试重连")
                try:
                    self.ser.close()
                except Exception:
                    pass
                self._open_serial()
        return False

    def _pc_click(self):
        pyautogui.click()

    def _arduino_move_to(self, x_target: int, y_target: int) -> bool:
        # 使用相对移动，将当前坐标与目标坐标的差值通过串口发送
        if self.ser and self.ser.is_open:
            try:
                curx, cury = pyautogui.position()
                dx = int(x_target - curx)
                dy = int(y_target - cury)
                cmd = f"M {dx} {dy}\n".encode('ascii')
                self.ser.write(cmd)
                self.ser.flush()
                return True
            except SerialException as e:
                print(f"[WARN] 串口移动失败: {e}")
        return False

    def swap_tiles(self, a, b):
        if not REGIONS.board_ready():
            print('[ERROR] 尚未设置棋盘区域')
            return
        (r1,c1),(r2,c2) = a,b
        left, top, right, bottom = REGIONS.board_region
        tile_w = (right - left)/CONFIG.cols
        tile_h = (bottom - top)/CONFIG.rows
        # 使用检测阶段记录的中心偏移 (crx, cry)
        if BOARD_RECOGNIZER.center_ratios is not None:
            crx1, cry1 = BOARD_RECOGNIZER.center_ratios[r1, c1]
            crx2, cry2 = BOARD_RECOGNIZER.center_ratios[r2, c2]
        else:
            crx1 = cry1 = crx2 = cry2 = 0.5
        x1 = int(left + c1*tile_w + crx1*tile_w)
        y1 = int(top + r1*tile_h + cry1*tile_h)
        x2 = int(left + c2*tile_w + crx2*tile_w)
        y2 = int(top + r2*tile_h + cry2*tile_h)
        print(f'[STEP] 移动到 ({r1},{c1}) -> 屏幕({x1},{y1}) 并点击')
        moved = self._arduino_move_to(x1, y1)
        if not moved:
            print('[WARN] 串口移动失败，尝试重连后重试一次')
            self._open_serial()
            time.sleep(0.1)
            if not self._arduino_move_to(x1, y1):
                print('[ERROR] 无法移动到第一个格子，放弃本次交换')
                return
        if not self._arduino_click():
            self._pc_click()
        time.sleep(CONFIG.swap_click_interval)
        print(f'[STEP] 移动到 ({r2},{c2}) -> 屏幕({x2},{y2}) 并点击')
        moved2 = self._arduino_move_to(x2, y2)
        if not moved2:
            print('[WARN] 串口移动失败，尝试重连后重试一次')
            self._open_serial()
            time.sleep(0.1)
            if not self._arduino_move_to(x2, y2):
                print('[ERROR] 无法移动到第二个格子，放弃本次交换')
                return
        if not self._arduino_click():
            self._pc_click()

ACTIONS = MouseActions()
