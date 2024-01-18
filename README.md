# pico_stepper
Manage a stepper with a pico using states machine

The stepper is a Nema 14 with 400 steps per revolution. The power interface is a A4988 Polulu module.

* `steps_signal()` send irq and do a step
* `Class Stepper` manage the motor and start the states machine.
* `Class Interrupt` manage the frequency of the step signal to manage the motor speed
