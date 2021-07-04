# Chat

Friday is a chatbot so these are the ways to make sure that if Friday has a response that you get that response

- Mentioning Friday (or using a reply) eg.

```md
@Friday hey, how are you?
```

- [Setting a channel to be the chat channel](/commands/moderation/#chatchannel). Friday will respond to every message in that channel as if they were directed to Friday. Eg:

```md
hey what is it like being a bot?
```

## Max message length

By default Friday has a maximum message length that she will respond to. For free users this is set to **100 characters**. To get longer message length [become a patreon](//www.patreon.com/bePatron?u=42649008&redirect_uri={{ config.site_url }})

## Rate limiting

Friday has a rate limit per user to help reduce spam and keep costs low. Currently the rate limits are:

- 80 messages every 12 hours per user for user that have not [voted for Friday](https://top.gg/bot/476303446547365891/vote) and not at least a tier 1 [Patreon](//www.patreon.com/bePatron?u=42649008&redirect_uri={{ config.site_url }}).
- 200 messages every 12 hours per user for users that have [voted](https://top.gg/bot/476303446547365891/vote) or are at least a tier 1 [Patreon](//www.patreon.com/bePatron?u=42649008&redirect_uri={{ config.site_url }}).
- 6 messages every 60 seconds per user absolute maximum.
- 180 messages every 1 hour per user absolute maximum.

## Using a chat channel

If your server has a set chat channel useing the [`!set chatchannel`](/commands/moderation/#chatchannel) command. You do not need to mention Friday in that channel to talk to her. She will respond to messages without being mentioned.
