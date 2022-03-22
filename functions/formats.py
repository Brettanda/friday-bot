class plural:
  def __init__(self, value):
    self.value = value

  def __format__(self, format_spec):
    v = self.value
    singular, sep, plural = format_spec.partition('|')
    plural = plural or f'{singular}s'
    if abs(v) != 1:
      return f'{v} {plural}'
    return f'{v} {singular}'


def human_join(seq, delim=', ', final='or'):
  size = len(seq)
  if size == 0:
    return ''

  if size == 1:
    return seq[0]

  if size == 2:
    return f'{seq[0]} {final} {seq[1]}'

  return delim.join(seq[:-1]) + f' {final} {seq[-1]}'
