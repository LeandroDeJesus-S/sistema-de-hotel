import pytest
from exc import Error, Result


def test_result_ok():
    res = Result.Ok(10)
    assert res.is_ok()
    assert not res.is_err()
    assert res.unwrap() == 10


def test_result_err():
    res = Result.Err("Test error")
    assert not res.is_ok()
    assert res.is_err()
    with pytest.raises(Exception):
        res.unwrap()


def test_unwrap_or():
    res_ok = Result.Ok(10)
    res_err = Result.Err("Test error")
    assert res_ok.unwrap_or(20) == 10
    assert res_err.unwrap_or(20) == 20


def test_map():
    res_ok = Result.Ok(10)
    res_err = Result.Err("Test error")
    assert res_ok.map(lambda x: x * 2).unwrap() == 20
    assert res_err.map(lambda x: x * 2).is_err()


def test_map_err():
    res_ok = Result.Ok(10)
    res_err = Result.Err("Test error")
    assert res_ok.map_err(lambda x: f"New error: {x}").is_ok()
    assert res_err.map_err(lambda x: f"New error: {x.msg}").unwrap_err().msg == "New error: Test error"


def test_then():
    res_ok = Result.Ok(10)
    res_err = Result.Err("Test error")
    assert res_ok.then(lambda x: Result.Ok(x * 2)).unwrap() == 20
    assert res_err.then(lambda x: Result.Ok(x * 2)).is_err()


def test_match():
    res_ok = Result.Ok(10)
    res_err = Result.Err("Test error")
    assert res_ok.match(lambda x: x * 2, lambda x: 0) == 20
    assert res_err.match(lambda x: x * 2, lambda x: 0) == 0
