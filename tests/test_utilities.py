import unittest
from unittest.mock import MagicMock

from src.utilities import timeit


class TestTimeitDecorator(unittest.TestCase):

    def test_timeit_returns_function_result(self):
        @timeit
        def add(a, b):
            return a + b

        result = add(2, 3)
        self.assertEqual(result, 5)

    def test_timeit_works_with_no_args(self):
        @timeit
        def get_constant():
            return 42

        result = get_constant()
        self.assertEqual(result, 42)

    def test_timeit_works_with_kwargs(self):
        @timeit
        def multiply(a, b=1):
            return a * b

        result = multiply(5, b=3)
        self.assertEqual(result, 15)

    def test_timeit_logs_to_dict_with_log_time(self):
        # The wrapped function must accept **kwargs for log_time to work
        @timeit
        def some_func(**kwargs):
            return 'done'

        log_dict = {}
        result = some_func(log_time=log_dict)
        self.assertEqual(result, 'done')
        # Default key is function name uppercased
        self.assertIn('SOME_FUNC', log_dict)
        self.assertIsInstance(log_dict['SOME_FUNC'], int)

    def test_timeit_logs_to_dict_with_custom_log_name(self):
        @timeit
        def another_func(**kwargs):
            return 'result'

        log_dict = {}
        result = another_func(log_time=log_dict, log_name='CUSTOM_KEY')
        self.assertEqual(result, 'result')
        self.assertIn('CUSTOM_KEY', log_dict)

    def test_timeit_timing_is_non_negative(self):
        @timeit
        def fast_func(**kwargs):
            return True

        log_dict = {}
        fast_func(log_time=log_dict)
        self.assertGreaterEqual(log_dict['FAST_FUNC'], 0)

    def test_timeit_prints_when_no_log_time(self):
        @timeit
        def printable_func():
            return 'printed'

        # Should print timing info (not raise)
        import io
        import sys
        captured = io.StringIO()
        sys.stdout = captured
        try:
            result = printable_func()
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(result, 'printed')
        output = captured.getvalue()
        self.assertIn('printable_func', output)

    def test_timeit_preserves_exceptions(self):
        @timeit
        def failing_func():
            raise ValueError("test error")

        with self.assertRaises(ValueError):
            failing_func()

    def test_timeit_returns_none_result(self):
        @timeit
        def returns_none():
            return None

        result = returns_none()
        self.assertIsNone(result)

    def test_timeit_wraps_function(self):
        @timeit
        def my_function():
            return 1

        # The wrapper function should be callable
        self.assertTrue(callable(my_function))


if __name__ == '__main__':
    unittest.main()
