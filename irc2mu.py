from sys import argv
import logging
import asyncio
#logging.basicConfig(level=logging.DEBUG)

BINDHOST = '127.0.0.1'
BINDPORT = 6667

MUHOST = argv[1]
MUPORT = int(argv[2])

class MUClientProtocol(asyncio.Protocol):
    def __init__(self):
        self.loop = loop
        
        self.last_bold = ""
        self.handling_contents = False
        self.contents = []
        self.last_said = []

    def connection_made(self, transport):
        print("Connection made")
        self.transport = transport

    def data_received(self, data):
        #print('*** Data received: {!r}'.format(data))
        lines = data.decode('ascii', 'replace').rstrip('\r\n').split('\r\n')
        if not (len(lines) == 1 and not lines[0].strip()):
            for line in lines:
                action = False
                name = "*"
                message = line.replace('[0m', '\x02').replace('[1m', '\x02')
                if len(line.split()) >= 3 and line.split(" ")[1] == "says,":
                    name = line.split(' ')[0]
                    message = line.split('"', 1)[1][:-1]
                else:
                    if len(line.split()) > 1 and line.split()[0] in self.contents:
                        name, message = line.split(' ', 1)
                        action = True
                
                if line.startswith("You say, \""):
                    for i, ls in reversed(list(enumerate(self.last_said))):
                        if ls.endswith(line.split('"', 1)[1][:-1]):
                            self.last_said.pop(i)
                            message = None
                            print("Not echoing own message: ", line)
                
                if message:
                    self.server.message(message, name=name, action=action)
                    
                    if message.startswith('\x02'):
                        if self.handling_contents:
                            self.contents.append(message.strip('\x02'))
                        else:
                            self.last_bold = message
                    elif message == 'Contents:':
                        self.handling_contents = True
                        self.contents = []
                    elif message == 'Obvious exits:':
                        if not self.handling_contents:
                            self.contents = []
                        self.handling_contents = False
                        self.server.topic(self.last_bold)
                        self.server.names(self.contents)
                    elif message.startswith("Use connect <name> <password>"):
                        if self.server.muuser:
                            self.send('connect {} {}'.format(self.server.muuser, self.server.mupassword))
                    
                    
    
    def connection_lost(self, exc):
        print('MUClient: The server closed the connection')
        self.loop.stop()
    
    def send(self, message):
        self.transport.write(message.encode('ascii')+b'\r\n')
        self.last_said.append(message)
        self.last_said = self.last_said[-10:]


class IRCServerClientProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        
        self.client = None
        
        self.buffer = b""
        
        self.muuser = None
        self.mupassword = None
        
        self.nick = None
        self.user = None
        self.fullname = None
        self.serverhost = BINDHOST
        
        self.channel = "#"
        

    def data_received(self, data):
        message = data
        self.buffer += message
        
        for line in self.buffer.split(b'\n'):
            if not line: continue
            if not line.endswith(b'\r'):
                break
            self._parse(line.rstrip(b'\r'))
            line = b""
        self.buffer = line

        #self.transport.close()
    
    def _parse(self, line):
        line = line.decode('utf-8', 'replace')
        print("RECV: "+line)
        message = None
        if " :" in line:
            command, message = line.split(' :', 1)
        else:
            command = line
        command, *arguments = command.split()
        if command == "PASS":
            self.muuser, self.mupassword = arguments[0].split(':')
            if self.client:
                self.client.send('connect {} {}'.format(self.muuser, self.mupassword))
        elif command == "NICK":
            self.nick = arguments[0]
        elif command == "USER":
            self.user = arguments[0]
            self.serverhost = arguments[2]
            self.fullname = message
            self._send("001", self.nick, ":Welcome to irc2mu!")
            self._send("375", self.nick, ":MoTD goes here.")
            self._send("JOIN", self.channel, "*", source=self.nick+"!"+self.user+"@x")
            self._send("366", self.channel, ":End of /NAMES list")
            self._send("324", self.channel, "+t")
            
            asyncio.Task(self.connect_client())
            
        elif command == "PART":
            if arguments[0] == self.channel:
                self._send("JOIN", self.channel, "*", source=self.nick+"!"+self.user+"@x")
        elif command == "PRIVMSG":
            if message.startswith("\x01ACTION "):
                message = ":"+message.split(" ", 1)[1].rstrip('\x01')
            self.client.send(message)
        else:
            if self.nick and self.user:
                self._send("421", self.nick, command, ":Unknown command")
        
    def _send(self, command, *arguments, source=None):
        if not source: source = self.serverhost
        packet = ":{} {}".format(source, command)
        if arguments:
            last = False
            for argument in arguments:
                if last:
                    print("ERROR: argument following last argument")
                if argument.startswith(":"):
                    last = True
                if " " in argument and not last:
                    print("ERROR: space before final argument")
                packet += " "+str(argument)
        
        print("SEND: "+packet)
        packet += "\r\n"
        
        self.transport.write(packet.encode('utf-8'))
    
    def message(self, message, name="*", action=False):
        if action:
            message = "\x01ACTION "+message+"\x01"
        self._send("PRIVMSG", self.channel, ":"+message, source=name+"!*@*")
        
    def topic(self, message, name="*"):
        self._send("TOPIC", self.channel, ":"+message, source=name+"!*@*")
        
    def names(self, users):
        self._send("353", self.nick, '=', self.channel, ":"+" ".join(user.replace(' ', '\xa0') for user in users))
        self._send("366", self.nick, self.channel, ":End of /NAMES list.")
    
    @asyncio.coroutine
    def connect_client(self):
        print("will connect client")
        protocol, self.client = yield from loop.create_connection(MUClientProtocol, MUHOST, MUPORT)
        self.client.server = self
        print("connected client?")

loop = asyncio.get_event_loop()
#loop.set_debug(True)
server_coro = loop.create_server(IRCServerClientProtocol, BINDHOST, BINDPORT)
server = loop.run_until_complete(server_coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
