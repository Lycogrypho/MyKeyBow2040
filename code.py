# SPDX-FileCopyrightText: 2021 Sandy Macdonald

# Modified by Frank Smith 2021 all the keys bar the modifier key
# can now be used as layer select and input keys
# prints debug messages via debug serial port (USB)
# sudo cat /dev/ttyACM0

# Modified by Cosimo Attanasi 2022
# Improved reactivity checking if the keys are released (now it is possible to type faster
# without bouncing characters)
# Added a few example layers, including read'n'type from files, type chars via ASCII codes
# demo mode with rainbow effects (the hue formula is the same as the raimbow example of
# 

# SPDX-License-Identifier: MIT

# An advanced example of how to set up a HID keyboard.

# There are four layers defined out of fifteen possible,
# selected by pressing and holding key 0 (bottom left),
# then tapping one of the coloured layer selector keys to switch layer.

# The defined layer colours are as follows:

#  * layer 1: pink   - numpad-style keys, 0-9, delete, and enter.
#  * layer 2: blue   - sends strings on each key press
#  * layer 3: yellow - media controls, rev, play/pause, fwd on row one, vol. down, mute,
#                      vol. up on row two
#  * Layer 4: white  - game control (just the letters normally used to play with keyboard)
#  * layer 5: red    - send ASCII combination (i.e. to write character not in your keyboard) 
#  * layer 6: green  - read fileset/file##.txt and write its content one character at time
#  * layer 7: blue   - demo mode: each button triggers a different demo pattern/colors/speed/


import time
import math
from pmk import PMK, number_to_xy, hsv_to_rgb
from pmk.platform.keybow2040 import Keybow2040 as Hardware          # for Keybow 2040
# from pmk.platform.rgbkeypadbase import RGBKeypadBase as Hardware  # for Pico RGB Keypad Base

import usb_hid
from adafruit_hid.keyboard import Keyboard
#from adafruit_hid.keyboard_layout_us import KeyboardLayout
from keyboard_layout_win_it import KeyboardLayout
from adafruit_hid.keycode import Keycode

from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Set up Keybow
keybow = PMK(Hardware())
keys = keybow.keys

# Set up the keyboard and layout
keyboard = Keyboard(usb_hid.devices)
layout = KeyboardLayout(keyboard)

# Set up consumer control (used to send media key presses)
consumer_control = ConsumerControl(usb_hid.devices)

# Variables

mode = 0
count = 0

# To prevent the strings (as opposed to single key presses) that are sent from
# refiring on a single key press, the debounce time for the strings has to be
# longer.

short_debounce = 0.03
avg_debounce   = 0.07
long_debounce  = 0.15
debounce = 0.03

fired = False
set_key_pressed = set()
time_of_press = keybow.time_of_last_press


# Our layers. The key of item in the layer dictionary is the key number on
# Keybow to map to, and the value is the key press to send.

# Note that key 0 is reserved as the modifier

# purple - numeric keypad
layer_1 =     {4: Keycode.ZERO,
               5: Keycode.ONE,
               6: Keycode.FOUR,
               7: Keycode.SEVEN,
               8: Keycode.DELETE,
               9: Keycode.TWO,
               10: Keycode.FIVE,
               11: Keycode.EIGHT,
               12: Keycode.ENTER,
               13: Keycode.THREE,
               14: Keycode.SIX,
               15: Keycode.NINE}

# blue - each button outputs a string
layer_2 =     { 7:  "string 1",
               11: "string 2",
               14: "string 3",
               15: "string 4",
               13: "string 5",
                6:  "\tstring 6, including a tab",
               10: """this is how to code a carriage return within a string:
""",
               11: f"this is how to output a variable: {count}"}

# yellow - media controls
layer_3 =     {6: ConsumerControlCode.VOLUME_DECREMENT,
               7: ConsumerControlCode.SCAN_PREVIOUS_TRACK,
               10: ConsumerControlCode.MUTE,
               11: ConsumerControlCode.PLAY_PAUSE,
               14: ConsumerControlCode.VOLUME_INCREMENT,
               15: ConsumerControlCode.SCAN_NEXT_TRACK}

# white - game control
layer_4 =     {5: Keycode.A,
               9: Keycode.S,
               10: Keycode.W,
               13: Keycode.D,
               8: Keycode.SPACE,
               15: Keycode.Y}

# red - send ASCII combination (i.e. to write character not in your keyboard)
layer_5 =     {3:  (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_SIX),
               7:  (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_THREE),
               11: (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_FIVE),
               15: (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_FOUR),
               6:  (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_SEVEN),
               10: (Keycode.KEYPAD_ONE, Keycode.KEYPAD_TWO,Keycode.KEYPAD_TWO)}

