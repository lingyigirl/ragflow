"""
RAGFlow 自定义扩展模块（非上游代码）。

本目录存放团队对 RAGFlow 的定制功能，所有新增代码与上游源码隔离。

约定：
- 每个子目录是一个独立的扩展模块
- 尽量通过 hook 方式（try/except import）与上游衔接
- 上游文件的侵入性修改用 `# [自定义]` 标记

当前模块：
- mineru_v2/    : MinerU content_list_v2.json 解析与独立存储链路
"""
