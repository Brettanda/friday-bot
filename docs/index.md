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

    **To actually use the Rock, Paper, Scissors command you would type this:**

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

    For this command you could also use the users IDs if you don't wish to mention the users. If you are not sure how to get a users ID please check out this article on [Where can I find my User/Server/Message ID](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-). For example:

    ```md
    !kick 123456789 987654321
    ```

## How to commands

### Prefix

The default prefix for Friday's commands is `!`, and for commands to execute every command needs this prefix or the custom prefix that you can set with the [prefix](commands/moderation/#prefix) command.

## Languages

Friday can speak every language available to Google translate, but can only speak one language at a time per server. To change which language Friday will respond in and to, simply use the following the [language command](commands/moderation/#language).

<!-- [^1]: Lorem ipsum dolor sit amet, consectetur adipiscing elit. -->

<!-- For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files. -->
