import asyncio
from functools import partial
import requests
import sys
import time
from typing import Optional, Mapping, Any, AsyncGenerator
try:
    import RPi.GPIO as GPIO
except:
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


async def get_transmission_header(url: str, session_id: Optional[str]) -> Optional[Mapping[str, str]]:
    """
    Return the transmission current session header

    :param url: the transmission rpc url
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
    header = await get_transmission_header(url, session_id)

    if not header:
        print("No header found!", file=sys.stderr)
        return None

    loop = asyncio.get_running_loop()

    session = requests.Session()
    session.auth = requests.auth.HTTPBasicAuth('transmission', 'transmission')
    session_id = await get_transmission_session_id(url)
    headers = await get_transmission_header(url, session_id)

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
    def __init__(self, led: int):
        self.__download_speed = 0
        self.__led = led

    async def get_download_speed(self, transmission_rpc_url: str, delay: int) -> Optional[int]:
        """
        Yields the download speed every delay seconds
        """
        while True:
            stats = await get_transmision_session_stats(transmission_rpc_url)
            if stats is None:
                d_speed = 0.
            try:
                d_speed = stats['downloadSpeed']
            except KeyError:
                d_speed = 0.
                pass
            print(f"Download speed is : {d_speed}")
            self.__download_speed = d_speed
            await asyncio.sleep(delay)

    async def blink_led(self):
        """
        The led blinking coroutine for one led.

        Makes the led blinks with a frequency inversely proportionnal to the dowload speed

        Inspired by : https://github.com/davesteele/pihut-xmas-asyncio/blob/master/
        """
        ontime = 0.5
        d_speed_max = int(0.75e+06)
        
        GPIO.setup(self.__led, GPIO.OUT)

        try:
            while True:
                if self.__download_speed:
                    offtime = d_speed_max / self.__download_speed * ontime
                else: 
                    offtime = 100 * ontime
                GPIO.output(self.__led, GPIO.HIGH)
                await asyncio.sleep(ontime)

                GPIO.output(self.__led, GPIO.LOW)
                await asyncio.sleep(offtime)
        except asyncio.CancelledError:
            GPIO.setup(self.__led, GPIO.IN)