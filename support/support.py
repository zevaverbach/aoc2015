from __future__ import annotations

import argparse
import contextlib
import enum
import os
import os.path
import pathlib as pl
import re
import sys
import time
from typing import Generator, Self

from dotenv import load_dotenv
import requests

load_dotenv()

COOKIE_HEADERS = {'Cookie': os.environ['ADVENT_OF_CODE_COOKIE']}

HERE = os.path.dirname(os.path.abspath(__file__))


@contextlib.contextmanager
def timing(name: str = '') -> Generator[None, None, None]:
    before = time.time()
    try:
        yield
    finally:
        after = time.time()
        t = (after - before) * 1000
        unit = 'ms'
        if t < 100:
            t *= 1000
            unit = 'μs'
        if name:
            name = f' ({name})'
        print(f'> {int(t)} {unit}{name}', file=sys.stderr, flush=True)


def get_input(year: int, day: int) -> str:
    url = f'https://adventofcode.com/{year}/day/{day}/input'
    res = requests.get(url, headers=COOKIE_HEADERS)
    if not res.ok:
        print(f'problem getting the test input: "{res.text}"')
        sys.exit()
    return res.text


def download_problem(year, day):
    problem = get_problem(year, day)
    module = pl.Path('part1.py')
    module_text = module.read_text()
    if module_text.strip().startswith('''"""'''):
        module_text = module_text.split('"""')[-1].split('"""')[-1]
    module_text = f'"""\n{problem}\n"""'
    module.write_text(module_text)



def get_problem(year: int, day: int) -> str:
    url = f'https://adventofcode.com/{year}/day/{day}'
    res = requests.get(url, headers=COOKIE_HEADERS)
    if not res.ok:
        print(f'problem getting the problem: "{res.text}"')
        sys.exit()
    return "---" + res.text.split('---', maxsplit=1)[0].split("To begin, ")[0]


def get_year_day() -> tuple[int, int]:
    cwd = os.getcwd()
    day_s = os.path.basename(cwd)
    year_s = os.path.basename(os.path.dirname(cwd))

    if not day_s.startswith('day') or not year_s.startswith('aoc'):
        raise AssertionError(f'unexpected working dir: {cwd}')

    return int(year_s[len('aoc'):]), int(day_s[len('day'):])


def download_challenge() -> int:
    year, day = get_year_day()
    download_input(year, day)
    download_problem(year, day)
    return 0


def download_input(year, day) -> None:
    if day == 0:
        print("days are one-indexed, so day00 is invalid")
        sys.exit()

    s = get_input(year, day)

    with open('input.txt', 'w') as f:
        f.write(s)

    lines = s.splitlines()
    if len(lines) > 10:
        for line in lines[:10]:
            print(line)
        print('...')
    else:
        print(lines[0][:80])
        print('...')


TOO_QUICK = re.compile('You gave an answer too recently.*to wait.')
WRONG = re.compile(r"That's not the right answer.*?\.")
RIGHT = "That's the right answer!"
ALREADY_DONE = re.compile(r"You don't seem to be solving.*\?")


def _post_answer(year: int, day: int, part: int, answer: int) -> str:
    return requests.post(
        f'https://adventofcode.com/{year}/day/{day}/answer',
        data={'level': part, 'answer': answer},
        headers=COOKIE_HEADERS,
    ).text


def submit_solution() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--part', type=int, required=True)
    args = parser.parse_args()

    year, day = get_year_day()
    answer = int(sys.stdin.read())

    print(f'answer: {answer}')

    contents = _post_answer(year, day, args.part, answer)

    for error_regex in (WRONG, TOO_QUICK, ALREADY_DONE):
        error_match = error_regex.search(contents)
        if error_match:
            print(f'\033[41m{error_match[0]}\033[m')
            return 1

    if RIGHT in contents:
        print(f'\033[42m{RIGHT}\033[m')
        return 0
    else:
        # unexpected output?
        print(contents)
        return 1


def submit_25_pt2() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()

    year, day = get_year_day()

    assert day == 25, day
    contents = _post_answer(year, day, part=2, answer=0)

    if 'Congratulations!' in contents:
        print('\033[42mCongratulations!\033[m')
        return 0
    else:
        print(contents)
        return 1


def adjacent_4(x: int, y: int) -> Generator[tuple[int, int], None, None]:
    yield x, y - 1
    yield x + 1, y
    yield x, y + 1
    yield x - 1, y


def adjacent_8(x: int, y: int) -> Generator[tuple[int, int], None, None]:
    for y_d in (-1, 0, 1):
        for x_d in (-1, 0, 1):
            if y_d == x_d == 0:
                continue
            yield x + x_d, y + y_d


def parse_coords_int(s: str) -> dict[tuple[int, int], int]:
    coords = {}
    for y, line in enumerate(s.splitlines()):
        for x, c in enumerate(line):
            coords[(x, y)] = int(c)
    return coords


def parse_coords_hash(s: str) -> set[tuple[int, int]]:
    coords = set()
    for y, line in enumerate(s.splitlines()):
        for x, c in enumerate(line):
            if c == '#':
                coords.add((x, y))
    return coords


def parse_numbers_split(s: str) -> list[int]:
    return [int(x) for x in s.split()]


def parse_numbers_comma(s: str) -> list[int]:
    return [int(x) for x in s.strip().split(',')]


def format_coords_hash(coords: set[tuple[int, int]]) -> str:
    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    return '\n'.join(
        ''.join(
            '#' if (x, y) in coords else ' '
            for x in range(min_x, max_x + 1)
        )
        for y in range(min_y, max_y + 1)
    )


def print_coords_hash(coords: set[tuple[int, int]]) -> None:
    print(format_coords_hash(coords))


class Direction4(enum.Enum):
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)

    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    @property
    def _vals(self) -> tuple[Self, ...]:
        return tuple(type(self).__members__.values())

    @property
    def cw(self) -> Self:
        vals = self._vals
        return vals[(vals.index(self) + 1) % len(vals)]

    @property
    def ccw(self) -> Self:
        vals = self._vals
        return vals[(vals.index(self) - 1) % len(vals)]

    @property
    def opposite(self) -> Self:
        vals = self._vals
        return vals[(vals.index(self) + 2) % len(vals)]

    def apply(self, x: int, y: int, *, n: int = 1) -> tuple[int, int]:
        return self.x * n + x, self.y * n + y
