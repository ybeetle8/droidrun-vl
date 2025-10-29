#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADB Content Provider Tool
支持query和insert操作的ADB命令行工具
"""
import subprocess
import json
import sys
import re
import os
import argparse
import shlex

# 设置输出编码
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')  # 设置控制台为UTF-8


def run_adb_content_query(uri):
    """运行adb content query命令"""
    try:
        cmd = ["adb", "shell", "content", "query", "--uri", uri]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True)
        if result.stdout:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as e:
        print(f"ADB查询命令执行失败: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("错误: 未找到adb命令，请确保ADB已安装并在PATH中", file=sys.stderr)
        return None


def run_adb_content_insert(uri, bindings):
    """运行adb content insert命令"""
    try:
        cmd = ["adb", "shell", "content", "insert", "--uri", uri]
        
        # 添加绑定参数
        for binding in bindings:
            cmd.extend(["--bind", binding])
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=True)
        if result.stdout:
            return result.stdout.strip()
        return "操作完成"
    except subprocess.CalledProcessError as e:
        print(f"ADB插入命令执行失败: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("错误: 未找到adb命令，请确保ADB已安装并在PATH中", file=sys.stderr)
        return None


def parse_json_output(output):
    """解析ADB输出中的JSON数据"""
    if not output:
        return None
    
    # 检查是否是query命令的result格式
    match = re.search(r'result=({.*})$', output)
    if match:
        result_str = match.group(1)
        try:
            # 解析外层JSON
            result_json = json.loads(result_str)
            
            # 检查是否有data字段需要进一步解析
            if "data" in result_json and isinstance(result_json["data"], str):
                try:
                    # 将转义的JSON字符串转换为实际的JSON对象
                    data_json = json.loads(result_json["data"])
                    result_json["data"] = data_json
                except json.JSONDecodeError:
                    pass  # 如果data不是JSON格式，保持原样
            
            return result_json
        except json.JSONDecodeError as e:
            print(f"警告: JSON解析失败: {e}", file=sys.stderr)
            return {"raw_output": output}
    
    # 如果不是JSON格式，返回原始输出
    return {"raw_output": output}


def cmd_query(args):
    """处理query子命令"""
    print(f"查询URI: {args.uri}")
    result = run_adb_content_query(args.uri)
    
    if result is None:
        sys.exit(1)
    
    # 解析并输出JSON
    parsed_result = parse_json_output(result)
    if parsed_result:
        print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
    else:
        print("无返回数据")


def cmd_insert(args):
    """处理insert子命令"""
    print(f"插入URI: {args.uri}")
    
    bindings = []
    if args.bind:
        bindings = args.bind
    
    if bindings:
        print(f"绑定参数: {bindings}")
    
    result = run_adb_content_insert(args.uri, bindings)
    
    if result is None:
        sys.exit(1)
    
    # 解析并输出结果
    parsed_result = parse_json_output(result)
    if parsed_result:
        print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
    else:
        print("操作完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="ADB Content Provider工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # query子命令
    query_parser = subparsers.add_parser('query', help='查询content provider')
    query_parser.add_argument('--uri', required=True, help='Content URI')
    
    # insert子命令
    insert_parser = subparsers.add_parser('insert', help='插入到content provider')
    insert_parser.add_argument('--uri', required=True, help='Content URI')
    insert_parser.add_argument('--bind', action='append', help='绑定参数，格式：key:type:value')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'query':
        cmd_query(args)
    elif args.command == 'insert':
        cmd_insert(args)


if __name__ == "__main__":
    main()