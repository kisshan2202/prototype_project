from referencer.ratelimit import RateLimiter


def test_blocks_after_limit_and_recovers():
    rl = RateLimiter(2, window_seconds=100)
    assert rl.allow("a", now=0) and rl.allow("a", now=1)
    assert not rl.allow("a", now=2)
    assert rl.allow("b", now=2)          # other visitors unaffected
    assert rl.allow("a", now=102)        # window passed


def test_zero_disables():
    rl = RateLimiter(0)
    assert all(rl.allow("a") for _ in range(100))
