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


async def blink_led(ledno):
    """
    The led blinking coroutine for one led.

    Inspired by : https://github.com/davesteele/pihut-xmas-asyncio/blob/master/
    """
    ontime = 3
    offtime = 3

    GPIO.setup(ledno, GPIO.OUT)

    try:
        while True:
            GPIO.output(ledno, GPIO.HIGH)
            await asyncio.sleep(ontime)

            GPIO.output(ledno, GPIO.LOW)
            await asyncio.sleep(offtime)
    except asyncio.CancelledError:
        GPIO.setup(ledno, GPIO.IN)

def cleanup():
    GPIO.cleanup()