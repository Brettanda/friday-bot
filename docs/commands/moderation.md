# Moderation

Manage your server with these commands

## Kick



Usage:

```md
kick <members> [reason]
```

Aliases:

```md
None
```

## Prefix

Sets the prefix for Fridays commands

Usage:

```md
prefix [new_prefix='!']
```

Aliases:

```md
None
```

## Ban



Usage:

```md
ban <members> [delete_message_days=0] <reason>
```

Aliases:

```md
None
```

## Rolecall

Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members

Usage:

```md
rolecall|rc <role> [voicechannel] <exclusions>
```

Aliases:

```md
rc
```

## Begone

Delete unwanted message that I send

Usage:

```md
begone [message]
```

Aliases:

```md
None
```

## Massmove

Move everyone from one voice channel to another

Usage:

```md
massmove|move <tochannel> [fromchannel]
```

Aliases:

```md
move
```

## Set



Usage:

```md
set|bot 
set|bot language [language]
set|bot musicchannel [voicechannel]
set|bot mute 
set|bot maxmessages <message_rate> <seconds> [max_before_mute]
set|bot chatchannel 
set|bot maxmentions [count]
set|bot deletecommandsafter [time=0]
set|bot removeinvites <choice>
```

Aliases:

```md
bot
```

### Language
Change the language that I will speak
Usage:

```none
set language|lang [language]
```

Aliases:

```none
lang
```

### Mute

Usage:

```none
set mute 
```

Aliases:

```none
None
```

### Chatchannel
Set the current channel so that I will always try to respond with something
Usage:

```none
set chatchannel 
```

Aliases:

```none
None
```

### Deletecommandsafter
Set the time in seconds for how long to wait before deleting command messages
Usage:

```none
set deletecommandsafter|deleteafter|delcoms [time=0]
```

Aliases:

```none
deleteafter,delcoms
```

### Removeinvites
Automaticaly remove Discord invites from text channels
Usage:

```none
set removeinvites <choice>
```

Aliases:

```none
None
```

## Blacklist



Usage:

```md
blacklist|bl 
blacklist|bl add <word>
blacklist|bl remove <word>
blacklist|bl display 
blacklist|bl clear 
```

Aliases:

```md
bl
```

### Add

Usage:

```none
blacklist add|+ <word>
```

Aliases:

```none
+
```

### Remove

Usage:

```none
blacklist remove|- <word>
```

Aliases:

```none
-
```

### Display

Usage:

```none
blacklist display|list|show 
```

Aliases:

```none
list,show
```

### Clear

Usage:

```none
blacklist clear 
```

Aliases:

```none
None
```

## Mute

Mute a member from text channels

Usage:

```md
mute <member>
```

Aliases:

```md
None
```

## Unmute

Unmute a member from text channels

Usage:

```md
unmute <member>
```

Aliases:

```md
None
```

