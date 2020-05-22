"""
This modules hold functions and classes that interacts with transmission deamon
"""
import asyncio
from functools import partial
import sys
from typing import Optional, Mapping, Any
import requests
try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    pass


async def get_transmission_session_id(url: str) -> Optional[str]:
    """
    Return the transmission session id

    :param url: the transmission rpc url
    """
    loop = asyncio.get_running_loop()

    session = requests.Session()
    session.auth = requests.auth.HTTPBasicAuth('transmission', 'transmission')

    response = await loop.run_in_executor(None, session.post, url)
    try:
        return response.headers['X-Transmission-Session-Id']
    except (AttributeError, KeyError):
        return None


async def get_transmission_header(session_id: Optional[str]
                                  ) -> Optional[Mapping[str, str]]:
    """
    Return the transmission current session header

    :param session_id: the id of the session
    :return: the session id in a dict
    """
    if not session_id:
        print("No session id found!", file=sys.stderr)
        return None
    return {'x-transmission-session-id': session_id}


async def get_transmision_session_stats(url: str) -> Optional[Mapping[str, Any]]:
    """
    Return the transmission current session stats

    :param url: the transmission rpc url
    """
    s_stats_request = {
        "method": "session-stats",
        "tag": 39693
    }

    session_id = await get_transmission_session_id(url)
    header = await get_transmission_header(session_id)

    if not header:
        print("No header found!", file=sys.stderr)
        return None

    loop = asyncio.get_running_loop()

    session = requests.Session()
    session.auth = requests.auth.HTTPBasicAuth('transmission', 'transmission')
    session_id = await get_transmission_session_id(url)
    headers = await get_transmission_header(session_id)

    p_post = partial(session.post, json=s_stats_request, headers=headers)

    response = await loop.run_in_executor(None, p_post, url)

    if response.status_code != 200:
        print("Response on error!", file=sys.stderr)
        return None

    try:
        res = response.json()['arguments']
        return res
    except (AttributeError, KeyError):
        print("Unable to get arguments!", file=sys.stderr)
        return None


class BlinkingDownloadSpeed:
    """
    This class retrieves the download speed and makes the led blink accordingly
    """
    def __init__(self, led: int, transmission_rpc_url: str, delay: int):
        """
        :param led: the pin number corresponding to the led that should blink
        :param transmission_rpc_url: url address of the transmission rpc
        :param delay: period between two measurement of the download speed
        """
        self.__download_speed = 0
        self.__led = led
        self._transmission_rpc_url = transmission_rpc_url
        self._delay = delay

    async def get_download_speed(self) -> Optional[int]:
        """
        Yields the download speed every delay seconds
        """
        while True:
            stats = await get_transmision_session_stats(self._transmission_rpc_url)
            if stats is None:
                d_speed = 0
            else:
                try:
                    d_speed = stats['downloadSpeed']
                except KeyError:
                    d_speed = 0
            print(f"Download speed is : {d_speed / 1024} kB/s")
            self.__download_speed = d_speed
            await asyncio.sleep(self._delay)

    async def blink_led(self):
        """
        The led blinking coroutine for one led.

        Makes the led blinks with a frequency inversely proportionnal
        to the download speed

        Inspired by :
        https://github.com/davesteele/pihut-xmas-asyncio/blob/master/
        """
        freq_min = 0.5  # Hz
        freq_max = 12  # Hz
        d_speed_max = int(0.75e+06)

        GPIO.setup(self.__led, GPIO.OUT)

        try:
            while True:
                freq = freq_min
                if self.__download_speed:
                    freq += ((freq_max - freq_min) / d_speed_max *
                             self.__download_speed)
                ontime = offtime = 1. / freq
                GPIO.output(self.__led, GPIO.HIGH)
                await asyncio.sleep(ontime)

                GPIO.output(self.__led, GPIO.LOW)
                await asyncio.sleep(offtime)
        except asyncio.CancelledError:
            GPIO.setup(self.__led, GPIO.IN)
