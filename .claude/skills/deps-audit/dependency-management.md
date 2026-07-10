# Python 项目依赖全流程审计、锁定版本与离线 wheel 包生成 Skill

## 目标

建立一套适用于通用 Python 项目的依赖管理流程：

1.  审计项目真实依赖
2.  修复项目依赖声明
3.  使用 uv 锁定可复现版本
4.  导出 requirements
5.  生成离线 `.whl` 安装包
6.  验证离线安装能力
7.  保持代码、依赖声明、锁文件、wheel 包一致

------------------------------------------------------------------------

# 一、整体流程

    扫描 import
        ↓
    审计 requirements.txt
        ↓
    检查 pyproject.toml
        ↓
    修复直接依赖声明
        ↓
    uv lock 生成锁文件
        ↓
    uv export 导出固定版本
        ↓
    pip wheel 生成离线 whl
        ↓
    离线安装验证
        ↓
    同步版本并提交

------------------------------------------------------------------------

# 二、依赖审计

## 1. 扫描代码中的 import

目标：

-   找出代码实际使用的第三方库
-   避免漏声明直接依赖
-   避免 requirements.txt 中存在无用依赖

示例：

``` bash
grep -rn "^from\|^import" \
  --include="*.py" \
  app/ src/ tests/ \
  | grep -v "from app\." \
  | grep -v "__future__" \
  | sort -u > imports.txt
```

------------------------------------------------------------------------

## 2. 判断是否属于直接依赖

规则：

  情况               处理
  ------------------ -------------------------
  代码直接 import    必须写入项目依赖
  仅被第三方包使用   不写入直接依赖
  测试代码使用       放入 dev dependencies
  构建工具使用       放入 build dependencies

例如：

错误：

``` text
代码:
import requests

requirements:
没有 requests
```

即使 httpx 间接依赖 requests，也必须声明：

``` text
requests>=版本
```

原因：

直接 import 的库属于项目自身依赖。

------------------------------------------------------------------------

# 三、检查 requirements.txt

检查内容：

## 1. 是否存在缺失依赖

代码：

``` python
import nacos
import requests
import openai
```

requirements 必须存在：

    nacos-sdk-python
    requests
    openai

------------------------------------------------------------------------

## 2. 是否存在多余传递依赖

不要直接添加：

    fonttools
    urllib3
    certifi

除非：

-   项目代码直接使用
-   特殊部署要求
-   离线环境明确需要固定

传递依赖应该由依赖解析工具管理。

------------------------------------------------------------------------

## 3. 检查错误包名

例如：

错误：

    c>=3.0.4

可能是：

-   拼写错误
-   内部包未上传
-   错误复制

必须确认 PyPI 包名称。

------------------------------------------------------------------------

# 四、修复 pyproject.toml

推荐：

-   pyproject.toml 维护范围
-   uv.lock 锁定精确版本
-   requirements.txt 用于部署

示例：

``` toml
[project]
dependencies = [
    "fastapi>=0.115.8",
    "requests>=2.32.0",
    "openai>=0.28.1,<1.0.0"
]


[dependency-groups]
dev = [
    "pytest>=8.3.4"
]
```

原则：

生产依赖：

    >= 最低兼容版本

不要：

    == 固定版本

版本固定交给：

    uv.lock

------------------------------------------------------------------------

# 五、生成 uv.lock

执行：

``` bash
uv lock
```

作用：

生成：

    uv.lock

包含：

-   精确版本
-   hash
-   依赖关系

检查：

如果出现大量异常依赖：

例如：

    scrapy
    twisted

说明某个依赖版本引入了异常依赖链。

------------------------------------------------------------------------

# 六、导出固定 requirements

pip 不读取 uv.lock。

需要转换：

``` bash
uv export \
 --format requirements-txt \
 --no-dev \
 --no-hashes \
 -o requirements_lock.txt
```

得到：

    requirements_lock.txt

例如：

    fastapi==0.115.8
    requests==2.32.3
    openai==0.28.1

------------------------------------------------------------------------

# 七、生成离线 wheel 包

准备目录：

``` bash
rm -rf pip_packages
mkdir pip_packages
```

生成：

``` bash
python3 -m pip wheel \
 -r requirements_lock.txt \
 -w pip_packages
```

结果：

    pip_packages/

    fastapi-xxx.whl
    requests-xxx.whl
    openai-xxx.whl
    ...

这些文件可以复制到无网络服务器。

------------------------------------------------------------------------

# 八、验证 wheel 完整性

## 1. 检查 wheel 内容

``` bash
ls pip_packages
```

确认：

所有 requirements 中的包都有对应 whl。

------------------------------------------------------------------------

## 2. 模拟离线安装

推荐：

``` bash
python3 -m pip install \
 --no-index \
 --find-links=pip_packages \
 --dry-run \
 -r requirements.txt
```

成功应该看到：

    Would install xxx

失败：

    No matching distribution found

说明：

-   wheel 缺失
-   Python版本不匹配
-   平台不匹配
-   requirements版本不一致

------------------------------------------------------------------------

# 九、版本一致性原则

必须保持：

    pyproject.toml
            |
            | uv lock
            ↓

    uv.lock
            |
            | uv export
            ↓

    requirements_lock.txt
            |
            | pip wheel
            ↓

    pip_packages/*.whl


    requirements.txt
    =
    实际 wheel 版本
    =
    uv.lock版本

------------------------------------------------------------------------

# 十、目标服务器离线安装

上传：

    pip_packages/
    requirements.txt

安装：

``` bash
pip install \
 --no-index \
 --find-links=pip_packages \
 -r requirements.txt
```

------------------------------------------------------------------------

# 十一、常见问题

## 1. Python版本不匹配

例如：

本机：

    Python 3.12

服务器：

    Python 3.10

生成的 wheel 可能无法使用。

解决：

在目标环境对应 Python 版本中构建。

------------------------------------------------------------------------

## 2. CPU架构不匹配

例如：

    x86_64

生成：

    numpy_x86_64.whl

无法安装到：

    ARM64

解决：

在目标架构环境生成 wheel。

------------------------------------------------------------------------

## 3. CUDA/GPU依赖

例如：

    torch
    tensorflow

需要确认：

-   CUDA版本
-   驱动版本
-   官方wheel源

------------------------------------------------------------------------

# 十二、Git提交

建议提交：

    pyproject.toml
    uv.lock
    requirements.txt
    .gitignore

忽略：

    pip_packages/
    requirements_lock.txt

.gitignore：

    pip_packages/
    requirements_lock.txt

提交：

``` bash
git add .
git commit -m "chore: update dependency management"
```

------------------------------------------------------------------------

# 十三、最终标准流程

每次发布：

1.  扫描 import
2.  更新 pyproject.toml
3.  uv lock
4.  uv export
5.  pip wheel
6.  离线安装测试
7.  发布代码 + wheel 包

这套流程可以保证 Python 项目：

-   依赖透明
-   版本可复现
-   部署无需联网
-   环境问题可追溯
