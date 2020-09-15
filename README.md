# apollo-client-python


## 入门使用:

* 见demo目录

## 功能点：
* apollo配置中心拉取配置
* 支持回调接口
* secret认证
* 支持灰度发布
* 支持本地文件缓存
* 默认开启热更新，参数配置可以不开启热更新
* 同时支持python2.x和python3.x，详情见./apollo/下的python_2x.py和python_3x.py文件

## 注意点:


## 代码更新
* 修改实例化方法ApolloClient，在内部默认启动异步热更新线程，可以通过参数配置不开启热更新。(2020.09.15)
* 修复停机阻塞问题。
* 增加回调接口，增加secret认证，增加demo