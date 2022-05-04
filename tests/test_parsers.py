import pytest
from loam import parsers


def test_slice_or_int_parser():
    assert parsers.slice_or_int_parser(28) == 28
    assert parsers.slice_or_int_parser(slice(2, 28, 5)) == slice(2, 28, 5)
    assert parsers.slice_or_int_parser("42") == 42
    assert parsers.slice_or_int_parser(":3") == slice(3)
    assert parsers.slice_or_int_parser("1:3") == slice(1, 3)
    assert parsers.slice_or_int_parser("1:") == slice(1, None)
    assert parsers.slice_or_int_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.slice_or_int_parser("::5") == slice(None, None, 5)
    with pytest.raises(ValueError):
        parsers.slice_or_int_parser("1:2:3:4")
    with pytest.raises(TypeError):
        parsers.slice_or_int_parser(object())


def test_strict_slice_parser():
    with pytest.raises(ValueError):
        parsers.strict_slice_parser(28)
    assert parsers.strict_slice_parser(slice(2, 28, 5)) == slice(2, 28, 5)
    with pytest.raises(ValueError):
        parsers.strict_slice_parser("42")
    assert parsers.strict_slice_parser(":3") == slice(3)
    assert parsers.strict_slice_parser("1:3") == slice(1, 3)
    assert parsers.strict_slice_parser("1:") == slice(1, None)
    assert parsers.strict_slice_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.strict_slice_parser("::5") == slice(None, None, 5)
    with pytest.raises(TypeError):
        parsers.strict_slice_parser(object())


def test_slice_parser():
    assert parsers.slice_parser(28) == slice(28)
    assert parsers.slice_parser(slice(2, 28, 5)) == slice(2, 28, 5)
    assert parsers.slice_parser("42") == slice(42)
    assert parsers.slice_parser(":3") == slice(3)
    assert parsers.slice_parser("1:3") == slice(1, 3)
    assert parsers.slice_parser("1:") == slice(1, None)
    assert parsers.slice_parser("23:54:2") == slice(23, 54, 2)
    assert parsers.slice_parser("::5") == slice(None, None, 5)
    with pytest.raises(TypeError):
        parsers.slice_parser(object())
