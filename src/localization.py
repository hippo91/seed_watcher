"""
This module holds functions that deal with ip localization of the seed box
"""
import asyncio
import json
import sys
from typing import Optional
try:
    import RPi.GPIO as GPIO
except ImportError:
    pass


async def get_ip_localisation(seed_box_user: str,
                              seed_box_addr: str) -> Optional[str]:
    """
    Return the public ip country name

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: the public ip country name
    """
    cmd = (f'ssh {seed_box_user}@{seed_box_addr} '
           'curl -s https://ipvigilante.com')
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if stdout:
        res_d = json.loads(stdout)
        if res_d['status'] != 'success':
            return None
        return res_d['data']['country_name']

    print("Unable to get ip localization", file=sys.stderr)
    print(f"Error is {stderr.decode()}", file=sys.stderr)
    return None


async def check_licit_ip(seed_box_user: str,
                         seed_box_addr: str) -> bool:
    """
    Return True if the public ip country name is licit

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: True if the public ip country name is licit (false otherwise)
    """
    loc = await get_ip_localisation(seed_box_user, seed_box_addr)
    if not loc or loc not in ('Germany', 'Netherlands'):
        return False
    return True


class BlinkingLocalization:
    """
    This class checks the localization and make leds blink accordingly
    """
    def __init__(self, led_ok: int, led_ko: int,  # pylint: disable=too-many-arguments
                 seed_box_user: str, seed_box_addr: str, delay: int):
        """
        :param led_ok: pin number corresponding to the led that will blink
                       if localization is ok
        :param led_ko: pin number corresponding to the led that will blink
                       if localization is not ok
        :param seed_box_user: user name on the seed box
        :param seed_box_addr: address of the seed box on the internal network
        :param delay: refreshing delay
        """
        self._licit_ip = False
        self._led_ok = led_ok
        self._led_ko = led_ko
        self._seed_box_user = seed_box_user
        self._seed_box_addr = seed_box_addr
        self._delay = delay

    async def check_localisation_status(self) -> bool:
        """
        Check the localisation status every delay seconds

        :return: True if the public ip country name is licit (false otherwise)
        """
        while True:
            self._licit_ip = await check_licit_ip(self._seed_box_user, self._seed_box_addr)
            print(f"Ip address is licit : {self._licit_ip}")
            await asyncio.sleep(self._delay)

    async def blink_led(self):
        """
        The led blinking coroutine for one led.

        If the ip address is licit lights on led_ok
        otherwise makes the led_ko blink

        Inspired by :
        https://github.com/davesteele/pihut-xmas-asyncio/blob/master/
        """
        ontime = 0.5
        offtime = 0.5

        GPIO.setup(self._led_ok, GPIO.OUT)
        GPIO.setup(self._led_ko, GPIO.OUT)

        try:
            while True:
                if self._licit_ip:
                    GPIO.output(self._led_ko, GPIO.LOW)
                    GPIO.output(self._led_ok, GPIO.HIGH)
                    await asyncio.sleep(ontime)
                else:
                    GPIO.output(self._led_ok, GPIO.LOW)
                    GPIO.output(self._led_ko, GPIO.HIGH)
                    await asyncio.sleep(ontime)

                    GPIO.output(self._led_ko, GPIO.LOW)
                    await asyncio.sleep(offtime)
        except asyncio.CancelledError:
            GPIO.setup(self._led_ok, GPIO.IN)
            GPIO.setup(self._led_ko, GPIO.IN)
