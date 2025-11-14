from typing import List, Tuple, Optional
import numpy as np
from config import CONFIG

Move = Tuple[Tuple[int,int], Tuple[int,int]]

class Solver:
    def find_matches(self, board: np.ndarray) -> List[List[Tuple[int,int]]]:
        matches = []
        rows, cols = board.shape
        # 行
        for r in range(rows):
            c = 0
            while c < cols:
                start = c
                while c+1 < cols and board[r, c+1] == board[r, start] and board[r, start] != 'UNKNOWN':
                    c += 1
                length = c - start + 1
                if length >= 3:
                    matches.append([(r, cc) for cc in range(start, c+1)])
                c += 1
        # 列
        for c in range(cols):
            r = 0
            while r < rows:
                start = r
                while r+1 < rows and board[r+1, c] == board[start, c] and board[start, c] != 'UNKNOWN':
                    r += 1
                length = r - start + 1
                if length >= 3:
                    matches.append([(rr, c) for rr in range(start, r+1)])
                r += 1
        return matches

    def evaluate_swap(self, board: np.ndarray, a: Tuple[int,int], b: Tuple[int,int]):
        temp = board.copy()
        (r1,c1),(r2,c2) = a,b
        temp[r1,c1], temp[r2,c2] = temp[r2,c2], temp[r1,c1]
        matches = self.find_matches(temp)
        score = 0
        if matches:
            unique_cells = set()
            for group in matches:
                for cell in group:
                    unique_cells.add(cell)
            score = len(unique_cells) + (len(matches)-1)*2
        return score, matches

    def find_best_move(self, board: np.ndarray) -> Tuple[Optional[Move], int, List[List[Tuple[int,int]]]]:
        rows, cols = board.shape
        best_score = 0
        best_move: Optional[Move] = None
        best_matches: List[List[Tuple[int,int]]] = []
        for r in range(rows):
            for c in range(cols):
                if c+1 < cols:
                    score, matches = self.evaluate_swap(board, (r,c),(r,c+1))
                    if score > best_score:
                        best_score = score
                        best_move = ((r,c),(r,c+1))
                        best_matches = matches
                if r+1 < rows:
                    score, matches = self.evaluate_swap(board, (r,c),(r+1,c))
                    if score > best_score:
                        best_score = score
                        best_move = ((r,c),(r+1,c))
                        best_matches = matches
        return best_move, best_score, best_matches

SOLVER = Solver()
