import discord

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


intents = discord.Intents(
    guilds=True,
    voice_states=True,
    messages=True,
    reactions=True,
    members=True,
    bans=True,
    # invites=True,
)

member_cache = discord.MemberCacheFlags(joined=True)

# all_support_ranks = [item for item in support_ranks]

patreon_supporting_role = 843941723041300480

premium_tiers = {
    "free": 0,
    "t1_one_guild": 1,
    "t1_three_guilds": 2,
    "t2_one_guild": 3,
    "t3_one_guild": 4,
    "t4_one_guild": 5,
}

premium_roles = {
    "t1_one_guild": 844090257221222401,
    premium_tiers["t1_one_guild"]: 844090257221222401,
    "t1_three_guilds": 849440438598238218,
    premium_tiers["t1_three_guilds"]: 849440438598238218,
    "t2_one_guild": 851980183962910720,
    premium_tiers["t2_one_guild"]: 851980183962910720,
    # "t2_three_guilds": 851980649920331798,
    # premium_tiers["t2_three_guilds"]: 851980649920331798,
    "t3_one_guild": 858993523536429056,
    premium_tiers["t3_one_guild"]: 858993523536429056,
    "t4_one_guild": 858993776994418708,
    premium_tiers["t4_one_guild"]: 858993776994418708,
}


allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)

games = [
    "Developing myself",
    "Minecraft 1.19",
    "Super Smash Bros. Ultimate",
    "Cyberpunk 2078",
    "Forza Horizon 6",
    "Red Dead Redemption 3",
    "Grand Theft Auto V",
    "Grand Theft Auto VI",
    "Grand Theft Auto IV",
    "Grand Theft Auto III",
    "Ori and the Will of the Wisps",
    "With the internet",
    "DOOM Eternal",
    "D&D (solo)",
    "Big brain time",
    "Uploading your consciousness",
    "Learning everything on the Internet",
    "some games",
    "with Machine Learning",
    "Escape from Tarkov",
    # "Giving out inspirational quotes",
    {
        "type": discord.ActivityType.listening, "content": "myself"
    },
    {
        "type": discord.ActivityType.watching, "content": "", "stats": True
    }
]

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
