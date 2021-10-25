---
title: Moderation
description: Manage your server with these commands
---
# Moderation

Manage your server with these commands

## Ban

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!ban <members>... [reason]
```

Examples:

```md
!ban @username @someone @someoneelse Spam
!ban @thisguy The most spam i have ever seen
!ban 12345678910 10987654321 @someone
!ban @someone They were annoying me
!ban 123456789 2 Sus
```

## Begone

Delete unwanted message that I send

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!begone [message]
```

Examples:

```md
!begone
!begone https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983
!begone 707520808448294983
```

## Blacklist

Blacklist words from being sent in text channels

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!blacklist|bl 
!blacklist|bl add <word>
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

Usage:

```md
!blacklist add|+ <word>
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

Usage:

```md
!blacklist clear 
```

### Display

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

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

## Chatchannel

Set the current channel so that I will always try to respond with something

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!chatchannel 
```

## Deletecommandsafter

Set the time in seconds for how long to wait before deleting command messages

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!deletecommandsafter|deleteafter|delcoms [time=0]
```

Aliases:

```md
deleteafter,delcoms
```

Examples:

```md
!deletecommandsafter
!deleteafter 0
!delcoms 180
```

## Kick

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!kick <members>... [reason]
```

Examples:

```md
!kick @username @someone @someoneelse
!kick @thisguy
!kick 12345678910 10987654321 @someone
!kick @someone I just really didn't like them
!kick @thisguy 12345678910 They were spamming general
```

## Language

Change the language that I will speak

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!language|lang [language]
```

Aliases:

```md
lang
```

Examples:

```md
!language
!lang en
!language es
!lang english
!language spanish
```

## Last

Gets the last member to leave a voice channel.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!last [voice_channel]
```

## Massmove

Move everyone from one voice channel to another

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!massmove|move <tochannel> [fromchannel]
```

Aliases:

```md
move
```

Examples:

```md
!massmove general
!move vc-2 general
!massmove 'long voice channel' general
```

## Mute

Mute a member from text channels

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!mute <member>... <reason>
!mute role <role>
```

Examples:

```md
!mute @Motostar @steve
!mute @steve 9876543210
!mute @Motostar
!mute 0123456789
```

### Role

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Set the role to be applied to members that get muted

Usage:

```md
!mute role <role>
```

## Prefix

Sets the prefix for Fridays commands

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!prefix [new_prefix='!']
```

Examples:

```md
!prefix
!prefix ?
!prefix f!
```

## Rolecall

Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!rolecall|rc <role> [voicechannel] <exclusions>...
```

Aliases:

```md
rc
```

Examples:

```md
!rolecall @mods vc-1
!rc 123456798910 vc-2 vc-1 10987654321
!rolecall @admins general @username @username
```

## Unban

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!unban <member> <reason>
```

## Unmute

Unmute a member from text channels

??? check "Has a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!unmute <members>... <reason>
```

Examples:

```md
!unmute @Motostar @steve
!unmute @steve 9876543210
!unmute @Motostar
!unmute 0123456789
```
