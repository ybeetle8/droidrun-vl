"""解析 UI 树 JSON 并检测重叠元素"""
import json
from typing import List, Dict, Tuple, Set


def parse_bounds(bounds_str: str) -> Dict[str, int]:
    """解析 bounds 字符串为坐标字典"""
    coords = bounds_str.split(', ')
    return {
        'left': int(coords[0]),
        'top': int(coords[1]),
        'right': int(coords[2]),
        'bottom': int(coords[3])
    }


def is_overlap(b1: Dict[str, int], b2: Dict[str, int]) -> bool:
    """检查两个边界是否重叠"""
    return not (b1['right'] <= b2['left'] or
               b1['left'] >= b2['right'] or
               b1['bottom'] <= b2['top'] or
               b1['top'] >= b2['bottom'])


def get_center(bounds: Dict[str, int]) -> Tuple[int, int]:
    """获取边界的中心点"""
    center_x = (bounds['left'] + bounds['right']) // 2
    center_y = (bounds['top'] + bounds['bottom']) // 2
    return (center_x, center_y)


def is_point_in_bounds(point: Tuple[int, int], bounds: Dict[str, int]) -> bool:
    """检查点是否在边界内"""
    x, y = point
    return (bounds['left'] <= x <= bounds['right'] and
            bounds['top'] <= y <= bounds['bottom'])


def is_covered_by(b1: Dict[str, int], b2: Dict[str, int]) -> bool:
    """检查 b1 的中心点是否被 b2 覆盖"""
    center = get_center(b1)
    return is_point_in_bounds(center, b2)


def flatten_tree(node: Dict, elements: List[Dict] = None) -> List[Dict]:
    """将树形结构扁平化为列表"""
    if elements is None:
        elements = []

    # 添加当前节点（如果有 index）
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


def find_overlaps(elements: List[Dict]) -> List[Tuple[int, int]]:
    """
    找出所有被覆盖的元素
    返回: [(被覆盖的index, 覆盖它的index), ...]
    """
    overlaps = []
    covered_indices: Set[int] = set()

    # 按 index 排序，index 大的元素渲染在上层
    sorted_elements = sorted(elements, key=lambda x: x['index'])

    for i, elem1 in enumerate(sorted_elements):
        b1 = parse_bounds(elem1['bounds'])

        # 检查后面的元素（index 更大的）是否覆盖当前元素
        for elem2 in sorted_elements[i+1:]:
            b2 = parse_bounds(elem2['bounds'])

            if is_covered_by(b1, b2):
                # elem1 被 elem2 覆盖
                if elem1['index'] not in covered_indices:
                    overlaps.append((elem1, elem2))
                    covered_indices.add(elem1['index'])
                    # 只记录第一个覆盖它的元素
                    break

    return overlaps


def main():
    # 读取 JSON 文件
    with open('test/xy.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取 a11y_tree
    a11y_tree = data['data']['a11y_tree']

    # 扁平化树结构
    all_elements = []
    for root in a11y_tree:
        all_elements.extend(flatten_tree(root))

    print(f"总共找到 {len(all_elements)} 个元素\n")

    # 查找重叠
    overlaps = find_overlaps(all_elements)

    print(f"发现 {len(overlaps)} 个被覆盖的元素:\n")
    print("=" * 80)

    for covered, covering in overlaps:
        print(f"index:{covered['index']} 被 index:{covering['index']} 挡住了")
        print(f"  被覆盖元素: {covered['className']} - {covered['text'][:30]}")
        print(f"    bounds: {covered['bounds']}")
        print(f"  覆盖元素: {covering['className']} - {covering['text'][:30]}")
        print(f"    bounds: {covering['bounds']}")
        print("-" * 80)


if __name__ == '__main__':
    main()
