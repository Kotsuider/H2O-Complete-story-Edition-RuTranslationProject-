#!/usr/bin/env python3
"""
choices_tool.py — Утилита для извлечения и вставки выборов (инлайн-строк 0x00B0)
в сценарии Ethornell (BGI V0).

Команды:
  python choices_tool.py extract <папка_сценариев_der> <файл.md>
  python choices_tool.py insert <папка_сценариев_вход> <папка_сценариев_выход> <файл.md> [--no-ruf]
"""

import os
import sys
import glob
import re
import struct
import argparse
from typing import List, Tuple, Dict, Optional

# Импорт трансляции шрифта RU_F (из ru_f_translate.py)
try:
    from ru_f_translate import apply_ru_f
except ImportError:
    apply_ru_f = lambda s: s

# Импорт словаря шаблонов опкодов из ethornell_py
try:
    from ethornell_py.disassembler import V0_OPERAND_TEMPLATES
except ImportError:
    # Запасной fallback, если импорт напрямую
    from .ethornell_py.disassembler import V0_OPERAND_TEMPLATES


def disassemble_v0(data: bytes) -> Tuple[int, List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int, int, List[bytes]]]]:
    """
    Разбирает сценарий Ethornell V0.
    Возвращает:
      code_length: длина блока инструкций
      code_ptrs: [(offset_in_data, target_address)] - указатели на адреса в коде
      msg_ptrs: [(offset_in_data, target_address)] - указатели на строки сообщений (0x0010)
      choices: [(op_start, op_end, count, [option_bytes, ...])] - точки выбора (0x00B0, 0x00B4)
    """
    pos = 0
    stream_len = len(data)
    code_ptrs = []
    msg_ptrs = []
    choices = []
    largest_code_addr = 0

    while pos < stream_len:
        if pos + 2 > stream_len:
            break
        opcode = struct.unpack('<H', data[pos:pos+2])[0]
        pos += 2

        if opcode == 0x00A9:
            count = struct.unpack('<i', data[pos:pos+4])[0]
            pos += 4
            for _ in range(count):
                tgt = struct.unpack('<i', data[pos:pos+4])[0]
                largest_code_addr = max(largest_code_addr, tgt)
                code_ptrs.append((pos, tgt))
                pos += 4
        elif opcode in (0x00B0, 0x00B4):
            op_start = pos - 2
            count = struct.unpack('<i', data[pos:pos+4])[0]
            pos += 4
            opts = []
            for _ in range(count):
                end = data.find(b'\x00', pos)
                if end == -1:
                    end = len(data)
                opts.append(bytes(data[pos:end]))
                pos = end + 1
            choices.append((op_start, pos, count, opts))
        elif opcode == 0x00FD:
            count = struct.unpack('<i', data[pos:pos+4])[0]
            pos += 4
            for _ in range(count):
                end = data.find(b'\x00', pos)
                if end == -1:
                    end = len(data)
                pos = end + 1
                tgt = struct.unpack('<i', data[pos:pos+4])[0]
                largest_code_addr = max(largest_code_addr, tgt)
                code_ptrs.append((pos, tgt))
                pos += 4
        elif opcode == 0x0248:
            break
        else:
            if opcode not in V0_OPERAND_TEMPLATES:
                break
            template = V0_OPERAND_TEMPLATES[opcode]
            for c in template:
                if c == 'h':
                    pos += 2
                elif c == 'i':
                    pos += 4
                elif c == 'c':
                    tgt = struct.unpack('<i', data[pos:pos+4])[0]
                    largest_code_addr = max(largest_code_addr, tgt)
                    code_ptrs.append((pos, tgt))
                    pos += 4
                elif c == 'm':
                    tgt = struct.unpack('<i', data[pos:pos+4])[0]
                    msg_ptrs.append((pos, tgt))
                    pos += 4
                elif c == 'z':
                    end = data.find(b'\x00', pos)
                    if end == -1:
                        end = len(data)
                    pos = end + 1

        if opcode == 0x00C2 and largest_code_addr < pos:
            break

    return pos, code_ptrs, msg_ptrs, choices


