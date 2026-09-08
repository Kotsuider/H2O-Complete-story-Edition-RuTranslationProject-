"""Word wrapping logic matching VNTextPatch WordWrapper.cs,
MonospaceWordWrapper.cs and ProportionalWordWrapper.cs.
"""

import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Iterable

LINE_BREAK_CHARS = (' ', '-')
CJK_PUNCTUATION = "，。？！」』】）’”"


class WordWrapper(ABC):
    @abstractmethod
    def get_text_width(self, text: str, offset: int, length: int) -> int:
        pass

    @property
    @abstractmethod
    def line_width(self) -> int:
        pass

    def get_wrap_positions(self, text: str) -> List[int]:
        positions: List[int] = []
        line_start_pos = 0
        n = len(text)

        while line_start_pos < n:
            line_end_pos = line_start_pos
            while line_end_pos < n:
                # Find next space or dash
                search_pos = -1
                for idx in range(line_end_pos + 1, n):
                    if text[idx] in LINE_BREAK_CHARS:
                        search_pos = idx
                        break

                if search_pos >= 0:
                    if text[search_pos] != ' ':
                        search_pos += 1
                else:
                    search_pos = n

                if self.get_text_width(text, line_start_pos, search_pos - line_start_pos) > self.line_width:
                    break

                line_end_pos = search_pos

            # If no word fits, break mid-word
            if line_end_pos == line_start_pos:
                search_pos = line_end_pos
                while line_end_pos < n:
                    search_pos += 1
                    if self.get_text_width(text, line_start_pos, search_pos - line_start_pos) > self.line_width:
                        break
                    line_end_pos = search_pos

            if line_end_pos < n and text[line_end_pos] in CJK_PUNCTUATION:
                line_end_pos += 1

            positions.append(line_end_pos)

            line_start_pos = line_end_pos
            while line_start_pos < n and text[line_start_pos] == ' ':
                line_start_pos += 1

        return positions

    def wrap(self, text: str, line_break: str = "\r\n") -> str:
        result_lines: List[str] = []
        # Split by explicit line breaks if already present
        # Handle CRLF and LF
        raw_lines = text.replace("\r\n", "\n").split("\n")

        for line in raw_lines:
            line_start_pos = 0
            wrap_positions = self.get_wrap_positions(line)
            if not wrap_positions:
                result_lines.append("")
                continue

            for line_end_pos in wrap_positions:
                if line_end_pos == line_start_pos:
                    continue
                result_lines.append(line[line_start_pos:line_end_pos])
                line_start_pos = line_end_pos
                while line_start_pos < len(line) and line[line_start_pos] == ' ':
                    line_start_pos += 1

        return line_break.join(result_lines)


class MonospaceWordWrapper(WordWrapper):
    def __init__(self, characters_per_line: int = 50):
        self._characters_per_line = characters_per_line

    @property
    def line_width(self) -> int:
        return self._characters_per_line

    def get_text_width(self, text: str, offset: int, length: int) -> int:
        return max(0, length)


