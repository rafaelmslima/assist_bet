from __future__ import annotations

import unittest

from app.services.cache_service import SimpleTTLCache


class CacheServiceTest(unittest.TestCase):
    def test_cache_hit_uses_existing_value(self) -> None:
        cache = SimpleTTLCache()
        calls = {"count": 0}

        def factory():
            calls["count"] += 1
            return {"ok": True}

        first = cache.get_or_set("key", 60, factory)
        second = cache.get_or_set("key", 60, factory)

        self.assertEqual(first, second)
        self.assertEqual(calls["count"], 1)
        self.assertEqual(cache.stats()["hits"], 1)

    def test_cache_expiration_calls_factory_again(self) -> None:
        cache = SimpleTTLCache()
        calls = {"count": 0}

        def factory():
            calls["count"] += 1
            return calls["count"]

        first = cache.get_or_set("key", 0, factory)
        second = cache.get_or_set("key", 0, factory)

        self.assertEqual(first, 1)
        self.assertEqual(second, 2)


if __name__ == "__main__":
    unittest.main()
