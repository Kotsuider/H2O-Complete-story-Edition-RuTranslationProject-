"""Handling of names.xml matching VNTextPatch CharacterNames.cs."""

import os
import xml.etree.ElementTree as ET
from typing import Dict


class CharacterNames:
    def __init__(self, file_path: str = "names.xml"):
        self.file_path = file_path
        self._translations: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self._translations.clear()
        if not os.path.exists(self.file_path):
            return

        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            for n_elem in root.findall('n'):
                o_elem = n_elem.find('o')
                tl_elem = n_elem.find('tl')
                if o_elem is not None and o_elem.text:
                    orig = o_elem.text
                    trans = tl_elem.text if (tl_elem is not None and tl_elem.text) else orig
                    self._translations[orig] = trans
        except Exception:
            pass

    def get_translation(self, orig_name: str) -> str:
        if orig_name not in self._translations:
            self._translations[orig_name] = orig_name
            return orig_name
        return self._translations[orig_name]

    def save(self) -> None:
        root = ET.Element('names')
        for orig, trans in self._translations.items():
            n_elem = ET.SubElement(root, 'n')
            o_elem = ET.SubElement(n_elem, 'o')
            o_elem.text = orig
            tl_elem = ET.SubElement(n_elem, 'tl')
            tl_elem.text = trans

        tree = ET.ElementTree(root)
        ET.indent(tree, space="\t", level=0)
        tree.write(self.file_path, encoding='utf-8', xml_declaration=True)
