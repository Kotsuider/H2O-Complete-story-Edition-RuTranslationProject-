"""Ethornell Disassembler matching EthornellDisassembler.cs,
EthornellV0Disassembler.cs, and EthornellV1Disassembler.cs.
"""

import io
import struct
from enum import Enum
from typing import List, Callable, Optional, NamedTuple


class ScriptStringType(Enum):
    CharacterName = 0
    Message = 1
    Internal = 2


class ScriptString(NamedTuple):
    text: str
    type: ScriptStringType


class EthornellScriptString(NamedTuple):
    operand_offset: int
    text_offset: int
    type: ScriptStringType


V1_MAGIC = b"BurikoCompiledScriptVer1.00\x00"

V0_OPERAND_TEMPLATES = {
    # h: short
    # i: int
    # c: code offset
    # m: message offset
    # z: inline zero-terminated string
    0x0010: "iim",
    0x0011: "",
    0x0012: "zz",
    0x0013: "z",
    0x0014: "z",
    0x0015: "",
    0x0018: "iiiii",
    0x0019: "iiii",
    0x001A: "iii",
    0x001B: "ziii",
    0x001F: "i",
    0x0020: "",
    0x0021: "",
    0x0022: "i",
    0x0024: "iiiii",
    0x0025: "ii",
    0x0028: "zi",
    0x0029: "zzi",
    0x002A: "i",
    0x002B: "zi",
    0x002C: "ziiiiiiii",
    0x002D: "ziiiiiiii",
    0x002E: "iiiii",
    0x0030: "zi",
    0x0031: "zii",
    0x0032: "i",
    0x0033: "i",
    0x0034: "ii",
    0x0035: "i",
    0x0036: "i",
    0x0037: "",
    0x0038: "iziiiii",
    0x0039: "ii",
    0x003A: "iziiiiiiii",
    0x003B: "iiiiii",
    0x003C: "iiiiiiiiii",
    0x003D: "iiiiiiiiiii",
    0x003F: "i",
    0x0040: "iizii",
    0x0041: "iizii",
    0x0042: "iizi",
    0x0043: "iizi",
    0x0044: "iizi",
    0x0045: "iizi",
    0x0046: "izi",
    0x0047: "izi",
    0x0048: "ii",
    0x0049: "ii",
    0x004A: "izi",
    0x004B: "",
    0x004C: "zi",
    0x004D: "zi",
    0x004E: "i",
    0x004F: "i",
    0x0050: "zi",
    0x0051: "zzi",
    0x0052: "i",
    0x0053: "zi",
    0x0054: "zii",
    0x0060: "iiiii",
    0x0061: "ii",
    0x0062: "iiiiii",
    0x0065: "i",
    0x0066: "ii",
    0x0067: "i",
    0x0068: "i",
    0x0069: "i",
    0x006A: "i",
    0x006B: "i",
    0x006C: "i",
    0x006E: "iii",
    0x006F: "i",
    0x0070: "izi",
    0x0071: "i",
    0x0072: "iii",
    0x0073: "iii",
    0x0074: "izi",
    0x0075: "i",
    0x0076: "iii",
    0x0078: "izi",
    0x0079: "i",
    0x007A: "iii",
    0x0080: "izii",
    0x0081: "z",
    0x0082: "i",
    0x0083: "i",
    0x0084: "izi",
    0x0085: "z",
    0x0086: "i",
    0x0087: "i",
    0x0088: "z",
    0x008C: "i",
    0x008D: "i",
    0x008E: "i",
    0x0090: "i",
    0x0091: "i",
    0x0092: "i",
    0x0093: "i",
    0x0094: "i",
    0x0098: "ii",
    0x0099: "ii",
    0x009A: "ii",
    0x009B: "ii",
    0x009C: "ii",
    0x009D: "ii",
    0x00A0: "c",
    0x00A1: "ic",
    0x00A2: "ic",
    0x00A3: "iic",
    0x00A4: "iic",
    0x00A5: "iic",
    0x00A6: "iic",
    0x00A7: "iic",
    0x00A8: "iic",
    0x00AC: "c",
    0x00AD: "",
    0x00AE: "i",
    0x00AF: "",
    0x00B8: "",
    0x00B9: "i",
    0x00BA: "i",
    0x00C0: "z",
    0x00C1: "z",
    0x00C2: "",
    0x00C4: "i",
    0x00C8: "z",
    0x00C9: "",
    0x00CA: "i",
    0x00D0: "",
    0x00D4: "i",
    0x00D8: "i",
    0x00D9: "i",
    0x00DA: "i",
    0x00DB: "i",
    0x00DC: "i",
    0x00F8: "z",
    0x00F9: "zi",
    0x00FE: "h",
    0x0110: "zz",
    0x0111: "i",
    0x0120: "i",
    0x0121: "i",
    0x0128: "zii",
    0x012A: "ii",
    0x0134: "ii",
    0x0135: "i",
    0x0136: "i",
    0x0138: "iziiiiziii",
    0x013B: "iiiiiiii",
    0x0140: "iiziiii",
    0x0141: "iiziiii",
    0x0142: "iiziii",
    0x0143: "iiziii",
    0x0144: "iiziii",
    0x0145: "iiziii",
    0x0146: "iziii",
    0x0147: "iziii",
    0x0148: "ii",
    0x0149: "ii",
    0x014B: "ziiz",
    0x0150: "zii",
    0x0151: "ziii",
    0x0152: "ii",
    0x0153: "iii",
    0x016E: "iiiiii",
    0x016F: "iiiiiii",
    0x0170: "izzii",
    0x01C0: "zz",
    0x01C1: "zz",
    0x0249: "z",
    0x024C: "zziii",
    0x024D: "z",
    0x024E: "zz",
    0x024F: "z"
}


