# Chat

Friday is a chatbot so these are the ways to make sure that if Friday has a response that you get that response

- Mentioning Friday (or using a reply) eg.

```md
@Friday hey, how are you?
```

- [Setting a channel to be the chat channel](/commands/moderation/#chatchannel). Friday will (try to) respond to every message in that channel as if they were directed to Friday.

## Max message length

By default Friday has a maximum message length that she will respond to. For free users this is set to **100 characters**.

## Rate limiting

Friday has a rate limit per user to help reduce spam. Currently the rate limit is set to **6 messages every 20 seconds per user**.

## Using a chat channel

If your server has a set chat channel useing the [`!set chatchannel`](/commands/moderation/#chatchannel) command. You do not need to mention Friday in that channel to talk to her. She will respond to messages without being mentioned.
