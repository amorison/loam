from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
import toml

from loam.base import Entry, Section, Config


class MyMut:
    def __init__(self, inner_list):
        if not isinstance(inner_list, list):
            raise TypeError
        self.inner_list = inner_list

    @staticmethod
    def from_str(s: str) -> MyMut:
        return MyMut(list(map(float, s.split(","))))


def test_with_val():
    @dataclass
    class MySection(Section):
        some_n: int = Entry(val=42).field()

    sec = MySection()
    assert sec.some_n == 42


def test_two_vals_fail():
    with pytest.raises(ValueError):
        Entry(val=5, val_factory=lambda: 5).field()


def test_set_from_str_type_hint(section_a):
    assert section_a.some_n == 42
    assert section_a.some_str == "foo"
    section_a.set_from_str_("some_n", "5")
    assert section_a.some_n == 5
    section_a.set_from_str_("some_str", "bar")
    assert section_a.some_str == "bar"


def test_context(section_a):
    with section_a.context_(some_n=5, some_str="bar"):
        assert section_a.some_n == 5
        assert section_a.some_str == "bar"
    assert section_a.some_n == 42
    assert section_a.some_str == "foo"


def test_context_from_str(section_b):
    with section_b.context_(some_path="my/path"):
        assert section_b.some_path == Path("my/path")
    assert section_b.some_path == Path()


def test_with_str_mutable_protected():
    @dataclass
    class MySection(Section):
        some_mut: MyMut = Entry(
            val_str="4.5,3.8", from_str=MyMut.from_str).field()

    MySection().some_mut.inner_list.append(5.6)
    assert MySection().some_mut.inner_list == [4.5, 3.8]


def test_type_hint_not_a_class():
    @dataclass
    class MySection(Section):
        maybe_n: Optional[int] = Entry(
            val_factory=lambda: None, from_str=int).field()
    assert MySection().maybe_n is None
    assert MySection("42").maybe_n == 42


def test_with_str_no_from_str():
    with pytest.raises(ValueError):
        Entry(val_str="5").field()


def test_init_wrong_type():
    @dataclass
    class MySection(Section):
        some_n: int = 42
    with pytest.raises(TypeError):
        MySection(42.0)


def test_missing_from_str():
    @dataclass
    class MySection(Section):
        my_mut: MyMut = Entry(val_factory=lambda: MyMut([4.5])).field()
    sec = MySection()
    assert sec.my_mut.inner_list == [4.5]
    with pytest.raises(ValueError):
        sec.set_from_str_("my_mut", "4.5,3.8")


def test_config_default(my_config):
    assert my_config.section_a.some_n == 42
    assert my_config.section_b.some_path == Path()
    assert my_config.section_a.some_str == "foo"
    assert my_config.section_b.some_str == "bar"


def test_to_from_toml(my_config, tmp_path):
    toml_file = tmp_path / "conf.toml"
    my_config.section_a.some_n = 5
    my_config.section_b.some_path = Path("foo/bar")
    my_config.to_file_(toml_file)
    new_config = my_config.default_()
    new_config.update_from_file_(toml_file)
    assert my_config == new_config


def test_to_toml_not_in_file(my_config, tmp_path):
    toml_file = tmp_path / "conf.toml"
    my_config.section_b.some_str = "ignored"
    my_config.to_file_(toml_file)
    assert "ignored" not in toml_file.read_text()


def test_from_toml_not_in_file(my_config, tmp_path):
    toml_file = tmp_path / "conf.toml"
    with toml_file.open("w") as tf:
        toml.dump({"section_b": {"some_str": "ignored"}}, tf)
    my_config.default_().update_from_file_(toml_file)
    assert my_config.section_b.some_str == "bar"


def test_to_file_exist_ok(my_config, tmp_path):
    toml_file = tmp_path / "conf.toml"
    my_config.to_file_(toml_file)
    with pytest.raises(RuntimeError):
        my_config.to_file_(toml_file, exist_ok=False)
    my_config.to_file_(toml_file)


def test_config_with_not_section():
    @dataclass
    class MyConfig(Config):
        dummy: int = 5
    with pytest.raises(TypeError):
        MyConfig.default_()
