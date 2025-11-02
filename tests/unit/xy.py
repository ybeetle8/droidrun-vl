"""Parse UI tree JSON and detect overlapping elements"""
import json
from typing import List, Dict, Tuple, Set


def parse_bounds(bounds_str: str) -> Dict[str, int]:
    """Parse bounds string into coordinate dictionary"""
    coords = bounds_str.split(', ')
    return {
        'left': int(coords[0]),
        'top': int(coords[1]),
        'right': int(coords[2]),
        'bottom': int(coords[3])
    }


def is_overlap(b1: Dict[str, int], b2: Dict[str, int]) -> bool:
    """Check if two boundaries overlap"""
    return not (b1['right'] <= b2['left'] or
               b1['left'] >= b2['right'] or
               b1['bottom'] <= b2['top'] or
               b1['top'] >= b2['bottom'])


def get_center(bounds: Dict[str, int]) -> Tuple[int, int]:
    """Get the center point of bounds"""
    center_x = (bounds['left'] + bounds['right']) // 2
    center_y = (bounds['top'] + bounds['bottom']) // 2
    return (center_x, center_y)


def is_point_in_bounds(point: Tuple[int, int], bounds: Dict[str, int]) -> bool:
    """Check if a point is within bounds"""
    x, y = point
    return (bounds['left'] <= x <= bounds['right'] and
            bounds['top'] <= y <= bounds['bottom'])


def is_covered_by(b1: Dict[str, int], b2: Dict[str, int]) -> bool:
    """Check if the center point of b1 is covered by b2"""
    center = get_center(b1)
    return is_point_in_bounds(center, b2)


def flatten_tree(node: Dict, elements: List[Dict] = None) -> List[Dict]:
    """Flatten tree structure into a list"""
    if elements is None:
        elements = []

    # Add current node (if it has an index)
    if 'index' in node:
        elements.append({
            'index': node['index'],
            'bounds': node['bounds'],
            'className': node.get('className', ''),
            'text': node.get('text', ''),
            'resourceId': node.get('resourceId', '')
        })

    # Recursively process child nodes
    for child in node.get('children', []):
        flatten_tree(child, elements)

    return elements


def find_overlaps(elements: List[Dict]) -> List[Tuple[int, int]]:
    """
    Find all covered elements
    Returns: [(covered index, covering index), ...]
    """
    overlaps = []
    covered_indices: Set[int] = set()

    # Sort by index, elements with larger index are rendered on top
    sorted_elements = sorted(elements, key=lambda x: x['index'])

    for i, elem1 in enumerate(sorted_elements):
        b1 = parse_bounds(elem1['bounds'])

        # Check if later elements (with larger index) cover the current element
        for elem2 in sorted_elements[i+1:]:
            b2 = parse_bounds(elem2['bounds'])

            if is_covered_by(b1, b2):
                # elem1 is covered by elem2
                if elem1['index'] not in covered_indices:
                    overlaps.append((elem1, elem2))
                    covered_indices.add(elem1['index'])
                    # Only record the first element that covers it
                    break

    return overlaps


def main():
    # Read JSON file
    with open('test/xy.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Get a11y_tree
    a11y_tree = data['data']['a11y_tree']

    # Flatten tree structure
    all_elements = []
    for root in a11y_tree:
        all_elements.extend(flatten_tree(root))

    print(f"Found {len(all_elements)} elements in total\n")

    # Find overlaps
    overlaps = find_overlaps(all_elements)

    print(f"Found {len(overlaps)} covered elements:\n")
    print("=" * 80)

    for covered, covering in overlaps:
        print(f"index:{covered['index']} is blocked by index:{covering['index']}")
        print(f"  Covered element: {covered['className']} - {covered['text'][:30]}")
        print(f"    bounds: {covered['bounds']}")
        print(f"  Covering element: {covering['className']} - {covering['text'][:30]}")
        print(f"    bounds: {covering['bounds']}")
        print("-" * 80)


if __name__ == '__main__':
    main()
