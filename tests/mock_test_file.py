"""
Mock test file for verifying git hooks.
This file tests that the post-commit hook triggers indexing.
"""


def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    return all(n % i != 0 for i in range(2, int(n**0.5) + 1))


class MockDataProcessor:
    """A mock data processor for testing."""

    def __init__(self, data: list):
        self.data = data

    def process(self) -> list:
        """Process the data."""
        return [x * 2 for x in self.data]

    def filter_primes(self) -> list:
        """Filter only prime numbers."""
        return [x for x in self.data if is_prime(x)]
