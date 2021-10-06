import pytest


@pytest.mark.asyncio
async def test_prefix(bot, channel):
  await channel.send("!prefix ?")

  f_msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)

  await channel.send("?prefix !")
  l_msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert f_msg.embeds[0].title == "My new prefix is `?`" and l_msg.embeds[0].title == "My new prefix is `!`"


class TestBlacklist:
  @pytest.mark.asyncio
  async def test_add(self, bot, channel):
    await channel.send("!blacklist add word")

    msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.asyncio
  async def test_remove(self, bot, channel):
    await channel.send("!blacklist remove word")

    def say_check(m) -> bool:
      return m.channel.id == channel.id and m.author.id == 751680714948214855

    msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed `word` from the blacklist" or msg.embeds[0].title == "You don't seem to be blacklisting that word"

  @pytest.mark.asyncio
  async def test_display(self, bot, channel):
    await channel.send("!blacklist display")

    msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.asyncio
  async def test_clear(self, bot, channel):
    await channel.send("!blacklist clear")

    msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed all blacklisted words"
