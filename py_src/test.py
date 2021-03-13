import urwid

palette = [('header', 'white', 'black'),
    ('reveal focus', 'black', 'dark cyan', 'standout')]

items = [urwid.Text("foo"),
         urwid.Text("bar"),
         urwid.Text("baz")]

content = urwid.SimpleListWalker([
    urwid.AttrMap(w, None, 'reveal focus') for w in items])

listbox = urwid.ListBox(content)

show_key = urwid.Text("Press any key", wrap='clip')
head = urwid.AttrMap(show_key, 'header')
top = urwid.Frame(listbox, head)

def show_all_input(input, raw):

    show_key.set_text("Pressed: " + " ".join([
        str(i) for i in input]))
    return input


def exit_on_cr(input):
    if input in ('q', 'Q'):
        raise urwid.ExitMainLoop()
    elif input == 'up':
        focus_widget, idx = listbox.get_focus()
        if idx > 0:
            idx = idx-1
            listbox.set_focus(idx)
    elif input == 'down':
        focus_widget, idx = listbox.get_focus()
        idx = idx+1
        listbox.set_focus(idx)
    elif input == 'enter':
        pass
    
    elif input in 'rR':
        _, idx = listbox.get_focus()
        am = content[idx].original_widget
        am.set_text(am.text[::-1])
    # 
    #how here can I change value of the items list  and display the ne value????
    #
def out(s):
    show_key.set_text(str(s))


loop = urwid.MainLoop(top, palette,
    input_filter=show_all_input, unhandled_input=exit_on_cr)
loop.run()
