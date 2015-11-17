# SWIM #
Static WIkipedia Mirror

## 运行必须的软件 ##

  * Python -- http://www.python.org/
  * Xapian -- http://www.xapian.org/
  * Django -- http://www.djangoproject.com/
  * mwlib -- http://code.pediapress.com/wiki/

## 可选的软件 ##

  * latex
  * dvips -- 以上两个软件用来生成数学公式。

## 运行环境 ##

  * Linux/UNIX系统。

## 配置SWIM ##

1. 下载SWIM

2. 使用向导功能建立镜像系统::

```
  $ python swim.py -W
```

2.1 列出可供下载的数据库

> 输入L，列出所有可供下载的数据库备份::

```
  ...
  2007-11-28 20:10:13     zhwiki/20071119
  2007-11-29 13:53:20     zhwikibooks/20071129
  2007-11-29 14:07:16     zhwikinews/20071129
  2007-11-29 14:17:17     zhwikiquote/20071129
  2007-11-29 15:44:00     zhwikisource/20071129
  2007-11-30 06:19:55     zhwiktionary/20071130
  ...
```

> 每行为一个数据库的备份时间，以及数据库的备份名称。

2.2 下载一个数据库

> 从上面的列表中选择一个数据库，把名称传给SWIM下载该文件。
> 例如，下载中文维基百科的备份文件::

```
  zhwiki/20071119
```

> 下载完成之后，向导自动对文件进行检索，在当前目录建立查询数据库。

3. 启动web服务::

```
  $ cd mywiki
  $ python manager runserver
```

> 访问 http://127.0.0.1:8000/ 浏览百科条目

## TODO ##

  * 为个人使用提供更简单的web服务，把Django改为备选方案
  * 条目链接区分显示已编写、未编写条目
  * 添加维基百科使用的javascript
  * 增加配置文件，保存设置参数
  * 条目自动重定向，显示条目重定向来源
  * 改进中文条目名称搜索
  * 中文繁简转换支持
  * 制作Windows版本
  * 支持多语言版本
  * 运行中添加或更新条目及索引
  * 把配置向导功能集成进web界面