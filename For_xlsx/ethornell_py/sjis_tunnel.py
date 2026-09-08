"""SJIS Tunnel Encoding implementation matching VNTextPatch SjisTunnelEncoding.cs.

Unsupported characters in CP932 (e.g. Cyrillic, accented letters, symbols)
are dynamically mapped into unused Shift-JIS lead/trail byte ranges, and the
mapping is persisted in `sjis_ext.bin`.
"""

from typing import Dict, List, Optional


class SjisTunnelEncoding:
    def __init__(self, mapping_table: Optional[bytes] = None):
        self._char_to_tunnel: Dict[str, int] = {}
        self._tunnel_to_char: Dict[int, str] = {}
        if mapping_table:
            self.set_mapping_table(mapping_table)

    def set_mapping_table(self, table: bytes) -> None:
        if len(table) % 2 != 0:
            raise ValueError("Mapping table length must be even")
        self._char_to_tunnel.clear()
        self._tunnel_to_char.clear()
        for i in range(0, len(table), 2):
            code_point = table[i] | (table[i + 1] << 8)
            char = chr(code_point)
            self._get_or_create_tunnel_char(char)

    def get_mapping_table(self) -> bytes:
        result = bytearray()
        for char in self._char_to_tunnel.keys():
            code_point = ord(char)
            result.append(code_point & 0xFF)
            result.append((code_point >> 8) & 0xFF)
        return bytes(result)

    def _get_or_create_tunnel_char(self, char: str) -> int:
        if char in self._char_to_tunnel:
            return self._char_to_tunnel[char]

        sjis_idx = len(self._char_to_tunnel)
        max_allowed = 0x3B * 0x3A
        if sjis_idx >= max_allowed:
            raise ValueError("SJIS tunnel limit exceeded")

        high_sjis_idx, low_sjis_idx = divmod(sjis_idx, 0x3A)
        if high_sjis_idx < 0x1F:
            high_byte = 0x81 + high_sjis_idx
        else:
            high_byte = 0xE0 + (high_sjis_idx - 0x1F)

        low_byte = 1 + low_sjis_idx
        if low_byte >= ord('\t'):
            low_byte += 1
        if low_byte >= ord('\n'):
            low_byte += 1
        if low_byte >= ord('\r'):
            low_byte += 1
        if low_byte >= ord(' '):
            low_byte += 1
        if low_byte >= ord(','):
            low_byte += 1

        tunnel_val = (high_byte << 8) | low_byte
        self._char_to_tunnel[char] = tunnel_val
        self._tunnel_to_char[tunnel_val] = char
        return tunnel_val

    def encode(self, text: str) -> bytes:
        result = bytearray()
        for c in text:
            if c in self._char_to_tunnel:
                tunnel_val = self._char_to_tunnel[c]
                result.append((tunnel_val >> 8) & 0xFF)
                result.append(tunnel_val & 0xFF)
                continue

            try:
                encoded = c.encode('cp932')
                if len(encoded) > 0 and encoded[0] >= 0xF0:
                    raise UnicodeEncodeError('cp932', c, 0, 1, 'lead byte >= 0xF0')
                result.extend(encoded)
            except UnicodeEncodeError:
                tunnel_val = self._get_or_create_tunnel_char(c)
                result.append((tunnel_val >> 8) & 0xFF)
                result.append(tunnel_val & 0xFF)

        return bytes(result)

    def decode(self, data: bytes) -> str:
        result: List[str] = []
        i = 0
        n = len(data)
        while i < n:
            high = data[i]
            i += 1
            if (0x81 <= high < 0xA0) or (0xE0 <= high < 0xFD):
                if i < n:
                    low = data[i]
                    i += 1
                    if low < 0x40:
                        tunnel_val = (high << 8) | low
                        if tunnel_val in self._tunnel_to_char:
                            result.append(self._tunnel_to_char[tunnel_val])
                        else:
                            result.append(f'\\x{high:02x}\\x{low:02x}')
                    else:
                        pair = bytes([high, low])
                        try:
                            result.append(pair.decode('cp932'))
                        except UnicodeDecodeError:
                            result.append(pair.decode('cp932', errors='replace'))
                else:
                    result.append(f'\\x{high:02x}')
            else:
                try:
                    result.append(bytes([high]).decode('cp932'))
                except UnicodeDecodeError:
                    result.append(bytes([high]).decode('cp932', errors='replace'))

        return "".join(result)


default_sjis_tunnel = SjisTunnelEncoding()
