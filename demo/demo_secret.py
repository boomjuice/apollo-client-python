#!/usr/bin/env python
# @Time:2020.09.12
# @author:xhrg
# @email:634789257@qq.com
import os

from apollo_client_python import ApolloClient

apollo_config_url = os.environ.get('APOLLO_CONFIG_URL')

print(apollo_config_url)

client = ApolloClient(app_id='demo-service',
                      cluster='default',
                      config_url=apollo_config_url,
                      secret='cdbb0b1b67d94a63a20f9002c092e6cf')
val = client.get_value('name', default_val='defaultVal')

print(val)