def apply_choice_replacements(data: bytes, replacements: List[List[bytes]]) -> bytes:
    """
    Вставляет новые варианты выборов в байткод и корректирует все относительные
    и абсолютные смещения и указатели.
    """
    code_length, code_ptrs, msg_ptrs, choices = disassemble_v0(data)
    if not choices:
        return data

    new_data = bytearray()
    old_pos = 0
    delta_map: List[Tuple[int, int]] = []
    cum_delta = 0

    for ch_idx, (op_start, op_end, count, opts) in enumerate(choices):
        new_data.extend(data[old_pos:op_start])
        new_data.extend(data[op_start:op_start+2])  # 0x00B0 / 0x00B4
        new_data.extend(struct.pack('<i', count))
        new_opts = replacements[ch_idx] if ch_idx < len(replacements) else opts
        for o in new_opts:
            new_data.extend(o + b'\x00')
        old_choice_len = op_end - op_start
        new_choice_len = 6 + sum(len(o) + 1 for o in new_opts)
        cum_delta += (new_choice_len - old_choice_len)
        delta_map.append((op_end, cum_delta))
        old_pos = op_end

    new_data.extend(data[old_pos:code_length])

    def remap_target(old_addr: int) -> int:
        shift = 0
        for split_pos, d in delta_map:
            if old_addr >= split_pos:
                shift = d
        return old_addr + shift

    def remap_ptr_offset(old_ptr_pos: int) -> int:
        shift = 0
        for split_pos, d in delta_map:
            if old_ptr_pos >= split_pos:
                shift = d
        return old_ptr_pos + shift

    # Корректируем прыжки внутри кода
    for ptr_pos, target_addr in code_ptrs:
        new_ptr_pos = remap_ptr_offset(ptr_pos)
        new_target_addr = remap_target(target_addr)
        struct.pack_into('<i', new_data, new_ptr_pos, new_target_addr)

    # Корректируем адреса текстовых строк, идущих после блока кода
    for ptr_pos, target_addr in msg_ptrs:
        new_ptr_pos = remap_ptr_offset(ptr_pos)
        new_target_addr = target_addr + cum_delta
        struct.pack_into('<i', new_data, new_ptr_pos, new_target_addr)

    # Дописываем исходный пул строк сценария
    new_data.extend(data[code_length:])
    return bytes(new_data)


def decode_str(b: bytes) -> str:
    try:
        return b.decode('cp932')
    except Exception:
        return b.decode('utf-8', errors='replace')


def escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\r", "").replace("\n", " ")


def unescape_md(text: str) -> str:
    return text.replace("\\|", "|").strip()


def extract_choices(input_dir: str, output_md: str) -> None:
    """Ищет все файлы с выборами и сохраняет их в Markdown-таблицы."""
    files = sorted(glob.glob(os.path.join(input_dir, "*")))
    lines = []
    lines.append("# Перевод выборов (Choices Translation)\n")

    found_files_count = 0
    total_options_count = 0

    for path in files:
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            data = f.read()

        _, _, _, choices = disassemble_v0(data)
        if not choices:
            continue

        found_files_count += 1
        base_name = os.path.basename(path)
        lines.append(f"## {base_name}\n")
        lines.append("| ID | Original | Translation |")
        lines.append("|---|---|---|")

        opt_num = 1
        for ch_idx, (_, _, count, opts) in enumerate(choices, 1):
            for opt_idx, opt_b in enumerate(opts, 1):
                text_orig = decode_str(opt_b)
                lines.append(f"| {ch_idx}.{opt_idx} | {escape_md(text_orig)} |  |")
                opt_num += 1
                total_options_count += 1
        lines.append("")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    print(f"Готово! Найдено файлов с выборами: {found_files_count}, всего вариантов: {total_options_count}")
    print(f"Таблицы сохранены в: {output_md}")


