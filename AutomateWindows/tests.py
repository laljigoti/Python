import psutil
p = psutil.Process()
with p.oneshot():
    print(p.name())  # execute internal routine once collecting multiple info
    p.cpu_times()  # return cached value
    p.cpu_percent()  # return cached value
    p.create_time()  # return cached value
    p.ppid()  # return cached value
    p.status()  # return cached value