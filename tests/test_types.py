import pytest
from loam import types


def test_slice_or_int_parser():
    assert types.slice_or_int_parser("42") == 42
    assert types.slice_or_int_parser(":3") == slice(3)
    assert types.slice_or_int_parser("1:3") == slice(1, 3)
    assert types.slice_or_int_parser("1:") == slice(1, None)
    assert types.slice_or_int_parser("23:54:2") == slice(23, 54, 2)
    assert types.slice_or_int_parser("::5") == slice(None, None, 5)
    with pytest.raises(ValueError):
        types.slice_or_int_parser("1:2:3:4")


def test_strict_slice_parser():
    with pytest.raises(ValueError):
        assert types.strict_slice_parser("42") == 42
    assert types.strict_slice_parser(":3") == slice(3)
    assert types.strict_slice_parser("1:3") == slice(1, 3)
    assert types.strict_slice_parser("1:") == slice(1, None)
    assert types.strict_slice_parser("23:54:2") == slice(23, 54, 2)
    assert types.strict_slice_parser("::5") == slice(None, None, 5)


def test_slice_parser():
    assert types.slice_parser("42") == slice(42)
    assert types.slice_parser(":3") == slice(3)
    assert types.slice_parser("1:3") == slice(1, 3)
    assert types.slice_parser("1:") == slice(1, None)
    assert types.slice_parser("23:54:2") == slice(23, 54, 2)
    assert types.slice_parser("::5") == slice(None, None, 5)


def test_list_of():
    lfloat = types.list_of(float)
    assert lfloat("3.2,4.5,12.8") == (3.2, 4.5, 12.8)
    assert lfloat("42") == (42.,)
    assert lfloat("78e4, 12,") == (7.8e5, 12.)
    assert lfloat("") == tuple()
    lint = types.list_of(int, ";")
    assert lint("3;4") == (3, 4)
