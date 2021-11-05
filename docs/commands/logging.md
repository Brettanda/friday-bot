---
title: Logging
description: Different from the log cog b/c this one deals with discord logging not bot logging
---
# Logging

Different from the log cog b/c this one deals with discord logging not bot logging

## Modlog

Set the channel where I can log moderation actions. This will log moderation action done by Friday, Fridays commands, and other moderation action logged by Discord.

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

Usage:

```md
!modlog|modlogs [channel]
!modlog|modlogs events <events>...
```

Aliases:

```md
modlogs
```

### Events

??? missing "Does not have a slash command to match"
	Learn more about [slash commands](/#slash-commands)

The events that will be logged in the mod log channel

Usage:

```md
!modlog events <events>...
```

Examples:

```md
!modlog events bans
!modlogs events mutes
!modlog events unbans
!modlogs events unmutes
!modlog events kicks
!modlogs events bans mutes kicks unbans unmutes
!modlog events bans unbans
```
