# Server moderation

Commands for managing Friday on your server

## Prefix



Usage:

```none
prefix [new_prefix='!']
```

Aliases:

```none
None
```

## Ban



Usage:

```none
ban [members]... [delete_message_days=0] <reason>
```

Aliases:

```none
None
```

## Set



Usage:

```none
set|bot 
set|bot maxmentions <count>
set|bot mute 
set|bot chatchannel 
set|bot language <language>
set|bot maxmessages <message_rate> <seconds> <max_before_mute>
set|bot musicchannel [voicechannel]
set|bot deletecommandsafter [time=0]
```

Aliases:

```none
!bot
```

### Maxmentions
Set the max amount of mentions one user can send per message
Usage:

```none
set maxmentions|maxpings <count>
```

Aliases:

```none
!maxpings
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

### Language
Change the language that I will speak
Usage:

```none
set language|lang <language>
```

Aliases:

```none
!lang
```

### Maxmessages
Sets a max message count for users per x seconds
Usage:

```none
set maxmessages|maxspam|ratelimit <message_rate> <seconds> <max_before_mute>
```

Aliases:

```none
!maxspam,!ratelimit
```

### Musicchannel
Set the channel where I can join and play music. If none then I will join any VC
Usage:

```none
set musicchannel [voicechannel]
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
!deleteafter,!delcoms
```

## Massmove



Usage:

```none
massmove|move <toChannel> [fromChannel]
```

Aliases:

```none
!move
```

## Rolecall

Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members

Usage:

```none
rolecall|rc <role> [voicechannel] [exclusions]...
```

Aliases:

```none
!rc
```

## Begone

Delete unwanted message that I send

Usage:

```none
begone [message]
```

Aliases:

```none
None
```

## Userinfo

Some information on the mentioned user

Usage:

```none
userinfo <user>
```

Aliases:

```none
None
```

## Mute

Mute a member from text channels

Usage:

```none
mute <member>
```

Aliases:

```none
None
```

## Unmute

Unmute a member from text channels

Usage:

```none
unmute <member>
```

Aliases:

```none
None
```

## Kick



Usage:

```none
kick [members]... [reason]
```

Aliases:

```none
None
```

