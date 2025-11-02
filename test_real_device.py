"""Test with real device"""
import sys
from src.tools.vision import get_ui_state
from src.utils.config import Config

config = Config()

print("Getting UI state from device...")
try:
    ui_state = get_ui_state(use_tcp=config.use_tcp)
except Exception as e:
    print(f"ERROR getting UI state: {e}")
    sys.exit(1)

print(f"\nUI state keys: {ui_state.keys()}")

if 'data' in ui_state:
    print(f"Data keys: {ui_state['data'].keys()}")

    if 'a11y_tree' in ui_state['data']:
        tree = ui_state['data']['a11y_tree']
        print(f"A11y tree length: {len(tree)}")

        if len(tree) > 0:
            first = tree[0]
            print(f"\nFirst element keys: {list(first.keys())}")
            print(f"Has is_covered: {'is_covered' in first}")

            if 'is_covered' in first:
                print(f"is_covered = {first['is_covered']}")
                print(f"covered_by = {first['covered_by']}")
            else:
                print("ERROR: is_covered field is MISSING!")

                # Debug: check if process_ui_overlaps is being called
                print("\nDirect test of process_ui_overlaps:")
                from src.utils.ui_processor import process_ui_overlaps
                processed = process_ui_overlaps(ui_state)
                first_processed = processed['data']['a11y_tree'][0]
                print(f"After manual processing: {list(first_processed.keys())}")
                print(f"Has is_covered now: {'is_covered' in first_processed}")
