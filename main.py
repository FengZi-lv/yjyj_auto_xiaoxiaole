import time
import keyboard
from config import CONFIG
from templates import TEMPLATES
from detection import REGIONS, BOARD_RECOGNIZER, SCORE_CHECKER
from solver import SOLVER
from actions import ACTIONS

COLOR_MAP = {
	'UNKNOWN': '\x1b[90m',  # 灰色
	'R': '\x1b[31m',
	'Y': '\x1b[33m',
	'P': '\x1b[35m',
	'B': '\x1b[34m',
}
RESET = '\x1b[0m'

def colorize(name: str) -> str:
	return f"{COLOR_MAP.get(name, '')}{name}{RESET}"

def print_board(board, highlight=None, underline=False):
	# highlight: set of (r,c)
	for r in range(board.shape[0]):
		row_out = []
		for c in range(board.shape[1]):
			cell = board[r, c]
			text = colorize(cell)
			if highlight and (r, c) in highlight:
				if underline:
					text = f"\x1b[4m{text}\x1b[24m"  # 下划线
				else:
					text = f"\x1b[1m{text}\x1b[22m"  # 加粗
			row_out.append(text)
		print(' '.join(row_out))

def register_hotkeys():
	def record(name):
		import pyautogui
		x,y = pyautogui.position()
		if name=='board_start': REGIONS.set_board_start(x,y)
		elif name=='board_end': REGIONS.set_board_end(x,y)
		elif name=='score_start': REGIONS.set_score_start(x,y)
		elif name=='score_end': REGIONS.set_score_end(x,y)
	keyboard.add_hotkey(CONFIG.hotkey_board_start, lambda: record('board_start'))
	keyboard.add_hotkey(CONFIG.hotkey_board_end, lambda: record('board_end'))
	keyboard.add_hotkey(CONFIG.hotkey_score_start, lambda: record('score_start'))
	keyboard.add_hotkey(CONFIG.hotkey_score_end, lambda: record('score_end'))

def wait_regions():
	print('[INFO] 请使用热键设置棋盘与分数区域, 按 F8 可退出')
	while True:
		if keyboard.is_pressed(CONFIG.hotkey_exit):
			print('[INFO] 用户退出')
			return False
		if REGIONS.ready():
			print(f'[STEP] 棋盘区域={REGIONS.board_region} 分数区域={REGIONS.score_region}')
			return True
		time.sleep(0.25)

def main_loop():
	print('[INFO] 加载模板...')
	TEMPLATES.load_templates()
	if len(TEMPLATES.templates) < 4:
		print('[ERROR] 模板不足，退出')
		return
	iteration = 0
	while True:
		if keyboard.is_pressed(CONFIG.hotkey_exit):
			print('[INFO] 用户退出主循环')
			break
		iteration += 1
		print(f"\n[STEP] ===== Iteration {iteration} =====")
		rec = BOARD_RECOGNIZER.recognize_board()
		if rec is None:
			time.sleep(0.5)
			continue
		board, confs = rec
		print('[INFO] 棋盘(彩色输出):')
		print_board(board)
		move, score, matches = SOLVER.find_best_move(board)
		if not move:
			print('[WARN] 无可行交换，结束')
			break
		print(f'[STEP] 最佳交换 {move} 得分={score} 组数={len(matches)}')
		# 再次输出棋盘并下划线标记即将交换的两个格子
		highlight = {move[0], move[1]}
		print('[STEP] 交换前高亮棋盘 (下划线标记):')
		print_board(board, highlight=highlight, underline=True)
		ACTIONS.swap_tiles(*move)
		print('[STEP] 等待分数区域稳定...')
		time.sleep(1)
		SCORE_CHECKER.wait_stable()
	print('[INFO] 结束')

if __name__ == '__main__':
	register_hotkeys()
	if wait_regions():
		main_loop()
