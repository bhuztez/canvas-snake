#!/usr/bin/env python2
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; -*-


from pyjamas.Canvas2D import Canvas
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.FocusPanel import FocusPanel
from pyjamas import DeferredCommand

__all__ = ['refresh', 'get_keyval', 'Canvas', 'main']


def refresh(widget):
    pass


def get_keyval(keycode):
    if 47 < keycode < 58:
        return chr(keycode)
    elif 64 < keycode < 91:
        return chr(keycode)
    elif keycode == 38:
        return 'Up'
    elif keycode == 40:
        return 'Down'
    elif keycode == 37:
        return 'Left'
    elif keycode == 39:
        return 'Right'

    return "NONE"



class Focus:
    def __init__(self, widget):
        self.widget = widget

    def execute(self):
        self.widget.setFocus(True)


def main(init):
    root = RootPanel()
    container = FocusPanel()
    DeferredCommand.add(Focus(container))
    root.add(container)
    container.setSize(21*15,21*15)
    init(container)



