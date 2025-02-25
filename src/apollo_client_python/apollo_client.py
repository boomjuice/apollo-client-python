import hashlib
import json
import logging
import os
import threading
import time
from urllib import parse

from .constants import CONFIGURATIONS
from .constants import NAMESPACE_NAME
from .constants import NOTIFICATION_ID
from .utils import get_value_from_dict
from .utils import http_request
from .utils import init_ip
from .utils import no_key_cache_key
from .utils import signature
from .logs import logger

class ApolloClient:

    def __init__(self,
                 config_url,
                 app_id,
                 cluster='default',
                 secret='',
                 namespaces='application',
                 start_hot_update=True,
                 change_listener=None):

        # 核心路由参数
        self.config_url = config_url
        self.cluster = cluster
        self.app_id = app_id

        # 非核心参数
        self.ip = init_ip()
        self.secret = secret

        # 检查参数变量

        # 私有控制变量
        self._cycle_time = 2
        self._stopping = False
        self._cache = {}
        self._no_key = {}
        self._hash = {}
        self._pull_timeout = 75
        self._cache_file_path = os.path.expanduser(
            '~') + '/data/apollo_client_python/cache/'
        self._long_poll_thread = None
        self._change_listener = change_listener  # "add" "delete" "update"
        if namespaces:
            self._notification_map = {ns: -1 for ns in namespaces.split(',')}
        else:
            self._notification_map = {'application': -1}
        self.last_release_key = None
        # 私有启动方法
        self._path_checker()
        if start_hot_update:
            self._start_hot_update()

        # 缓存预热
        self._refesh_notification_map()

        # 启动心跳线程
        heartbeat = threading.Thread(target=self._heartBeat)
        heartbeat.setDaemon(True)
        heartbeat.start()

    def get_json_from_net(self, namespace='application'):
        url = '{}/configs/{}/{}/{}?releaseKey={}&ip={}'.format(
            self.config_url, self.app_id, self.cluster, namespace, '', self.ip)
        try:
            code, body = http_request(url,
                                      timeout=3,
                                      headers=self._signHeaders(url))
            if code == 200:
                data = json.loads(body)
                data = data[CONFIGURATIONS]
                return_data = {CONFIGURATIONS: data}
                return return_data
            else:
                return None
        except Exception as e:
            logger.error(str(e))
            return None

    def get_value(self, key, default_val=None, namespace='application'):
        try:
            # 读取内存配置
            namespace_cache = self._cache.get(namespace)
            val = get_value_from_dict(namespace_cache, key)
            if val is not None:
                return val

            no_key = no_key_cache_key(namespace, key)
            if no_key in self._no_key:
                return default_val

            # 读取网络配置
            namespace_data = self.get_json_from_net(namespace)
            val = get_value_from_dict(namespace_data, key)
            if val is not None:
                self._update_cache_and_file(namespace_data, namespace)
                return val

            # 读取文件配置
            namespace_cache = self._get_local_cache(namespace)
            val = get_value_from_dict(namespace_cache, key)
            if val is not None:
                self._update_cache_and_file(namespace_cache, namespace)
                return val

            # 如果全部没有获取，则把默认值返回，设置本地缓存为None
            self._set_local_cache_none(namespace, key)
            return default_val
        except Exception as e:
            logger.error(
                'get_value has error, [key is %s], [namespace is %s], [error is %s], ',
                key, namespace, e)
            return default_val

    def get_config(self):
        configs = {}
        for config in self._cache.values():
            configs.update(**config[CONFIGURATIONS])
        return configs

    # 设置某个namespace的key为none，这里不设置default_val，是为了保证函数调用实时的正确性。
    # 假设用户2次default_val不一样，然而这里却用default_val填充，则可能会有问题。
    def _set_local_cache_none(self, namespace, key):
        no_key = no_key_cache_key(namespace, key)
        self._no_key[no_key] = key

    def _start_hot_update(self):
        self._long_poll_thread = threading.Thread(target=self._listener)
        # 启动异步线程为守护线程，主线程推出的时候，守护线程会自动退出。
        self._long_poll_thread.setDaemon(True)
        self._long_poll_thread.start()

    def stop(self):
        self._stopping = True
        logger.info('Stopping listener...')

    # 调用设置的回调函数，如果异常，直接try掉
    def _call_listener(self, namespace, old_kv, new_kv):
        if self._change_listener is None:
            return
        if old_kv is None:
            old_kv = {}
        if new_kv is None:
            new_kv = {}
        try:
            for key in old_kv:
                new_value = new_kv.get(key)
                old_value = old_kv.get(key)
                if new_value is None:
                    # 如果newValue 是空，则表示key，value被删除了。
                    self._change_listener('delete', namespace, key, old_value)
                    continue
                if new_value != old_value:
                    self._change_listener('update', namespace, key, new_value)
                    continue
            for key in new_kv:
                new_value = new_kv.get(key)
                old_value = old_kv.get(key)
                if old_value is None:
                    self._change_listener('add', namespace, key, new_value)
        except BaseException as e:
            logger.warning(str(e))

    def _path_checker(self):
        if not os.path.isdir(self._cache_file_path):
            os.makedirs(self._cache_file_path, exist_ok=True)

    # 更新本地缓存和文件缓存
    def _update_cache_and_file(self, namespace_data, namespace='application'):
        # 更新本地缓存
        self._cache[namespace] = namespace_data
        # 更新文件缓存
        new_string = json.dumps(namespace_data)
        new_hash = hashlib.md5(new_string.encode('utf-8')).hexdigest()
        if self._hash.get(namespace) == new_hash:
            pass
        else:
            with open(
                    os.path.join(
                        self._cache_file_path,
                        f'{self.app_id}_configuration_{namespace}.txt'),
                    'w') as f:
                f.write(new_string)
            self._hash[namespace] = new_hash

    # 从本地文件获取配置
    def _get_local_cache(self, namespace='application'):
        cache_file_path = os.path.join(
            self._cache_file_path,
            f'{self.app_id}_configuration_{namespace}.txt')
        if os.path.isfile(cache_file_path):
            with open(cache_file_path) as f:
                result = json.loads(f.readline())
            return result
        return {}

    def _long_poll(self):
        notifications = []
        for key in self._cache:
            namespace_data = self._cache[key]
            notification_id = -1
            if NOTIFICATION_ID in namespace_data:
                notification_id = self._cache[key][NOTIFICATION_ID]
            notifications.append({
                NAMESPACE_NAME: key,
                NOTIFICATION_ID: notification_id
            })
        try:
            # 如果长度为0直接返回
            if len(notifications) == 0:
                return
            url = f'{self.config_url}/notifications/v2'
            params = {
                'appId': self.app_id,
                'cluster': self.cluster,
                'notifications': json.dumps(notifications, ensure_ascii=False)
            }
            param_str = parse.urlencode(params)
            url = url + '?' + param_str
            code, body = http_request(url,
                                      self._pull_timeout,
                                      headers=self._signHeaders(url))
            http_code = code
            if http_code == 304:
                logger.debug('No change, loop...')
                return
            if http_code == 200:
                data = json.loads(body)
                for entry in data:
                    namespace = entry[NAMESPACE_NAME]
                    n_id = entry[NOTIFICATION_ID]
                    logger.info(
                        '%s has changes: notificationId=%d', namespace, n_id)
                    self._get_net_and_set_local(namespace,
                                                n_id,
                                                call_change=True)
                    return
            else:
                logger.warning('Sleep...')
        except Exception as e:
            logger.warning(str(e))

    def _get_net_and_set_local(self, namespace, n_id, call_change=False):
        namespace_data = self.get_json_from_net(namespace)
        namespace_data[NOTIFICATION_ID] = n_id
        old_namespace = self._cache.get(namespace)
        self._update_cache_and_file(namespace_data, namespace)
        if self._change_listener is not None and call_change:
            old_kv = old_namespace.get(CONFIGURATIONS)
            new_kv = namespace_data.get(CONFIGURATIONS)
            self._call_listener(namespace, old_kv, new_kv)

    def _listener(self):
        logger.info('start long_poll')
        while not self._stopping:
            self._long_poll()
            time.sleep(self._cycle_time)
        logger.info('stopped, long_poll')

    # 给header增加加签需求
    def _signHeaders(self, url):
        headers = {}
        if self.secret == '':
            return headers
        uri = url[len(self.config_url):len(url)]
        time_unix_now = str(int(round(time.time() * 1000)))
        headers['Authorization'] = 'Apollo ' + self.app_id + ':' + signature(
            time_unix_now, uri, self.secret)
        headers['Timestamp'] = time_unix_now
        return headers

    def _heartBeat(self):
        while not self._stopping:
            self._refesh_notification_map()
            time.sleep(60 * 10)  # 10分钟

    def _refesh_notification_map(self):
        for namespace in self._notification_map:
            self._do_heartBeat(namespace)

    def _do_heartBeat(self, namespace):
        url = '{}/configs/{}/{}/{}?ip={}'.format(self.config_url, self.app_id,
                                                 self.cluster, namespace,
                                                 self.ip)
        try:
            code, body = http_request(url,
                                      timeout=3,
                                      headers=self._signHeaders(url))
            if code == 200:
                data = json.loads(body)
                if self.last_release_key == data['releaseKey']:
                    return None
                self.last_release_key = data['releaseKey']
                self._update_cache_and_file(data, namespace)
            else:
                return None
        except Exception as e:
            logger.error(str(e))
            return None
