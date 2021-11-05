import asyncio
import nextcord as discord
from nextcord.ext import commands
from nextcord.ext.menus import MenuPages
from . import views


class Menu(MenuPages):
  def __init__(self, source, extra_items=[], **kwargs):
    self.extra_items = extra_items
    self.button_ids = ["help-first", "help-back", "help-next", "help-last", "help-stop"]
    self.interaction = None
    super().__init__(source, **kwargs)

  class PaginationButtons(discord.ui.View):
    def __init__(self, *, extra=[], first_disabled=False, back_disabled=False, next_disabled=False, last_disabled=False, stop_disabled=False):
      self.first_disabled, self.back_disabled, self.next_disabled, self.last_disabled, self.stop_disabled, = first_disabled, back_disabled, next_disabled, last_disabled, stop_disabled
      super().__init__()
      for item in extra:
        self.add_item(item)
      self.add_item(discord.ui.Button(emoji="⏮", disabled=first_disabled, style=discord.ButtonStyle.primary, custom_id="help-first"))
      self.add_item(discord.ui.Button(emoji="◀", disabled=back_disabled, style=discord.ButtonStyle.primary, custom_id="help-back"))
      self.add_item(discord.ui.Button(emoji="▶", disabled=next_disabled, style=discord.ButtonStyle.primary, custom_id="help-next"))
      self.add_item(discord.ui.Button(emoji="⏭", disabled=last_disabled, style=discord.ButtonStyle.primary, custom_id="help-last"))
      self.add_item(discord.ui.Button(emoji="⛔", disabled=stop_disabled, style=discord.ButtonStyle.danger, custom_id="help-stop"))

  async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel):
    page = await self._source.get_page(0)
    kwargs = await self._get_kwargs_from_page(page)
    view = self.PaginationButtons(extra=views.Links().links, first_disabled=True, back_disabled=True)
    return await ctx.send(**kwargs, view=view)

  def component_check(self, payload: discord.Interaction) -> bool:
    if payload.message.id != self.message.id:
      return False
    if payload.user.id not in {self.bot.owner_id, self._author_id, *self.bot.owner_ids}:
      return False
    return payload.data["custom_id"] in self.button_ids

  async def _internal_loop(self):
    try:
      self.__timed_out = False
      loop = self.bot.loop
      tasks = []
      while self._running:
        interaction = await self.bot.wait_for("interaction", check=self.component_check, timeout=self.timeout)

        loop.create_task(self.update(interaction))
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
            return await self.message.edit(view=views.Links())
      except Exception:
        pass

  async def update(self, payload: discord.Interaction):
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
      kwargs.update(view=self.PaginationButtons(extra=views.Links().links, first_disabled=True, back_disabled=True))
    elif page_number == self._source.get_max_pages() - 1:
      kwargs.update(view=self.PaginationButtons(extra=views.Links().links, last_disabled=True, next_disabled=True))
    else:
      kwargs.update(view=self.PaginationButtons(extra=views.Links().links))
    if self.interaction:
      await self.interaction.edit_original_message(**kwargs)
    else:
      await self.message.edit(**kwargs)

  async def on_component(self, ctx: discord.Interaction):
    if not self.interaction:
      await ctx.response.defer()
    if ctx.data["custom_id"] == "help-first":
      await self.show_page(0)
    elif ctx.data["custom_id"] == "help-back":
      await self.show_checked_page(self.current_page - 1)
    elif ctx.data["custom_id"] == "help-next":
      await self.show_checked_page(self.current_page + 1)
    elif ctx.data["custom_id"] == "help-last":
      await self.show_page(self._source.get_max_pages() - 1)
    elif ctx.data["custom_id"] == "help-stop":
      self.stop()
    if not self.interaction:
      self.interaction = ctx

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
