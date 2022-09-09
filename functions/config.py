from __future__ import annotations

import asyncio
import enum
import json
import os
import uuid
from typing import (Any, Callable, Dict, Generic, Optional, Type, TypeVar,
                    Union, overload)

import discord
from discord.ext import commands
from typing_extensions import Self

_T = TypeVar('_T')

ObjectHook = Callable[[Dict[str, Any]], Any]


class Config(Generic[_T]):
  """The "database" object. Internally based on ``json``."""

  def __init__(
      self,
      name: str,
      *,
      object_hook: Optional[ObjectHook] = None,
      encoder: Optional[Type[json.JSONEncoder]] = None,
      load_later: bool = False,
  ):
    self.name = name
    self.object_hook = object_hook
    self.encoder = encoder
    self.loop = asyncio.get_running_loop()
    self.lock = asyncio.Lock()
    self._db: Dict[str, Union[_T, Any]] = {}
    if load_later:
      self.loop.create_task(self.load())
    else:
      self.load_from_file()

  def load_from_file(self):
    try:
      with open(self.name) as f:
        self._db = json.load(f, object_hook=self.object_hook)
    except FileNotFoundError:
      self._db = {}

  async def load(self):
    async with self.lock:
      await self.loop.run_in_executor(None, self.load_from_file)

  def _dump(self):
    temp = f'{uuid.uuid4()}-{self.name}.tmp'
    with open(temp, 'w', encoding='utf-8') as tmp:
      json.dump(self._db.copy(), tmp, ensure_ascii=True, cls=self.encoder, separators=(',', ':'))

    # atomically move the file
    os.replace(temp, self.name)

  async def save(self) -> None:
    async with self.lock:
      await self.loop.run_in_executor(None, self._dump)

  @overload
  def get(self, key: Any) -> Optional[Union[_T, Any]]:
    ...

  @overload
  def get(self, key: Any, default: Any) -> Union[_T, Any]:
    ...

  def get(self, key: Any, default: Any = None) -> Optional[Union[_T, Any]]:
    """Retrieves a config entry."""
    return self._db.get(str(key), default)

  async def put(self, key: Any, value: Union[_T, Any]) -> None:
    """Edits a config entry."""
    self._db[str(key)] = value
    await self.save()

  async def remove(self, key: Any) -> None:
    """Removes a config entry."""
    del self._db[str(key)]
    await self.save()

  def __contains__(self, item: Any) -> bool:
    return str(item) in self._db

  def __getitem__(self, item: Any) -> Union[_T, Any]:
    return self._db[str(item)]

  def __len__(self) -> int:
    return len(self._db)

  def all(self) -> Dict[str, Union[_T, Any]]:
    return self._db


class ReadOnly(Generic[_T]):
  """The "database" object. Internally based on ``json``."""

  def __init__(
      self,
      name: str,
      *,
      object_hook: Optional[ObjectHook] = None,
      encoder: Optional[Type[json.JSONEncoder]] = None,
      load_later: bool = False,
  ):
    self.name = name
    self.object_hook = object_hook
    self.encoder = encoder
    self.loop = asyncio.get_running_loop()
    self.lock = asyncio.Lock()
    self._db: Dict[str, Union[_T, Any]] = {}
    if load_later:
      self.loop.create_task(self.load())
    else:
      self.load_from_file()

  def load_from_file(self):
    try:
      with open(self.name, 'r') as f:
        self._db = json.load(f, object_hook=self.object_hook)
    except FileNotFoundError:
      self._db = {}

  async def load(self):
    async with self.lock:
      await self.loop.run_in_executor(None, self.load_from_file)

  @overload
  def get(self, key: Any) -> Optional[Union[_T, Any]]:
    ...

  @overload
  def get(self, key: Any, default: Any) -> Union[_T, Any]:
    ...

  def get(self, key: Any, default: Any = None) -> Optional[Union[_T, Any]]:
    """Retrieves a config entry."""
    return self._db.get(str(key), default)

  def __contains__(self, item: Any) -> bool:
    return str(item) in self._db

  def __getitem__(self, item: Any) -> Union[_T, Any]:
    return self._db[str(item)]

  def __len__(self) -> int:
    return len(self._db)

  def all(self) -> Dict[str, Union[_T, Any]]:
    return self._db


