import timeit
import itertools


def with_countdown(n, chunk_size):
    processed = 0
    countdown = chunk_size
    for i, row in enumerate(range(n), 1):
        countdown -= 1
        if not countdown:
            countdown = chunk_size
            processed = i
    return processed


def with_batched(n, chunk_size):
    processed = 0
    for chunk in itertools.batched(range(n), chunk_size):
        for row in chunk:
            pass
        processed += len(chunk)
    return processed


n = 10_000_000
chunk_size = 1000

t1 = timeit.timeit(lambda: with_countdown(n, chunk_size), number=1)
t2 = timeit.timeit(lambda: with_batched(n, chunk_size), number=1)

print(f"Countdown: {t1:.4f}s")
print(f"Batched: {t2:.4f}s")
print(f"Difference: {(t1 / t2 - 1) * 100:.2f}% faster")
