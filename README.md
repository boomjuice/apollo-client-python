# apollo-client-python

## 安装使用:
```shell
pip install apollo-client-python
```

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
* 【已经废弃,换为不带缓存接口,原因见代码更新】本项目获取配置使用的是缓存接口，而非实时拉取数据库接口，详情见：https://github.com/ctripcorp/apollo/wiki/%E5%85%B6%E5%AE%83%E8%AF%AD%E8%A8%80%E5%AE%A2%E6%88%B7%E7%AB%AF%E6%8E%A5%E5%85%A5%E6%8C%87%E5%8D%97

## 代码更新
* 修改实例化方法ApolloClient，在内部默认启动异步热更新线程，可以通过参数配置不开启热更新。(2020.09.15)
* 修复停机阻塞问题。
* 增加回调接口，增加secret认证，增加demo
* 修改获取配置的接口改为不带缓存的接口。如果使用缓存接口，config有多个节点的时候，可能A通知更新，但是B的缓存没有更新到。
* 增加心跳机制。增加心跳机制，如果不增加心跳机制，apollo的ui界面可能看不到实例。
* 2021-03-23 修复创建文件夹异常，1.py2并发创建文件夹会抛出异常
