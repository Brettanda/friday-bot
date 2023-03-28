from __future__ import annotations

import re
import textwrap
from typing import Callable, Iterable, Literal, Optional, TypeVar, overload

import numpy as np
from discord.app_commands import Choice
from fuzzywuzzy import fuzz

T = TypeVar('T')


def autocomplete(arr: list[Choice], value: str | float | int) -> list[Choice]:
  """Return a list of choices that are at least 90% similar to current."""
  if not value:
    # If the value is empty, return the original list
    return arr[:25]

  # Create a list of tuples with the choices and their fuzzy match score
  choices_with_score = [(choice, fuzz.token_set_ratio(value, textwrap.shorten(choice.value, width=100))) for choice in arr]
  # Sort the list by descending score
  choices_with_score.sort(key=lambda x: x[1], reverse=True)
  # Get the top 25 choices (or less if there are less than 25)
  top_choices = [choice for choice, score in choices_with_score[:25]]

  return top_choices


def levenshtein_ratio_and_distance(first: str, second: str, ratio_calc: bool = False) -> float:
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

  new_row = 0
  new_col = 0

  # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions
  for col in range(1, cols):
    new_col = col
    for row in range(1, rows):
      new_row = row
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
    Ratio = ((len(first) + len(second)) - distance[new_row][new_col]) / (len(first) + len(second))
    return Ratio
  else:
    return distance[new_row][new_col]


def levenshtein_string_list(string: str, arr: list[str], *, min_: float = 0.7) -> list[tuple[float, str]]:
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


@overload
def finder(
    text: str,
    collection: Iterable[T],
    *,
    key: Optional[Callable[[T], str]] = ...,
    raw: Literal[True],
) -> list[tuple[int, int, T]]:
  ...


@overload
def finder(
    text: str,
    collection: Iterable[T],
    *,
    key: Optional[Callable[[T], str]] = ...,
    raw: Literal[False],
) -> list[T]:
  ...


@overload
def finder(
    text: str,
    collection: Iterable[T],
    *,
    key: Optional[Callable[[T], str]] = ...,
    raw: bool = ...,
) -> list[T]:
  ...


def finder(
    text: str,
    collection: Iterable[T],
    *,
    key: Optional[Callable[[T], str]] = None,
    raw: bool = False,
) -> list[tuple[int, int, T]] | list[T]:
  suggestions: list[tuple[int, int, T]] = []
  text = str(text)
  pat = '.*?'.join(map(re.escape, text))
  regex = re.compile(pat, flags=re.IGNORECASE)
  for item in collection:
    to_search = key(item) if key else str(item)
    r = regex.search(to_search)
    if r:
      suggestions.append((len(r.group()), r.start(), item))

  def sort_key(tup: tuple[int, int, T]) -> tuple[int, int, str | T]:
    if key:
      return tup[0], tup[1], key(tup[2])
    return tup

  if raw:
    return sorted(suggestions, key=sort_key)
  else:
    return [z for _, _, z in sorted(suggestions, key=sort_key)]
