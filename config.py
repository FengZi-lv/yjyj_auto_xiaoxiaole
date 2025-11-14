from dataclasses import dataclass

@dataclass
class BoardConfig:
    rows: int = 6
    cols: int = 6
    min_confidence: float = 0.6
    retry_low_conf: int = 2
    wait_score_stable_seconds: float = 0.8
    poll_interval: float = 0.15
    swap_click_interval: float = 0.5
    score_stable_checks: int = 5
    score_diff_threshold: float = 4.0
    hotkey_board_start: str = 'ctrl+alt+s'
    hotkey_board_end: str = 'ctrl+alt+e'
    hotkey_score_start: str = 'ctrl+alt+f'
    hotkey_score_end: str = 'ctrl+alt+g'
    hotkey_exit: str = 'f8'
    # Arduino 串口配置
    # serial_port: str = ''  # 运行时交互选择，会保存到 config.json
    serial_baud: int = 115200
    serial_click_char: str = 'c'

CONFIG = BoardConfig()
