from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
import toml

from loam.base import entry, Section, ConfigBase


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
        some_n: int = entry(val=42)

    sec = MySection()
    assert sec.some_n == 42


def test_two_vals_fail():
    with pytest.raises(ValueError):
        entry(val=5, val_factory=lambda: 5)


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
        some_mut: MyMut = entry(val_str="4.5,3.8", from_str=MyMut.from_str)

    MySection().some_mut.inner_list.append(5.6)
    assert MySection().some_mut.inner_list == [4.5, 3.8]


def test_type_hint_not_a_class():
    @dataclass
    class MySection(Section):
        maybe_n: Optional[int] = entry(val_factory=lambda: None, from_str=int)
    assert MySection().maybe_n is None
    assert MySection("42").maybe_n == 42


def test_with_str_no_from_str():
    with pytest.raises(ValueError):
        entry(val_str="5")


def test_init_wrong_type():
    @dataclass
    class MySection(Section):
        some_n: int = 42
    with pytest.raises(TypeError):
        MySection(42.0)


def test_missing_from_str():
    @dataclass
    class MySection(Section):
        my_mut: MyMut = entry(val_factory=lambda: MyMut([4.5]))
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
    content = toml_file.read_text()
    assert "ignored" not in content
    assert "section_not_in_file" not in content


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
    class MyConfig(ConfigBase):
        dummy: int = 5
    with pytest.raises(TypeError):
        MyConfig.default_()


def test_update_opt(conf):
    conf.sectionA.update_from_dict_({'optA': 42, 'optC': 43})
    assert conf.sectionA.optA == 42 and conf.sectionA.optC == 43


def test_update_section(conf):
    conf.update_from_dict_(
        {'sectionA': {'optA': 42}, 'sectionB': {'optA': 43}})
    assert conf.sectionA.optA == 42 and conf.sectionB.optA == 43
