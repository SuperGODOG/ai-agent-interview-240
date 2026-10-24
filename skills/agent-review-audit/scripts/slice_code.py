#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

def slice_code(file_path, start_line=1, max_lines=150):
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
        
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    end_line = min(start_line + max_lines - 1, total_lines)
    
    sliced = lines[start_line-1:end_line]
    header = f"# [Sliced View] {file_path} (Lines {start_line}-{end_line} / Total {total_lines})\n"
    return header + "".join(sliced)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(slice_code(path, start))
    else:
        print("Usage: python3 slice_code.py <file_path> [start_line]")
