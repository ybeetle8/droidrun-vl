"""
Android 设备操作工具 - 简化版
"""
import io
import json
import time
import base64
import logging
from typing import Dict, Callable, Optional, List, Any, Tuple
from adbutils import adb
import requests

logger = logging.getLogger(__name__)
PORTAL_DEFAULT_TCP_PORT = 8080


class SimpleAdbTools:
    """简化的 Android 操作工具，移除了上下文管理和不必要的状态"""

    def __init__(
        self,
        serial: str | None = None,
        use_tcp: bool = False,
        remote_tcp_port: int = PORTAL_DEFAULT_TCP_PORT,
    ) -> None:
        """
        初始化 ADB 工具

        Args:
            serial: 设备序列号
            use_tcp: 是否使用 TCP 通信（默认 False，使用 ADB）
            remote_tcp_port: TCP 端口（默认 8080）
        """
        self.device = adb.device(serial=serial)
        self.use_tcp = use_tcp
        self.remote_tcp_port = remote_tcp_port
        self.tcp_forwarded = False

        # UI 元素缓存（用于 tap_by_index）
        self._ui_cache: List[Dict[str, Any]] = []

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
            logger.debug(
                f"Setting up TCP port forwarding for port tcp:{self.remote_tcp_port}"
            )
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

    def _parse_content_provider_output(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """
        解析 ADB content provider 输出

        Args:
            raw_output: ADB 命令的原始输出

        Returns:
            解析后的 JSON 数据
        """
        lines = raw_output.strip().split("\n")

        for line in lines:
            line = line.strip()

            # 查找 "result=" 模式
            if "result=" in line:
                result_start = line.find("result=") + 7
                json_str = line[result_start:]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

            # 备用方案：尝试解析以 { 或 [ 开头的行
            elif line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        # 最后尝试解析整个输出
        try:
            return json.loads(raw_output.strip())
        except json.JSONDecodeError:
            return None

    def _find_element_by_index(
        self, elements: List[Dict], target_index: int
    ) -> Optional[Dict]:
        """递归查找指定 index 的元素"""
        for item in elements:
            if item.get("index") == target_index:
                return item
            children = item.get("children", [])
            result = self._find_element_by_index(children, target_index)
            if result:
                return result
        return None

    def _collect_all_indices(self, elements: List[Dict]) -> List[int]:
        """递归收集所有元素的 index"""
        indices = []
        for item in elements:
            if item.get("index") is not None:
                indices.append(item.get("index"))
            children = item.get("children", [])
            indices.extend(self._collect_all_indices(children))
        return indices

    # ==================== UI 交互方法 ====================

    def tap_by_index(self, index: int) -> str:
        """
        通过索引点击 UI 元素

        Args:
            index: 元素索引

        Returns:
            操作结果描述
        """
        try:
            if not self._ui_cache:
                return "Error: No UI elements cached. Call get_state first."

            element = self._find_element_by_index(self._ui_cache, index)

            if not element:
                indices = sorted(self._collect_all_indices(self._ui_cache))
                indices_str = ", ".join(str(idx) for idx in indices[:20])
                if len(indices) > 20:
                    indices_str += f"... and {len(indices) - 20} more"
                return f"Error: No element found with index {index}. Available indices: {indices_str}"

            bounds_str = element.get("bounds")
            if not bounds_str:
                return f"Error: Element with index {index} has no bounds"

            # 解析 bounds 并计算中心点
            try:
                left, top, right, bottom = map(int, bounds_str.split(","))
            except ValueError:
                return f"Error: Invalid bounds format: {bounds_str}"

            x = (left + right) // 2
            y = (top + bottom) // 2

            # 执行点击
            self.device.click(x, y)
            time.sleep(0.5)

            # 构建响应信息
            response_parts = [
                f"Tapped element with index {index}",
                f"Text: '{element.get('text', 'No text')}'",
                f"Class: {element.get('className', 'Unknown')}",
                f"Coordinates: ({x}, {y})",
            ]

            return " | ".join(response_parts)

        except Exception as e:
            return f"Error: {str(e)}"

    def tap_by_coordinates(self, x: int, y: int) -> str:
        """
        通过坐标点击屏幕

        Args:
            x: X 坐标
            y: Y 坐标

        Returns:
            操作结果
        """
        try:
            self.device.click(x, y)
            logger.debug(f"Tapped at ({x}, {y})")
            return f"Tapped at coordinates ({x}, {y})"
        except Exception as e:
            return f"Error: {str(e)}"

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: float = 300,
    ) -> str:
        """
        执行滑动操作

        Args:
            start_x: 起始 X 坐标
            start_y: 起始 Y 坐标
            end_x: 结束 X 坐标
            end_y: 结束 Y 坐标
            duration_ms: 滑动时长（毫秒）

        Returns:
            操作结果
        """
        try:
            self.device.swipe(start_x, start_y, end_x, end_y, float(duration_ms / 1000))
            time.sleep(duration_ms / 1000)
            logger.debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration_ms}ms"
        except Exception as e:
            return f"Error: {str(e)}"

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 3,
    ) -> str:
        """
        执行拖拽操作

        Args:
            start_x: 起始 X 坐标
            start_y: 起始 Y 坐标
            end_x: 结束 X 坐标
            end_y: 结束 Y 坐标
            duration: 拖拽时长（秒）

        Returns:
            操作结果
        """
        try:
            self.device.drag(start_x, start_y, end_x, end_y, duration)
            time.sleep(duration)
            logger.debug(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration}s"
        except Exception as e:
            return f"Error: {str(e)}"

    def input_text(self, text: str) -> str:
        """
        输入文本

        Args:
            text: 要输入的文本

        Returns:
            操作结果
        """
        try:
            encoded_text = base64.b64encode(text.encode()).decode()

            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                payload = {"base64_text": encoded_text}
                response = requests.post(
                    f"{self.tcp_base_url}/keyboard/input",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if response.status_code != 200:
                    return f"Error: HTTP {response.status_code}: {response.text}"

            else:
                # ADB 方式
                cmd = f'content insert --uri "content://com.droidrun.portal/keyboard/input" --bind base64_text:s:"{encoded_text}"'
                self.device.shell(cmd)

            logger.debug(f"Text input completed: {text[:50]}")
            return f"Text input completed: {text[:50]}{'...' if len(text) > 50 else ''}"

        except Exception as e:
            return f"Error: {str(e)}"

    def press_key(self, keycode: int) -> str:
        """
        按键操作

        Args:
            keycode: Android 按键码
                - 3: HOME
                - 4: BACK
                - 66: ENTER
                - 67: DELETE

        Returns:
            操作结果
        """
        try:
            key_names = {3: "HOME", 4: "BACK", 66: "ENTER", 67: "DELETE"}
            key_name = key_names.get(keycode, str(keycode))

            self.device.keyevent(keycode)
            logger.debug(f"Pressed key {key_name}")
            return f"Pressed key {key_name}"
        except Exception as e:
            return f"Error: {str(e)}"

    def back(self) -> str:
        """
        返回键操作

        Returns:
            操作结果
        """
        return self.press_key(4)

    # ==================== 状态获取方法 ====================

    def get_state(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        获取设备状态（包括 a11y_tree 和 phone_state）

        Returns:
            包含 a11y_tree 和 phone_state 的字典
        """
        try:
            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                response = requests.get(f"{self.tcp_base_url}/state", timeout=10)

                if response.status_code == 200:
                    tcp_response = response.json()

                    if isinstance(tcp_response, dict) and "data" in tcp_response:
                        data_str = tcp_response["data"]
                        try:
                            combined_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            return {
                                "error": "Parse Error",
                                "message": "Failed to parse JSON from TCP response",
                            }
                    else:
                        combined_data = tcp_response
                else:
                    return {
                        "error": "HTTP Error",
                        "message": f"HTTP {response.status_code}",
                    }
            else:
                # ADB 方式
                adb_output = self.device.shell(
                    "content query --uri content://com.droidrun.portal/state"
                )

                state_data = self._parse_content_provider_output(adb_output)

                if state_data is None:
                    return {
                        "error": "Parse Error",
                        "message": "Failed to parse state data",
                    }

                if isinstance(state_data, dict) and "data" in state_data:
                    data_str = state_data["data"]
                    try:
                        combined_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        return {
                            "error": "Parse Error",
                            "message": "Failed to parse JSON from ADB response",
                        }
                else:
                    return {
                        "error": "Format Error",
                        "message": "Unexpected state data format",
                    }

            # 验证数据结构
            if "a11y_tree" not in combined_data:
                return {"error": "Missing Data", "message": "a11y_tree not found"}

            if "phone_state" not in combined_data:
                return {"error": "Missing Data", "message": "phone_state not found"}

            # 过滤并缓存 UI 元素
            elements = combined_data["a11y_tree"]
            filtered_elements = []
            for element in elements:
                filtered_element = {k: v for k, v in element.items() if k != "type"}

                if "children" in filtered_element:
                    filtered_element["children"] = [
                        {k: v for k, v in child.items() if k != "type"}
                        for child in filtered_element["children"]
                    ]

                filtered_elements.append(filtered_element)

            self._ui_cache = filtered_elements

            return {
                "a11y_tree": filtered_elements,
                "phone_state": combined_data["phone_state"],
            }

        except requests.exceptions.RequestException as e:
            return {"error": "TCP Error", "message": str(e)}
        except Exception as e:
            return {"error": str(e), "message": f"Error getting state: {str(e)}"}

    def take_screenshot(self, hide_overlay: bool = True) -> Tuple[str, bytes]:
        """
        截取屏幕

        Args:
            hide_overlay: 是否隐藏覆盖层（默认 True）

        Returns:
            (格式, 图像字节数据)
        """
        try:
            img_format = "PNG"
            image_bytes = None

            if self.use_tcp and self.tcp_forwarded:
                # TCP 方式
                url = f"{self.tcp_base_url}/screenshot"
                if not hide_overlay:
                    url += "?hideOverlay=false"

                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    tcp_response = response.json()

                    if tcp_response.get("status") == "success" and "data" in tcp_response:
                        base64_data = tcp_response["data"]
                        image_bytes = base64.b64decode(base64_data)
                        logger.debug("Screenshot taken via TCP")
                    else:
                        error_msg = tcp_response.get("error", "Unknown error")
                        raise ValueError(f"Screenshot error: {error_msg}")
                else:
                    raise ValueError(f"HTTP {response.status_code}")

            else:
                # ADB 方式
                img = self.device.screenshot()
                img_buf = io.BytesIO()
                img.save(img_buf, format=img_format)
                image_bytes = img_buf.getvalue()
                logger.debug("Screenshot taken via ADB")

            return img_format, image_bytes

        except Exception as e:
            raise ValueError(f"Error taking screenshot: {str(e)}")

    # ==================== 应用管理方法 ====================

    def start_app(self, package: str, activity: str | None = None) -> str:
        """
        启动应用

        Args:
            package: 包名（如 com.android.settings）
            activity: Activity 名称（可选，会自动查找）

        Returns:
            操作结果
        """
        try:
            if not activity:
                dumpsys_output = self.device.shell(
                    f"cmd package resolve-activity --brief {package}"
                )
                activity = dumpsys_output.splitlines()[1].split("/")[1]

            self.device.app_start(package, activity)
            logger.debug(f"Started app: {package}/{activity}")
            return f"App started: {package} with activity {activity}"
        except Exception as e:
            return f"Error: {str(e)}"

    def list_packages(self, include_system_apps: bool = False) -> List[str]:
        """
        列出已安装的应用包

        Args:
            include_system_apps: 是否包含系统应用（默认 False）

        Returns:
            包名列表
        """
        try:
            return self.device.list_packages(["-3"] if not include_system_apps else [])
        except Exception as e:
            logger.error(f"Error listing packages: {e}")
            return []

    def install_app(
        self, apk_path: str, reinstall: bool = False, grant_permissions: bool = True
    ) -> str:
        """
        安装应用

        Args:
            apk_path: APK 文件路径
            reinstall: 是否重新安装
            grant_permissions: 是否授予所有权限

        Returns:
            安装结果
        """
        try:
            import os

            if not os.path.exists(apk_path):
                return f"Error: APK not found at {apk_path}"

            result = self.device.install(
                apk_path,
                nolaunch=True,
                uninstall=reinstall,
                flags=["-g"] if grant_permissions else [],
                silent=True,
            )
            logger.debug(f"Installed app: {apk_path}")
            return result
        except Exception as e:
            return f"Error: {str(e)}"


# ==================== LangGraph 集成函数 ====================


def get_android_tools(
    serial: str | None = None,
    use_tcp: bool = True,
    exclude_tools: list = None,
) -> Dict[str, Callable]:
    """
    获取 Android 操作工具集（返回字典形式供 LangGraph 使用）

    Args:
        serial: 设备序列号
        use_tcp: 是否使用 TCP 连接（默认 True）
        exclude_tools: 要排除的工具列表

    Returns:
        工具字典 {工具名: 工具函数}
    """
    if exclude_tools is None:
        exclude_tools = []

    tools = SimpleAdbTools(serial=serial, use_tcp=use_tcp)

    tool_dict = {
        # UI 交互
        "tap_by_index": tools.tap_by_index,
        "tap_by_coordinates": tools.tap_by_coordinates,
        "swipe": tools.swipe,
        "drag": tools.drag,
        "input_text": tools.input_text,
        "press_key": tools.press_key,
        "back": tools.back,
        # 状态获取
        "get_state": tools.get_state,
        "take_screenshot": tools.take_screenshot,
        # 应用管理
        "start_app": tools.start_app,
        "list_packages": tools.list_packages,
        "install_app": tools.install_app,
    }

    # 移除排除的工具
    for tool_name in exclude_tools:
        tool_dict.pop(tool_name, None)

    return tool_dict


def get_demo_tools(serial: str | None = None, use_tcp: bool = True) -> Dict[str, Callable]:
    """
    获取演示用的精简工具集

    Args:
        serial: 设备序列号
        use_tcp: 是否使用 TCP

    Returns:
        包含常用工具的字典
    """
    all_tools = get_android_tools(serial=serial, use_tcp=use_tcp)

    demo_tools = {
        "tap_by_index": all_tools["tap_by_index"],
        "swipe": all_tools["swipe"],
        "input_text": all_tools["input_text"],
        "get_state": all_tools["get_state"],
    }

    return demo_tools
