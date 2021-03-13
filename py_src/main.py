#!/usr/bin/env python3

import argparse
import logging
import urwid
import paho.mqtt.client as mqtt
from datetime import datetime
import time
import json

palette = [
    ('banner', '', '', '', '#f7f7f2', '#364652'),
    ('streak', '', '', '', 'g50', '#364652'),
    ('inside', '', '', '', 'g27', '#f29559'),
    ('title', '', '', '', 'g27,bold', '#f25757'),
    ('key', '', '', '', 'g27,bold', '#f25757'),
    ('descr', '', '', '', '#fff', '#f25757'),
    ('header_online', '', '', '', 'g27,bold', '#f25757'),
    ('header_offline', '', '', '', 'g27,italics', '#f25757'),
    ('footer', '', '', '', 'g27', '#f25757'),
    ('bg', '', '', '', '#fff', '#071108'),
    ('online', '', '', '', '#f7f7f2,bold', '#364652'),
    ('offline', '', '', '', '#aaaaaa,italics', '#364652'),
    ('undelivered', '', '', '', '#aaaaaa,italics', '#364652'),
    ('delivered', '', '', '', '#f25757', '#364652'),
    ('received', '', '', '', '#7dc4ff', '#364652'),
]

footer_text = [
    ('title', "MQTT Chat Client"), "     ",
    ('descr', "Press "), ('key', "ENTER"), ('descr', " to send message"),
    "     ",
    ('descr', "Press "), ('key', "ESC"), ('descr', " to exit"),
]


contacts = {}
contacts_walker = urwid.SimpleListWalker([w for w in contacts.values()])
messages = {}
messages_walker = urwid.SimpleListWalker([w for w in messages.values()])


def exit_on_esc(key):
    """
    Catches the escape key and exits
    @param key - character caught
    """
    if key == 'esc':
        payload = json.dumps({"name": args.name, "online": 0})
        client.publish(args.netid+"/status", payload, qos=1, retain=True)
        raise urwid.ExitMainLoop()

# Ensures that the provided port is within the allowable range
# @param port - number that will be checked
# RETURN: true or false on whether the port fits the parameters


def is_valid_port(port):
    """
    Ensures that the provided port is within the allowable range
    @param port - number that will be checked
    RETURN: true or false on whether the port fits the parameters
    """
    return str(port).isnumeric() and (port < 65535 and port > 1024)

# Callback function from MQTT lib that is called when client connects to broker
# @param client - object that connects with broker
# @param userdata - specialized client params
# @param rc - return code from connect
# @param properties - properties to be sent with connection?


def on_connect(client, userdata, rc, properties=None):
    """
    Callback function from MQTT lib that is called when client connects to broker
    @param client - object that connects with broker
    @param userdata - specialized client params
    @param rc - return code from connect
    @param properties - properties to be sent with connection?
    """

    logging.debug("Connected with result code "+str(rc))

    # Set Header text
    header.original_widget.set_text("Welcome, "+args.name)
    header.set_attr('header_online')
    loop.draw_screen()

    # Subscribe to status and message topics
    client.subscribe("+/status", qos=1)
    client.subscribe("+/message", qos=1)

    # Let world know that we're online, baby
    payload = json.dumps({"name": args.name, "online": 1})
    client.publish(args.netid+"/status", payload, qos=1, retain=True)


