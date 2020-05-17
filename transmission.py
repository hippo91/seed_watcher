import asyncio
from functools import partial
import requests
import sys
import time
from typing import Optional, Mapping, Any, AsyncGenerator


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


async def get_download_speed(transmission_rpc_url: str, delay: int) -> Optional[int]:
    """
    Yields the download speed every delay seconds
    """
    while True:
        stats = await get_transmision_session_stats(transmission_rpc_url)
        try:
            res = stats['downloadSpeed']
        except KeyError:
            res = "Undef"
            pass
        print(f"Download speed is : {res}")
        await asyncio.sleep(delay)