# green - read fileset/file##.txt and write its content one character at time
layer_6 =     {1: "file01.txt",
               2: "file02.txt",
               3: "file03.txt",
               4: "file04.txt",
               5: "file05.txt",
               6: "file06.txt",
               7: "file07.txt",
               8: "file08.txt",
               9: "file09.txt",
               10: "file10.txt",
               11: "file11.txt",
               12: "file12.txt",
               13: "file13.txt",
               14: "file14.txt",
               15: "file15.txt"}

# Blue - demo mode: each button is associated to a  color pattern, number of hues displayed and speed
#                   color patterns are defined by assigning each button to a (numbered group); all the
#                   buttons in the group will have the same color over time
layer_7 =     {0:   (( 1,  5,  1,  5,   5,  1,  5,  1,   5,  1,  5,  1,   1,  5,  1,  5),  8, 13),
               1:   (( 0,  1,  2,  3,   4,  5,  6,  5,   4,  3,  2,  1,   0,  1,  2,  1),  8, 13),
               2:   (( 0,  1,  2,  3,   0,  2,  3,  4,   0,  3,  4,  5,   0,  1,  2,  1),  8, 13),
               3:   (( 1,  2,  3,  4,  12, 13, 14,  5,  11, 16, 15,  6,  10,  9,  8,  7), 32,  7),
               4:   (( 1,  2,  3,  4,   0,  1,  2,  3,   1,  2,  3,  4,   2,  3,  4,  5), 10, 13),
               5:   (( 2,  1,  2,  3,   1,  0,  1,  2,   2,  1,  2,  3,   3,  2,  3,  4),  8, 13),
               6:   (( 0,  1,  2,  3,   1,  2,  3,  4,   2,  3,  4,  5,   3,  4,  5,  6), 12, 12),
               7:   (( 0,  2,  4,  6,   2,  4,  6,  8,   4,  6,  8, 10,   6,  8, 10, 12),  6, 12),
               8:   (( 1, 15,  1, 15,  15,  1, 15,  1,   1, 15,  1, 15,  15,  1, 15,  1),  3, 30),
               9:   (( 4,  2,  4,  6,   2,  0,  2,  4,   4,  3,  4,  6,   6,  5,  6,  8), 12, 20),
               10:  ((12, 10,  8,  6,  10,  8,  6,  3,  10,  8,  6,  3,   8,  6,  3,  0),  6,  5),
               11:  ((12, 10,  8,  6,  10,  8,  6,  3,  10,  8,  6,  3,   8,  6,  3,  0), 12,  5),
               12:  ((12, 10,  8,  6,  10,  8,  6,  3,  10,  8,  6,  3,   8,  6,  3,  0), 20,  5),
               13:  (( 1,  2,  3,  4,  12, 13, 14,  5,  11, 16, 15,  6,  10,  9,  8,  7), 19,  5),
               14:  (( 1,  2,  3,  4,  12, 13, 14,  5,  11, 16, 15,  6,  10,  9,  8,  7), 19, 10),
               15:  (( 1,  2,  3,  4,  12, 13, 14,  5,  11, 16, 15,  6,  10,  9,  8,  7), 19, 20)}

# here is the list of enabled layers
layers =      {1: layer_1,
               2: layer_2,
               3: layer_3,
               4: layer_4,
               5: layer_5,
               6: layer_6,
               7: layer_7}

selectors =   {1: keys[1],
               2: keys[2],
               3: keys[3],
               4: keys[4],
               5: keys[5],
               6: keys[6],
               7: keys[7]}

# Define the modifier key and layer selector keys
modifier = keys[0]

# Start on layer 7 (demo)
current_layer = 7

# The colours for each layer
colours = {1: (255,   0, 255),
           2: (  0, 255, 255),
           3: (255, 255,   0),
           4: (128, 255, 128),
           5: (255,   0,   0),
           6: (  0, 255,   0),
           7: (  0,   0, 255)}

layer_keys = range(0, 16)

# dictionary of sets (sets cannot be changed but can be replaced)
LEDs = {0:  ( 64,   0,   0),
        1:  (128,   0,   0),
        2:  (196,   0,   0),
        3:  (255,   0,   0),
        4:  (  0,   4,   0),
        5:  (  0, 128,   0),
        6:  (  0,  12,   0),
        7:  (  0, 196,   0),
        8:  (  0,   0,  64),
        9:  (  0,   0, 128),
        10: (  0,   0, 196),
        11: (  0,   0, 255),
        12: ( 64,  64,   0),
        13: (128, 128,   0),
        14: (196, 196,   0),
        15: (255, 255,   0)}

