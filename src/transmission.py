"""
This modules hold functions and classes that interacts with transmission deamon
"""
import asyncio
import sys
from typing import Optional, Mapping, Any, Callable, Awaitable
import aiohttp
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    pass


SessionStats = Mapping[str, Any]


async def get_transmision_session_stats(url: str, username: str, password: str) -> Optional[SessionStats]:  # pylint:disable=line-too-long
    """
    Return the transmission current session stats

    :param url: the transmission rpc url
    :param username: username to connect to transmission rpc
    :param password: password to connect to transmission rpc
    """
    auth = aiohttp.BasicAuth(username, password)
    async with aiohttp.ClientSession(auth=auth) as session:
        response = await session.post(url)
        try:
            session_id = response.headers['X-Transmission-Session-Id']
        except (AttributeError, KeyError):
            print("No session id found!", file=sys.stderr)
            return None

        header = {'x-transmission-session-id': session_id}

        s_stats_request = {
            "method": "session-stats",
            "tag": 42
        }

        response = await session.post(url, json=s_stats_request, headers=header)

        if response.status != 200:
            print("Response on error!", file=sys.stderr)
            return None

        res = await response.json()
        try:
            args: Mapping[str, Any] = res['arguments']
            return args
        except KeyError:
            print("Unable to get arguments!", file=sys.stderr)
            return None


class BlinkingDownloadSpeed:
    """
    This class retrieves the download speed and makes the led blink accordingly
    """
    def __init__(self, led: int, delay: int,  # pylint:disable=too-many-arguments
                 min_frequency: float, max_frequency: float, max_download_speed: int):
        """
        :param led: the pin number corresponding to the led that should blink
        :param delay: period between two measurement of the download speed [s]
        :param min_frequency: minimum blinking frequency [Hz] (download speed is nill)
        :param max_frequency: maximum blinking frequency [Hz] (download speed is max_download_speed)
        :param max_download_speed: maximum downloading speed [B/s]
        """
        self._download_speed = 0
        self._led = led
        self._delay = delay
        self._min_freq = min_frequency
        self._max_freq = max_frequency
        self._max_download_speed = max_download_speed

    async def get_download_speed(self, transmission_stats_getter: Callable[[], Awaitable[Optional[SessionStats]]]) -> Optional[int]:  # pylint:disable=line-too-long
        """
        Yields the download speed every delay seconds
        """
        while True:
            stats = await transmission_stats_getter()
            if stats is None:
                d_speed = 0
            else:
                try:
                    d_speed = stats['downloadSpeed']
                except KeyError:
                    d_speed = 0
            print(f"Download speed is : {d_speed / 1024} kB/s")
            self._download_speed = d_speed
            await asyncio.sleep(self._delay)

    async def blink_led(self):
        """
        The led blinking coroutine for one led.

        Makes the led blinks with a frequency inversely proportionnal
        to the download speed

        Inspired by :
        https://github.com/davesteele/pihut-xmas-asyncio/blob/master/
        """
        GPIO.setup(self._led, GPIO.OUT)

        try:
            while True:
                freq = self._min_freq
                if self._download_speed:
                    freq += ((self._max_freq - self._min_freq) / self._max_download_speed *
                             self._download_speed)
                ontime = offtime = 1. / freq
                GPIO.output(self._led, GPIO.HIGH)
                await asyncio.sleep(ontime)

                GPIO.output(self._led, GPIO.LOW)
                await asyncio.sleep(offtime)
        except asyncio.CancelledError:
            GPIO.setup(self._led, GPIO.IN)
            raise