defaultPrefix = "!"

description = "Hello, my name is Friday, I am a chatbot built with TensorFlow and Keras, meaning I enjoy conversations. I also have a few commands for fun and moderating your servers!"

support_server_id = 707441352367013899

support_server_invites = {
    "NTRuFjU": "General",
    "xfMZ8q9k3J": "On Patreon",
    "vqHBD3QCv2": "Top.gg",
    "paMxRvvZFc": "On join",
    "XP4avQ449V": "Website",
}


# all_support_ranks = [item for item in support_ranks]

patreon_supporting_role = 843941723041300480


class PremiumTiersNew(enum.Enum):
  free = 0
  voted = 1
  streaked = 1.5
  tier_1 = 2
  tier_2 = 3
  tier_3 = 4
  tier_4 = 5

  @classmethod
  def from_patreon_tier(cls, tier: int = 7212079):
    if int(tier) == 7212079:  # Patreon Tier 1
      return cls.tier_1
    return cls.free

  def __str__(self):
    return self.name.capitalize().replace("_", " ")

  def __ge__(self, other: Self):
    return self.value >= other.value

  def __gt__(self, other: Self):
    return self.value > other.value

  def __le__(self, other: Self):
    return self.value <= other.value

  def __lt__(self, other: Self):
    return self.value < other.value


class PremiumPerks:
  def __init__(self, tier: PremiumTiersNew = PremiumTiersNew.free):
    self.tier: PremiumTiersNew = tier

    self._roles = {
          PremiumTiersNew.tier_1.value: 844090257221222401,
          PremiumTiersNew.tier_2.value: 851980183962910720,
          PremiumTiersNew.tier_3.value: 858993523536429056,
          PremiumTiersNew.tier_4.value: 858993776994418708
    }

  def __repr__(self) -> str:
    return f"<PremiumPerks tier={self.tier}>"

  @property
  def guild_role(self) -> Optional[int]:
    """The patron role for the support guild"""
    return self._roles.get(self.tier.value, None)

  @property
  def chat_ratelimit(self) -> commands.CooldownMapping:
    from cogs.chat import SpamChecker
    if self.tier == PremiumTiersNew.free:
      return SpamChecker().free
    elif self.tier == PremiumTiersNew.voted:
      return SpamChecker().voted
    elif self.tier == PremiumTiersNew.streaked:
      return SpamChecker().streaked
    elif self.tier >= PremiumTiersNew.tier_1:
      return SpamChecker().patron
    return SpamChecker().free

  @property
  def max_chat_characters(self) -> int:
    if self.tier == PremiumTiersNew.free:
      return 100
    return 200

  @property
  def max_chat_history(self) -> int:
    if self.tier.value >= PremiumTiersNew.tier_1.value:
      return 5
    return 3

  @property
  def max_chat_tokens(self) -> int:
    if not self.tier >= PremiumTiersNew.tier_1:
      return 25
    return 50


allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True, replied_user=False)


