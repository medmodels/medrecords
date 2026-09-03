import math
import unittest
from datetime import datetime, timedelta, timezone

import pytest
from graphrecords import QueryError

from medrecords.evaluation.results import read, read_each, read_pairs


class TestRead(unittest.TestCase):
    def test_read(self) -> None:
        moment = datetime(2026, 9, 3, tzinfo=timezone.utc)
        truth = True

        assert read(1) == 1
        assert read("lorem") == "lorem"
        assert read(None) is None
        assert read(3, int) == 3
        assert read("sit", str) == "sit"
        assert read(truth, bool) is True
        assert read(moment, datetime) == moment
        assert read(timedelta(days=2), timedelta) == timedelta(days=2)
        assert math.isclose(read(1.5, float), 1.5)
        assert math.isclose(read(3, float), 3.0)

    def test_invalid_read(self) -> None:
        truth = True

        with pytest.raises(QueryError, match="lorem"):
            read(QueryError("lorem"))

        with pytest.raises(QueryError, match="lorem"):
            read(QueryError("lorem"), int)

        with pytest.raises(TypeError, match=r"expected int, got 1\.5"):
            read(1.5, int)

        with pytest.raises(TypeError, match="expected int, got True"):
            read(truth, int)

        with pytest.raises(TypeError, match="expected float, got True"):
            read(truth, float)

        with pytest.raises(TypeError, match="expected float, got 'sit'"):
            read("sit", float)

        with pytest.raises(TypeError, match="expected timedelta, got 2"):
            read(2, timedelta)


class TestReadEach(unittest.TestCase):
    def test_read_each(self) -> None:
        assert read_each([1, "sit", None]) == [1, "sit", None]
        assert read_each([]) == []
        assert read_each([1, 2], int) == [1, 2]
        assert read_each([1, 2.5], float) == [1.0, 2.5]

    def test_invalid_read_each(self) -> None:
        with pytest.raises(QueryError, match="lorem"):
            read_each([1, QueryError("lorem")])

        with pytest.raises(TypeError, match="expected int, got 'sit'"):
            read_each([1, "sit"], int)


class TestReadPairs(unittest.TestCase):
    def test_read_pairs(self) -> None:
        assert read_pairs([("amet", 1), ("sit", None)]) == [("amet", 1), ("sit", None)]
        assert read_pairs([("amet", 1), ("sit", 2)], int) == [("amet", 1), ("sit", 2)]

    def test_invalid_read_pairs(self) -> None:
        with pytest.raises(QueryError, match="lorem"):
            read_pairs([("amet", 1), ("sit", QueryError("lorem"))])

        with pytest.raises(TypeError, match="expected int, got 'dolor'"):
            read_pairs([("amet", "dolor")], int)


if __name__ == "__main__":
    unittest.main()
