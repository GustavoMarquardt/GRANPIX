#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

file_path = r"c:\Users\Gustavo Marquardt\Documents\GRANPIX\templates\admin.html"

try:
    # Try reading with different encodings
    content = None
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            print(f"Successfully read with {enc} encoding")
            break
        except Exception as e:
            print(f"Failed with {enc}: {e}")
            continue
    
    if content:
        # Remove the corrupted script tag references that were added
        # Look for any recent script tags that aren't properly formatted
        lines = content.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            # Skip lines that look corrupted or have wrong encoding
            try:
                line.encode('utf-8')
                cleaned_lines.append(line)
            except:
                print(f"Skipping corrupted line {i}: {line[:50]}")
                continue
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Write with UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"File restored successfully. New size: {len(cleaned_content)} bytes")
    else:
        print("Could not read file with any encoding")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
