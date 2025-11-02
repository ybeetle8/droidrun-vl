"""
测试 UI 元素重叠检测功能
使用 test/xy.json 作为测试数据
"""
import json
import sys
import os
from pathlib import Path

# 使用 src 包导入
from src.utils.ui_processor import process_ui_overlaps


def count_covered_elements(node: dict, count: dict = None) -> dict:
    """递归统计被遮挡的元素"""
    if count is None:
        count = {'covered': 0, 'total': 0}

    if 'index' in node:
        count['total'] += 1
        if node.get('is_covered', False):
            count['covered'] += 1
            print(f"  ✗ index:{node['index']:3d} 被遮挡 (被 index:{node.get('covered_by')} 遮挡) - {node.get('className', '')} - {node.get('text', '')[:30]}")

    for child in node.get('children', []):
        count_covered_elements(child, count)

    return count


def main():
    """测试主函数"""
    print("=" * 100)
    print("🧪 UI 元素重叠检测测试")
    print("=" * 100)
    print()

    # 读取测试数据
    json_path = Path("test/xy.json")
    if not json_path.exists():
        print(f"❌ 测试文件不存在: {json_path}")
        return

    print(f"📂 读取测试数据: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        ui_state = json.load(f)

    print("✅ 数据加载成功\n")

    # 处理重叠检测
    print("🔍 开始检测元素重叠...")
    processed_state = process_ui_overlaps(ui_state)
    print("✅ 重叠检测完成\n")

    # 统计结果
    print("📊 检测结果:")
    print("-" * 100)

    count = {'covered': 0, 'total': 0}
    for root in processed_state['data']['a11y_tree']:
        count_covered_elements(root, count)

    print("-" * 100)
    print(f"\n📈 统计:")
    print(f"  总元素数: {count['total']}")
    print(f"  被遮挡数: {count['covered']}")
    print(f"  遮挡比例: {count['covered']/count['total']*100:.1f}%")

    # 保存处理后的结果（可选）
    output_path = Path("test/xy_processed.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_state, f, ensure_ascii=False, indent=2)
    print(f"\n💾 处理后的数据已保存: {output_path}")

    print("\n" + "=" * 100)
    print("✅ 测试完成！")
    print("=" * 100)


if __name__ == "__main__":
    main()
