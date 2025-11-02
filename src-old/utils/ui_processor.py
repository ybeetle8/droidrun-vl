"""
UI 树处理工具
处理 UI 元素重叠检测等功能
"""
from typing import Dict, List, Set, Tuple


def parse_bounds(bounds_str: str) -> Dict[str, int]:
    """
    解析 bounds 字符串为坐标字典

    Args:
        bounds_str: 格式如 "0, 79, 110, 195"

    Returns:
        坐标字典 {'left': x1, 'top': y1, 'right': x2, 'bottom': y2}
    """
    coords = bounds_str.split(', ')
    return {
        'left': int(coords[0]),
        'top': int(coords[1]),
        'right': int(coords[2]),
        'bottom': int(coords[3])
    }


def get_center(bounds: Dict[str, int]) -> Tuple[int, int]:
    """
    获取 bounds 的中心点坐标

    Args:
        bounds: 坐标字典

    Returns:
        (center_x, center_y)
    """
    center_x = (bounds['left'] + bounds['right']) // 2
    center_y = (bounds['top'] + bounds['bottom']) // 2
    return (center_x, center_y)


def is_point_in_bounds(point: Tuple[int, int], bounds: Dict[str, int]) -> bool:
    """
    检查点是否在 bounds 内

    Args:
        point: (x, y) 坐标
        bounds: 坐标字典

    Returns:
        是否在 bounds 内
    """
    x, y = point
    return (bounds['left'] <= x <= bounds['right'] and
            bounds['top'] <= y <= bounds['bottom'])


def is_covered_by(b1: Dict[str, int], b2: Dict[str, int]) -> bool:
    """
    检查 b1 的中心点是否被 b2 覆盖

    Args:
        b1: 元素1的坐标
        b2: 元素2的坐标

    Returns:
        b1 是否被 b2 覆盖
    """
    center = get_center(b1)
    return is_point_in_bounds(center, b2)


def flatten_tree(node: Dict, elements: List[Dict] = None) -> List[Dict]:
    """
    将树结构扁平化为列表

    Args:
        node: UI 树节点
        elements: 累积的元素列表

    Returns:
        扁平化的元素列表
    """
    if elements is None:
        elements = []

    # 添加当前节点
    if 'index' in node:
        elements.append({
            'index': node['index'],
            'bounds': node['bounds'],
            'className': node.get('className', ''),
            'text': node.get('text', ''),
            'resourceId': node.get('resourceId', '')
        })

    # 递归处理子节点
    for child in node.get('children', []):
        flatten_tree(child, elements)

    return elements


def find_covered_elements(elements: List[Dict]) -> Dict[int, int]:
    """
    找出所有被遮挡的元素

    Args:
        elements: 扁平化的元素列表

    Returns:
        字典 {被遮挡元素的index: 遮挡它的元素index}
    """
    covered_map = {}
    covered_indices: Set[int] = set()

    # 按 index 排序，index 大的元素在上层
    sorted_elements = sorted(elements, key=lambda x: x['index'])

    for i, elem1 in enumerate(sorted_elements):
        b1 = parse_bounds(elem1['bounds'])

        # 检查后面的元素（index 更大的）是否遮挡当前元素
        for elem2 in sorted_elements[i+1:]:
            b2 = parse_bounds(elem2['bounds'])

            if is_covered_by(b1, b2):
                # elem1 被 elem2 遮挡
                if elem1['index'] not in covered_indices:
                    covered_map[elem1['index']] = elem2['index']
                    covered_indices.add(elem1['index'])
                    # 只记录第一个遮挡它的元素
                    break

    return covered_map


def add_overlap_info_to_node(node: Dict, covered_map: Dict[int, int]) -> None:
    """
    递归地为节点添加遮挡信息

    Args:
        node: UI 树节点
        covered_map: 遮挡关系映射
    """
    if 'index' in node:
        index = node['index']
        if index in covered_map:
            node['is_covered'] = True
            node['covered_by'] = covered_map[index]
        else:
            node['is_covered'] = False
            node['covered_by'] = None

    # 递归处理子节点
    for child in node.get('children', []):
        add_overlap_info_to_node(child, covered_map)


def process_ui_overlaps(ui_state: Dict) -> Dict:
    """
    处理 UI 状态数据，添加元素重叠信息

    Args:
        ui_state: 原始 UI 状态数据（来自 get_ui_state）
                 支持两种格式：
                 1. {'a11y_tree': [...], ...}  (真实设备格式)
                 2. {'data': {'a11y_tree': [...]}, ...}  (测试文件格式)

    Returns:
        添加了 is_covered 和 covered_by 字段的 UI 状态数据
    """
    # 获取 a11y_tree（兼容两种格式）
    a11y_tree = None

    # 格式1: 直接包含 a11y_tree (真实设备)
    if 'a11y_tree' in ui_state:
        a11y_tree = ui_state['a11y_tree']

    # 格式2: 嵌套在 data 中 (测试文件)
    elif 'data' in ui_state and 'a11y_tree' in ui_state['data']:
        a11y_tree = ui_state['data']['a11y_tree']

    # 如果找不到 a11y_tree，直接返回
    if not a11y_tree:
        return ui_state

    # 扁平化树结构
    all_elements = []
    for root in a11y_tree:
        all_elements.extend(flatten_tree(root))

    # 找出遮挡关系
    covered_map = find_covered_elements(all_elements)

    # 为每个节点添加遮挡信息
    for root in a11y_tree:
        add_overlap_info_to_node(root, covered_map)

    return ui_state
