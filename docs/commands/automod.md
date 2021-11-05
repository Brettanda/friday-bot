---
title: Automod
description: There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server.
---
# Automod

There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server.

## Blacklist

Blacklist words from being sent in text channels

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!blacklist|bl 
!blacklist|bl add <phrase>
!blacklist|bl clear 
!blacklist|bl display 
!blacklist|bl remove <word>
```

Aliases:

```md
bl
```

### Add

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Add a word to the current servers blacklist settings.

Usage:

```md
!blacklist add|+ <phrase>
```

Aliases:

```md
+
```

Examples:

```md
!blacklist add penis
!bl + shit
```

### Clear

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Remove all words from the current servers blacklist settings.

Usage:

```md
!blacklist clear 
```

### Display

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Display the current servers blacklist settings.

Usage:

```md
!blacklist display|list|show 
```

Aliases:

```md
list,show
```

### Remove

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Remove a word from the current servers blacklist settings.

Usage:

```md
!blacklist remove|- <word>
```

Aliases:

```md
-
```

Examples:

```md
!blacklist remove penis
!bl - shit
```

## Contentspam

Sets the max number of message that can have the same content (ignoring who sent the message) until passing the given threshold and muting anyone spamming the same content further.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!contentspam <message_rate> <seconds>
!contentspam disable 
!contentspam punishment <action>
```

Examples:

```md
!contentspam 3 5
!contentspam 15 17
```

### Disable

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Disable the max amount of messages per x seconds with the same content for this server.

Usage:

```md
!contentspam disable 
```

### Punishment

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.

Usage:

```md
!contentspam punishment|punishments <action>
```

Aliases:

```md
punishments
```

Examples:

```md
!contentspam punishment delete
!contentspam punishments kick
!contentspam punishment ban
!contentspam punishments mute
```

## Invitespam

Automaticaly remove Discord invites (originating from external servers) from text channels. Not giving an argument will display the current setting.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!invitespam|removeinvites [enable]
```

Aliases:

```md
removeinvites
```

Examples:

```md
!invitespam
!removeinvites 1
!invitespam 0
!removeinvites true
!invitespam false
```

## Mentionspam

Set the max amount of mentions one user can send per message before muting the author

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!mentionspam|maxmentions|maxpings <mention_count> <seconds>
!mentionspam|maxmentions|maxpings disable 
!mentionspam|maxmentions|maxpings punishment <action>
```

Aliases:

```md
maxmentions,maxpings
```

Examples:

```md
!mentionspam 3
!maxmentions 5
!maxpings 10
```

### Disable

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Disable the max amount of mentions per message for this server.

Usage:

```md
!mentionspam disable 
```

### Punishment

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Set the punishment for the max amount of mentions one user can send per message. Combining kick,ban and/or mute will only apply one of them.

Usage:

```md
!mentionspam punishment|punishments <action>
```

Aliases:

```md
punishments
```

Examples:

```md
!mentionspam punishment delete
!maxmentions punishments kick
!maxpings punishment ban
!mentionspam punishments mute
```

## Messagespam

Sets a max message count for users per x seconds

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!messagespam|maxmessages|ratelimit <message_rate> <seconds>
!messagespam|maxmessages|ratelimit disable 
!messagespam|maxmessages|ratelimit punishment <action>
```

Aliases:

```md
maxmessages,ratelimit
```

Examples:

```md
!messagespam 3 5
!maxmessages 10 12
```

### Disable

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Disable the max amount of messages per x seconds by the same member for this server.

Usage:

```md
!messagespam disable 
```

### Punishment

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.

Usage:

```md
!messagespam punishment|punishments <action>
```

Aliases:

```md
punishments
```

Examples:

```md
!messagespam punishment delete
!maxmessages punishments kick
!ratelimit punishment ban
!messagespam punishments mute
```

## Unwhitelist

Unwhitelist channels and/or roles from being automoded.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!unwhitelist|unwl <channel_or_roles>...
```

Aliases:

```md
unwl
```

Examples:

```md
!unwhitelist #memes
!unwl @admin #admin 707457407512739951
```

## Whitelist

Whitelist channels and/or roles from being automoded.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!whitelist|wl <channel_or_roles>...
```

Aliases:

```md
wl
```

Examples:

```md
!whitelist #memes
!wl #admin @admin 707457407512739951
```
