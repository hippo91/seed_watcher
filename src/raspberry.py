import asyncio

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    # For the purpose of testing connection to seedbox we may not be on a raspberry
    ON_PI = False

def initialize_gpio(led: int) -> None:
    """
    Initalizes the led

    :param led: led index (BOARD mode)
    """
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(True)
    GPIO.setup(led, GPIO.OUT)

    if GPIO.input(led):
        GPIO.output(led, GPIO.LOW)


def cleanup():
    GPIO.cleanup()