class BaseDisassembler:
    def __init__(self, data: bytes):
        self._data = data
        self._stream = io.BytesIO(data)
        self._largest_code_address = 0
        self.string_addresses: List[EthornellScriptString] = []

    @property
    def code_offset(self) -> int:
        raise NotImplementedError

    def read_zero_terminated_sjis_string(self, offset: int) -> str:
        cur = offset
        while cur < len(self._data) and self._data[cur] != 0:
            cur += 1
        raw = self._data[offset:cur]
        try:
            return raw.decode('cp932')
        except Exception:
            return raw.decode('cp932', errors='replace')

    def is_empty_string(self, addr: int) -> bool:
        pos = self.code_offset + addr
        if pos >= len(self._data):
            return True
        return self._data[pos] == 0

    def read_string_at_address(self, addr: int) -> str:
        return self.read_zero_terminated_sjis_string(self.code_offset + addr)

    def skip_inline_string(self) -> None:
        while True:
            b = self._stream.read(1)
            if not b or b == b'\x00':
                break

    def read_code_address(self) -> int:
        offset = self._stream.tell()
        addr = struct.unpack('<i', self._stream.read(4))[0]
        self._largest_code_address = max(self._largest_code_address, addr)
        return addr

    def read_string_address(self, string_type: ScriptStringType) -> None:
        offset = self._stream.tell()
        addr = struct.unpack('<i', self._stream.read(4))[0]
        self.string_addresses.append(EthornellScriptString(offset, self.code_offset + addr, string_type))


class EthornellV0Disassembler(BaseDisassembler):
    @property
    def code_offset(self) -> int:
        return 0

    def disassemble(self) -> int:
        self._stream.seek(self.code_offset)
        while True:
            raw_op = self._stream.read(2)
            if not raw_op or len(raw_op) < 2:
                break
            opcode = struct.unpack('<H', raw_op)[0]

            if opcode == 0x00A9:
                count = struct.unpack('<i', self._stream.read(4))[0]
                for _ in range(count):
                    self.read_code_address()
            elif opcode in (0x00B0, 0x00B4):
                count = struct.unpack('<i', self._stream.read(4))[0]
                for _ in range(count):
                    self.skip_inline_string()
            elif opcode == 0x00FD:
                count = struct.unpack('<i', self._stream.read(4))[0]
                for _ in range(count):
                    self.skip_inline_string()
                    self.read_code_address()
            elif opcode == 0x0248:
                raise NotImplementedError("Opcode 0x0248 not implemented")
            else:
                if opcode not in V0_OPERAND_TEMPLATES:
                    raise ValueError(f"Unknown V0 opcode 0x{opcode:04X} at offset {self._stream.tell() - 2}")
                template = V0_OPERAND_TEMPLATES[opcode]
                for c in template:
                    if c == 'h':
                        self._stream.read(2)
                    elif c == 'i':
                        self._stream.read(4)
                    elif c == 'c':
                        self.read_code_address()
                    elif c == 'n':
                        self.read_string_address(ScriptStringType.CharacterName)
                    elif c == 'm':
                        self.read_string_address(ScriptStringType.Message)
                    elif c == 'z':
                        self.skip_inline_string()
                    else:
                        raise ValueError(f"Unknown operand template char '{c}'")

            if opcode == 0x00C2 and self._largest_code_address < (self._stream.tell() - self.code_offset):
                break

        return self._stream.tell() - self.code_offset


