from dataclasses import dataclass, field
from typing import Optional, Generator
from enum import Enum
from copy import deepcopy


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

    # def _inplace_drop_token(self, column: int, token: TokenEnum) -> "ConnectFourBoard":
    #     if self.is_column_full[column]:
    #         raise ColumnFullException(f"Column {column} is full")
    #
    #     for row in range(self.height - 1, -1, -1):
    #         if self.board[column][row] is None:
    #             self.board[column][row] = token
    #
    #             self.last_token_placed_position = (column, row)
    #             self.last_token_placed = token
    #
    #             if row == self.height - 1:
    #                 self.is_column_full[column] = True
    #             return self

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
        if self.last_token_placed is None:
            return False

        column, row = self.last_token_placed_position

        # Check horizontal left
        if column - 4 > -2:
            for i in range(column, column - 4, -1):
                if self.board[i][row] != self.last_token_placed:
                    break
            else:
                return True

        # Check horizontal right
        if column + 4 < self.width + 1:
            for i in range(column, column + 4):
                if self.board[i][row] != self.last_token_placed:
                    break
            else:
                return True

        # Check vertical down
        if row + 4 < self.height + 1:
            for i in range(row, row + 4):
                if self.board[column][i] != self.last_token_placed:
                    break
            else:
                return True

        # Check diagonal left
        if column - 4 > -2 and row + 4 < self.height + 1:
            count_token_equals = 0
            for i in range(column, column - 4, -1):
                for j in range(row, row + 4):
                    count_token_equals += self.board[i][j] == self.last_token_placed and i - column == (j - row) * -1

            if count_token_equals == 4:
                return True

        # Check diagonal right
        if column + 4 < self.width + 1 and row + 4 < self.height + 1:
            count_token_equals = 0
            for i in range(column, column + 4):
                for j in range(row, row + 4):
                    count_token_equals += self.board[i][j] == self.last_token_placed and i - column == j - row

            if count_token_equals == 4:
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
        yield from (self.drop_token(i, self._select_token()) for i in range(self.width) if not self.is_column_full[i])

    def who_won(self) -> int:
        win = self.is_last_move_winning()

        if win:
            return win * 1 if self.last_token_placed == TokenEnum.YELLOW else -1

        return 0


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


def print_tree(root: Node) -> None:
    stack = [root]

    while stack:
        top = stack.pop()
        print("    " * top.depth + str(top.value.__repr__()))

        stack += top.children


board = ConnectFourBoard(7, 6)

root = Node(board)
root = build_tree(root, 2)
print_tree(root)
