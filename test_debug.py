"""Quick debug test"""
import json
from pathlib import Path
from src.utils.ui_processor import process_ui_overlaps

# Read test data
with open('test/xy.json', 'r', encoding='utf-8') as f:
    ui_state = json.load(f)

print("BEFORE processing:")
first_elem = ui_state['data']['a11y_tree'][0]
print(f"First element keys: {list(first_elem.keys())}")
print(f"Has is_covered: {'is_covered' in first_elem}")

# Process
processed = process_ui_overlaps(ui_state)

print("\nAFTER processing:")
first_elem_after = processed['data']['a11y_tree'][0]
print(f"First element keys: {list(first_elem_after.keys())}")
print(f"Has is_covered: {'is_covered' in first_elem_after}")
print(f"is_covered value: {first_elem_after.get('is_covered')}")
print(f"covered_by value: {first_elem_after.get('covered_by')}")

# Check children
if 'children' in first_elem_after and len(first_elem_after['children']) > 0:
    child = first_elem_after['children'][0]
    print(f"\nFirst child keys: {list(child.keys())}")
    print(f"Child is_covered: {child.get('is_covered')}")
    print(f"Child covered_by: {child.get('covered_by')}")

# Count covered elements
def count_covered(node, stats=None):
    if stats is None:
        stats = {'total': 0, 'covered': 0}
    if 'index' in node:
        stats['total'] += 1
        if node.get('is_covered'):
            stats['covered'] += 1
    for child in node.get('children', []):
        count_covered(child, stats)
    return stats

stats = {'total': 0, 'covered': 0}
for root in processed['data']['a11y_tree']:
    count_covered(root, stats)

print(f"\nSTATISTICS:")
print(f"Total elements: {stats['total']}")
print(f"Covered elements: {stats['covered']}")
print(f"Coverage rate: {stats['covered']/stats['total']*100:.1f}%")