class StackItem(NamedTuple):
    offset: int
    value: int


# Load V1 Operand Templates (all 0x0000..0x04EB)
V1_OPERAND_TEMPLATES = {
    0x0000: "i",
    0x0001: "c",
    0x0002: "i",
    0x0003: "m",
    0x0008: "i",
    0x0009: "i",
    0x000A: "i",
    0x0010: "",
    0x0011: "",
    0x0015: "",
    0x0016: "",
    0x0017: "i",
    0x0018: "",
    0x0019: "i",
    0x001A: "",
    0x001B: "",
    0x001C: "",
    0x001D: "",
    0x001E: "",
    0x001F: "",
    0x0020: "",
    0x0021: "",
    0x0022: "",
    0x0023: "",
    0x0024: "",
    0x0025: "",
    0x0026: "",
    0x0027: "",
    0x0028: "",
    0x0029: "",
    0x002A: "",
    0x002B: "",
    0x0030: "",
    0x0031: "",
    0x0032: "",
    0x0033: "",
    0x0034: "",
    0x0035: "",
    0x0038: "",
    0x0039: "",
    0x003A: "",
    0x003E: "",
    0x003F: "i",
    0x0040: "",
    0x0048: "",
    0x007B: "iii",
    0x007E: "i",
    0x007F: "ii",
    0x0080: "",
    0x0081: "",
    0x0082: "",
    0x0083: "",
    0x0090: "",
    0x0091: "",
    0x0092: "",
    0x0093: "",
    0x0094: "",
    0x0095: "",
    0x0098: "",
    0x0099: "",
    0x00A0: "",
    0x00A8: "",
    0x00AA: "",
    0x00AC: "",
    0x00C0: "",
    0x00C1: "",
    0x00C2: "",
    0x00D0: "",
    0x00E0: "",
    0x00E1: "",
    0x00E2: "",
    0x00E3: "",
    0x00E4: "",
    0x00E5: "",
    0x00E6: "",
    0x00E7: "",
    0x00E8: "",
    0x00E9: "",
    0x00EA: "",
    0x00EB: "",
    0x00EC: "",
    0x00ED: "",
    0x00EE: "",
    0x00EF: "",
    0x00F0: "",
    0x00F1: "",
    0x00F3: "",
    0x00F4: "",
    0x00F5: "",
    0x00F6: "",
    0x00F7: "",
    0x00F8: "",
    0x00F9: "",
    0x00FA: "",
    0x00FB: "",
    0x00FC: "",
    0x00FD: "",
    0x00FE: "",
    0x00FF: "",
    0x0100: "",
    0x0101: "",
    0x0102: "",
    0x0103: "",
    0x0104: "",
    0x0105: "",
    0x0106: "",
    0x0107: "",
    0x0108: "",
    0x0109: "",
    0x010A: "",
    0x010B: "",
    0x010D: "",
    0x010E: "",
    0x010F: "",
    0x0110: "",
    0x0111: "",
    0x0112: "",
    0x0113: "",
    0x0114: "",
    0x0115: "",
    0x0116: "",
    0x0117: "",
    0x0118: "",
    0x0119: "",
    0x011A: "",
    0x011B: "",
    0x011C: "",
    0x011D: "",
    0x011E: "",
    0x011F: "",
    0x0120: "",
    0x0121: "",
    0x0122: "",
    0x0123: "",
    0x0124: "",
    0x0125: "",
    0x0126: "",
    0x0127: "",
    0x0128: "",
    0x0129: "",
    0x012A: "",
    0x012C: "",
    0x012D: "",
    0x012E: "",
    0x012F: "",
    0x0130: "",
    0x0131: "",
    0x0132: "",
    0x0133: "",
    0x0134: "",
    0x0135: "",
    0x0136: "",
    0x0137: "",
    0x0138: "",
    0x0139: "",
    0x013A: "",
    0x013B: "",
    0x013C: "",
    0x013D: "",
    0x013E: "",
    0x013F: "",
    0x0140: "",
    0x0141: "",
    0x0142: "",
    0x0143: "",
    0x0144: "",
    0x0145: "",
    0x0146: "",
    0x0147: "",
    0x0148: "",
    0x0149: "",
    0x014A: "",
    0x014B: "",
    0x014C: "",
    0x014D: "",
    0x014E: "",
    0x014F: "",
    0x0150: "",
    0x0151: "",
    0x0152: "",
    0x0153: "",
    0x0156: "",
    0x0157: "",
    0x0158: "",
    0x0159: "",
    0x015A: "",
    0x015C: "",
    0x015D: "",
    0x015E: "",
    0x015F: "",
    0x0160: "",
    0x0161: "",
    0x0163: "",
    0x0164: "",
    0x0165: "",
    0x0166: "",
    0x0167: "",
    0x0168: "",
    0x0169: "",
    0x016A: "",
    0x016B: "",
    0x016C: "",
    0x016D: "",
    0x016E: "",
    0x016F: "",
    0x0170: "",
    0x0171: "",
    0x0172: "",
    0x0173: "",
    0x0174: "",
    0x0175: "",
    0x0176: "",
    0x0178: "",
    0x0179: "",
    0x017A: "",
    0x017D: "",
    0x017E: "",
    0x017F: "",
    0x0180: "",
    0x0181: "",
    0x0182: "",
    0x0184: "",
    0x0185: "",
    0x0186: "",
    0x0187: "",
    0x0188: "",
    0x0189: "",
    0x018A: "",
    0x018B: "",
    0x018D: "",
    0x018E: "",
    0x018F: "",
    0x0190: "",
    0x0191: "",
    0x0194: "",
    0x0195: "",
    0x0196: "",
    0x0197: "",
    0x0198: "",
    0x0199: "",
    0x019C: "",
    0x019D: "",
    0x019E: "",
    0x019F: "",
    0x01A0: "",
    0x01A1: "",
    0x01A2: "",
    0x01A3: "",
    0x01A4: "",
    0x01A5: "",
    0x01A6: "",
    0x01A7: "",
    0x01A8: "",
    0x01A9: "",
    0x01AA: "",
    0x01AB: "",
    0x01AC: "",
    0x01AD: "",
    0x01AE: "",
    0x01AF: "",
    0x01B0: "",
    0x01B1: "",
    0x01B2: "",
    0x01B4: "",
    0x01B5: "",
    0x01B6: "",
    0x01B7: "",
    0x01BF: "",
    0x01D0: "",
    0x01D4: "",
    0x01D8: "",
    0x01D9: "",
    0x01E0: "",
    0x01F0: "",
    0x0200: "",
    0x0204: "",
    0x0205: "",
    0x0208: "",
    0x0209: "",
    0x020A: "",
    0x020C: "",
    0x020E: "",
    0x020F: "",
    0x0210: "",
    0x0220: "",
    0x0222: "",
    0x0225: "",
    0x0226: "",
    0x0228: "",
    0x0229: "",
    0x022A: "",
    0x0230: "",
    0x0231: "",
    0x0232: "",
    0x0233: "",
    0x0234: "",
    0x0235: "",
    0x0236: "",
    0x0237: "",
    0x0238: "",
    0x0239: "",
    0x023A: "",
    0x023B: "",
    0x023C: "",
    0x023D: "",
    0x0240: "",
    0x0241: "",
    0x0242: "",
    0x0244: "",
    0x0245: "",
    0x0248: "",
    0x024C: "",
    0x024D: "",
    0x024E: "",
    0x0250: "",
    0x0251: "",
    0x0252: "",
    0x0254: "",
    0x0255: "",
    0x0256: "",
    0x0257: "",
    0x0258: "",
    0x025E: "",
    0x025F: "",
    0x0260: "",
    0x0261: "",
    0x0262: "",
    0x0266: "",
    0x0268: "",
    0x027F: "",
    0x0280: "",
    0x0281: "",
    0x0284: "",
    0x0288: "",
    0x0289: "",
    0x028A: "",
    0x0290: "",
    0x0294: "",
    0x0295: "",
    0x0296: "",
    0x0297: "",
    0x0298: "",
    0x0299: "",
    0x029C: "",
    0x02A0: "",
    0x02A1: "",
    0x02A2: "",
    0x02A3: "",
    0x02A4: "",
    0x02A8: "",
    0x02C0: "",
    0x02C1: "",
    0x02C2: "",
    0x02C3: "",
    0x02C4: "",
    0x02C5: "",
    0x02C6: "",
    0x02C7: "",
    0x02C8: "",
    0x02CA: "",
    0x02CB: "",
    0x02CC: "",
    0x02CD: "",
    0x02CE: "",
    0x02CF: "",
    0x02D0: "",
    0x02D2: "",
    0x02D4: "",
    0x02D5: "",
    0x02D6: "",
    0x02D7: "",
    0x02D8: "",
    0x02D9: "",
    0x02DA: "",
    0x02DB: "",
    0x02DC: "",
    0x02DD: "",
    0x02DE: "",
    0x02DF: "",
    0x02E0: "",
    0x02E1: "",
    0x02E2: "",
    0x02E3: "",
    0x02E4: "",
    0x02E5: "",
    0x02E6: "",
    0x02E7: "",
    0x02E8: "",
    0x02E9: "",
    0x02EA: "",
    0x02EB: "",
    0x02EC: "",
    0x02EE: "",
    0x02F0: "",
    0x02F1: "",
    0x02F3: "",
    0x02F4: "",
    0x02F8: "",
    0x02FA: "",
    0x02FC: "",
    0x02FD: "",
    0x0300: "",
    0x0301: "",
    0x0302: "",
    0x0303: "",
    0x0304: "",
    0x0306: "",
    0x0307: "",
    0x0308: "",
    0x0309: "",
    0x030A: "",
    0x030C: "",
    0x030D: "",
    0x030E: "",
    0x0310: "",
    0x0311: "",
    0x0314: "",
    0x031E: "",
    0x031F: "",
    0x0320: "",
    0x0328: "",
    0x032C: "",
    0x0330: "",
    0x0331: "",
    0x0334: "",
    0x0335: "",
    0x0336: "",
    0x0337: "",
    0x0338: "",
    0x0339: "",
    0x033F: "",
    0x0340: "",
    0x0341: "",
    0x0348: "",
    0x0350: "",
    0x0351: "",
    0x0352: "",
    0x0353: "",
    0x0354: "",
    0x0355: "",
    0x0358: "",
    0x0360: "",
    0x0368: "",
    0x0380: "",
    0x0388: "",
    0x038D: "",
    0x038E: "",
    0x038F: "",
    0x0390: "",
    0x0391: "",
    0x0392: "",
    0x0393: "",
    0x0394: "",
    0x03AF: "",
    0x03C0: "",
    0x03C1: "",
    0x03C2: "",
    0x03C4: "",
    0x03C5: "",
    0x03C6: "",
    0x03C7: "",
    0x03C8: "",
    0x03C9: "",
    0x03CA: "",
    0x03D0: "",
    0x03D2: "",
    0x03D4: "",
    0x03D5: "",
    0x03D6: "",
    0x03D8: "",
    0x03DC: "",
    0x03F0: "",
    0x03F1: "",
    0x03F4: "",
    0x03F5: "",
    0x03F6: "",
    0x03F7: "",
    0x03F8: "",
    0x03FA: "",
    0x03FB: "",
    0x03FC: "",
    0x03FD: "",
    0x03FE: "",
    0x03FF: "",
    0x0400: "",
    0x0401: "",
    0x0402: "",
    0x0403: "",
    0x0404: "",
    0x0405: "",
    0x0408: "",
    0x0409: "",
    0x040A: "",
    0x040B: "",
    0x040C: "",
    0x040D: "",
    0x040F: "",
    0x0410: "",
    0x0411: "",
    0x0412: "",
    0x0413: "",
    0x0418: "",
    0x0427: "",
    0x0428: "",
    0x0429: "",
    0x042A: "",
    0x042B: "",
    0x042C: "",
    0x042D: "",
    0x042F: "",
    0x0430: "",
    0x0431: "",
    0x0432: "",
    0x0440: "",
    0x0441: "",
    0x0442: "",
    0x0444: "",
    0x0448: "",
    0x0449: "",
    0x0450: "",
    0x0451: "",
    0x0452: "",
    0x0453: "",
    0x0454: "",
    0x0455: "",
    0x0458: "",
    0x0459: "",
    0x045C: "",
    0x045D: "",
    0x045E: "",
    0x0480: "",
    0x0481: "",
    0x0482: "",
    0x0483: "",
    0x0484: "",
    0x0485: "",
    0x04C0: "",
    0x04C1: "",
    0x04C2: "",
    0x04C3: "",
    0x04C4: "",
    0x04C5: "",
    0x04C6: "",
    0x04C7: "",
    0x04C8: "",
    0x04C9: "",
    0x04CA: "",
    0x04CB: "",
    0x04D0: "",
    0x04D1: "",
    0x04D5: "",
    0x04D8: "",
    0x04D9: "",
    0x04DA: "",
    0x04E0: "",
    0x04E4: "",
    0x04E5: "",
    0x04E8: "",
    0x04E9: "",
    0x04EA: "",
    0x04EB: ""
}


