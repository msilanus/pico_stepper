###############################################################################
#
# Manage a stepper motor using PIO program and state machine
# 
# Author : MS
# Version : 0
# Date : 19/01/2023
#
# sources : https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
#           https://blog.leonti.dev/controlling-stepper-with-pio-on-raspberry-pi-pico/
#           https://github.com/raspberrypi/pico-micropython-examples/tree/master/pio
#
# steps_signal(): PIO program make a step with adjustable periode
#                 and causes an IRQ
# class Interrupt : manage IRQ - compute the periode of a step
#                   count steps - manage acceleration and deceleration ramps
# class Stepper : manage the stepper motor
###############################################################################

import time
from machine import Pin
import rp2


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def steps_signal():
    irq(rel(0)) # causes an interruption
    
    pull(noblock) # pull the latest data into osr or put current x into osr if queue is empty
    mov(x, osr) # copy osr into x
    mov(y, x) # copy x into y to reset later
    
    # High level
    set(pins, 1)
    label("delay_high")
    jmp(x_dec, "delay_high") # loop and decrement x until it's 0
    
    mov(x, y)  # restore x, which is 0 at this point
    # Low level
    set(pins, 0)
    label("delay_low")
    jmp(x_dec, "delay_low") # loop and decrement x until it's 0
    mov(x, y)  # restore x, which is 0 at this point

class Interrupt:
    '''
    class Interrupt :
        - param :
            - motor : stepper instance
            - steps : number of steps to do
        - public members :
            - interruption(sm) : do a new step - sm is the state machine
    '''
    def __init__(self, motor, steps):
        self.__steps = steps
        self.__final = steps
        self.__motor = motor
        self.__final_speed = self.__motor.get_steps_per_second()
        self.__speed = 0
        self.__acc = 0
        
    def interruption(self, sm):
        self.__steps -= 1
        motor_total_steps = self.__motor.get_total_steps()
        steps = self.__final - self.__steps
        limit = 800
        if self.__final <= limit:
            limit = self.__final//10
            #print(limit)
        step = limit//10
        if 0 <= steps <= limit \
           and steps % (step)==0 \
           and self.__acc < step:
            self.__acc +=1
            self.__speed = self.__acc*self.__final_speed//10
            #print(self.acc, steps, self.__speed)
            delay = abs(round(50000 / self.__speed))
            self.__motor.sm.put(delay)
            
        
        if 0 <= self.__steps <=limit \
           and steps % (step)==0 \
           and self.__acc > 1:
            self.__acc -=1
            self.__speed = self.__acc*self.__final_speed//10 
            #print(self.acc, self.__steps, self.__speed)
            delay = abs(round(50000 / self.__speed))
            self.__motor.sm.put(delay)
        
                
        if  self.__motor.get_direction()== 0:
            self.__motor.set_total_steps(motor_total_steps+1)
        else:
            self.__motor.set_total_steps(motor_total_steps-1)
        
        
        if self.__steps<=0:
            self.__motor.stop()
    
    def __call__(self, sm):
        """
        This enables the possibility to call the instance directly.
        """
        self.interruption(sm)


class Stepper:
    '''
    class Stepper :
        - param :
            - dir_pin  : GPIO direction   -> pin DIR (8) A4988
            - step_pin : GPIO step signal -> pin STEP(7) A4988
        - public members :
            - sm : state machine uses to make step signal
            - get_direction() : return rotation direction (0 or 1)
            - set_direction(direction) : set the rotation direction (0 or 1)
            - set_steps_per_second(steps_per_second) : set the speed rotation
            - get_steps_per_second() : get the instant speed rotation
            - goto(steps) : move to steps
            - stop() : disable state machine - instant end of rotation
            - get_total_steps() : get the total steps done by the motor
            - set_total_steps(st) : set the total steps done by the motor
            - is_running(self): is the state machine running ? return True or False
    '''
    def __init__(self, dir_pin, step_pin):
        self.__dir_pin = Pin(dir_pin, Pin.OUT)
        self.sm = rp2.StateMachine(0, steps_signal, freq=100000, set_base=Pin(step_pin))        
        self.__total_steps = 0
        self.__sps = 0
        self.__direction = 0
        self.__is_runnig = False

    def get_direction(self):
        return self.__direction
    
    def set_direction(self, direction):
        self.__direction = direction
        if direction == 0:
            self.__dir_pin.high()
        else:
            self.__dir_pin.low()
    
    def set_steps_per_second(self, steps_per_second):
        self.__sps = steps_per_second

        if self.__sps == 0:
            delay = 0
        else:
            if self.__sps >= 0:
                self.set_direction(0)
            else:
                self.set_direction(1)

        
    def get_steps_per_second(self):
        return self.__sps
        
    def goto(self, steps):
        self.my_interrupt = Interrupt(self, steps) 
        self.sm.irq(self.my_interrupt)
        self.sm.active(1)
        self.__is_running = True
    
    def stop(self):
        self.sm.active(0)
        self.__is_running = False

    
    def get_total_steps(self):
        return self.__total_steps
    
    def set_total_steps(self, st):
        self.__total_steps = st
        
    def is_running(self):
        return self.__is_running

motor = Stepper(2, 3)

end = False
pulsation = 0
old_steps = 0
while not end:
    pulsation = int(input("Vitesse en pas/s ? "))
    motor.set_steps_per_second(pulsation)
    
    nb_pas = int(input("Nombre de pas ? "))
    motor.goto(nb_pas)
    
    end = input("Quit (O/N) ? ")
    if end=="O" :
        end = True
        motor.stop()
    else:
        total_steps = motor.get_total_steps()
        print('total_steps :',total_steps)
        while  motor.is_running():
            pass
        end = False

        
    print("Total steps = ", motor.get_total_steps())

