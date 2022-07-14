from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cogs.chat import ChatHistory

if TYPE_CHECKING:
  ...

pytestmark = pytest.mark.asyncio


async def test_chat_history(event_loop):
  history = ChatHistory(loop=event_loop)

  assert len(history) == 0
  assert str(history) == ""
  assert history.__repr__() == "<Chathistory len=0>"
  assert history.bot_repeating() is False
  assert len(history.history()) == 0

  assert history.banned_nickname("nig ge r") == "Cat"
  assert history.banned_nickname("nigger") == "Cat"
  assert history.banned_nickname("niger") == "Cat"
  assert history.banned_nickname("steve") == "steve"
  assert history.banned_nickname("asd") == "asd"

  class msg:
    clean_content = "hey there"

    class author:
      display_name = "Motostar"

    class guild:
      class me:
        display_name = "Friday"

  response = "This is a test"
  actual_prompt = await history.prompt(msg.clean_content, msg.author.display_name)
  expected_prompt = f"{msg.author.display_name}: {msg.clean_content}\n{msg.guild.me.display_name}:"

  assert actual_prompt == expected_prompt

  assert len(history) == 0
  assert str(history) == ""
  assert history.__repr__() == "<Chathistory len=0>"
  assert history.bot_repeating() is False
  assert len(history.history()) == 0

  assert history.banned_nickname("nig ge r") == "Cat"
  assert history.banned_nickname("nigger") == "Cat"
  assert history.banned_nickname("niger") == "Cat"
  assert history.banned_nickname("steve") == "steve"
  assert history.banned_nickname("asd") == "asd"

  await history.add_message(msg, response)  # type: ignore
  expected_prompt_response = f"{msg.author.display_name}: {msg.clean_content}\n{msg.guild.me.display_name}: {response}"
  assert len(history) == len(expected_prompt_response)
  assert str(history) == expected_prompt_response
  assert history.__repr__() == "<Chathistory len=2>"
  assert history.bot_repeating() is False
  assert len(history.history()) == 2

  assert history.banned_nickname("nig ge r") == "Cat"
  assert history.banned_nickname("nigger") == "Cat"
  assert history.banned_nickname("niger") == "Cat"
  assert history.banned_nickname("steve") == "steve"
  assert history.banned_nickname("asd") == "asd"

  await history.add_message(msg, response)  # type: ignore
  assert history.bot_repeating() is True
