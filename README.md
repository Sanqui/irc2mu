What?
=====

irc2mu connects to a MU* (MUD, MUSH, MUCK etc.) and behaves like an IRC server, letting you connect to it and chat from 
the comfort of your favorite IRC client.  It's fine tuned for PennMUSH.  Without the extras, it's in essence a Telnet 
client for IRC.

Why?
====
Because I recently got interested in MUs, have been chatting in one, and thought it would be convenient to have it in my 
IRC client.  Also, I want to learn Python asyncio.

How?
====
To launch the gateway, use:
```
	python irc2mud.py HOSTNAME PORT
```
Then, connect with your IRC client to localhost, port 6667.  If you specify an IRC server password in the format of 
name:password, it will be automatically used with the `connect` command.
