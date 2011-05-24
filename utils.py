#!/usr/bin/env python2
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; -*-

import pygtk
pygtk.require('2.0')
import gobject, gtk, cairo
import re


__all__ = ['refresh', 'get_keyval', 'Canvas', 'main', 'window']


def refresh(widget):
    widget.queue_draw()


def get_keyval(keycode):
    return gtk.gdk.keyval_name(keycode)



def context_method(method):
    def wrapper(self, *args, **kwargs):
        self.save()
        try:
            method(self, *args, **kwargs)
        finally:
            self.restore()

    return wrapper



class BaseProperty(object):

    def __init__(self, name):
        self.name = name



class Proxy(BaseProperty):

    def __get__(self, instance, owner):
        assert owner is not None
        return getattr(instance.current_state, self.name)   

    def __set__(self, instance, value):
        setattr(instance.current_state, self.name, value)


class StateProperty(BaseProperty):

    def __get__(self, instance, owner):
        return instance.data[self.name]

    def __set__(self, instance, value):
        instance.data[self.name] = value


def parse_color(value):
    m = re.match(r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$', value)
    if m: return tuple(int(s)/255.0 for s in m.groups())
    m = re.match(r'^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([01](?:\.\d+)?)\s*\)$', value)
    if m: return tuple(int(s)/255.0 for s in m.groups()[:-1]) + (float(m.groups()[3]),)
    m = re.match(r'^#([A-Fa-f0-9])([A-Fa-f0-9])([A-Fa-f0-9])$', value)
    if m:
        value = '#' + ''.join(sum(zip(m.groups(), m.groups()), ()))
    color = gtk.gdk.color_parse(value)
    return (color.red_float, color.green_float, color.blue_float)



class ColorProperty(StateProperty):

    def __set__(self, instance ,value):
        if isinstance(value, str):
            instance.data[self.name] = parse_color(value)
        else:
            instance.data[self.name] = value.obj


class CairoProperty(StateProperty):
    def __init__(self, name, style, mapper=None):
        self.name = name
        self.style = style

    def __set__(self, instance, value):
        instance.data[self.name] = getattr(cairo, ('%s_%s'%(self.style, value)).upper() ) 


def get_operator(name):
    name = name.lower()
    if name.startswith('source-'):
        return getattr(cairo, ('OPERATOR_%s'%(name[7:])).upper())
    elif name.startswith('destination-'):
        return getattr(cairo, ('OPERATOR_DEST_%s'%(name[12:])).upper())
    elif name == 'lighter':
        return 18
    elif name == 'darker':
        return 17
    elif name == 'copy':
        return cairo.OPERATOR_SOURCE
    else:
        return getattr(cairo, ('OPERATOR_%s'%(name)).upper())


class CairoOperatorProperty(StateProperty):

    def __set__(self, instance, value):
        instance.data[self.name] = get_operator(value)


class ContextState(object):

    fillStyle = ColorProperty('fillStyle')
    strokeStyle = ColorProperty('strokeStyle')
    globalAlpha = StateProperty('globalAlpha')
    lineWidth = StateProperty('lineWidth')
    lineCap = CairoProperty('lineCap', 'line_cap')
    lineJoin = CairoProperty('lineJoin', 'line_join')
    miterLimit = StateProperty('miterLimit')
    globalCompositeOperation = CairoOperatorProperty('globalCompositeOperation')
    mozImageSmoothingEnabled = StateProperty('mozImageSmoothingEnabled')
    

    def __init__(self, data=None):
        if data is None:
            self.data = dict(
                fillStyle   = (0.0, 0.0, 0.0),
                strokeStyle = (0.0, 0.0, 0.0),
                globalAlpha = 1.0,
                lineWidth = 1.0,
                lineCap = cairo.LINE_CAP_BUTT,
                lineJoin = cairo.LINE_JOIN_MITER,
                miterLimit = 10.0,
                globalCompositeOperation = cairo.OPERATOR_OVER,
                mozImageSmoothingEnabled = True)
        else:
            self.data = data


    def copy(self):
        return ContextState(self.data.copy())


class Gradient(object):

    def __init__(self, klass, *args):
        self.obj = klass(*args)

    def addColorStop(self, offset, value):
        color = parse_color(value)
        if len(color) == 3:
            self.obj.add_color_stop_rgb(offset, *color)
        else:
            self.obj.add_color_stop_rgba(offset, *color)


def load_image(filename):
    pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
    w, h = pixbuf.get_width(), pixbuf.get_height()
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    gtk.gdk.CairoContext(ctx).set_source_pixbuf(pixbuf, 0, 0)
    ctx.paint()
    return surf


class Pattern(object):
    def __init__(self, surface, extend):
        w, h = surface.get_width(), surface.get_height()
        self.obj = cairo.SurfacePattern(surface)
        self.obj.set_extend(getattr(cairo, ('EXTEND_%s'%(extend)).upper()))

    

class Context(cairo.Context):
    fillStyle = Proxy('fillStyle')
    strokeStyle = Proxy('strokeStyle')
    globalAlpha = Proxy('globalAlpha')
    lineWidth = Proxy('lineWidth')
    lineCap = Proxy('lineCap')
    lineJoin = Proxy('lineJoin')
    miterLimit = Proxy('miterLimit')
    globalCompositeOperation = Proxy('globalCompositeOperation')
    mozImageSmoothingEnabled = Proxy('mozImageSmoothingEnabled')


    def __init__(self, surface):
        # FIXME:
        # cairo.Context.__init__(self, surface)
        self.state_stack = []
        self.current_state = ContextState()


    def save(self):
        self.state_stack.append(self.current_state.copy())
        cairo.Context.save(self)


    def restore(self):
        cairo.Context.restore(self)
        self.current_state = self.state_stack.pop()


    def _set_color_style(self, name):
        color = getattr(self, name)
        if isinstance(color, tuple):
            if len(color) == 3:
                color += (self.globalAlpha,)
            self.set_source_rgba(*color)
        else:
            self.set_source(color)


    def _set_line_style(self):
        self.set_line_width(self.lineWidth)
        self.set_line_cap(self.lineCap)
        self.set_line_join(self.lineJoin)
        self.set_miter_limit(self.miterLimit)

    def _set_operator(self):
        self.set_operator(self.globalCompositeOperation)

    
    def fill(self):
        self._set_color_style('fillStyle')
        self._set_operator()
        cairo.Context.fill(self)

    def stroke(self):
        self._set_color_style('strokeStyle')
        self._set_line_style()
        self._set_operator()
        cairo.Context.stroke(self)


    def createLinearGradient(self, x0, y0, x1, y1):
        return Gradient(cairo.LinearGradient, x0, y0, x1, y1)

    def createRadialGradient(self, x0, y0, r0, x1, y1, r1):
        return Gradient(cairo.RadialGradient, x0, y0, r0, x1, y1, r1)

    def createPattern(self, surface, extend):
        return Pattern(surface, extend)

    def transform(self, m11, m12, m21, m22, dx, dy):
        matrix = cairo.Matrix(m11,m12,m21,m22,dx,dy)
        cairo.Context.transform(self, matrix)

    def setTransform(self, m11, m12, m21, m22, dx, dy):
        matrix = cairo.Matrix(m11,m12,m21,m22,dx,dy)
        self.set_matrix(matrix)


    def arc(self, x,y,r,startAngle,endAngle,ccw):
        if ccw:
            cairo.Context.arc_negative(self,x,y,r,startAngle,endAngle)
        else:
            cairo.Context.arc(self,x,y,r,startAngle,endAngle)



    beginPath = cairo.Context.new_path
    closePath = cairo.Context.close_path
    moveTo = cairo.Context.move_to
    lineTo = cairo.Context.line_to
    rect = cairo.Context.rectangle
    bezierCurveTo = cairo.Context.curve_to
    isPointInPath = cairo.Context.in_fill
    



    @context_method
    def fillRect(self, x, y, width, height):
        self.rectangle(x, y, width, height)
        self.fill()


    @context_method
    def strokeRect(self, x, y, width, height):
        self.rectangle(x, y, width, height)
        self.stroke()


    @context_method
    def clearRect(self, x, y, width, height):
        self.rectangle(x, y, width, height)
        self.globalCompositeOperation = 'clear'
        self.fill()


    # mozilla/gfx/thebes/gfxContext.cpp
    @context_method
    def quadraticCurveTo(self, x1, y1, x2, y2):
        x, y = self.get_current_point()
        self.curve_to(
            ( x + x1*2.0 ) / 3.0,
            ( y + y1*2.0 ) / 3.0,
            ( x1 * 2.0 + x2 ) / 3.0,
            ( y1 * 2.0 + y2 ) / 3.0,
            x2,
            y2)


    @context_method
    def drawImage(self, surface, sx, sy, sw=None, sh=None, dx=None, dy=None, dw=None, dh=None):
        w, h = surface.get_width(), surface.get_height()

        if sw is None:
            dx, dy = sx, sy
            sw, sh = w, h
            dw, dh = sw, sh
            sx, sy = 0, 0
        elif dx is None:
            dx, dy = sx, sy
            dw, dh = sw, sh
            sw, sh = w, h
            sx, sy = 0, 0

        matrix = cairo.Matrix()
        matrix.translate(sx, sy)
        matrix.scale(float(sw)/dw, float(sh)/dh)
        pattern = cairo.SurfacePattern(surface)
        pattern.set_matrix(matrix)
        if self.mozImageSmoothingEnabled:
            pattern.set_filter(cairo.FILTER_GOOD)
        else:
            pattern.set_filter(cairo.FILTER_NEAREST)
        
        self.translate(dx, dy)
        self.set_source(pattern)
        self.rectangle(0,0,dw,dh)
        self.clip()
        self.paint()


    @context_method
    def fillText(self, text, x, y):
        self.move_to(x,y)
        self.show_text(text)



class Canvas(gtk.DrawingArea):
    __gsignals__ = { "expose-event": "override" }

    def __init__(self, width, height):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(width, height)
        self.buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.ctx = Context(self.buffer)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('white'))


    def do_expose_event(self, event):
        cr = self.window.cairo_create()
        cr.set_source_surface(self.buffer, 0, 0)
        cr.paint()


    def getContext(self):
        return self.ctx




class Window(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)
        self.connect("destroy", gtk.main_quit)
        self.set_resizable(False)
        self.show_all()


    clearInterval = staticmethod(gobject.source_remove)
    clearTimeout = staticmethod(gobject.source_remove)


    @staticmethod
    def setInterval(func, delay):
        def wrapper():
            try:
                func()
            finally:
                return True
        return gobject.timeout_add(delay, wrapper)


    @staticmethod
    def setTimeout(func, delay):
        def wrapper():
            try:
                func()
            finally:
                return
        return gobject.timeout_add(delay, wrapper)


    def addKeyboardListener(self, listener):
        self.connect('key-press-event', lambda widget, event: listener.onKeyPress(widget, event.keyval, event.state))


window = Window()

def main(init):
    init(window)
    window.show_all()
    gtk.main()


