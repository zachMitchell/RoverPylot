#!/usr/bin/env python

'''
ps3rover20.py Drive the Brookstone Rover 2.0 via the P3 Controller, displaying
the streaming video using OpenCV.

Copyright (C) 2014 Simon D. Levy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as 
published by the Free Software Foundation, either version 3 of the 
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

# Avoid button bounce by enforcing lag between button events
MIN_BUTTON_LAG_SEC = 0.0

# Avoid close-to-zero values on axis
MIN_AXIS_ABSVAL    = 0.4

dpadMoveList = {
    "(0, 1)":[1,1], # Forward
    "(0, -1)":[-1,-1],# Backward
    "(-1, 0)":[-1,1], # Left
    "(1, 0)":[1,-1] # Right
}

from rover import Rover20


import time
import pygame
import sys
import signal
import json

SETTINGS = json.load(open('settings.json'))
CONTROLLER = SETTINGS['controllers'][SETTINGS['default_controller']]
                                   
# Supports CTRL-C to override threads
def _signal_handler(signal, frame):
    frame.f_locals['rover'].close()
    sys.exit(0)

# Try to start OpenCV for video
try:
    import cv
except:
    cv = None

# Rover subclass for PS3 + OpenCV
class PS3Rover(Rover20):

    def __init__(self):

        # Set up basics
        Rover20.__init__(self)
        self.wname = 'Rover 2.0: Hit ESC to quit'
        self.quit = False

        # Set up controller using PyGame
        pygame.display.init()
        pygame.joystick.init()
        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()

         # Defaults on startup: lights off, ordinary camera
        self.lightsAreOn = False
        self.stealthIsOn = False

        # Tracks button-press times for debouncing
        self.lastButtonTime = 0

        # Try to create OpenCV named window
        try:
            if cv:
                cv.NamedWindow(self.wname, cv.CV_WINDOW_AUTOSIZE )
            else:
                pass
        except:
            pass
        if SETTINGS['audio']:
            self.pcmfile = open('rover20.pcm', 'w')

    # Automagically called by Rover class
    def processAudio(self, pcmsamples, timestamp_10msec):
        #for samp in pcmsamples:
        if SETTINGS['audio']:
            self.pcmfile.write('%d\n' % samp)

    # Automagically called by Rover class
    def processVideo(self, jpegbytes, timestamp_10msec):

        # Update controller events
        pygame.event.pump()    

        # Toggle lights    
        self.lightsAreOn  = self.checkButton(self.lightsAreOn, CONTROLLER['lights'], self.turnLightsOn, self.turnLightsOff)   
            
        # Toggle night vision (infrared camera)    
        self.stealthIsOn = self.checkButton(self.stealthIsOn, CONTROLLER['stealth'], self.turnStealthOn, self.turnStealthOff)   
        # Move camera up/down    
        if self.controller.get_button(CONTROLLER['camera_up']):
            self.moveCameraVertical(1)
        elif self.controller.get_button(CONTROLLER['camera_down']):
            self.moveCameraVertical(-1)
        else:
            self.moveCameraVertical(0)

        self.dpadPressed = False
        # Set treads based on hat (D-Pad)
        dpad = self.checkHat()
        if dpad:
            self.dpadTreadsMove(str(dpad))
            self.dpadPressed = True
        if not self.dpadPressed:
            # Set treads based on axes
            self.setTreads(self.axis(CONTROLLER['wheel_l']), self.axis(CONTROLLER['wheel_r']) )

        # Display video image if possible
        try:
            if cv:

                # Save image to file on disk and load as OpenCV image
                fname = SETTINGS['video_out']
                fd = open(fname, 'w')
                fd.write(jpegbytes)
                fd.close()
                image = cv.LoadImage(fname)        

                # Show image
                cv.ShowImage(self.wname, image )
                if cv.WaitKey(1) & 0xFF == 27: # ESC
                    self.quit = True
            else:
                pass
        except:
            pass
        
        
    # Converts Y coordinate of specified axis to +/-1 or 0
    def axis(self, index):
        
        value = -self.controller.get_axis(index)
        
        if value > MIN_AXIS_ABSVAL:
            return value
        elif value < -MIN_AXIS_ABSVAL:
            return value
        else:
            return 0

    # Handles button bounce by waiting a specified time between button presses   
    def checkButton(self, flag, buttonID, onRoutine=None, offRoutine=None):
        if self.controller.get_button(buttonID):
            if (time.time() - self.lastButtonTime) > MIN_BUTTON_LAG_SEC:
                self.lastButtonTime = time.time()
                if flag:
                    if offRoutine:
                        offRoutine()
                    flag = False
                else:
                    if onRoutine:
                        onRoutine()
                    flag = True
        return flag

    def checkHat(self):
        result = self.controller.get_hat(0)
        if (result[0] or result[1]) and (time.time() - self.lastButtonTime) > MIN_BUTTON_LAG_SEC:
            self.lastButtonTime = time.time()
            return result

    def dpadTreadsMove(self,key):
        if(dpadMoveList.get(key)):
            self.setTreads(dpadMoveList[key][0],dpadMoveList[key][1])

# main -----------------------------------------------------------------------------------

if __name__ == '__main__':

    # Create a PS3 Rover object
    rover = PS3Rover()

    # Set up signal handler for CTRL-C
    signal.signal(signal.SIGINT, _signal_handler)

    # Loop until user hits quit button on controller
    while not rover.quit:
        pass

    # Shut down Rover
    rover.close()