def on_message(client, userdata, msg):
    """
    Callback function from MQTT lib that is called when client receives message from broker
    @param client - object that connects with broker
    @param userdata - specialized client params
    @param rc - return code from connect
    """
    logging.info(msg.topic+" "+str(msg.payload))

    mesg = json.loads(msg.payload)  # Deserialize JSON into obj

    # Checking vals
    for title in mesg.keys():

        # Check to see if its a status message
        if title == "online":

            # If someone is spoofing my name and tries to kick me off, I stay on
            if mesg["name"] == args.name and mesg["online"] == 0:
                payload = json.dumps({"name": args.name, "online": 1})
                client.publish(args.netid+"/status",
                               payload, qos=1, retain=True)

            # Text style for contacts based on logged-in status
            style = ""
            if mesg["online"] == 1:
                style = 'online'
            else:
                style = 'offline'

            # Contact is already registered
            if mesg["name"] in contacts.keys():
                logging.info("Dude already exists")
                for contact in contacts_walker:

                    # If the name is already in the list, we update the style based on whether the new message indicates online or offline
                    if contact.original_widget.get_text()[0] == mesg["name"] or contact.original_widget.get_text()[0] == mesg["name"] + " 🔵":
                        contact.set_attr(style)
                        if mesg["online"] == 1:
                            contact.original_widget.set_text(
                                mesg["name"] + " 🔵")
                        else:
                            contact.original_widget.set_text(
                                mesg["name"])
            else:
                # This is a new message to register and apply styles based on online or offline
                logging.info("A new friend is online!")
                contacts.__setitem__(mesg["name"], urwid.AttrWrap(
                    urwid.Text(mesg["name"]), 'online'))
                if mesg["online"] == 1:
                    contacts_walker.contents.append(urwid.AttrWrap(
                        urwid.Text(mesg["name"] + " 🔵"), style))
                else:
                    contacts_walker.contents.append(urwid.AttrWrap(
                        urwid.Text(mesg["name"]), style))

        # This is a message to be printed
        elif title == "timestamp":

            # This checks to see if the message came from me, sets appropriate status for statusbox
            if mesg["name"] == args.name:
                sttsbx.original_widget.set_attr('delivered')
                sttsbx.original_widget.original_widget.set_text(
                    "Message delivered")
            else:
                sttsbx.original_widget.set_attr('received')
                sttsbx.original_widget.original_widget.set_text(
                    "Received Message")

            # Updates message queue and will update screen on draw
            messages.__setitem__(mesg["name"], urwid.Text(mesg["message"]))
            msgstr = str(datetime.fromtimestamp(int(mesg["timestamp"])).strftime(
                "%-I:%M:%S %p")) + ' ' + mesg["name"] + ': ' + mesg["message"]  # Format string for protocol

            # Truncate long messages
            if len(mesg["message"]) > 1000:
                messages_walker.contents.append(
                    urwid.Text(msgstr[0:999]+"..."))
            else:
                messages_walker.contents.append(urwid.Text(msgstr))

    # Sets up always focusing list box to the bottom-most message
    if len(messages_walker.contents) > 1:
        msgbx.original_widget.original_widget.original_widget.set_focus(
            len(messages_walker.contents) - 1)
    logging.debug("this is focused: %s",
                  msgbx.original_widget.original_widget.original_widget.focus)

    # Updates all screen artifacts that have been made
    loop.draw_screen()


def on_disconnect(client, userdata, rc):
    """
    Callback function from MQTT lib that is called when client disconnects from broker
    @param client - object that connects with broker
    @param userdata - specialized client params
    @param rc - return code from connect
    """
    logging.debug("DISCONNECTED")
    header.original_widget.set_text("Welcome, "+args.name+" (Offline)")
    header.set_attr('header_offline')
    loop.draw_screen()


