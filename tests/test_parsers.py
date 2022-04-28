import pytest
from loam import parsers


def test_slice_or_int_parser():
    assert parsers.slice_or_int_parser("42") == 42
    assert parsers.slice_or_int_parser(":3") == slice(3)
    assert parsers.slice_or_int_parser("1:3") == slice(1, 3)
    assert parsers.slice_or_int_parser("1:") == slice(1, None)
    assert parsers.slice_or_int_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.slice_or_int_parser("::5") == slice(None, None, 5)
    with pytest.raises(ValueError):
        parsers.slice_or_int_parser("1:2:3:4")


def test_strict_slice_parser():
    with pytest.raises(ValueError):
        assert parsers.strict_slice_parser("42") == 42
    assert parsers.strict_slice_parser(":3") == slice(3)
    assert parsers.strict_slice_parser("1:3") == slice(1, 3)
    assert parsers.strict_slice_parser("1:") == slice(1, None)
    assert parsers.strict_slice_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.strict_slice_parser("::5") == slice(None, None, 5)


def test_slice_parser():
    assert parsers.slice_parser("42") == slice(42)
    assert parsers.slice_parser(":3") == slice(3)
    assert parsers.slice_parser("1:3") == slice(1, 3)
    assert parsers.slice_parser("1:") == slice(1, None)
    assert parsers.slice_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.slice_parser("::5") == slice(None, None, 5)


def test_tuple_of():
    lfloat = parsers.tuple_of(float)
    assert lfloat("3.2,4.5,12.8") == (3.2, 4.5, 12.8)
    assert lfloat("42") == (42.,)
    assert lfloat("78e4, 12,") == (7.8e5, 12.)
    assert lfloat("") == tuple()
    lint = parsers.tuple_of(int, ";")
    assert lint("3;4") == (3, 4)
