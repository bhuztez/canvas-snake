#!/usr/bin/env python2
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; -*-


from utils import *
import snake


class Display(snake.Display):
    refresh = staticmethod(refresh)
    Canvas = Canvas
    get_keyval = staticmethod(get_keyval)
    window = window


if __name__ == '__main__':
    main(Display)
