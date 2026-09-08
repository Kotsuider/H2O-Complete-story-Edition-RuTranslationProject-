"""EthornellScript implementation matching EthornellScript.cs and BinaryPatcher.cs."""

import io
import os
import struct
from typing import List, Dict, Optional, Tuple, Iterable

from .disassembler import (
    create_disassembler,
    ScriptString,
    ScriptStringType,
    EthornellScriptString,
    BaseDisassembler,
)
from .sjis_tunnel import SjisTunnelEncoding, default_sjis_tunnel
from .word_wrapper import WordWrapper, ProportionalWordWrapper


class EthornellScript:
    def __init__(self, data: Optional[bytes] = None):
        self._scenario_data = bytearray(data) if data else bytearray()
        self._strings: List[EthornellScriptString] = []
        self._code_offset = 0
        self._code_length = 0
        if self._scenario_data:
            self._disassemble()

    @property
    def extension(self) -> str:
        return ".bgi"

    def load_bytes(self, data: bytes) -> None:
        self._scenario_data = bytearray(data)
        self._strings.clear()
        self._disassemble()

    def load_file(self, file_path: str) -> None:
        with open(file_path, "rb") as f:
            self.load_bytes(f.read())

    def _disassemble(self) -> None:
        disassembler = create_disassembler(bytes(self._scenario_data))
        self._code_offset = disassembler.code_offset
        self._code_length = disassembler.disassemble()
        self._strings = disassembler.string_addresses

    def _read_string(self, offset: int, tunnel: SjisTunnelEncoding) -> str:
        cur = offset
        while cur < len(self._scenario_data) and self._scenario_data[cur] != 0:
            cur += 1
        return tunnel.decode(bytes(self._scenario_data[offset:cur]))

    def get_strings(self, tunnel: Optional[SjisTunnelEncoding] = None) -> List[ScriptString]:
        if tunnel is None:
            tunnel = default_sjis_tunnel

        results: List[ScriptString] = []
        for s in self._strings:
            if s.type != ScriptStringType.Internal:
                text = self._read_string(s.text_offset, tunnel)
                results.append(ScriptString(text, s.type))
        return results

    def write_patched(
        self,
        script_strings: Iterable[ScriptString],
        wrapper: Optional[WordWrapper] = None,
        tunnel: Optional[SjisTunnelEncoding] = None
    ) -> bytes:
        if tunnel is None:
            tunnel = default_sjis_tunnel
        if wrapper is None:
            wrapper = ProportionalWordWrapper()

        provided_strings = list(script_strings)
        expected_strings = [s for s in self._strings if s.type != ScriptStringType.Internal]

        string_buffer = bytearray()
        string_offsets: Dict[str, int] = {}
        new_strings: List[EthornellScriptString] = []

        provided_idx = 0
        last_matched_str = None

        for eth_str in self._strings:
            if eth_str.type == ScriptStringType.Internal:
                text = self._read_string(eth_str.text_offset, tunnel)
            else:
                if provided_idx >= len(provided_strings):
                    # Form detailed error message
                    orig_missing = self._read_string(eth_str.text_offset, tunnel)
                    remaining_missing = []
                    for missing_item in self._strings[self._strings.index(eth_str):]:
                        if missing_item.type != ScriptStringType.Internal:
                            missing_text = self._read_string(missing_item.text_offset, tunnel)
                            remaining_missing.append(f"  - [{missing_item.type.name}] {repr(missing_text)}")
                            if len(remaining_missing) >= 4:
                                break

                        missing_preview = "\n".join(remaining_missing)
                    context_msg = f"Last matched string: {repr(last_matched_str.text)}\n" if last_matched_str else ""
                    raise ValueError(
                        f"Not enough strings in translation table!\n"
                        f"Expected {len(expected_strings)} strings, but translation table only has {len(provided_strings)}.\n"
                        f"{context_msg}"
                        f"First missing string #{provided_idx + 1} ({eth_str.type.name}):\n"
                        f"{missing_preview}"
                    )

                next_str = provided_strings[provided_idx]
                provided_idx += 1
                last_matched_str = next_str

                text = next_str.text
                if eth_str.type == ScriptStringType.Message:
                    text = wrapper.wrap(text)

            if text not in string_offsets:
                offset = self._code_offset + self._code_length + len(string_buffer)
                encoded_bytes = tunnel.encode(text) + b'\x00'
                string_buffer.extend(encoded_bytes)
                string_offsets[text] = offset
            else:
                offset = string_offsets[text]

            new_strings.append(EthornellScriptString(eth_str.operand_offset, offset, eth_str.type))

        if provided_idx < len(provided_strings):
            extra_count = len(provided_strings) - provided_idx
            extra_first = provided_strings[provided_idx]
            raise ValueError(
                f"Too many strings in translation table!\n"
                f"Expected {len(expected_strings)} strings, but table has {len(provided_strings)} ({extra_count} extra).\n"
                f"First extra string: [{extra_first.type.name}] {repr(extra_first.text)}"
            )

        output_bytes = bytearray(self._scenario_data[:self._code_offset + self._code_length])

        for new_str in new_strings:
            rel_address = new_str.text_offset - self._code_offset
            struct.pack_into('<i', output_bytes, new_str.operand_offset, rel_address)

        output_bytes.extend(string_buffer)
        return bytes(output_bytes)
