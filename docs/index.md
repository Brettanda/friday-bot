---
description: The full list of commands and how to use them from the Friday Discord bot.
---

# Home

<!-- [:fontawesome-brands-patreon: Become a patreon](//www.patreon.com/bePatron?u=42649008&redirect_uri={{ config.site_url }}){ .md-button .md-button--primary .md-button--patreon } -->

**Important Links:**

| [Website](https://friday-bot.com) | [Support Server](http://discord.gg/XP4avQ449V) | [Patreon](//www.patreon.com/bePatron?u=42649008&redirect_uri={{ config.site_url }}) |

???+ danger "Understanding how to use commands"
    **Do not literally type out < > [ ] | ...**

    These are just to display information about the arguments.

    Some examples of these in use would be:

    ```md
    !rps|rockpaperscissors <choice>
    ```

    then both of these will execute the command.

    ```md
    !rps <choice>
    ```

    and

    ```md
    !rockpaperscissors <choice>
    ```

    **To use the Rock, Paper, Scissors command you would type this:**

    ```md
    !rps rock
    ```

???+ warning "Understanding command arguments"
    If you see a command with an argument ending with `...` this means that this one argument will accept multiple of the same type of argument one after another. Let's use this kick command for example.

    ```md
    !kick <members>... <reason>
    ```

    If you want to kick more than one user for the same reason then you would type it like this.

    ```md
    !kick @someone @someoneelse They were annoying me
    ```

    For this command, you could also use the users' IDs if you don't wish to mention the users. If you are not sure how to get a users ID please check out this article on [Where can I find my User/Server/Message ID](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-). For example:

    ```md
    !kick 123456789 987654321
    ```

    An argument wrapped with `[` or `]` just means that the argument is optional. For example with the 

## How to commands

### Prefix

The default prefix for Friday's commands is `!`, and for commands to execute every command needs this prefix or the custom prefix that you can set with the [prefix](/commands/moderation/#prefix) command.

### Slash commands

Friday also supports slash commands. To use these commands, go to any text channel and start typing `/`, you should be greeted with a list of commands from bots and built-in commands.
