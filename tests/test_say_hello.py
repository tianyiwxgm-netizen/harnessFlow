"""Acceptance test for examples/hello/ — used by the /harnessFlow E2E walkthrough.

Run via: pytest tests/test_say_hello.py -v
"""

from examples.hello import say_hello


def test_say_hello_returns_expected_string():
    assert say_hello() == "hello, harnessflow"


def test_say_hello_is_callable_idempotent():
    assert say_hello() == say_hello()