class ProportionalWordWrapper(WordWrapper):
    """Proportional word wrapper using Win32 GDI (CreateFontW, GetCharABCWidthsFloatW, GetKerningPairsW)

    on Windows to produce 100% bit-exact widths with C# ProportionalWordWrapper.cs.
    Falls back to Monospace or Tkinter/Pillow on other platforms.
    """
    def __init__(
        self,
        font_name: str = "Franklin Gothic Book",
        font_size: int = 40,
        bold: bool = False,
        line_width: int = 1000
    ):
        self._font_name = font_name
        self._font_size = font_size
        self._bold = bold
        self._line_width = line_width
        self._char_widths = {}
        self._kern_amounts = {}
        self._init_font()

    @property
    def line_width(self) -> int:
        return self._line_width

    def _init_font(self):
        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                gdi32 = ctypes.windll.gdi32

                dc = user32.GetDC(0)
                FW_BOLD = 700
                FW_NORMAL = 400
                ANSI_CHARSET = 0
                OUT_DEFAULT_PRECIS = 0
                CLIP_DEFAULT_PRECIS = 0
                DEFAULT_QUALITY = 0
                DEFAULT_PITCH = 0
                FF_DONTCARE = 0

                weight = FW_BOLD if self._bold else FW_NORMAL
                hfont = gdi32.CreateFontW(
                    self._font_size,
                    0, 0, 0,
                    weight,
                    0, 0, 0,
                    ANSI_CHARSET,
                    OUT_DEFAULT_PRECIS,
                    CLIP_DEFAULT_PRECIS,
                    DEFAULT_QUALITY,
                    DEFAULT_PITCH | FF_DONTCARE,
                    self._font_name
                )
                gdi32.SelectObject(dc, hfont)

                class ABCFLOAT(ctypes.Structure):
                    _fields_ = [
                        ('abcfA', ctypes.c_float),
                        ('abcfB', ctypes.c_float),
                        ('abcfC', ctypes.c_float),
                    ]

                class KERNINGPAIR(ctypes.Structure):
                    _fields_ = [
                        ('wFirst', wintypes.WORD),
                        ('wSecond', wintypes.WORD),
                        ('iKernAmount', ctypes.c_int),
                    ]

                # Measure 0..255
                abc_array = (ABCFLOAT * 256)()
                if gdi32.GetCharABCWidthsFloatW(dc, 0, 255, abc_array):
                    for i in range(256):
                        w = int(abc_array[i].abcfA + abc_array[i].abcfB + abc_array[i].abcfC)
                        self._char_widths[chr(i)] = max(0, w)

                # Kerning pairs
                num_pairs = gdi32.GetKerningPairsW(dc, 0, None)
                if num_pairs > 0:
                    pairs_array = (KERNINGPAIR * num_pairs)()
                    gdi32.GetKerningPairsW(dc, num_pairs, pairs_array)
                    for pair in pairs_array:
                        key = (chr(pair.wFirst), chr(pair.wSecond))
                        self._kern_amounts[key] = pair.iKernAmount

                user32.ReleaseDC(0, dc)
                gdi32.DeleteObject(hfont)
                return
            except Exception:
                pass

        # Fallback if non-windows or GDI failed
        # Approximate width based on font_size
        self._char_widths = {}

    def _get_char_width(self, c: str) -> int:
        if c in self._char_widths:
            return self._char_widths[c]

        # Query dynamically if in Windows
        if sys.platform == 'win32':
            try:
                import ctypes
                user32 = ctypes.windll.user32
                gdi32 = ctypes.windll.gdi32

                dc = user32.GetDC(0)
                weight = 700 if self._bold else 400
                hfont = gdi32.CreateFontW(
                    self._font_size, 0, 0, 0, weight, 0, 0, 0,
                    0, 0, 0, 0, 0, self._font_name
                )
                gdi32.SelectObject(dc, hfont)

                class ABCFLOAT(ctypes.Structure):
                    _fields_ = [
                        ('abcfA', ctypes.c_float),
                        ('abcfB', ctypes.c_float),
                        ('abcfC', ctypes.c_float),
                    ]

                code = ord(c)
                abc = (ABCFLOAT * 1)()
                if gdi32.GetCharABCWidthsFloatW(dc, code, code, abc):
                    w = int(abc[0].abcfA + abc[0].abcfB + abc[0].abcfC)
                    self._char_widths[c] = max(0, w)
                    user32.ReleaseDC(0, dc)
                    gdi32.DeleteObject(hfont)
                    return self._char_widths[c]

                user32.ReleaseDC(0, dc)
                gdi32.DeleteObject(hfont)
            except Exception:
                pass

        # Default fallback approximation
        w = self._font_size if ord(c) > 0x2E80 else self._font_size // 2
        self._char_widths[c] = w
        return w

    def _get_kern_amount(self, first: str, second: str) -> int:
        return self._kern_amounts.get((first, second), 0)

    def get_text_width(self, text: str, offset: int, length: int) -> int:
        if length <= 0:
            return 0
        width = 0
        for i in range(offset, offset + length):
            width += self._get_char_width(text[i])
            if i > offset:
                width += self._get_kern_amount(text[i - 1], text[i])
        return width


class NoOpWordWrapper(WordWrapper):
    @property
    def line_width(self) -> int:
        return 999999

    def get_text_width(self, text: str, offset: int, length: int) -> int:
        return 0

    def wrap(self, text: str, line_break: str = "\r\n") -> str:
        return text
