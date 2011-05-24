#!/usr/bin/env python2
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; -*-


import random


class GameOver(Exception):
    pass


class Core(object):

    DIRS = (Up, Right, Down, Left) = [(0,-1), (1,0), (0,1), (-1,0)]


    def __init__(self, w, h):
        assert w>20 and h>20
        self.headmap = [ (x,y) for y in range(7,h-7) for x in range(7,w-7)  ]
        self.map = [ (x,y) for y in range(h) for x in range(w) ]


    def start(self):
        self.dir = random.choice(self.DIRS)
        self.dirty = False
        self.head = random.choice(self.headmap)
        self.body = [
            ( (self.head[0]-self.dir[0]*i),
              (self.head[1]-self.dir[1]*i) )
            for i in range(3) ]
        self.food = set()
        
        return self.body


    def put_food(self):
        pos = random.choice(
            [ p for p in self.map
                if p not in self.body and p not in self.food ])
        self.food.add(pos)
        return pos


    def turn(self, direction):
        if not self.dirty:
            if (self.dir[0]+direction[0]) and (self.dir[1]+direction[1]):
                self.dir = direction
                self.dirty = True


    def move(self):
        self.head = ( self.head[0]+self.dir[0], self.head[1]+self.dir[1] )
        
        if self.head in self.body or self.head not in self.map:
            raise GameOver

        self.dirty = False        
        
        self.body.insert(0, self.head)
        if self.head in self.food:
            self.food.remove(self.head)
            return (self.head, None)
        else:
            return (self.head, self.body.pop())
        


class Display(object):
    BODY = 'blue'
    FOOD = 'red'
    CLEAR = 'white'
    BLOCK = 15
    DELAY = 100

    refresh = None
    get_keyval = None
    Canvas = None
    window = None


    def __init__(self, container, width=21, height=21):
        self.core = Core(width, height)
        self.canvas = self.Canvas(self.BLOCK * width, self.BLOCK * height)
        self.ctx = self.canvas.getContext()

        container.add(self.canvas)
        container.addKeyboardListener(self)

        self.started = False
        self.start()



    def onKeyDown(self, sender, keycode, modifiers):
        pass
  	
    def onKeyUp(self, sender, keycode, modifiers):
        pass

    def onKeyPress(self, sender, keycode, modifiers):
        self.on_dir(self.get_keyval(keycode))


    def on_dir(self, keyname):
        if self.started:
            d = getattr(self.core, keyname, None)
            if d:
                self.core.turn(d)


    def _draw(self, pos, fill=CLEAR):
        x,y = pos
        self.ctx.fillStyle = fill
        self.ctx.fillRect(
            self.BLOCK*x+1,
            self.BLOCK*y+1,
            self.BLOCK-2,
            self.BLOCK-2)


    def start(self):
        assert not self.started
        for pos in self.core.start():
            self._draw(pos, self.BODY)
        self._draw(self.core.put_food(), self.FOOD)
        self.started = True
        self.timer = self.window.setInterval(self.move, self.DELAY)
        


    def move(self):
        if self.started:
            try:
                draw, clr = self.core.move()
                self._draw(draw, self.BODY)
                if clr:
                    self._draw(clr, self.CLEAR)
                else:
                    self._draw(self.core.put_food(), self.FOOD)
                                
            except GameOver:
                self.ctx.fillStyle = 'black'
                self.ctx.fillText("GAME OVER", 50, 50)
                self.started = False
                self.window.clearInterval(self.timer)
            
            self.refresh(self.canvas)


