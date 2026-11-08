# Проект перевода H2O after and another Complete story Edition на русский язык

## Общие сведения

Перевод делается c [англофикатора от Studio Frisay](https://nreus.github.io/H2OPatch/) c помощью gemini с последующей редактурой.

## Статус

**Progress:**
`[▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩▩] 100%`

- [x] Полный перевод
- [x] Перевод графики
- [x] Редактура

[Таблица с переводом](https://docs.google.com/spreadsheets/d/1W_IoG1-Khw1V3mISkmLECusFw5K96owc/edit?usp=sharing&ouid=103224880279791937700&rtpof=true&sd=true)

## Установка
1. Скачайте
2. Распакуйте архив в папку, установите шрифт
3. Профит!

## Редактирование патча
### Текст
Для распаковки используем [GARbro](https://github.com/morkt/GARbro/releases/tag/v1.5.44) и распаковываем все файлы из data01xxx допустим в папку H2o_ORIG.
Получаем папку со скриптами. 

Скачиваем таблицу с переводом и запускаем `build_patch.bat`

Копируем файлы из `h2o_OUT` в `patch` и готово!


# Licenses, Credits & Disclaimers

## Copyright & License Notice

This repository contains both original software developed by the repository author and modified/rewritten tools based on third-party open-source code.

### Original Tools & Translation Files
Copyright (c) 2026 Kotsuider
* Distributed under the terms of the [MIT License](LICENSE).
* Applies to original utility scripts, custom translation tools, and modified Russian text assets.

### Rewritten BGI/Ethornell Engine Tools
Copyright (c) 2026 Kotsuider
Copyright (c) arcusmaximus (https://github.com/arcusmaximus)
* Distributed under the terms of the [MIT License](LICENSE).
* Core asset-handling and parsing logic is based on VNTranslationTools by @arcusmaximus.

---

## Credits & Acknowledgments

* **Original Tooling:** Custom scripts and utilities designed to manage the translation workflow were written entirely from scratch by Kotsuider.
* **BGI Engine Tooling:** Tools for parsing, text extraction, and injection compatible with the BGI/Ethornell engine were rewritten into Python by the author of this repository. The logic is deeply based on the **[VNTranslationTools](https://github.com/arcusmaximus/VNTranslationTools)** project by **[@arcusmaximus](https://github.com/arcusmaximus)**. Special thanks to @arcusmaximus for their invaluable research.
* **Script Injection Framework:** Dynamic code injection and script loading into the game process utilize the **[UniversalInjectorFramework (UIF)](https://github.com/AtomCrafty/UniversalInjectorFramework)** developed by **[@AtomCrafty](https://github.com/AtomCrafty)**. Special thanks to the author for making this project public and providing invaluable research for the visual novel modding community.

---

## Game Copyright & Non-Commercial Disclaimer

* **Original Game Assets:** All rights to the visual novel, graphics, characters, music, original text, and the **H2O √ after and another Complete story Edition** trademark belong solely to **Makura** (c) 2009. 
* **Fan Project Nature:** This repository contains a non-commercial, non-profit fan-made text modification (patch). It is distributed for free solely for educational, archival, and entertainment purposes. 
* **Requirements:** These translation files cannot be used as a standalone product and strictly require the user to already own a legitimate, legally purchased copy of the original game from the copyright holder. This repository does not host original game executables or full copyrighted media assets.

