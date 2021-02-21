def is_pm(ctx):
  # print(ctx.message.channel.type)
  if str(ctx.message.channel.type) == "private":
    # await ctx.reply(embed=embed(title="This command does not work in non-server text channels"),mention_author=False)
    return True
  else:
    return False