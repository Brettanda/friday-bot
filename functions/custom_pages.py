import asyncio
import discord
from discord.ext import commands
from discord.ext.menus import MenuPages
from discord_slash import SlashContext, manage_components, ButtonStyle, ComponentContext


class Menu(MenuPages):
  def __init__(self, source, extra_rows=dict(), **kwargs):
    self.extra_rows = extra_rows
    self.button_ids = ["help-first", "help-back", "help-next", "help-last", "help-stop"]
    super().__init__(source, **kwargs)

  def get_action_rows(self, *, first_disabled=False, back_disabled=False, next_disabled=False, last_disabled=False, stop_disabled=False) -> dict:
    buttons = [
        manage_components.create_button(
            style=ButtonStyle.primary,
            disabled=first_disabled,
            custom_id=self.button_ids[0],
            label="⏮"
        ),
        manage_components.create_button(
            style=ButtonStyle.primary,
            disabled=back_disabled,
            custom_id=self.button_ids[1],
            label="◀"
        ),
        manage_components.create_button(
            style=ButtonStyle.primary,
            disabled=next_disabled,
            custom_id=self.button_ids[2],
            label="▶"
        ),
        manage_components.create_button(
            style=ButtonStyle.primary,
            disabled=last_disabled,
            custom_id=self.button_ids[3],
            label="⏭"
        ),
        manage_components.create_button(
            style=ButtonStyle.danger,
            disabled=stop_disabled,
            custom_id=self.button_ids[4],
            label="⛔"
        )
    ]
    return manage_components.create_actionrow(*buttons)

  async def send_initial_message(self, ctx: commands.Context or SlashContext, channel: discord.TextChannel):
    page = await self._source.get_page(0)
    kwargs = await self._get_kwargs_from_page(page)
    if isinstance(ctx, SlashContext):
      return await ctx.send(**kwargs, components=[self.get_action_rows(first_disabled=True, back_disabled=True), *self.extra_rows])
    return await ctx.reply(**kwargs, components=[self.get_action_rows(first_disabled=True, back_disabled=True), *self.extra_rows])

  def component_check(self, payload: ComponentContext) -> bool:
    if payload.origin_message_id != self.message.id:
      return False
    if payload.author_id not in {self.bot.owner_id, self._author_id, *self.bot.owner_ids}:
      return False
    return payload.custom_id in self.button_ids

  async def _internal_loop(self):
    try:
      self.__timed_out = False
      loop = self.bot.loop
      tasks = []
      while self._running:
        tasks = [
            asyncio.ensure_future(manage_components.wait_for_component(self.bot, components=self.get_action_rows(), check=self.component_check))
        ]
        done, pending = await asyncio.wait(tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
          task.cancel()
        if len(done) == 0:
          raise asyncio.TimeoutError()

        payload = done.pop().result()
        loop.create_task(self.update(payload))
    except asyncio.TimeoutError:
      self.__timed_out = True
    finally:
      # self.__event.set()
      for task in tasks:
        task.cancel()
      try:
        await self.finalize(self.__timed_out)
      except Exception:
        pass
      finally:
        self.__timed_out = False
      if self.bot.is_closed():
        return
      try:
        if self.delete_message_after:
          return await self.message.delete()
        if self.clear_reactions_after:
          if self._can_remove_reactions:
            return await self.message.edit(components=[*self.extra_rows])
        #     return await self.message.clear_reactions()
          # for button_emoji in self.buttons:
          #   try:
          #     await self.message.remove_reaction(button_emoji, self.__me)
          #   except discord.HTTPException:
          #     continue
      except Exception:
        pass

  async def update(self, payload: ComponentContext):
    if not self._running:
      return

    try:
      await self.on_component(payload)
    except Exception as exc:
      self.bot.logger.exception(exc)
      # await self.on_menu_button_error(exc)

  async def show_page(self, page_number):
    page = await self._source.get_page(page_number)
    self.current_page = page_number
    kwargs = await self._get_kwargs_from_page(page)
    if page_number == 0:
      kwargs.update(components=[self.get_action_rows(first_disabled=True, back_disabled=True), *self.extra_rows])
    elif page_number == self._source.get_max_pages() - 1:
      kwargs.update(components=[self.get_action_rows(last_disabled=True, next_disabled=True), *self.extra_rows])
    else:
      kwargs.update(components=[self.get_action_rows(), *self.extra_rows])
    await self.message.edit(**kwargs)

  async def on_component(self, ctx: ComponentContext):
    await ctx.defer(edit_origin=True)
    if ctx.custom_id == "help-first":
      await self.show_page(0)
    elif ctx.custom_id == "help-back":
      await self.show_checked_page(self.current_page - 1)
    elif ctx.custom_id == "help-next":
      await self.show_checked_page(self.current_page + 1)
    elif ctx.custom_id == "help-last":
      await self.show_page(self._source.get_max_pages() - 1)
    elif ctx.custom_id == "help-stop":
      self.stop()

  async def start(self, ctx: commands.Context, *, channel: discord.TextChannel = None, wait: bool = False):
    try:
      del self.buttons
    except AttributeError:
      pass

    self.bot = bot = ctx.bot
    self.ctx = ctx
    self._author_id = ctx.author.id
    channel = channel or ctx.channel
    is_guild = isinstance(channel, discord.abc.GuildChannel)
    me = channel.guild.me if is_guild else ctx.bot.user
    permissions = channel.permissions_for(me)
    self.__me = discord.Object(id=me.id)
    self._verify_permissions(ctx, channel, permissions)
    self._event.clear()
    msg = self.message
    if msg is None:
      self.message = msg = await self.send_initial_message(ctx, channel)

    if self.should_add_reactions():
      for task in self.__tasks:
        task.cancel()
      self.__tasks.clear()
      self._running = True
      self.__tasks.append(bot.loop.create_task(self._internal_loop()))
      if wait:
        await self._event.wait()

  def stop(self):
    self._running = False
    for task in self.__tasks:
      task.cancel()
    self.__tasks.clear()