# Set the LEDs for each key in the current layer
for k in layers[current_layer].keys():
    keys[k].set_led(*colours[current_layer])



# Helper Functions
def readAndSend(fileName):
    # print("fileset/" + fileName)
    with open("fileset/" + fileName, 'r') as readFile:
        # read the file with a for loop
        for line in readFile:
            # print(line)
            layout.write(line.strip())
            keyboard.send(Keycode.ENTER)

# print("Starting!") #print commands output to the serial console, uncomment for debugging
# For demo mode (layer 7)
step = 0
shape = 3
# normal cycle

while True:
    # Always remember to call keybow.update()
    keybow.update()

    # if no key is pressed ensure not locked in layer change mode
    if ((mode == 2) & keybow.none_pressed()):
        mode = 0

    if modifier.held:
        # set to looking to change the keypad layer
        for layer in layers.keys():
            # If the modifier key is held, light up the layer selector keys
            if mode == 1:
                # print("Looking for layer select")
                # Set the LEDs for each key in selectors
                for k in layer_keys:
                    keys[k].set_led(0, 0, 0)
                for k in selectors.keys():
                    keys[k].set_led(*colours[k])
                keys[0].set_led(0, 255, 0)
                mode = 2

            # Change current layer if layer key is pressed
            if selectors[layer].pressed:
                if mode >= 1:
                    mode = 0
                    current_layer = layer
                    # print("Layer Changed:", current_layer)
                    # Set the LEDs for each key in the current layer
                    for k in layer_keys:
                        keys[k].set_led(0, 0, 0)
                    for k in layers[current_layer].keys():
                        keys[k].set_led(*colours[current_layer])
    else:
        # set to look for a key presses
        if mode == 0:
            # print("Looking for key press on layer:", current_layer)
            mode = 1

            if current_layer == 7:
                step += 1
                
                for k in layers[current_layer].keys():
                    keys[k].set_led(*colours[current_layer])
                                        
            else:
                # Set the LEDs for each key in the current layer
                for k in layer_keys:
                    keys[k].set_led(0, 0, 0)
                for k in layers[current_layer].keys():
                    keys[k].set_led(*colours[current_layer])
                    

    # Loop through all of the keys in the layer and if they're pressed, get the
    # key code from the layer's key map
    for k in layers[current_layer].keys():
        if keys[k].pressed:
            key_press = layers[current_layer][k]

            # If the key hasn't just fired (prevents refiring)
            if (not fired) or not (k in set_key_pressed):
                if (not fired):
                    fired = True
                set_key_pressed.add(k)

                # Send the right sort of key press and set debounce for each
                # layer accordingly (layer 2 needs a long debounce)
                if current_layer == 1 or current_layer == 4:
                    debounce = short_debounce
                    keyboard.send(key_press)
                elif current_layer == 2:
                    debounce = 2*long_debounce
                    layout.write(key_press)
                elif current_layer == 3:
                    debounce = short_debounce
                    consumer_control.send(key_press)
                elif current_layer == 5:
                    #TODO: Check that block num is on
                    debounce = long_debounce
                    keyboard.press(Keycode.ALT)
                    for combo_k in key_press:
                        keyboard.press(combo_k)
                        #print(combo_k)
                    keyboard.release_all()
                elif current_layer == 6:
                    debounce = 3 * long_debounce
                    readAndSend(key_press) 
                elif current_layer == 7:
                    debounce = 3 * long_debounce
                    if k!= 0:
                        shape = k
                        #print(shape)
                        
                    #mode = 0
        else:
            set_key_pressed.discard(k)
            


    # Enhanced bounce control:  
    # If enough time has passed, reset the fired variable
    # if the key is released, the variable fired is reset and
    # it is possible to type another key without waiting for the debounce
    # delay    
    if fired and time.monotonic() - keybow.time_of_last_press > debounce:
        fired = False
        set_key_pressed = set()

    if (current_layer == 7) and not keys[0].pressed:
        step += 1
                
        for k in layers[current_layer].keys():
            # print(k) #for debugging purposes
            # Calculate the hue.
            hue = (layer_7[shape][0][k] + (step / layer_7[shape][2])) / layer_7[shape][1]
            hue = hue - int(hue)
            hue = hue - math.floor(hue)
            
            # Convert the hue to RGB values.
            r, g, b = hsv_to_rgb(hue, 1, 1)
            
            # Display it on the key!
            keys[k].set_led(r, g, b)