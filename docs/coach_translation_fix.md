# Виправлення перекладів у панелі тренера

## Проблема

При виборі спортсмена в панелі тренера кнопки і текст повідомлення не були перекладені на українську мову. Користувачі бачили англійський текст замість українського.

## Виявлені проблеми

### 1. Жорстко закодовані англійські тексти кнопок
- `"🔙 Back to Coach Panel"` - кнопка повернення до панелі тренера
- `"📊 {name}"` - кнопка перегляду деталей спортсмена
- `"❌ Cancel"` - кнопка скасування
- `"🔙 Back to Athletes"` - кнопка повернення до списку спортсменів

### 2. Жорстко закодовані англійські повідомлення
- `"👥 **Remove Athlete**\n\nSelect the athlete you want to remove from your supervision:"` - повідомлення при видаленні спортсмена

## Виправлення

### Замінені жорстко закодовані тексти на ключі перекладів:

#### У файлі `src/easy_track/bot.py`:

1. **Рядок 640, 665, 769**: Кнопка "Back to Coach Panel"
   ```python
   # Було:
   text="🔙 Back to Coach Panel"

   # Стало:
   text=translator.get("buttons.back_to_coach_panel", user_lang)
   ```

2. **Рядок 735**: Кнопка деталей спортсмена
   ```python
   # Було:
   text=f"📊 {name}"

   # Стало:
   text=translator.get("coach.buttons.view_athlete_details", user_lang, name=name)
   ```

3. **Рядок 1297**: Кнопка скасування
   ```python
   # Було:
   text="❌ Cancel"

   # Стало:
   text=translator.get("buttons.cancel", user_lang)
   ```

4. **Рядок 1304**: Повідомлення про видалення спортсмена
   ```python
   # Було:
   "👥 **Remove Athlete**\n\nSelect the athlete you want to remove from your supervision:"

   # Стало:
   translator.get("coach.remove_athlete.select", user_lang)
   ```

5. **Рядок 418**: Кнопка "Back to Athletes"
   ```python
   # Було:
   text="🔙 Back to Athletes"

   # Стало:
   text=translator.get("coach.buttons.my_athletes", user_lang)
   ```

6. **Багато інших місць**: Всі інші випадки "🔙 Back to Coach Panel"
   ```python
   # Всі замінені на:
   text=translator.get("buttons.back_to_coach_panel", user_lang)
   ```

## Використані ключі перекладів

### Кнопки (`buttons` секція в uk.json):
- `buttons.back_to_coach_panel` → "🔙 Назад до панелі тренера"
- `buttons.cancel` → "❌ Скасувати"

### Тренерські кнопки (`coach.buttons` секція в uk.json):
- `coach.buttons.my_athletes` → "👥 Мої спортсмени"
- `coach.buttons.view_athlete_details` → "📊 Деталі {name}"

### Повідомлення (`coach` секція в uk.json):
- `coach.remove_athlete.select` → "👥 **Видалити спортсмена**\n\nОберіть спортсмена якого ви хочете видалити з вашого нагляду:"

## Тестування

Створено тестовий скрипт `debug_scripts/test_translations_only.py` для перевірки перекладів:

```bash
python debug_scripts/test_translations_only.py
```

### Результати тестування:
- ✅ Всі кнопки тепер показують український текст
- ✅ Параметризовані переклади працюють правильно
- ✅ Повідомлення відображаються українською
- ✅ Англійські переклади також працюють

## До та після

### До виправлення:
- 🔙 Back to Coach Panel
- 📊 Ivan
- ❌ Cancel
- 👥 **Remove Athlete** Select the athlete...

### Після виправлення:
- 🔙 Назад до панелі тренера
- 📊 Деталі Іван
- ❌ Скасувати
- 👥 **Видалити спортсмена** Оберіть спортсмена...

## Перевірка у боті

1. Запустіть бота: `make docker-run`
2. Встановіть українську мову: `/language`
3. Станьте тренером: `/become_coach`
4. Відкрийте меню: `/menu`
5. Натисніть "🎯 Панель тренера"
6. Натисніть "👥 Мої спортсмени"
7. Перевірте, що всі кнопки та повідомлення відображаються українською

## Затронуті файли

- `src/easy_track/bot.py` - основні виправлення перекладів
- `debug_scripts/test_translations_only.py` - новий тестовий скрипт
- `docs/coach_translation_fix.md` - ця документація

## Технічні деталі

Усі зміни використовують існуючу систему перекладів через `translator.get()` метод. Переклади вже існували в файлах `src/easy_track/i18n/translations/uk.json` та `en.json`, просто не використовувались у коді.

Виправлення забезпечує:
- Консистентний досвід користувача
- Правильну локалізацію інтерфейсу
- Підтримку параметризованих перекладів
- Легке додавання нових мов у майбутньому
