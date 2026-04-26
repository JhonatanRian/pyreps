import timeit

def with_modulo(n, chunk_size):
    count = 0
    for i in range(1, n + 1):
        if i % chunk_size == 0:
            count += 1
    return count

def with_countdown(n, chunk_size):
    count = 0
    countdown = chunk_size
    for i in range(1, n + 1):
        countdown -= 1
        if not countdown:
            countdown = chunk_size
            count += 1
    return count

n = 10_000_000
chunk_size = 1000

t1 = timeit.timeit(lambda: with_modulo(n, chunk_size), number=1)
t2 = timeit.timeit(lambda: with_countdown(n, chunk_size), number=1)

print(f"Modulo: {t1:.4f}s")
print(f"Countdown: {t2:.4f}s")
print(f"Difference: {(t1/t2 - 1)*100:.2f}%")