# Formatter for log.txt
formatter = logging.Formatter(
    '[%(asctime)s] \p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    '%m-%d %H:%M:%S')

# Ensures all the arguments behave as expected for proper program execution
parser = argparse.ArgumentParser(add_help=False, prog="chat")
parser.add_argument('--help', action="help")
parser.add_argument('netid', metavar='NETID', type=str,
                    help='The NetID of the user.')
parser.add_argument('-v', '--verbose', action="store_true")
parser.add_argument('-h', '--host', metavar='HOST',
                    type=str, default='localhost')
parser.add_argument('-p', '--port', metavar='PORT', type=int, default=1883)
parser.add_argument('-n', '--name', metavar='NAME',
                    type=str)

args = parser.parse_args()

# Enables logging in the verbose flag is true
if args.verbose:
    logging.basicConfig(
        filename='log.txt',
        level=logging.DEBUG, format='[%(levelname)s][%(asctime)s][%(pathname)s:%(lineno)d]: %(message)s')

# Assigns name to be NetID if no name is provided
if args.name is None:
    args.name = args.netid

# Initializing MQTT Client parameters
client = mqtt.Client(clean_session=True)
client.on_connect = on_connect
lwt = json.dumps({"name": args.name, "online": 0})
client.will_set(args.netid+'/status', payload=lwt, retain=True, qos=1)
client.on_disconnect = on_disconnect
client.on_message = on_message


class Config:
    def __init__(self, port, host, netid, name):
        self.port = port
        self.host = host
        self.netid = netid
        self.name = name

    def check_is_valid(self):
        """
        Checks to see if port is valid
        RETURNS: Whether config obj is valid or not
        """
        return is_valid_port(self.port)


class MessageBox(urwid.LineBox):
    def keypress(self, size, key):
        """
        Takes the size and key and processes the key press
        """

        # If the message isn't submitted keep typing
        if key != 'enter':
            return super(MessageBox, self).keypress(size, key)

        # Publish message to MQTT server
        if self.original_widget.get_edit_text() == "":
            return super(MessageBox, self).keypress(size, key)
        payload = json.dumps(
            {"timestamp": int(time.time()), "name": args.name, "message": self.original_widget.get_edit_text()})
        logging.debug(payload)
        client.publish(args.netid+'/message', payload,
                       qos=1, properties="banana")

        # Blank input field and set status box
        self.original_widget.set_edit_text("")
        sttsbx.original_widget.set_attr('undelivered')
        sttsbx.original_widget.original_widget.set_text("Sent Message")


# Assigns config object
myconf = Config(args.port, args.host, args.netid, args.name)

# TUI object packing and style defining
header = urwid.AttrWrap(urwid.Text(
    "Welcome, " + args.name, 'right'), 'header_online')
sndmsg = urwid.AttrWrap(MessageBox(urwid.Edit()), 'bg')
msgbx = urwid.BoxAdapter(urwid.AttrWrap(
    urwid.LineBox(urwid.ListBox(messages_walker)), 'bg'), height=50)
msgbx.offset_rows = 1
pilediv = urwid.AttrWrap(urwid.Divider(), 'banner')
pile = urwid.Filler(urwid.Pile([msgbx, pilediv, sndmsg]))
footer = urwid.AttrWrap(urwid.Text(footer_text), 'footer')
cntctbx = urwid.BoxAdapter(urwid.LineBox(
    urwid.ListBox(contacts_walker), title='Contacts'), height=50)
cntctbx.offset_rows = 1
sttsbx = urwid.LineBox(urwid.AttrWrap(
    urwid.Text(""), 'undelivered'), title='Status')
leftpile = urwid.Filler(urwid.Pile([cntctbx, pilediv, sttsbx]))
clmns = urwid.Columns([(30, leftpile), (205, pile)])
view = urwid.Frame(
    urwid.AttrWrap(clmns, 'banner'),
    header=header,
    footer=footer)
loop = urwid.MainLoop(
    view,
    palette,
    unhandled_input=exit_on_esc)
loop.screen.set_terminal_properties(colors=256)


def main():
    """
    Runs the setting up of the TUI and MQTT clients and blocks on loop.run
    """

    # Sanitizing the rest of the values
    if not myconf.check_is_valid():
        logging.error("Invalid port %d entered", args.port)
        print(parser.print_help())
        exit(1)

    logging.info("This worked")
    logging.info("NetID: %s", args.netid)
    logging.info("Host: %s", args.host)
    logging.info("Verbose: %s", str(args.verbose))
    logging.info("Port: %s", str(args.port))

    # Starting MQTT client
    client.reconnect_delay_set(1, 5)
    client.connect_async(args.host, args.port)
    client.loop_start()

    # Starts TUI
    loop.run()


if __name__ == "__main__":
    main()