class EthornellV1Disassembler(BaseDisassembler):
    def __init__(self, data: bytes):
        super().__init__(data)
        self._stream.seek(len(V1_MAGIC))
        header_size = struct.unpack('<i', self._stream.read(4))[0]
        self._code_offset = len(V1_MAGIC) + header_size
        self._string_stack: List[StackItem] = []

    @property
    def code_offset(self) -> int:
        return self._code_offset

    def _read_push_string_address(self) -> None:
        offset = self._stream.tell()
        addr = struct.unpack('<i', self._stream.read(4))[0]
        self._string_stack.append(StackItem(offset, addr))

    def _handle_user_function_call(self) -> None:
        if not self._string_stack:
            return
        item = self._string_stack.pop()
        self.string_addresses.append(EthornellScriptString(item.offset, self.code_offset + item.value, ScriptStringType.Internal))
        func_name = self.read_string_at_address(item.value)
        if func_name == "_SelectEx":
            self._handle_choice_screen()

    def _handle_message(self) -> None:
        if not self._string_stack:
            return
        msg = self._string_stack.pop()

        if self._string_stack:
            name = self._string_stack.pop()
            name_type = ScriptStringType.CharacterName if not self.is_empty_string(name.value) else ScriptStringType.Internal
            self.string_addresses.append(EthornellScriptString(name.offset, self.code_offset + name.value, name_type))

        msg_type = ScriptStringType.Message if not self.is_empty_string(msg.value) else ScriptStringType.Internal
        self.string_addresses.append(EthornellScriptString(msg.offset, self.code_offset + msg.value, msg_type))

    def _handle_choice_screen(self) -> None:
        choice_operands: List[StackItem] = []
        while self._string_stack:
            choice_operands.insert(0, self._string_stack.pop())

        for item in choice_operands:
            self.string_addresses.append(EthornellScriptString(item.offset, self.code_offset + item.value, ScriptStringType.Message))

    def _output_internal_strings(self) -> None:
        while self._string_stack:
            item = self._string_stack.pop()
            self.string_addresses.append(EthornellScriptString(item.offset, self.code_offset + item.value, ScriptStringType.Internal))

    def disassemble(self) -> int:
        self._stream.seek(self.code_offset)
        while True:
            raw_op = self._stream.read(4)
            if not raw_op or len(raw_op) < 4:
                break
            opcode = struct.unpack('<i', raw_op)[0]

            if opcode == 0x0003:
                self._read_push_string_address()
            elif opcode == 0x001C:
                self._handle_user_function_call()
            elif opcode in (0x0140, 0x0143):
                self._handle_message()
            elif opcode == 0x0160:
                self._handle_choice_screen()
            else:
                if opcode not in V1_OPERAND_TEMPLATES:
                    raise ValueError(f"Unknown V1 opcode 0x{opcode:04X} at offset {self._stream.tell() - 4}")
                template = V1_OPERAND_TEMPLATES[opcode]
                for c in template:
                    if c == 'i':
                        self._stream.read(4)
                    elif c == 'c':
                        self.read_code_address()
                    elif c == 'm':
                        self._read_push_string_address()
                    else:
                        raise ValueError(f"Unknown operand template char '{c}'")

            if (opcode in (0x001B, 0x00F4)) and self._largest_code_address < (self._stream.tell() - self.code_offset):
                break

            if opcode in (0x007E, 0x007F, 0x00FE):
                self._output_internal_strings()

        self._output_internal_strings()
        return self._stream.tell() - self.code_offset


def create_disassembler(data: bytes) -> BaseDisassembler:
    if data.startswith(V1_MAGIC):
        return EthornellV1Disassembler(data)
    return EthornellV0Disassembler(data)
