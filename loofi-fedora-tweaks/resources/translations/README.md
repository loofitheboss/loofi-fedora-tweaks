# Translations

This directory contains translation files for Loofi Fedora Tweaks.

## Files

- `en.ts` - English (source strings, 414 entries)
- `sv.ts` - Swedish (copy for translation)

## Translation Workflow

### 1. Install Qt Linguist Tools

```bash
sudo dnf install qt6-linguist
```

### 2. Edit Translations

```bash
linguist resources/translations/sv.ts
```

### 3. Compile to Binary

```bash
lrelease resources/translations/*.ts
```

### 4. Test

```bash
LANG=sv_SE.UTF-8 python3 main.py
```

## For Translators

1. Open `sv.ts` in Qt Linguist
2. Translate strings (keep `{}` placeholders)
3. Mark translations as "Finished"
4. Save and compile

## Adding New Languages

```bash
# Copy English source
cp en.ts de.ts  # German example

# Edit language attribute
# Change: language="en_US" → language="de_DE"
```
