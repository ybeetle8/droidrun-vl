"""Test if imports work correctly"""
import sys

print("Testing imports...")

try:
    from src.tools.vision import get_ui_state
    print("[OK] Successfully imported get_ui_state")

    # Check if process_ui_overlaps was imported
    import src.tools.vision as vision_module
    print(f"[OK] vision module file: {vision_module.__file__}")

    # Check if ui_processor is accessible
    try:
        from src.utils.ui_processor import process_ui_overlaps
        print("[OK] Successfully imported process_ui_overlaps directly")
    except Exception as e:
        print(f"[FAIL] Failed to import process_ui_overlaps: {e}")

    # Test with actual data
    import json
    with open('test/xy.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print("\nTesting process_ui_overlaps directly...")
    from src.utils.ui_processor import process_ui_overlaps
    result = process_ui_overlaps(test_data)

    # Check first element
    first = result['data']['a11y_tree'][0]
    print(f"[OK] First element has is_covered: {'is_covered' in first}")
    print(f"  is_covered = {first.get('is_covered')}")
    print(f"  covered_by = {first.get('covered_by')}")

except Exception as e:
    import traceback
    print(f"[FAIL] Error: {e}")
    traceback.print_exc()