soups = [
    "https://cdn.discordapp.com/attachments/503687266594586634/504016368618700801/homemade-chicken-noodle-soup.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504016424801402891/chicken-noodle-soup-from-scratch-feature.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504017222377668610/pumpkin-soup-with-a-twist-71237-1.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504016234967203843/Thai-Chicken-Noodle-Soup_EXPS_EDSC17_196599_B03_16_4b.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504016172983779329/chicken-noodle-soup-604x334_0.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504016140008161280/1371591003021.png",
    "https://cdn.discordapp.com/attachments/503687266594586634/504016115161366559/WIMF_HomeTile_Soups_RW_CHIKNOODLE_51.png",
    "https://static01.nyt.com/images/2016/11/29/dining/recipelab-chick-noodle-still/recipelab-chick-noodle-still-videoSixteenByNineJumbo1600.jpg",
    "https://food-images.files.bbci.co.uk/food/recipes/chickensoup_1918_16x9.jpg",
    "https://food.fnr.sndimg.com/content/dam/images/food/fullset/2014/7/17/1/FN_Simple-Chicken-Soup_s4x3.jpg.rend.hgtvcom.616.462.suffix/1408067446307.jpeg",
    "https://img1.cookinglight.timeinc.net/sites/default/files/styles/4_3_horizontal_-_1200x900/public/image/2017/08/main/fire-roasted-tomato-basil-soup-1709p63.jpg?itok=E0VGnlJw",
    "https://nutritiouslife.com/wp-content/uploads/2012/03/homemade-chicken-soup.jpg",
    "https://thecozyapron.com/wp-content/uploads/2012/02/tomato-basil-soup_thecozyapron_1.jpg",
    "https://minimalistbaker.com/wp-content/uploads/2018/02/DELICIOUS-Fire-Roasted-Tomato-Veggie-Mung-Bean-Soup-10-ing-fiber-rich-BIG-flavor-vegan-glutenfree-soup-dinner-plantbased-recipe-minimalistbaker-8.jpg",
    "https://www.seriouseats.com/recipes/images/2017/12/20171115-chicken-soup-vicky-wasik-11-1500x1125.jpg",
    "https://d3cizcpymoenau.cloudfront.net/images/25534/SFS_sweet_potato_soup-10.jpg",
    "https://www.gimmesomeoven.com/wp-content/uploads/2011/08/Asian-Cabbage-Egg-Roll-Soup-Recipe-3.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTmMWvoct4mfJI-7IM1pq6zUD4y3kIljjh2zpd7DarwyeKr3VWC",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRyXFdRGcnlSlttsiaguqeUIgApqM98tiIm6SL0eDImEiRnWk3n",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTRoi5ByFVoqxMVk4lBNoLMRssXzM-r6nZZXLZsMb7-fZ7IIn-yRA",
    "https://assets.marthastewart.com/styles/wmax-750/d35/ginger-spice-chicken-soup-103228718/ginger-spice-chicken-soup-103228718_horiz.jpg?itok=aGDCBfvE",
    "https://static1.squarespace.com/static/5a4fb14ecd39c3e7d62e485f/5a4fbd75c8302547a5796aeb/5a4fbd7ef9619a5160c089aa/1515175440082/4+Soups.jpeg?format=1000w",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAtPoIpqNPy73yolOmEVDtMkjy2q3CAQessIHqL96LGpbZ2ffbSg",
    "https://homemadehooplah.com/wp-content/uploads/2016/03/weight-loss-wonder-soup-1.jpg",
    "http://cdn2.simplysated.com/wp-content/uploads/2017/11/square-creamy-chicken-soup-1-of-1.jpg",
    "https://assets.marthastewart.com/styles/wmax-1500/d37/sas-chicken-noodle-soup-002-med108875/sas-chicken-noodle-soup-002-med108875_sq.jpg?itok=nr_KUsIO",
    "https://www.errenskitchen.com/wp-content/uploads/2014/04/quick-and-easy-chinese-noodle-soup3-1.jpg",
    "http://assets.kraftfoods.com/recipe_images/opendeploy/583452_2_1_retail-356ddcdcc4ca55a40dc952a4300a5f4645e691f0_306x204.jpg",
    "https://cf-images.us-east-1.prod.boltdns.net/v1/static/1033249144001/4b3d4b20-d97e-4be3-8840-a2783a6d20ff/399d6c0b-d754-441a-bc75-aa86ec6628f3/1280x720/match/image.jpg",
    "http://www.yummymummyclub.ca/sites/default/files/styles/large/public/Crockpot_Chicken_Noodle_Soup_.JPG?itok=y56MvBnI",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Chinese_cuisine-Shark_fin_soup-04.jpg/1200px-Chinese_cuisine-Shark_fin_soup-04.jpg",
    "https://hips.hearstapps.com/hmg-prod.s3.amazonaws.com/images/delish-instant-pot-chicken-tortilla-soup-pinterest-still002-1544466821.jpg",
    "https://www.onceuponachef.com/images/2018/10/Crab-Soup-227x307.jpg",
    "http://media.foodnetwork.ca/recipetracker/b431c7b1-b4ed-4d87-bd2c-5f715f55228a_grilled-cheese-tomato-soup_webready.jpg",
    "https://www.spendwithpennies.com/wp-content/uploads/2018/10/chicken-rice-soup-www.thereciperebel.com-SWP-2-of-15.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSx3bhfnnLFVjULL_Fum2LR3j54u7zx7Q_tsCqGrg9zg-w_mmjvsQ",
    "https://www.bbcgoodfood.com/sites/default/files/styles/teaser_item/public/recipe/recipe-image/2018/10/cauliflower-soup-with-fancy-chorizo-topping.jpg?itok=eYP9xgNk",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRbJOhpQo-oi8HWToVw6ZZQYfEbqwxiJGz2FnzUaXPR68yh-PKJ"
]


