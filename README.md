# Проект перевода H2O after and another Complete story Edition на русский язык

## Общие сведения

Перевод делается c [англофикатора от Studio Frisay](https://nreus.github.io/H2OPatch/) c помощью gemini с последующей редактурой.

## Статус

**Progress:**
`[███████░░░░░░░░] 50%`

- [x] Полный перевод
- [ ] Перевод графики
- [ ] Редактура

[Таблица с переводом](https://docs.google.com/spreadsheets/d/1W_IoG1-Khw1V3mISkmLECusFw5K96owc/edit?usp=sharing&ouid=103224880279791937700&rtpof=true&sd=true)

## Установка
1. Скачайте
2. Распакуйте архив в папку, установите шрифт
3. Профит!

## Редактирование патча
### Текст
Для распаковки используем [GARbro](https://github.com/morkt/GARbro/releases/tag/v1.5.44) и распаковываем все файлы из data01xxx допустим в папку H2o_ORIG.
Получаем папку со скриптами. 

Скачиваем таблицу с переводом и используем ru_f_translate.py

```Python
py -3.10 ru_f_translate.py h2o_full.xlsx
```
Получаем h2o_full_ruf.xlsx

Для введения изменений используем [VNTextPatch](https://github.com/arcusmaximus/VNTranslationTools) с командой 
```cmd/powershell
VNTextPatch.exe insertlocal H2o_ORIG h2o_full_ruf.xlsx output
```
Копируем файлы из output в patch и готово!

### Графика 
Для редактирования графики используется BgiImageEncoder.exe и результат так же закидываем в patch 

## По улучшениям и замечаниям
Вы можете оставить заметки по улучшениям и замечаниям, а так же предложить свою помощь в `issues`.
Если перевод будет `заброшен`, то можете сделать форк.
