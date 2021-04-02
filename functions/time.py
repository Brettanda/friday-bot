# import asyncio
# import time
import cProfile
import pstats
import io


def timeit(func):
  async def helper(*args, **kwargs):
    pr = cProfile.Profile()
    print('{}.time'.format(func.__name__))
    pr.enable()
    result = await func(*args, **kwargs)
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())

    return result

  return helper
