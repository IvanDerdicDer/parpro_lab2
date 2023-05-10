from dataclasses import dataclass, field
from typing import Optional, Generator
from enum import Enum
from copy import deepcopy
from hashlib import md5


class TokenEnum(Enum):
    RED = 1
    YELLOW = 2


class BoardTooSmallException(Exception):
    pass


class ColumnFullException(Exception):
    pass


@dataclass
class ConnectFourBoard:
    width: int
    height: int
    board: Optional[list[list[Optional[TokenEnum]]]] = field(default=None)
    is_column_full: Optional[list[bool]] = field(default=None)
    last_token_placed_position: Optional[tuple[int, int]] = field(default=None, init=False)
    last_token_placed: Optional[TokenEnum] = field(default=None, init=False)
    weight: int = field(default=0, init=False)
    is_winning: bool = field(default=False, init=False)

    def __hash__(self):
        return md5(str(self))

    def __post_init__(self) -> None:
        if self.width < 7 or self.height < 6:
            raise BoardTooSmallException(f"Board must be at least 7x6, got {self.width}x{self.height}")

        if not self.board:
            self.board = [[None] * self.height for _ in range(self.width)]

        if not self.is_column_full:
            self.is_column_full = [False] * self.width

    def __str__(self) -> str:
        return "\n".join(
            " ".join(
                "R" if token == TokenEnum.RED else "Y" if token == TokenEnum.YELLOW else "x"
                for token in column
            )
            for column in zip(*self.board)
        )

    def __repr__(self) -> str:
        return f"ConnectFourBoard(width={self.width}, height={self.height}, board={self.board})"

    def drop_token(self, column: int, token: TokenEnum) -> "ConnectFourBoard":
        new_board = ConnectFourBoard(self.width, self.height, deepcopy(self.board), self.is_column_full)
        # return new_board._inplace_drop_token(column, token)

        if new_board.is_column_full[column]:
            raise ColumnFullException(f"Column {column} is full")

        for row in range(new_board.height - 1, -1, -1):
            if new_board.board[column][row] is None:
                new_board.board[column][row] = token

                new_board.last_token_placed_position = (column, row)
                new_board.last_token_placed = token

                if row == 0:
                    new_board.is_column_full[column] = True
                return new_board

    def is_last_move_winning(self) -> bool:
        horizontal_count = 0
        vertical_count = 0
        diagonal_left_count = 0
        diagonal_right_count = 0

        column, row = self.last_token_placed_position

        for i in range(self.height):
            if vertical_count < 4 and self.board[column][i] != self.last_token_placed:
                vertical_count = 0
            else:
                vertical_count += 1

            if vertical_count >= 4:
                return True

            if (column - row + i) in range(self.width) and diagonal_right_count < 4 and self.board[column - row + i][
                i] != self.last_token_placed:
                diagonal_right_count = 0
            elif (column - row + i) in range(self.width):
                diagonal_right_count += 1

            if diagonal_right_count >= 4:
                return True

            if (column + row - i) in range(self.width) and diagonal_left_count < 4 and self.board[column + row - i][
                i] != self.last_token_placed:
                diagonal_right_count = 0
            elif (column + row - i) in range(self.width):
                diagonal_left_count += 1

            if diagonal_left_count >= 4:
                return True

        for i in range(self.width):
            if horizontal_count < 4 and self.board[i][row] != self.last_token_placed:
                horizontal_count = 0
            else:
                horizontal_count += 1

            if horizontal_count >= 4:
                return True

        return False

    def _select_token(self) -> TokenEnum:
        match self.last_token_placed:
            case TokenEnum.RED:
                return TokenEnum.YELLOW
            case TokenEnum.YELLOW:
                return TokenEnum.RED
            case _:
                return TokenEnum.RED

    def generate_all_children(self) -> Generator["ConnectFourBoard", None, None]:
        if self.is_winning:
            return
        yield from (self.drop_token(i, self._select_token()) for i in range(self.width) if not self.is_column_full[i])

    def who_won(self) -> float:
        win = self.is_last_move_winning()

        if win:
            win *= 1 if self.last_token_placed == TokenEnum.YELLOW else -1
            self.weight = win
            self.is_winning = True
            return win

        return self.weight

    def __eq__(self, other: "ConnectFourBoard") -> bool:
        for i in range(self.width):
            for j in range(self.height):
                if self.board[i][j] != other.board[i][j]:
                    return False

        return True


@dataclass
class Node:
    value: ConnectFourBoard
    children: list["Node"] = field(default_factory=list)
    parent: Optional["Node"] = field(default=None)
    depth: int = field(default=0)


def build_tree(root: Node, depth: int = 0) -> Node:
    end_depth = root.depth + depth

    stack = [root]

    while stack:
        top = stack.pop()

        if top.depth == end_depth:
            continue

        for child in (Node(value=i, parent=top, depth=top.depth + 1) for i in top.value.generate_all_children()):
            stack.append(child)
            top.children.append(child)

    return root


def get_all_tree_leafs(root: Node) -> list[Node]:
    stack = [root]

    leafs = []

    while stack:
        top = stack.pop()

        if not top.children:
            leafs.append(top)

        stack += top.children

    return leafs


def calculate_tree_weight(root: Node) -> Node:
    if not root.children:
        root.value.who_won()
        return root

    for child in root.children:
        calculate_tree_weight(child)

        root.value.weight += child.value.weight

    root.value.weight /= len(root.children)

    return root


def print_tree(root: Node) -> None:
    stack = [root]

    while stack:
        top = stack.pop()
        print("    " * top.depth + str(top.depth) + " " + str(top.value.__repr__()))

        stack += top.children


board = ConnectFourBoard(15, 15)

board = board.drop_token(0, TokenEnum.RED)
board = board.drop_token(1, TokenEnum.YELLOW)
board = board.drop_token(1, TokenEnum.RED)
board = board.drop_token(2, TokenEnum.YELLOW)
board = board.drop_token(2, TokenEnum.RED)
board = board.drop_token(3, TokenEnum.YELLOW)
board = board.drop_token(3, TokenEnum.RED)

root = Node(board)
root = build_tree(root, 3)
root = calculate_tree_weight(root)
print(max(i.value.weight for i in root.children))
print(*(i.value.weight for i in root.children))
# print_tree(root)
