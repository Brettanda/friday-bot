import numpy as np


def levenshtein_ratio_and_distance(first: str, second: str, ratio_calc=False) -> float:
  """ levenshtein_ratio_and_distance:
      Calculates levenshtein distance between two strings.
      If ratio_calc = True, the function computes the
      levenshtein distance ratio of similarity between two strings
      For all i and j, distance[i,j] will contain the Levenshtein
      distance between the first i characters of first and the
      first j characters of second
  """
  # Initialize matrix of zeros
  rows = len(first) + 1
  cols = len(second) + 1
  distance = np.zeros((rows, cols), dtype=int)

  # Populate matrix of zeros with the indeces of each character of both strings
  for i in range(1, rows):
    for k in range(1, cols):
      distance[i][0] = i
      distance[0][k] = k

  # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions
  for col in range(1, cols):
    for row in range(1, rows):
      if first[row - 1] == second[col - 1]:
        cost = 0  # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
      else:
        # the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
        if ratio_calc is True:
          cost = 2
        else:
          cost = 1
      distance[row][col] = min(distance[row - 1][col] + 1,      # Cost of deletions
                               distance[row][col - 1] + 1,          # Cost of insertions
                               distance[row - 1][col - 1] + cost)     # Cost of substitutions
  if ratio_calc is True:
    Ratio = ((len(first) + len(second)) - distance[row][col]) / (len(first) + len(second))  # type: ignore
    return Ratio
  else:
    return distance[row][col]  # type: ignore


def levenshtein_string_list(string: str, arr: list, *, min_: float = 0.7) -> list:
  """ Return an ordered list in numeric order of the strings in arr that are
  at least min_ percent similar to string."""
  return sorted(
      [
          (levenshtein_ratio_and_distance(string, arr[x]), i)
          for x, i in enumerate(arr)
          if levenshtein_ratio_and_distance(string, arr[x]) >= min_
      ],
      key=lambda x: x[0],
  )
