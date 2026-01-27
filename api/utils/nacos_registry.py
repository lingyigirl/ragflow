#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""Nacos 服务注册模块

提供 RAGFlow 服务注册到 Nacos 注册中心的功能。
支持服务注册、心跳维持、服务注销等完整生命周期管理。
"""

import logging
import os
import socket
import threading
import time
from typing import Optional

try:
    from nacos import NacosClient
    NACOS_AVAILABLE = True
except ImportError:
    NACOS_AVAILABLE = False
    logging.warning("nacos-sdk-python not installed, Nacos integration disabled")

try:
    from common.config_utils import get_base_config
    CONFIG_UTILS_AVAILABLE = True
except ImportError:
    CONFIG_UTILS_AVAILABLE = False
    get_base_config = lambda key, default=None: default
    logging.warning("config_utils not available, using environment variables only")


class NacosRegistry:
    """Nacos 服务注册管理类

    负责 RAGFlow 服务与 Nacos 注册中心的交互，包括：
    - 服务注册与注销
    - 心跳维持
    - 健康检查
    - 服务实例管理

    配置优先级（从高到低）：
        1. 环境变量
        2. YAML 配置文件 (conf/service_conf.yaml)
        3. 代码默认值

    环境变量配置：
        NACOS_SERVER_ADDR: Nacos 服务器地址（默认：127.0.0.1:8848）
        NACOS_SERVICE_NAME: 注册的服务名称（默认：ragflow-service）
        NACOS_NAMESPACE: 命名空间（默认：空字符串）
        NACOS_USERNAME: 认证用户名（默认：nacos）
        NACOS_PASSWORD: 认证密码（默认：nacos）
        NACOS_GROUP: 服务分组（默认：DEFAULT_GROUP）
        SERVICE_IP: 服务实例 IP（默认：自动获取本机 IP）
        SERVICE_PORT: 服务端口（默认：9380）
        NACOS_ENABLED: 启用 Nacos 注册（默认：true）
        NACOS_HEARTBEAT_INTERVAL: 心跳间隔秒数（默认：5）
        NACOS_CLUSTER_NAME: 集群名称（默认：DEFAULT）
        NACOS_SERVICE_WEIGHT: 服务权重（默认：1.0）

    YAML 配置示例 (conf/service_conf.yaml):
        nacos:
          server_addr: '127.0.0.1:8848'
          service_name: 'ragflow-service'
          namespace: ''
          username: 'nacos'
          password: 'nacos'
          group: 'DEFAULT_GROUP'
          enabled: true
          heartbeat_interval: 5
          cluster_name: 'DEFAULT'
          service_weight: 1.0
    """

    def __init__(self):
        """初始化 Nacos 注册配置"""
        self.client: Optional[NacosClient] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()

        # 从 YAML 加载 nacos 配置（如果可用）
        nacos_config = get_base_config("nacos", {}) if CONFIG_UTILS_AVAILABLE else {}

        # 辅助函数：按优先级获取配置（环境变量 > YAML 配置 > 默认值）
        def get_config(env_key: str, yaml_key: Optional[str], default, type_conv=str):
            env_val = os.environ.get(env_key)
            if env_val is not None:
                return type_conv(env_val)
            if yaml_key and nacos_config:
                val = nacos_config.get(yaml_key, default)
                if val is not None:
                    return type_conv(val) if type_conv else val
            return default

        # 从配置读取（优先级：环境变量 > YAML > 默认值）
        self._enabled = get_config("NACOS_ENABLED", "enabled", "true").lower() == "true"
        self.service_name = get_config("NACOS_SERVICE_NAME", "service_name", "ragflow-service")
        self.nacos_server = get_config("NACOS_SERVER_ADDR", "server_addr", "127.0.0.1:8848")
        self.nacos_namespace = get_config("NACOS_NAMESPACE", "namespace", "")
        self.nacos_username = get_config("NACOS_USERNAME", "username", "nacos")
        self.nacos_password = get_config("NACOS_PASSWORD", "password", "nacos")
        self.nacos_group = get_config("NACOS_GROUP", "group", "DEFAULT_GROUP")
        self.service_ip = get_config("SERVICE_IP", None, self._get_local_ip())
        self.service_port = get_config("SERVICE_PORT", None, "9380", int)
        self.heartbeat_interval = get_config("NACOS_HEARTBEAT_INTERVAL", "heartbeat_interval", "5", int)

        # 集群配置
        self.cluster_name = get_config("NACOS_CLUSTER_NAME", "cluster_name", "DEFAULT")
        self.service_weight = get_config("NACOS_SERVICE_WEIGHT", "service_weight", "1.0", float)

        # 输出实际生效的配置（包含环境变量覆盖）
        if self._enabled:
            logging.info(
                f"Nacos configuration loaded (env > YAML > default):\n"
                f"  server_addr: {self.nacos_server}\n"
                f"  service_name: {self.service_name}\n"
                f"  namespace: {self.nacos_namespace or 'empty'}\n"
                f"  group: {self.nacos_group}\n"
                f"  cluster: {self.cluster_name}\n"
                f"  weight: {self.service_weight}\n"
                f"  heartbeat_interval: {self.heartbeat_interval}s\n"
                f"  enabled: {self._enabled}"
            )

    def _get_local_ip(self) -> str:
        """获取本机 IP 地址

        通过创建 UDP socket 连接到外部 DNS 服务器来获取本机 IP。
        这比使用 socket.gethostbyname(socket.gethostname()) 更可靠。

        Returns:
            str: 本机 IP 地址，获取失败时返回 127.0.0.1
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logging.warning(f"Failed to get local IP: {e}, using 127.0.0.1")
            return "127.0.0.1"

    def is_available(self) -> bool:
        """检查 Nacos SDK 是否可用且已启用

        Returns:
            bool: 如果 Nacos SDK 已安装且功能已启用返回 True
        """
        return NACOS_AVAILABLE and self._enabled

    def initialize(self) -> bool:
        """初始化 Nacos 客户端连接

        创建 NacosClient 实例并配置认证信息。

        Returns:
            bool: 初始化成功返回 True，否则返回 False
        """
        if not self.is_available():
            logging.info("Nacos integration is disabled or SDK not available")
            return False

        try:
            self.client = NacosClient(
                server_addresses=self.nacos_server,
                namespace=self.nacos_namespace or "",
                username=self.nacos_username,
                password=self.nacos_password
            )
            logging.info(
                f"Nacos client initialized successfully: "
                f"server={self.nacos_server}, "
                f"service={self.service_name}, "
                f"namespace={self.nacos_namespace or 'default'}"
            )
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Nacos client: {e}")
            self.client = None
            return False

    def register_service(self) -> bool:
        """注册服务到 Nacos 注册中心

        将当前服务实例注册为临时实例（ephemeral=true），
        需要定期发送心跳以维持注册状态。

        Returns:
            bool: 注册成功返回 True，否则返回 False
        """
        if not self.client:
            if not self.initialize():
                return False

        try:
            self.client.add_naming_instance(
                service_name=self.service_name,
                ip=self.service_ip,
                port=self.service_port,
                cluster_name=self.cluster_name,
                weight=self.service_weight,
                ephemeral=True,  # 临时实例，需要心跳维持
                healthy=True,
                enable=True,
                group_name=self.nacos_group
            )
            logging.info(
                f"Service registered to Nacos successfully: "
                f"name={self.service_name}, "
                f"address={self.service_ip}:{self.service_port}, "
                f"group={self.nacos_group}, "
                f"cluster={self.cluster_name}, "
                f"weight={self.service_weight}"
            )
            return True
        except Exception as e:
            logging.error(f"Failed to register service to Nacos: {e}")
            return False

    def deregister_service(self) -> bool:
        """从 Nacos 注册中心注销服务

        主动移除服务实例注册，通常在服务关闭时调用。

        Returns:
            bool: 注销成功返回 True，否则返回 False
        """
        if not self.client:
            return True

        try:
            self.client.remove_naming_instance(
                service_name=self.service_name,
                ip=self.service_ip,
                port=self.service_port,
                group_name=self.nacos_group
            )
            logging.info(
                f"Service deregistered from Nacos: "
                f"name={self.service_name}, "
                f"address={self.service_ip}:{self.service_port}, "
                f"group={self.nacos_group}"
            )
            return True
        except Exception as e:
            logging.error(f"Failed to deregister service from Nacos: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """发送服务心跳

        向 Nacos 发送心跳以维持临时实例的注册状态。
        如果心跳停止超过一定时间，Nacos 会将实例标记为不健康。

        Returns:
            bool: 心跳发送成功返回 True，否则返回 False
        """
        if not self.client:
            return False

        try:
            self.client.send_heartbeat(
                service_name=self.service_name,
                ip=self.service_ip,
                port=self.service_port
            )
            return True
        except Exception as e:
            logging.error(f"Failed to send heartbeat to Nacos: {e}")
            return False

    def start_heartbeat(self):
        """启动心跳线程

        在后台线程中定期发送心跳以维持服务注册状态。
        心跳间隔由 NACOS_HEARTBEAT_INTERVAL 环境变量控制（默认 5 秒）。
        """
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            logging.warning("Heartbeat thread is already running")
            return

        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            daemon=True,
            name="NacosHeartbeat"
        )
        self._heartbeat_thread.start()
        logging.info(
            f"Nacos heartbeat thread started, interval: {self.heartbeat_interval}s"
        )

    def stop_heartbeat(self):
        """停止心跳线程

        设置停止标志并等待心跳线程结束。
        通常在服务关闭前调用。
        """
        if not self._heartbeat_thread or not self._heartbeat_thread.is_alive():
            return

        self._stop_heartbeat.set()
        self._heartbeat_thread.join(timeout=10)
        logging.info("Nacos heartbeat thread stopped")

    def _heartbeat_worker(self):
        """心跳工作线程

        定期调用 send_heartbeat() 发送心跳，
        直到收到停止信号或发生无法恢复的错误。
        """
        while not self._stop_heartbeat.is_set():
            try:
                if not self.send_heartbeat():
                    logging.warning(
                        "Heartbeat failed, will retry in next interval"
                    )
            except Exception as e:
                logging.exception(f"Heartbeat worker error: {e}")

            # 等待指定的间隔时间，或直到收到停止信号
            self._stop_heartbeat.wait(self.heartbeat_interval)

    def get_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> Optional[str]:
        """从 Nacos 配置中心获取配置

        Args:
            data_id: 配置项 ID
            group: 配置分组（默认：DEFAULT_GROUP）

        Returns:
            Optional[str]: 配置内容，获取失败返回 None
        """
        if not self.client:
            return None

        try:
            config = self.client.get_config(data_id, group)
            logging.debug(f"Retrieved config from Nacos: {data_id}/{group}")
            return config
        except Exception as e:
            logging.error(f"Failed to get config from Nacos: {e}")
            return None

    def get_service_instances(self, service_name: Optional[str] = None) -> list:
        """获取服务实例列表

        Args:
            service_name: 服务名称，不指定则使用自身服务名

        Returns:
            list: 服务实例列表，每个实例包含 ip、port、weight 等信息
        """
        if not self.client:
            return []

        name = service_name or self.service_name
        try:
            instances = self.client.list_naming_instance(name)
            logging.debug(f"Retrieved {len(instances)} instances for service: {name}")
            return instances
        except Exception as e:
            logging.error(f"Failed to get service instances from Nacos: {e}")
            return []


# 全局 Nacos 注册实例（延迟初始化，确保环境变量已加载）
_nacos_registry_instance = None
_nacos_lock = threading.Lock()

def get_nacos_registry() -> NacosRegistry:
    """获取 Nacos 注册实例（单例模式，延迟初始化）

    第一次调用时才创建实例，确保环境变量已加载。

    Returns:
        NacosRegistry: Nacos 注册实例
    """
    global _nacos_registry_instance
    if _nacos_registry_instance is None:
        with _nacos_lock:
            # 双重检查锁定
            if _nacos_registry_instance is None:
                _nacos_registry_instance = NacosRegistry()
    return _nacos_registry_instance