def parse_markdown_choices(md_path: str) -> Dict[str, Dict[str, str]]:
    """
    Парсит markdown файл с таблицами.
    Возвращает: { 'filename': { 'ch_idx.opt_idx': 'translation_text' } }
    """
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Файл не найден: {md_path}")

    current_file = None
    results: Dict[str, Dict[str, str]] = {}

    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            line_s = line.strip()
            if line_s.startswith("## "):
                current_file = line_s[3:].strip()
                results[current_file] = {}
                continue

            if current_file and line_s.startswith("|") and not line_s.startswith("|---"):
                parts = [p.strip() for p in line_s.split("|")[1:-1]]
                if len(parts) >= 3:
                    choice_id = parts[0]
                    orig_text = unescape_md(parts[1])
                    trans_text = unescape_md(parts[2])
                    if choice_id and choice_id.lower() != "id":
                        results[current_file][choice_id] = trans_text

    return results


def insert_choices(input_dir: str, output_dir: str, md_path: str, use_ruf: bool = True) -> None:
    """
    Берёт сценарии из input_dir (обычно h2o_OUT), заменяет выборы
    согласно md_path (с конвертацией в RU_F при необходимости)
    и сохраняет результат в output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    translations = parse_markdown_choices(md_path)

    script_files = sorted(glob.glob(os.path.join(input_dir, "*")))
    patched_files = 0
    total_patched_choices = 0

    for path in script_files:
        if not os.path.isfile(path):
            continue
        base_name = os.path.basename(path)
        out_path = os.path.join(output_dir, base_name)

        with open(path, "rb") as f:
            data = f.read()

        _, _, _, choices = disassemble_v0(data)
        if not choices:
            # Если выборов нет и пути разные - просто копируем если нужно
            if os.path.abspath(path) != os.path.abspath(out_path):
                with open(out_path, "wb") as f_out:
                    f_out.write(data)
            continue

        file_trans = translations.get(base_name, {})
        replacements: List[List[bytes]] = []

        has_any_tl = False
        for ch_idx, (_, _, count, opts) in enumerate(choices, 1):
            ch_opts: List[bytes] = []
            for opt_idx, orig_bytes in enumerate(opts, 1):
                key = f"{ch_idx}.{opt_idx}"
                tl_text = file_trans.get(key, "").strip()
                if tl_text:
                    has_any_tl = True
                    # Применяем кодировку шрифта RU_F
                    final_text = apply_ru_f(tl_text) if use_ruf else tl_text
                    ch_opts.append(final_text.encode("cp932", errors="replace"))
                else:
                    ch_opts.append(orig_bytes)
            replacements.append(ch_opts)

        if has_any_tl:
            patched_data = apply_choice_replacements(data, replacements)
            with open(out_path, "wb") as f_out:
                f_out.write(patched_data)
            patched_files += 1
            total_patched_choices += len(choices)
            print(f"Вставлены выборы в: {base_name}")
        else:
            if os.path.abspath(path) != os.path.abspath(out_path):
                with open(out_path, "wb") as f_out:
                    f_out.write(data)

    print(f"Готово! Вставлены выборы в {patched_files} файлов (всего точек выбора: {total_patched_choices}).")


def main():
    parser = argparse.ArgumentParser(description="Инструмент работы с выборами в Ethornell (BGI V0)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_p = subparsers.add_parser("extract", help="Извлечь выборы в MD-файл")
    extract_p.add_argument("input", help="Папка с декомпилированными сценариями (например, h2o_der)")
    extract_p.add_argument("output", help="Выходной файл Markdown (например, choices.md)")

    insert_p = subparsers.add_parser("insert", help="Вставить перевод выборов из MD-файла")
    insert_p.add_argument("input", help="Папка со сценариями для вставки (например, h2o_OUT)")
    insert_p.add_argument("output", help="Папка для сохранения пропатченных сценариев (например, h2o_OUT)")
    insert_p.add_argument("table", help="Файл Markdown с переводом выборов (например, choices.md)")
    insert_p.add_argument("--no-ruf", action="store_true", help="Не применять трансляцию RU_F к тексту")

    args = parser.parse_args()
    if args.command == "extract":
        extract_choices(args.input, args.output)
    elif args.command == "insert":
        insert_choices(args.input, args.output, args.table, use_ruf=not args.no_ruf)


if __name__ == "__main__":
    main()
