#!/usr/bin/env python3
"""CLI utility for Ethornell (BGI) visual novel script localization.
Matches VNTextPatch usage:
  python ethornell_tool.py extractlocal <infile|infolder> <scriptfile.xlsx>
  python ethornell_tool.py insertlocal <infile|infolder> <scriptfile.xlsx> <outfile|outfolder> [sjis_ext.bin]
"""

import os
import sys
import argparse
from typing import List, Dict

# Fix Windows console UTF-8 output if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ethornell_py import (
    EthornellScript,
    ExcelHandler,
    CharacterNames,
    SjisTunnelEncoding,
    default_sjis_tunnel,
    MonospaceWordWrapper,
    ProportionalWordWrapper,
    NoOpWordWrapper
)


def extract_local(args):
    input_path = os.path.abspath(args.input)
    text_path = os.path.abspath(args.output_table)

    names_xml_path = os.path.join(os.path.dirname(text_path), "names.xml")
    char_names = CharacterNames(names_xml_path)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "VNTextPatch.Shared", "template.xlsx")
    if not os.path.exists(template_path):
        template_path = None

    scripts_data = {}
    total_lines = 0
    total_chars = 0

    if os.path.isfile(input_path):
        script = EthornellScript()
        script.load_file(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        strings = script.get_strings(default_sjis_tunnel)
        if strings:
            scripts_data[base_name] = strings
            for s in strings:
                if s.type.name == "Message":
                    total_lines += 1
                    total_chars += len([c for c in s.text if c not in "「」『』【】（）“”、。？！\r\n "])
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, input_path)
                sheet_name = os.path.splitext(rel_path)[0].replace("\\", "/")
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[-31:]

                try:
                    script = EthornellScript()
                    script.load_file(file_path)
                    strings = script.get_strings(default_sjis_tunnel)
                    if strings:
                        scripts_data[sheet_name] = strings
                        print(f"Extracted: {rel_path} ({len(strings)} strings)")
                        for s in strings:
                            if s.type.name == "Message":
                                total_lines += 1
                                total_chars += len([c for c in s.text if c not in "「」『』【】（）“”、。？！\r\n "])
                except Exception as ex:
                    print(f"Skipping {rel_path}: {ex}")
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)

    if not scripts_data:
        print("No script text found to extract.")
        return

    ExcelHandler.write_workbook(
        text_path,
        scripts_data,
        char_names_db=char_names,
        template_path=template_path
    )
    char_names.save()

    print(f"Total lines: {total_lines}")
    print(f"Total characters: {total_chars}")
    print(f"Saved to: {text_path}")


def get_wrapper(args):
    wrapper_type = args.wrapper.lower()
    if wrapper_type == "none":
        return NoOpWordWrapper()
    elif wrapper_type == "monospace":
        return MonospaceWordWrapper(characters_per_line=args.line_width or 50)
    elif wrapper_type == "proportional":
        return ProportionalWordWrapper(
            font_name=args.font_name,
            font_size=args.font_size,
            bold=args.font_bold,
            line_width=args.line_width or 1000
        )
    else:
        raise ValueError(f"Unknown wrapper type: {wrapper_type}")


def insert_local(args):
    input_path = os.path.abspath(args.input)
    text_path = os.path.abspath(args.table)
    output_path = os.path.abspath(args.output)
    sjis_ext_path = os.path.abspath(args.sjis_ext) if args.sjis_ext else None

    if sjis_ext_path is None:
        target_dir = os.path.dirname(output_path) if os.path.isfile(input_path) else output_path
        sjis_ext_path = os.path.join(target_dir, "sjis_ext.bin")

    tunnel = SjisTunnelEncoding()
    if os.path.exists(sjis_ext_path):
        with open(sjis_ext_path, "rb") as f:
            tunnel.set_mapping_table(f.read())

    wrapper = get_wrapper(args)

    if not os.path.exists(text_path):
        print(f"Error: Translation table {text_path} not found")
        sys.exit(1)

    sheets_data = ExcelHandler.read_workbook(text_path)
    patched_count = 0

    if os.path.isfile(input_path):
        script = EthornellScript()
        script.load_file(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        strings = sheets_data.get(base_name)
        if not strings and len(sheets_data) == 1:
            strings = next(iter(sheets_data.values()))

        if strings is None:
            print(f"Warning: No matching sheet for {base_name} found in {text_path}")
            return

        patched_bytes = script.write_patched(strings, wrapper=wrapper, tunnel=tunnel)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(patched_bytes)
        print(f"Patched {input_path} -> {output_path}")
    elif os.path.isdir(input_path):
        os.makedirs(output_path, exist_ok=True)
        for root, _, files in os.walk(input_path):
            for file in files:
                in_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(in_file_path, input_path)
                out_file_path = os.path.join(output_path, rel_path)
                os.makedirs(os.path.dirname(out_file_path), exist_ok=True)

                sheet_name = os.path.splitext(rel_path)[0].replace("\\", "/")
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[-31:]

                strings = sheets_data.get(sheet_name)
                if strings is not None:
                    try:
                        script = EthornellScript()
                        script.load_file(in_file_path)
                        patched_bytes = script.write_patched(strings, wrapper=wrapper, tunnel=tunnel)
                        with open(out_file_path, "wb") as f:
                            f.write(patched_bytes)
                        print(f"Patched: {rel_path}")
                        patched_count += 1
                    except Exception as ex:
                        print(f"Error patching {rel_path}: {ex}")
                else:
                    with open(in_file_path, "rb") as fin, open(out_file_path, "wb") as fout:
                        fout.write(fin.read())

    table_bytes = tunnel.get_mapping_table()
    if table_bytes:
        os.makedirs(os.path.dirname(sjis_ext_path), exist_ok=True)
        with open(sjis_ext_path, "wb") as f:
            f.write(table_bytes)
        print(f"Saved SJIS extension table ({len(table_bytes) // 2} characters): {sjis_ext_path}")


def main():
    parser = argparse.ArgumentParser(description="Ethornell (BGI) script localization tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extractlocal
    p_extract = subparsers.add_parser("extractlocal", help="Extract strings to Excel workbook (.xlsx)")
    p_extract.add_argument("input", help="Input scenario file or folder")
    p_extract.add_argument("output_table", help="Output Excel .xlsx file")

    # insertlocal
    p_insert = subparsers.add_parser("insertlocal", help="Insert translated strings into scenario file(s)")
    p_insert.add_argument("input", help="Input scenario file or folder")
    p_insert.add_argument("table", help="Input Excel .xlsx translation table")
    p_insert.add_argument("output", help="Output patched scenario file or folder")
    p_insert.add_argument("sjis_ext", nargs="?", default=None, help="Optional sjis_ext.bin path")

    for p in [p_insert]:
        p.add_argument("--wrapper", choices=["proportional", "monospace", "none"], default="proportional",
                       help="Word wrapping algorithm (default: proportional)")
        p.add_argument("--font-name", default="Franklin Gothic Book", help="Font family for proportional wrapping")
        p.add_argument("--font-size", type=int, default=40, help="Font size in px (default: 40)")
        p.add_argument("--font-bold", action="store_true", help="Use bold font in wrapping")
        p.add_argument("--line-width", type=int, default=None,
                       help="Max line width in px (proportional, default 1000) or chars (monospace, default 50)")

    args = parser.parse_args()

    if args.command == "extractlocal":
        extract_local(args)
    elif args.command == "insertlocal":
        insert_local(args)


if __name__ == "__main__":
    main()
