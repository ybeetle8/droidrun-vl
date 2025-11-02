"""
Android 设备控制器

基于 droidrun + adbutils 的异步设备操作封装
"""

import asyncio
import base64
import io
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from adbutils import adb
from loguru import logger

from .execution_result import ExecutionResult

PORTAL_DEFAULT_TCP_PORT = 8080


class AndroidController:
    """
    Android 设备控制器（异步）

    提供完整的设备操作能力：
    - UI 交互（tap, swipe, input 等）
    - 查询操作（screenshot, get_ui_tree 等）
    - 应用管理（start_app, list_packages 等）

    所有方法均为异步，返回 ExecutionResult 或直接抛出异常
    """

    def __init__(
        self,
        serial: Optional[str] = None,
        use_tcp: bool = False,
        remote_tcp_port: int = PORTAL_DEFAULT_TCP_PORT,
    ) -> None:
        """
        初始化 Android 控制器

        Args:
            serial: 设备序列号（None 表示使用默认设备）
            use_tcp: 是否使用 TCP 通信（默认 False，使用 ADB）
            remote_tcp_port: TCP 端口（默认 8080）
        """
        self.device = adb.device(serial=serial)
        self.use_tcp = use_tcp
        self.remote_tcp_port = remote_tcp_port
        self.tcp_forwarded = False

        # UI 元素缓存（用于 tap_by_index）
        self._ui_cache: List[Dict[str, Any]] = []

        logger.info(f"AndroidController initialized (serial={serial}, use_tcp={use_tcp})")

        # 初始化设置
        self._init_sync()

    def _init_sync(self) -> None:
        """同步初始化（键盘、TCP 转发）"""
        # 设置键盘
        self._setup_keyboard()

        # TCP 转发设置
        if self.use_tcp:
            self._setup_tcp_forward()

    def _setup_keyboard(self) -> bool:
        """设置 DroidRun 键盘为默认输入法"""
        try:
            self.device.shell("ime enable com.droidrun.portal/.DroidrunKeyboardIME")
            self.device.shell("ime set com.droidrun.portal/.DroidrunKeyboardIME")
            logger.debug("DroidRun keyboard setup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to setup DroidRun keyboard: {e}")
            return False

    def _setup_tcp_forward(self) -> bool:
        """设置 ADB TCP 端口转发"""
        try:
            logger.debug(f"Setting up TCP port forwarding for port tcp:{self.remote_tcp_port}")
            self.local_tcp_port = self.device.forward_port(self.remote_tcp_port)
            self.tcp_base_url = f"http://localhost:{self.local_tcp_port}"
            logger.debug(f"TCP forwarding setup: {self.tcp_base_url}")

            # 测试连接
            response = requests.get(f"{self.tcp_base_url}/ping", timeout=5)
            if response.status_code == 200:
                logger.debug("TCP connection test successful")
                self.tcp_forwarded = True
                return True
            else:
                logger.warning(f"TCP test failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to setup TCP forwarding: {e}")
            self.tcp_forwarded = False
            return False

    def _teardown_tcp_forward(self) -> bool:
        """移除 TCP 端口转发"""
        try:
            if self.tcp_forwarded:
                cmd = f"killforward:tcp:{self.local_tcp_port}"
                c = self.device.open_transport(cmd)
                c.close()
                self.tcp_forwarded = False
                logger.debug("TCP forwarding removed")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to remove TCP forwarding: {e}")
            return False

    def __del__(self):
        """清理资源"""
        if hasattr(self, "tcp_forwarded") and self.tcp_forwarded:
            self._teardown_tcp_forward()

    # ========================================
    # UI 交互方法（异步）
    # ========================================

    async def tap(self, x: int, y: int) -> ExecutionResult:
        """
        点击坐标

        Args:
            x: X 坐标
            y: Y 坐标

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 点击失败时抛出异常
        """
        start_time = time.time()

        try:
            # 在线程池中执行同步操作
            await asyncio.to_thread(self.device.click, x, y)
            await asyncio.sleep(0.1)  # 短暂等待

            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Tapped at ({x}, {y})")

            return ExecutionResult.success_result(
                message=f"Tapped at ({x}, {y})",
                operation="tap",
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Failed to tap at ({x}, {y}): {e}")
            raise RuntimeError(f"Tap failed: {e}") from e

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> ExecutionResult:
        """
        滑动操作

        Args:
            start_x: 起始 X 坐标
            start_y: 起始 Y 坐标
            end_x: 结束 X 坐标
            end_y: 结束 Y 坐标
            duration_ms: 滑动时长（毫秒）

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 滑动失败时抛出异常
        """
        start_time = time.time()

        try:
            duration_sec = duration_ms / 1000
            await asyncio.to_thread(
                self.device.swipe, start_x, start_y, end_x, end_y, duration_sec
            )
            await asyncio.sleep(duration_sec)

            total_duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")

            return ExecutionResult.success_result(
                message=f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})",
                operation="swipe",
                duration_ms=total_duration_ms,
                data={
                    "start": (start_x, start_y),
                    "end": (end_x, end_y),
                    "duration_ms": duration_ms,
                },
            )

        except Exception as e:
            logger.error(f"Failed to swipe: {e}")
            raise RuntimeError(f"Swipe failed: {e}") from e

    async def input_text(self, text: str) -> ExecutionResult:
        """
        输入文本

        Args:
            text: 要输入的文本

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 输入失败时抛出异常
        """
        start_time = time.time()

        try:
            encoded_text = base64.b64encode(text.encode()).decode()

            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                payload = {"base64_text": encoded_text}
                response = await asyncio.to_thread(
                    requests.post,
                    f"{self.tcp_base_url}/keyboard/input",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

            else:
                # ADB 方式
                cmd = f'content insert --uri "content://com.droidrun.portal/keyboard/input" --bind base64_text:s:"{encoded_text}"'
                await asyncio.to_thread(self.device.shell, cmd)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Text input completed: {text[:50]}")

            return ExecutionResult.success_result(
                message=f"Input text: {text[:50]}{'...' if len(text) > 50 else ''}",
                operation="input_text",
                duration_ms=duration_ms,
                data={"text": text, "length": len(text)},
            )

        except Exception as e:
            logger.error(f"Failed to input text: {e}")
            raise RuntimeError(f"Input text failed: {e}") from e

    async def press_back(self) -> ExecutionResult:
        """
        按返回键

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 按键失败时抛出异常
        """
        return await self.press_key(4, "BACK")

    async def press_home(self) -> ExecutionResult:
        """
        按 Home 键

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 按键失败时抛出异常
        """
        return await self.press_key(3, "HOME")

    async def press_key(self, keycode: int, key_name: Optional[str] = None) -> ExecutionResult:
        """
        按键操作

        Args:
            keycode: Android 按键码
            key_name: 按键名称（可选，用于日志）

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 按键失败时抛出异常
        """
        start_time = time.time()

        try:
            await asyncio.to_thread(self.device.keyevent, keycode)

            duration_ms = int((time.time() - start_time) * 1000)

            key_display = key_name or str(keycode)
            logger.debug(f"Pressed key {key_display}")

            return ExecutionResult.success_result(
                message=f"Pressed key {key_display}",
                operation="press_key",
                duration_ms=duration_ms,
                data={"keycode": keycode, "key_name": key_name},
            )

        except Exception as e:
            logger.error(f"Failed to press key {keycode}: {e}")
            raise RuntimeError(f"Press key failed: {e}") from e

    # ========================================
    # 查询方法（异步）
    # ========================================

    async def screenshot(self) -> ExecutionResult:
        """
        截取屏幕

        Returns:
            ExecutionResult，data 字段包含 "image_bytes" 和 "format"

        Raises:
            RuntimeError: 截屏失败时抛出异常
        """
        start_time = time.time()

        try:
            image_bytes = None
            img_format = "PNG"

            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                url = f"{self.tcp_base_url}/screenshot?hideOverlay=true"
                response = await asyncio.to_thread(requests.get, url, timeout=10)

                if response.status_code == 200:
                    tcp_response = response.json()

                    if tcp_response.get("status") == "success" and "data" in tcp_response:
                        base64_data = tcp_response["data"]
                        image_bytes = base64.b64decode(base64_data)
                        logger.debug("Screenshot taken via TCP")
                    else:
                        error_msg = tcp_response.get("error", "Unknown error")
                        raise RuntimeError(f"Screenshot error: {error_msg}")
                else:
                    raise RuntimeError(f"HTTP {response.status_code}")

            else:
                # ADB 方式
                img = await asyncio.to_thread(self.device.screenshot)
                img_buf = io.BytesIO()
                img.save(img_buf, format=img_format)
                image_bytes = img_buf.getvalue()
                logger.debug("Screenshot taken via ADB")

            duration_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult.success_result(
                message=f"Screenshot taken ({len(image_bytes)} bytes)",
                operation="screenshot",
                duration_ms=duration_ms,
                data={
                    "image_bytes": image_bytes,
                    "format": img_format,
                    "size": len(image_bytes),
                },
            )

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise RuntimeError(f"Screenshot failed: {e}") from e

    async def get_ui_tree(self) -> ExecutionResult:
        """
        获取 UI 树（无障碍树）

        Returns:
            ExecutionResult，data 字段包含 "a11y_tree" 和 "phone_state"

        Raises:
            RuntimeError: 获取 UI 树失败时抛出异常
        """
        start_time = time.time()

        try:
            combined_data = None

            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                response = await asyncio.to_thread(
                    requests.get, f"{self.tcp_base_url}/state", timeout=10
                )

                if response.status_code == 200:
                    tcp_response = response.json()

                    if isinstance(tcp_response, dict) and "data" in tcp_response:
                        data_str = tcp_response["data"]
                        combined_data = json.loads(data_str)
                    else:
                        combined_data = tcp_response
                else:
                    raise RuntimeError(f"HTTP {response.status_code}")

            else:
                # ADB 方式
                adb_output = await asyncio.to_thread(
                    self.device.shell, "content query --uri content://com.droidrun.portal/state"
                )

                state_data = self._parse_content_provider_output(adb_output)

                if state_data is None:
                    raise RuntimeError("Failed to parse state data")

                if isinstance(state_data, dict) and "data" in state_data:
                    data_str = state_data["data"]
                    combined_data = json.loads(data_str)
                else:
                    raise RuntimeError("Unexpected state data format")

            # 验证数据结构
            if "a11y_tree" not in combined_data:
                raise RuntimeError("a11y_tree not found in state data")

            if "phone_state" not in combined_data:
                raise RuntimeError("phone_state not found in state data")

            # 过滤并缓存 UI 元素
            elements = combined_data["a11y_tree"]
            filtered_elements = self._filter_ui_elements(elements)
            self._ui_cache = filtered_elements

            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"UI tree fetched ({len(filtered_elements)} elements)")

            return ExecutionResult.success_result(
                message=f"UI tree fetched ({len(filtered_elements)} elements)",
                operation="get_ui_tree",
                duration_ms=duration_ms,
                data={
                    "a11y_tree": filtered_elements,
                    "phone_state": combined_data["phone_state"],
                },
            )

        except Exception as e:
            logger.error(f"Failed to get UI tree: {e}")
            raise RuntimeError(f"Get UI tree failed: {e}") from e

    # ========================================
    # 应用管理方法（异步）
    # ========================================

    async def start_app(self, package: str, activity: Optional[str] = None) -> ExecutionResult:
        """
        启动应用

        Args:
            package: 包名（如 com.android.settings）
            activity: Activity 名称（可选，会自动查找）

        Returns:
            ExecutionResult

        Raises:
            RuntimeError: 启动失败时抛出异常
        """
        start_time = time.time()

        try:
            if not activity:
                dumpsys_output = await asyncio.to_thread(
                    self.device.shell, f"cmd package resolve-activity --brief {package}"
                )
                activity = dumpsys_output.splitlines()[1].split("/")[1]

            await asyncio.to_thread(self.device.app_start, package, activity)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Started app: {package}/{activity}")

            return ExecutionResult.success_result(
                message=f"App started: {package}",
                operation="start_app",
                duration_ms=duration_ms,
                data={"package": package, "activity": activity},
            )

        except Exception as e:
            logger.error(f"Failed to start app {package}: {e}")
            raise RuntimeError(f"Start app failed: {e}") from e

    # ========================================
    # 辅助方法
    # ========================================

    def _parse_content_provider_output(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """解析 ADB content provider 输出"""
        lines = raw_output.strip().split("\n")

        for line in lines:
            line = line.strip()

            if "result=" in line:
                result_start = line.find("result=") + 7
                json_str = line[result_start:]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

            elif line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        try:
            return json.loads(raw_output.strip())
        except json.JSONDecodeError:
            return None

    def _filter_ui_elements(self, elements: List[Dict]) -> List[Dict]:
        """过滤 UI 元素（移除 type 字段）"""
        filtered = []
        for element in elements:
            filtered_element = {k: v for k, v in element.items() if k != "type"}

            if "children" in filtered_element:
                filtered_element["children"] = self._filter_ui_elements(
                    filtered_element["children"]
                )

            filtered.append(filtered_element)

        return filtered


# 全局实例（单例）
_controller: Optional[AndroidController] = None


def get_android_controller(
    serial: Optional[str] = None, use_tcp: bool = False
) -> AndroidController:
    """
    获取全局 AndroidController 实例（单例）

    Args:
        serial: 设备序列号
        use_tcp: 是否使用 TCP

    Returns:
        AndroidController 实例
    """
    global _controller
    if _controller is None:
        _controller = AndroidController(serial=serial, use_tcp=use_tcp)
    return _controller


if __name__ == "__main__":
    import asyncio

    async def test():
        """测试 AndroidController"""
        print("=" * 50)
        print("AndroidController 测试")
        print("=" * 50)

        controller = AndroidController(use_tcp=False)

        # 测试点击
        print("\n[测试 1] 点击")
        result = await controller.tap(100, 200)
        print(result.model_dump_json(indent=2))

        # 测试截屏
        print("\n[测试 2] 截屏")
        result = await controller.screenshot()
        print(f"Screenshot: {result.message}, size: {result.data['size']} bytes")

        # 测试 UI 树
        print("\n[测试 3] UI 树")
        result = await controller.get_ui_tree()
        print(f"UI Tree: {result.message}")

        print("\n" + "=" * 50)
        print("测试完成!")
        print("=" * 50)

    asyncio.run(test())
