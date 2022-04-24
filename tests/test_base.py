from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from loam.base import Entry, Section


class MyMut:
    def __init__(self, inner_list):
        self.inner_list = inner_list

    @staticmethod
    def from_str(s: str) -> MyMut:
        return MyMut(list(map(float, s.split(","))))


def test_with_val():
    @dataclass
    class MySection(Section):
        some_n: int = Entry().with_val(42)

    sec = MySection()
    assert sec.some_n == 42


def test_set_from_str_type_hint():
    @dataclass
    class MySection(Section):
        some_n: int = 5
        some_str: str = "foo"
    sec = MySection()
    assert sec.some_n == 5
    assert sec.some_str == "foo"
    sec.set_from_str("some_n", "42")
    assert sec.some_n == 42
    sec.set_from_str("some_str", "bar")
    assert sec.some_str == "bar"


def test_with_str_mutable_protected():
    @dataclass
    class MySection(Section):
        outdir: Path = Entry(from_str=Path, to_str=str).with_str(".")
        some_mut: MyMut = Entry(from_str=MyMut.from_str).with_str("4.5,3.8")

    MySection().some_mut.inner_list.append(5.6)
    assert MySection().some_mut.inner_list == [4.5, 3.8]
