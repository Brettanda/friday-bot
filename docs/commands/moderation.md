# Moderation

Manage your server with these commands

## Ban



Usage:

```md
!ban <members>... [delete_message_days=0] <reason>
```

Aliases:

```md
None
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

Usage:

```md
!begone [message]
```

Aliases:

```md
None
```

Examples:

```md
None
```

## Blacklist

Blacklist words from being sent in text channels

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

Examples:

```md
None
```

### Add

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

Usage:

```md
!blacklist clear 
```

Aliases:

```md
None
```

Examples:

```md
None
```

### Display

Usage:

```md
!blacklist display|list|show 
```

Aliases:

```md
list,show
```

Examples:

```md
None
```

### Remove

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

Usage:

```md
!chatchannel 
```

Aliases:

```md
None
```

Examples:

```md
None
```

## Deletecommandsafter

Set the time in seconds for how long to wait before deleting command messages

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



Usage:

```md
!kick <members>... [reason]
```

Aliases:

```md
None
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

## Massmove

Move everyone from one voice channel to another

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

Usage:

```md
!mute <member>...
```

Aliases:

```md
None
```

Examples:

```md
None
```

## Prefix

Sets the prefix for Fridays commands

Usage:

```md
!prefix [new_prefix='!']
```

Aliases:

```md
None
```

Examples:

```md
None
```

## Rolecall

Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members

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

## Unmute

Unmute a member from text channels

Usage:

```md
!unmute <member>...
```

Aliases:

```md
None
```

Examples:

```md
None
```

