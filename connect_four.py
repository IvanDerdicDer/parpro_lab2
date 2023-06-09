import pickle
from dataclasses import dataclass, field
from typing import Optional, Generator, Union
from enum import Enum
from copy import deepcopy
from hashlib import md5
from mpi4py import MPI
import sys
from concurrent.futures import ThreadPoolExecutor, Future
from uuid import uuid4, UUID
from queue import Queue
import os


class TokenEnum(Enum):
    RED = 1
    YELLOW = 2


class BoardTooSmallException(Exception):
    pass


class ColumnFullException(Exception):
    pass


class Shutdown:
    pass


class Request:
    pass


@dataclass
class ConnectFourBoard:
    width: int
    height: int
    board: Optional[list[list[Optional[TokenEnum]]]] = field(default=None)
    is_column_full: Optional[list[bool]] = field(default=None)
    last_token_placed_position: Optional[tuple[int, int]] = field(default=None, init=False)
    last_token_placed: Optional[TokenEnum] = field(default=None, init=False)
    weight: float = field(default=0, init=False)
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
        new_board = ConnectFourBoard(self.width, self.height, deepcopy(self.board), self.is_column_full.copy())
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


def calculate_tree_weight2(root: Node) -> Node:
    if not root.children:
        return root

    for child in root.children:
        calculate_tree_weight2(child)

        root.value.weight += child.value.weight

    root.value.weight /= len(root.children)

    return root


def print_tree(root: Node) -> None:
    stack = [root]

    while stack:
        top = stack.pop()
        print("    " * top.depth + ' ' + str(top.value.weight))

        stack += top.children


def create_board() -> ConnectFourBoard:
    if os.path.exists("board.pickle"):
        with open("board.pickle", "rb") as f:
            return pickle.load(f)

    board = ConnectFourBoard(7, 6)

    # board = board.drop_token(0, TokenEnum.RED)
    # board = board.drop_token(1, TokenEnum.YELLOW)
    # board = board.drop_token(1, TokenEnum.RED)
    # board = board.drop_token(2, TokenEnum.YELLOW)
    # board = board.drop_token(2, TokenEnum.RED)
    # board = board.drop_token(3, TokenEnum.YELLOW)

    return board


def get_next_move(l: list[float]) -> int:
    m = max(l)

    return l.index(m)


def calculate_on_worker(
        message: Union[ConnectFourBoard, Shutdown],
        worker_id: int,
        comm: MPI.Comm
) -> float:
    result = comm.sendrecv(
        message,
        dest=worker_id,
        sendtag=1,
        source=worker_id,
        recvtag=1
    )

    return result


def foo(
        queue: Queue,
        worker_id: int,
        comm: MPI.Comm,
        executor: ThreadPoolExecutor
) -> dict[UUID, tuple[Node, Future]]:
    nodes_waiting = {}
    if comm.iprobe(worker_id, tag=2):
        message = comm.recv(source=worker_id, tag=2)

        if isinstance(message, Request) and queue.qsize():
            to_send = queue.get()
            nodes_waiting[uuid4()] = (
                to_send,
                executor.submit(
                    calculate_on_worker,
                    to_send.value,
                    worker_id,
                    comm
                )
            )

    return nodes_waiting


def get_next_move_distributed(root: Node, worker_count: int, comm: MPI.Comm) -> int:
    nodes = get_all_tree_leafs(root)
    node_queue = Queue()
    for node in nodes:
        node_queue.put(node)

    nodes_waiting: dict[UUID, tuple[Node, Future]] = {}
    with ThreadPoolExecutor() as executor:
        while node_queue.qsize():
            results = executor.map(
                foo,
                [node_queue] * worker_count,
                range(1, worker_count + 1),
                [comm] * worker_count,
                [executor] * worker_count
            )
            for i in results:
                nodes_waiting.update(i)

        for worker_id in range(1, worker_count + 1):
            executor.submit(
                comm.send,
                Shutdown(),
                worker_id,
                1
            )

    for i in nodes_waiting:
        nodes_waiting[i][0].value.weight = nodes_waiting[i][1].result()

    root = calculate_tree_weight2(root)

    return get_next_move(list(i.value.weight for i in root.children))


def shutdown_all_workers(
        comm: MPI.Comm,
        worker_count: int
) -> None:
    for worker_id in range(1, worker_count + 1):
        comm.send(Shutdown(), worker_id, 1)


def main() -> None:
    comm = MPI.COMM_WORLD
    mpi_id = comm.Get_rank()
    cluster_size = comm.Get_size()

    args = sys.argv

    next_move = 3
    if len(args) > 1:
        next_move = int(args[1])

    if cluster_size == 1:
        board = create_board()
        board = board.drop_token(next_move, TokenEnum.RED)
        if board.is_last_move_winning():
            print(board)
            print(board.who_won())
            shutdown_all_workers(comm, cluster_size - 1)
            return

        root = Node(board)
        root = build_tree(root, 7)
        root = calculate_tree_weight(root)

        next_move = get_next_move(list(i.value.weight for i in root.children))

        board = board.drop_token(next_move, TokenEnum.YELLOW)

        with open("board.pickle", "wb") as f:
            pickle.dump(board, f)

        print(board)
        print(board.who_won())
    else:
        if mpi_id == 0:
            board = create_board()
            board = board.drop_token(next_move, TokenEnum.RED)
            if board.is_last_move_winning():
                print(board)
                print(board.who_won())
                shutdown_all_workers(comm, cluster_size - 1)
                return

            root = Node(board)
            root = build_tree(root, 2)

            next_move = get_next_move_distributed(root, cluster_size - 1, comm)

            board = board.drop_token(next_move, TokenEnum.YELLOW)

            with open("board.pickle", "wb") as f:
                pickle.dump(board, f)

            print(board)
            print(board.who_won())
        else:
            while True:
                message = comm.sendrecv(Request(), source=0, dest=0, sendtag=2, recvtag=1)

                if isinstance(message, Shutdown):
                    return

                root = Node(message)
                root = build_tree(root, 5)
                root = calculate_tree_weight(root)

                weight = root.value.weight

                comm.send(weight, 0, tag=1)


if __name__ == '__main__':
    main()