unoCards = [
    "https://images-ext-1.discordapp.net/external/8lkW_Oc75LUsInVfw-SHFmixndOid-lriow7ld69ynI/%3Fitemid%3D13032597/https/media1.tenor.com/images/8a650dbffd5d35fcfa81816bcff1bbf9/tenor.gif",
    "https://i.imgur.com/yXEiYQ4.png",
    "https://i.redd.it/wiga0fsqors11.png"
]

# {
#     "theGame": [
#         "https://tenor.com/view/the-game-you-lost-simon-pegg-shaun-of-the-dead-gif-15513407",
#         "https://media1.tenor.com/images/4ee6e56242913c21e7581a1d38748b15/tenor.gif"
#     ],
#     "inspImages": [
#         "https://cdn.discordapp.com/attachments/243945221086248961/750276288169771108/nur-bayraktepe-TBWYkMaDElk-unsplash_1.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750276629263286292/lynda-b-qCejnWFEs54-unsplash_2.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750434086908067880/veronica-reverse-diAIZW5IWBY-unsplash.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750434222405058580/racim-amr-8KKGTKmULU8-unsplash.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750434504962867240/george-howden-CxvpmTTlj2M-unsplash.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750435116202983484/solen-feyissa-g5CAJdzndhI-unsplash.jpg",
#         "https://cdn.discordapp.com/attachments/243945221086248961/750435323812773998/waldemar-brandt-WX65IQ6BX18-unsplash.jpg"
#     ],
#     "inspImageSources": [
#         "Photo by Nur Bayraktepe on Unsplash",
#         "Photo by Lynda B on Unsplash",
#         "Photo by Veronica Reverse on Unsplash",
#         "Photo by Racim Amr on Unsplash",
#         "Photo by George Howden on Unsplash",
#         "Photo by Solen Feyissa on Unsplash",
#         "Photo by Waldemar Brandt on Unsplash"
#     ],
#     "inspImageQuotes": [
#         "Lechuga",
#         "Manzana",
#         "Peace",
#         ":)",
#         "Love, Laugh, Live",
#         "GTFO",
#         "If you are not first, you are last",
#         "Have you eaten?",
#         "@everyone",
#         "@here",
#         "Drink some water!",
#         "Have you eaten yet today?",
#         "If at first you don't succeed,\n then skydiving definitely\n isn't for you.",
#         "People who wonder\nwhether the glass is\nhalf empty or half full\nare missing the point.\n\nThe glass is REFFILABLE!",
#         "The elevator to success\nis out of order.\nYou'll need to use the stairs...\none step at a time.",
#         "When nothing\ngoes right...\n\ngo left.",
#         "When life gives\nyou lemons,\ngo outside and\ntake a walk",
#         "When life gives\nyou lemons",
#         "When life has you down\nput on some lip chap",
#         "Alt + F4\nis the solution to\nall of life's\nproblems",
#         "E",
#         "Empty the grease tray",
#         "You are not insane",
#         "Bruh",
#         "Lemons",
#         "Pineapple",
#         "Eat your vegetables",
#         "Where there's a will"
#     ]
# }
