import base64
import hashlib
import hmac
import socket
import urllib.request
from urllib.error import HTTPError

from .constants import CONFIGURATIONS
from .logs import logger

def http_request(url, timeout, headers=None):
    if headers is None:
        headers = {}
    try:
        request = urllib.request.Request(url, headers=headers)
        res = urllib.request.urlopen(request, timeout=timeout)
        body = res.read().decode('utf-8')
        return res.code, body
    except HTTPError as e:
        if e.code == 304:
            logger.warning(
                'http_request error,code is 304, maybe you should check secret')
            return 304, None
        logger.warning(
            'http_request error,code is %d, msg is %s', e.code, e.msg)
        raise e


# 对时间戳，uri，秘钥进行加签
def signature(timestamp, uri, secret):
    string_to_sign = '' + timestamp + '\n' + uri
    hmac_code = hmac.new(secret.encode(), string_to_sign.encode(),
                         hashlib.sha1).digest()
    return base64.b64encode(hmac_code).decode()


def no_key_cache_key(namespace, key):
    return f'{namespace}{len(namespace)}{key}'


# 返回是否获取到的值，不存在则返回None
def get_value_from_dict(namespace_cache, key):
    if namespace_cache:
        kv_data = namespace_cache.get(CONFIGURATIONS)
        if kv_data is None:
            return None
        if key in kv_data:
            return kv_data[key]
    return None


def init_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 53))
        ip = s.getsockname()[0]
        return ip
    finally:
        s.close()
