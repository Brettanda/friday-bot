<div align="center">
<h1>Friday Discord Bot</h1>
<a href="https://www.codacy.com/gh/Brettanda/friday-discord-python/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Brettanda/friday-discord-python&amp;utm_campaign=Badge_Grade"><img src="https://app.codacy.com/project/badge/Grade/0ad7826bb256410d885a47fca99ce624"/></a>
<a href="https://github.com/Brettanda/friday-discord-python/blob/master/LICENSE.md"><img src="https://img.shields.io/github/license/Brettanda/friday-discord-python" alt="GitHub license"/></a>
<a href="https://github.com/Brettanda/friday-discord-python/issues"><img src="https://img.shields.io/github/issues/Brettanda/friday-discord-python" alt="GitHub issues"/></a>
<a href="https://discord.gg/NTRuFjU"><img src="https://img.shields.io/discord/707441352367013899?color=7289da&logo=discord&logoColor=white" alt="Discord Chat"/></a>
<a href="https://top.gg/bot/476303446547365891/vote"><img src="https://img.shields.io/badge/Vote-Friday-blue" alt="Vote"/></a>
<a href="https://discord.com/api/oauth2/authorize?client_id=476303446547365891&permissions=2469521478&scope=bot%20applications.commands"><img src="https://img.shields.io/badge/Add%20Friday-to%20your%20server-orange" alt="Add Friday to your server"/></a>
<a href="https://www.patreon.com/fridaybot"><img src="https://img.shields.io/badge/-Become%20a%20Patron!-rgb(232%2C%2091%2C%2070)" alt="Become a Patron!"/></a>
</div>


## Commands

Another way to see the full list of commands is by typing `!help` in a Discord server that I have been invited to. You can also direct message me any commands as well (if you want to keep our conversation more private).

## Reddit posts

When someone posts a link to a Reddit post with and image or video, Friday will check to see if there is an available link to grab the video or image from, and then react with a 🔗 emoji. To extract the video or image from the post simply add your own 🔗 reaction to your message. Friday will then send a link the image or download the video and post it.

Reddit posts that wont be extracted include text posts and gallary posts. If there is a post type that i missed please use the `!issue` command followed by the Reddit post and I will get to work.

## Custom sounds

This command will let you make a sub-command that plays a specific link of your choosing. This makes it easier to play a song or sound that you would like to play often without having to find the url every time.

For example if you wanted to play `Bruh Sound Effect #2` you can add it to the list like so `!c add bruh https://www.youtube.com/watch?v=2ZIpFytCSVc`. To then play that sound you would type this command `!c bruh`.

## D&D Dice rolling

Friday can also roll D&D dice for you with the command `!d` or `!r`. This command should work with everything on [wikipedia.org/wiki/Dice_notation](https://en.wikipedia.org/wiki/Dice_notation). If the command returns with an error please ~~use the `!issue` command to~~ connect to Friday's support server to explain what happened so I can fix the problem ASAP. A simple example of what this command can do is `!d d20` and a more complex example is `!r 3d20+d4*3`.

## Inspirational Quotes

~~If you ask Friday for an inspirational quote like `@Friday could you provide me an inspirational quote` Friday will build an image from a JavaScript Canvas with a background from a list and place a string of text from an array overtop of the image then send it as a message attachment~~

The inspirational quotes command has been disabled for the time being.

## Music

Friday can play music in a voice channel with the command `!play` followed by a search query, a YouTube video URL, or almost anyother video link you can find. At the moment Spotify links doen't work because it requies API keys that I haven't setup yet. Here are examples of those two uses `!play uptown funk` or `!play https://youtu.be/dQw4w9WgXcQ`.

## Chat

Friday can respond to normal chat without the message being directed towards Friday

### Context

~~Friday checks if a message is being directed towards Friday if the message contains a mention (`@Friday`), the word 'Friday' in capital letters or lowercase if the most recent message is from Friday, and Friday will (try) to respond to any message send through a direct message to Friday. If a phrase is said that Friday should respond to for a joke or something it will respond if it matches one of the 'no context' phrases. For example, if someone says 'Goodbye' with no context it will respond because goodbyes are apart of 'no context' and therefore can respond anyway.~~

## Todo

- [x] Add queue system for playing YouTube audio
- [x] Make a modern-looking icon
- [x] Add spam protection for the commands like `!issue`
- [x] When music is playing and someone sends a message there is a little bit of a lag spike that occurs in the audio. This needs to be fixed.
- [x] Add a search function to the `!play` command
- [x] Friday will sometimes stop playing a video at some point and thinks that it still is playing
- [x] Ignore the command `!d bump`
- [ ] Add D&D dice rolling command and dialogflow intent
- [ ] If a role is tagged that Friday is not apart of, ignore the message.
- [x] Add the ability to play playlists from youtube as well as adding several
- [ ] Teach friday to see images and recognize them, then play uno with card images
- [ ] Make Friday still respond to messages sent while it was offline
- [ ] Slash Commands?
- [x] Move to [LavaLink](https://github.com/Devoxin/Lavalink.py) for music playing. this should/will fix the lag when playing music
- [ ] Reaction roles
- [ ] Send memes to meme channels at the average time that humans post memes? (could/will take the fun out of sending memes to servers though (make this toggleable))
- [ ] Auto role on join server (waiting on an email from Discord)
- [ ] Give Friday a voice (but not from the movies because that voice belongs to a real person)
- [ ] Generative text responses for the chat bot (GPT-2)
- [ ] Auto-add intents or self-teaching ML
- [ ] Make music playback persist through Fridays script restarts
- [ ] Add named entity recognition/sequence labeling so questions like "friday what is 1+1" can be answered

## To add to the dashboard

- [ ] Add some kind of server-specific settings
- [ ] Custom commands for sound clips to play in a voice channel
- ~~[ ] Custom prefix setting for paying~~
- [ ] Disable some intents like "title of your sex tape"
- [ ] A command to send one message to selected chats (only for admins)
- [ ] auto delete gifs with certain keywords
- [ ] If the server has a specific nickname scheme send messages to those people for the nicknames like if the scheme is first name then friday will ask for their first name
- [ ] Option to select a text channel for updates on Friday from the support server