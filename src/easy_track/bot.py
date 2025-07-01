import os
import asyncio
import logging
from datetime import datetime, time
from typing import Optional
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from .database import DatabaseManager, init_db, close_db
from .repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
    MeasurementRepository,
    NotificationScheduleRepository,
)
from .i18n import translator
from .scheduler import set_scheduler, get_scheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class UserStates(StatesGroup):
    waiting_for_measurement_value = State()
    selecting_measurement_types = State()
    selecting_language = State()
    creating_custom_type_name = State()
    creating_custom_type_unit = State()
    creating_custom_type_description = State()
    waiting_for_notification_time = State()


class BotHandlers:
    """Main bot handlers class."""

    @staticmethod
    async def get_or_create_user(telegram_user: types.User) -> int:
        """Get or create user and return user ID."""

        async def _get_or_create(session):
            user = await UserRepository.get_user_by_telegram_id(
                session, telegram_user.id
            )
            if not user:
                user = await UserRepository.create_user(
                    session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                )
            return user.id

        return await DatabaseManager.execute_with_session(_get_or_create)

    @staticmethod
    async def get_user_language(user_id: int) -> str:
        """Get user's language preference by user ID."""

        async def _get_language(session):
            user = await UserRepository.get_user_by_id(session, user_id)
            return user.language if user else "en"

        return await DatabaseManager.execute_with_session(_get_language)

    @staticmethod
    async def get_user_language_by_telegram_id(telegram_id: int) -> str:
        """Get user's language preference by telegram ID."""

        async def _get_language(session):
            return await UserRepository.get_user_language(session, telegram_id)

        return await DatabaseManager.execute_with_session(_get_language)

    @staticmethod
    async def start_command(message: types.Message):
        """Handle /start command."""
        try:
            user_id = await BotHandlers.get_or_create_user(message.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            welcome_text = translator.get(
                "commands.start.welcome", user_lang, name=message.from_user.first_name
            )

            await message.answer(welcome_text)
            await BotHandlers.show_main_menu(message)

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            error_text = translator.get(
                "commands.start.error",
                (
                    await BotHandlers.get_user_language(user_id)
                    if "user_id" in locals()
                    else "en"
                ),
            )
            await message.answer(error_text)

    @staticmethod
    async def show_main_menu(message: types.Message):
        """Show main menu with options."""
        user_id = await BotHandlers.get_or_create_user(message.from_user)
        user_lang = await BotHandlers.get_user_language(user_id)

        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(
                text=translator.get("buttons.add_measurement", user_lang),
                callback_data="add_measurement",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.manage_types", user_lang),
                callback_data="manage_types",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.view_progress", user_lang),
                callback_data="view_progress",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.view_by_date", user_lang),
                callback_data="view_by_date",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.statistics", user_lang),
                callback_data="statistics",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.notifications", user_lang),
                callback_data="notifications",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.language_settings", user_lang),
                callback_data="language_settings",
            ),
        )
        keyboard.adjust(2)

        await message.answer(
            translator.get("commands.menu.title", user_lang),
            reply_markup=keyboard.as_markup(),
        )

    @staticmethod
    async def menu_command(message: types.Message):
        """Handle /menu command."""
        await BotHandlers.show_main_menu(message)

    @staticmethod
    async def handle_language_settings(callback: CallbackQuery):
        """Handle language settings selection."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.english", user_lang),
                    callback_data="set_language_en",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.ukrainian", user_lang),
                    callback_data="set_language_uk",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back_to_menu", user_lang),
                    callback_data="back_to_menu",
                ),
            )
            keyboard.adjust(2, 1)

            text = translator.get("language.select", user_lang)
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
            await callback.answer()

        except Exception as e:
            logger.error(f"Error in language settings: {e}")
            await callback.answer(translator.get("common.error", "en"))

    @staticmethod
    async def handle_set_language(callback: CallbackQuery):
        """Handle language selection."""
        try:
            # Extract language code from callback data
            lang_code = callback.data.replace("set_language_", "")

            if not translator.is_supported_language(lang_code):
                await callback.answer("❌ Unsupported language")
                return

            # Update user language in database
            async def _update_language(session):
                return await UserRepository.update_user_language(
                    session, callback.from_user.id, lang_code
                )

            await DatabaseManager.execute_with_session(_update_language)

            # Send confirmation in new language
            success_text = translator.get("language.changed", lang_code)
            await callback.message.edit_text(success_text)
            await callback.answer()

            # Show main menu in new language
            await asyncio.sleep(1)  # Brief pause before showing menu
            await BotHandlers.show_main_menu(callback.message)

        except Exception as e:
            logger.error(f"Error setting language: {e}")
            await callback.answer(translator.get("common.error", "en"))

    @staticmethod
    async def handle_add_measurement(callback: CallbackQuery):
        """Handle add measurement callback."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, user_id
                )

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.message.edit_text(
                    translator.get("add_measurement.no_types", user_lang),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=translator.get(
                                        "buttons.manage_types", user_lang
                                    ),
                                    callback_data="manage_types",
                                ),
                                InlineKeyboardButton(
                                    text=translator.get("buttons.back", user_lang),
                                    callback_data="back_to_menu",
                                ),
                            ]
                        ]
                    ),
                )
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                type_name = translator.get_measurement_type_name(
                    user_type.measurement_type.name, user_lang
                )
                unit_name = translator.get_unit_name(
                    user_type.measurement_type.unit, user_lang
                )
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"{type_name} ({unit_name})",
                        callback_data=f"measure_{user_type.measurement_type.id}",
                    )
                )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="back_to_menu",
                )
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                translator.get("add_measurement.select_type", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in add measurement: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"User ID: {callback.from_user.id}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

    @staticmethod
    async def handle_measure_type(callback: CallbackQuery, state: FSMContext):
        """Handle measurement type selection for adding value."""
        try:
            measurement_type_id = int(callback.data.split("_")[1])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_type_info(session):
                return await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )

            measurement_type = await DatabaseManager.execute_with_session(
                _get_type_info
            )

            if not measurement_type:
                await callback.answer(translator.get("common.error", user_lang))
                return

            await state.update_data(measurement_type_id=measurement_type_id)
            await state.set_state(UserStates.waiting_for_measurement_value)

            # Get latest measurement for reference
            async def _get_latest(session):
                return await MeasurementRepository.get_latest_measurement(
                    session, user_id, measurement_type_id
                )

            latest = await DatabaseManager.execute_with_session(_get_latest)

            # Get localized names
            type_name = translator.get_measurement_type_name(
                measurement_type.name, user_lang
            )
            unit_name = translator.get_unit_name(measurement_type.unit, user_lang)

            if latest:

                message_text = translator.get(
                    "add_measurement.enter_value",
                    user_lang,
                    type=type_name,
                    latest=f"{latest.value} {unit_name}",
                    unit=unit_name,
                )
            else:
                message_text = translator.get(
                    "add_measurement.enter_value_no_history",
                    user_lang,
                    type=type_name,
                    unit=unit_name,
                )

            await callback.message.edit_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=translator.get("buttons.cancel", user_lang),
                                callback_data="add_measurement",
                            )
                        ]
                    ]
                ),
            )

        except Exception as e:
            logger.error(f"Error in handle_measure_type: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Callback data: {callback.data}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_measurement_value(message: types.Message, state: FSMContext):
        """Handle measurement value input."""
        try:
            data = await state.get_data()
            measurement_type_id = data.get("measurement_type_id")
            user_id = await BotHandlers.get_or_create_user(message.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            if not measurement_type_id:
                await message.answer(translator.get("common.error", user_lang))
                await state.clear()
                return

            # Validate numeric input
            try:
                value = float(message.text.strip())
                if value <= 0:
                    raise ValueError("Value must be positive")
            except ValueError:
                await message.answer(
                    translator.get("add_measurement.invalid_number", user_lang)
                )
                return

            async def _save_measurement(session):
                measurement = await MeasurementRepository.create_measurement(
                    session, user_id, measurement_type_id, value
                )
                measurement_type = await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )
                return measurement, measurement_type

            measurement, measurement_type = await DatabaseManager.execute_with_session(
                _save_measurement
            )

            await state.clear()

            # Get localized names
            type_name = translator.get_measurement_type_name(
                measurement_type.name, user_lang
            )
            unit_name = translator.get_unit_name(measurement_type.unit, user_lang)
            date_str = measurement.measurement_date.strftime("%d/%m/%Y %H:%M")

            success_text = translator.get(
                "add_measurement.success",
                user_lang,
                type=type_name,
                value=value,
                unit=unit_name,
                date=date_str,
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.add_measurement", user_lang),
                            callback_data="add_measurement",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.view_progress", user_lang),
                            callback_data="view_progress",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.back_to_menu", user_lang),
                            callback_data="back_to_menu",
                        )
                    ],
                ]
            )

            await message.answer(success_text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in handle_measurement_value: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                message.from_user.id
            )
            await message.answer(translator.get("add_measurement.error", user_lang))
            await state.clear()

    @staticmethod
    async def handle_manage_types(callback: CallbackQuery):
        """Handle manage measurement types."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_data(session):
                user_types = (
                    await UserMeasurementTypeRepository.get_user_measurement_types(
                        session, user_id
                    )
                )
                all_types = (
                    await MeasurementTypeRepository.get_available_types_for_user(
                        session, user_id
                    )
                )
                return user_types, all_types

            user_types, all_types = await DatabaseManager.execute_with_session(
                _get_data
            )

            user_type_ids = {ut.measurement_type_id for ut in user_types}
            available_types = [t for t in all_types if t.id not in user_type_ids]

            keyboard = InlineKeyboardBuilder()

            if user_types:
                keyboard.add(
                    InlineKeyboardButton(
                        text=translator.get("manage_types.remove_types", user_lang),
                        callback_data="remove_types",
                    )
                )

            if available_types:
                keyboard.add(
                    InlineKeyboardButton(
                        text=translator.get("manage_types.add_types", user_lang),
                        callback_data="add_types",
                    )
                )

            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="back_to_menu",
                )
            )
            keyboard.adjust(1)

            # Build message text
            title = translator.get("manage_types.title", user_lang)
            description = translator.get("manage_types.description", user_lang)

            current_types_text = ""
            if user_types:
                current_types_list = []
                for ut in user_types:
                    type_name = translator.get_measurement_type_name(
                        ut.measurement_type.name, user_lang
                    )
                    unit_name = translator.get_unit_name(
                        ut.measurement_type.unit, user_lang
                    )
                    icon = "🔧" if ut.measurement_type.is_custom else "📏"
                    current_types_list.append(f"{icon} {type_name} ({unit_name})")
                current_types_text = "\n\n📋 " + "\n".join(current_types_list)

            message_text = f"{title}\n\n{description}{current_types_text}"

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_manage_types: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_add_types(callback: CallbackQuery):
        """Handle adding measurement types to user."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_available_types(session):
                user_types = (
                    await UserMeasurementTypeRepository.get_user_measurement_types(
                        session, user_id
                    )
                )
                all_types = (
                    await (
                        MeasurementTypeRepository.get_available_types_for_user(
                            session, user_id
                        )
                    )
                )
                user_type_ids = {ut.measurement_type_id for ut in user_types}
                return [t for t in all_types if t.id not in user_type_ids]

            available_types = await DatabaseManager.execute_with_session(
                _get_available_types
            )

            keyboard = InlineKeyboardBuilder()

            # Add available measurement types
            for mtype in available_types:
                icon = "🔧" if mtype.is_custom else "➕"
                # Translate measurement type name and unit
                translated_name = translator.get_measurement_type_name(
                    mtype.name, user_lang
                )
                translated_unit = translator.get_unit_name(mtype.unit, user_lang)
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"{icon} {translated_name} ({translated_unit})",
                        callback_data=f"add_type_{mtype.id}",
                    )
                )

            # Add "Create Custom Type" button
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("custom_types.create_button", user_lang),
                    callback_data="create_custom_type",
                )
            )

            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="manage_types",
                )
            )
            keyboard.adjust(1)

            if not available_types:
                message_text = translator.get("add_types.no_available", user_lang)
            else:
                message_text = translator.get("add_types.select", user_lang)

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_add_types: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_add_type_confirm(callback: CallbackQuery):
        """Handle confirmation of adding a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[2])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _add_type(session):
                await UserMeasurementTypeRepository.add_measurement_type_to_user(
                    session, user_id, measurement_type_id
                )
                return await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )

            measurement_type = await DatabaseManager.execute_with_session(_add_type)

            translated_name = translator.get_measurement_type_name(
                measurement_type.name, user_lang
            )
            await callback.answer(f"✅ Added {translated_name} to your tracking list!")
            await BotHandlers.handle_add_types(callback)

        except Exception as e:
            logger.error(f"Error in handle_add_type_confirm: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_create_custom_type(callback: CallbackQuery, state: FSMContext):
        """Start the custom measurement type creation flow."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            await state.set_state(UserStates.creating_custom_type_name)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("custom_types.cancel", user_lang),
                    callback_data="add_types",
                )
            )

            title_text = translator.get("custom_types.title", user_lang)
            prompt_text = translator.get("custom_types.name_prompt", user_lang)

            await callback.message.edit_text(
                f"{title_text}\n\n{prompt_text}", reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_create_custom_type: {e}")
            await callback.answer(translator.get("common.error", "en"))

    @staticmethod
    async def handle_custom_type_name(message: Message, state: FSMContext):
        """Handle custom type name input."""
        try:
            user_id = await BotHandlers.get_or_create_user(message.from_user)
            name = message.text.strip()

            user_lang = await BotHandlers.get_user_language(user_id)

            # Validate name length
            if len(name) < 2:
                await message.reply(
                    translator.get("custom_types.name_too_short", user_lang)
                )
                return

            if len(name) > 50:
                await message.reply(
                    translator.get("custom_types.name_too_long", user_lang)
                )
                return

            # Check if name already exists
            async def _check_name_exists(session):
                return await MeasurementTypeRepository.check_custom_type_name_exists(
                    session, name, user_id
                )

            name_exists = await DatabaseManager.execute_with_session(_check_name_exists)

            if name_exists:
                await message.reply(
                    translator.get("custom_types.name_exists", user_lang, name=name)
                )
                return

            # Store the name and move to next state
            await state.update_data(custom_type_name=name)
            await state.set_state(UserStates.creating_custom_type_unit)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("custom_types.cancel", user_lang),
                    callback_data="add_types",
                )
            )

            await message.reply(
                f"✅ Name: '{name}'\n\n{translator.get('custom_types.unit_prompt', user_lang)}",
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_custom_type_name: {e}")
            await message.reply(translator.get("common.error", "en"))

    @staticmethod
    async def handle_custom_type_unit(message: Message, state: FSMContext):
        """Handle custom type unit input."""
        try:
            unit = message.text.strip()

            user_id = await BotHandlers.get_or_create_user(message.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            # Validate unit length
            if len(unit) < 1:
                await message.reply(
                    translator.get("custom_types.unit_empty", user_lang)
                )
                return

            if len(unit) > 10:
                await message.reply(
                    translator.get("custom_types.unit_too_long", user_lang)
                )
                return

            # Store the unit and move to next state
            await state.update_data(custom_type_unit=unit)
            await state.set_state(UserStates.creating_custom_type_description)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("custom_types.skip_description", user_lang),
                    callback_data="skip_description",
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("custom_types.cancel", user_lang),
                    callback_data="add_types",
                )
            )
            keyboard.adjust(1)

            data = await state.get_data()
            await message.reply(
                f"✅ Name: '{data['custom_type_name']}'\n"
                f"✅ Unit: '{unit}'\n\n"
                f"{translator.get('custom_types.description_prompt', user_lang)}",
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_custom_type_unit: {e}")
            await message.reply(translator.get("common.error", "en"))

    @staticmethod
    async def handle_custom_type_description(message: Message, state: FSMContext):
        """Handle custom type description input."""
        try:
            description = message.text.strip()

            user_id = await BotHandlers.get_or_create_user(message.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            # Validate description length
            if len(description) > 200:
                await message.reply(
                    translator.get("custom_types.description_too_long", user_lang)
                )
                return

            await BotHandlers.create_custom_measurement_type(
                message, state, description
            )

        except Exception as e:
            logger.error(f"Error in handle_custom_type_description: {e}")
            await message.reply(translator.get("common.error", "en"))

    @staticmethod
    async def handle_skip_description(callback: CallbackQuery, state: FSMContext):
        """Handle skipping description and create the custom type."""
        try:
            await BotHandlers.create_custom_measurement_type(
                callback.message, state, None
            )
        except Exception as e:
            logger.error(f"Error in handle_skip_description: {e}")
            await callback.answer(translator.get("common.error", "en"))

    @staticmethod
    async def create_custom_measurement_type(
        message: Message, state: FSMContext, description: Optional[str] = None
    ):
        """Create the custom measurement type and add it to user's tracking list."""
        try:
            user_id = await BotHandlers.get_or_create_user(message.from_user)
            data = await state.get_data()

            name = data["custom_type_name"]
            unit = data["custom_type_unit"]

            async def _create_and_add_type(session):
                # Create the custom measurement type
                custom_type = (
                    await (
                        MeasurementTypeRepository.create_custom_measurement_type(
                            session, name, unit, user_id, description
                        )
                    )
                )

                # Automatically add it to user's tracking list
                await UserMeasurementTypeRepository.add_measurement_type_to_user(
                    session, user_id, custom_type.id
                )

                return custom_type

            custom_type = await DatabaseManager.execute_with_session(
                _create_and_add_type
            )

            # Clear the state
            await state.clear()

            user_lang = await BotHandlers.get_user_language(user_id)

            # Show success message
            if description:
                success_message = translator.get(
                    "custom_types.success_with_description",
                    user_lang,
                    name=custom_type.name,
                    unit=custom_type.unit,
                    description=description,
                )
            else:
                success_message = translator.get(
                    "custom_types.success",
                    user_lang,
                    name=custom_type.name,
                    unit=custom_type.unit,
                )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.add_measurement", user_lang),
                    callback_data="add_measurement",
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.manage_types", user_lang),
                    callback_data="manage_types",
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back_to_menu", user_lang),
                    callback_data="back_to_menu",
                )
            )
            keyboard.adjust(1)

            await message.reply(
                success_message,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error in create_custom_measurement_type: {e}")
            user_lang = "en"
            try:
                user_id = await BotHandlers.get_or_create_user(message.from_user)
                user_lang = await BotHandlers.get_user_language(user_id)
            except Exception:
                user_lang = "en"  # fallback language
            await message.reply(translator.get("custom_types.error", user_lang))
            await state.clear()

    @staticmethod
    async def handle_remove_types(callback: CallbackQuery):
        """Handle removing measurement types from user."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, user_id
                )

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.answer(
                    translator.get("remove_types.no_types", user_lang)
                )
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                # Translate measurement type name
                translated_name = translator.get_measurement_type_name(
                    user_type.measurement_type.name, user_lang
                )
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"➖ {translated_name}",
                        callback_data=f"remove_type_{user_type.measurement_type.id}",
                    )
                )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="manage_types",
                )
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                translator.get("remove_types.select", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_remove_types: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_remove_type_confirm(callback: CallbackQuery):
        """Handle confirmation of removing a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[2])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _remove_type(session):
                success = await UserMeasurementTypeRepository.remove_measurement_type_from_user(
                    session, user_id, measurement_type_id
                )
                if success:
                    return await MeasurementTypeRepository.get_type_by_id(
                        session, measurement_type_id
                    )
                return None

            measurement_type = await DatabaseManager.execute_with_session(_remove_type)

            if measurement_type:
                translated_name = translator.get_measurement_type_name(
                    measurement_type.name, user_lang
                )
                await callback.answer(
                    f"✅ Removed {translated_name} from your tracking list!"
                )
            else:
                await callback.answer(translator.get("common.error", user_lang))

            await BotHandlers.handle_remove_types(callback)

        except Exception as e:
            logger.error(f"Error in handle_remove_type_confirm: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_view_progress(callback: CallbackQuery):
        """Handle view progress callback."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, user_id
                )

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.message.edit_text(
                    translator.get("view_progress.no_types", user_lang),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=translator.get(
                                        "buttons.manage_types", user_lang
                                    ),
                                    callback_data="manage_types",
                                ),
                                InlineKeyboardButton(
                                    text=translator.get("buttons.back", user_lang),
                                    callback_data="back_to_menu",
                                ),
                            ]
                        ]
                    ),
                )
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                type_name = translator.get_measurement_type_name(
                    user_type.measurement_type.name, user_lang
                )
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"📊 {type_name}",
                        callback_data=f"progress_{user_type.measurement_type.id}",
                    )
                )
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="back_to_menu",
                )
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                translator.get("view_progress.select_type", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_view_progress: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_progress_detail(callback: CallbackQuery):
        """Handle detailed progress view for a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[1])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_progress_data(session):
                measurement_type = await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )
                measurements = await MeasurementRepository.get_user_measurements(
                    session, user_id, measurement_type_id, limit=10
                )
                stats = await MeasurementRepository.get_measurement_stats(
                    session, user_id, measurement_type_id
                )
                return measurement_type, measurements, stats

            measurement_type, measurements, stats = (
                await DatabaseManager.execute_with_session(_get_progress_data)
            )

            type_name = translator.get_measurement_type_name(
                measurement_type.name, user_lang
            )
            unit_name = translator.get_unit_name(measurement_type.unit, user_lang)

            if not measurements:
                progress_text = translator.get(
                    "view_progress.no_measurements", user_lang, type=type_name
                )
            else:
                latest = measurements[0]
                latest_date = latest.measurement_date.strftime("%d/%m/%Y")

                progress_text = (
                    f"{translator.get('view_progress.title', user_lang, type=type_name)}\n\n"
                    f"{translator.get('view_progress.latest', user_lang, value=latest.value, unit=unit_name, date=latest_date)}\n"
                    f"{translator.get('view_progress.total_count', user_lang, count=stats['count'])}\n\n"
                    f"📊 Statistics:\n"
                    f"• Average: {stats['average']} {unit_name}\n"
                    f"• Minimum: {stats['minimum']} {unit_name}\n"
                    f"• Maximum: {stats['maximum']} {unit_name}\n\n"
                    f"{translator.get('view_progress.recent_measurements', user_lang)}\n"
                )

                for i, measurement in enumerate(measurements[:5], 1):
                    measurement_date = measurement.measurement_date.strftime("%d/%m")
                    progress_text += (
                        f"{i}. {measurement.value} {unit_name} - {measurement_date}\n"
                    )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.add_measurement", user_lang),
                            callback_data=f"measure_{measurement_type_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.back", user_lang),
                            callback_data="view_progress",
                        )
                    ],
                ]
            )

            await callback.message.edit_text(progress_text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in handle_progress_detail: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Measurement type ID: {callback.data}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_statistics(callback: CallbackQuery):
        """Handle statistics overview."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_stats_overview(session):
                user_types = (
                    await UserMeasurementTypeRepository.get_user_measurement_types(
                        session, user_id
                    )
                )
                total_measurements = 0
                type_stats = []

                for user_type in user_types:
                    measurements = await MeasurementRepository.get_user_measurements(
                        session, user_id, user_type.measurement_type_id
                    )
                    stats = await MeasurementRepository.get_measurement_stats(
                        session, user_id, user_type.measurement_type_id
                    )
                    total_measurements += stats["count"]
                    if stats["count"] > 0:
                        type_stats.append(
                            {
                                "name": user_type.measurement_type.name,
                                "unit": user_type.measurement_type.unit,
                                "count": stats["count"],
                                "latest": measurements[0] if measurements else None,
                            }
                        )

                return total_measurements, type_stats

            total_measurements, type_stats = await DatabaseManager.execute_with_session(
                _get_stats_overview
            )

            if total_measurements == 0:
                stats_text = translator.get("statistics.no_data", user_lang)
            else:
                stats_text = (
                    f"{translator.get('statistics.title', user_lang)}\n\n"
                    f"{translator.get('statistics.total_measurements', user_lang, count=total_measurements)}\n"
                    f"{translator.get('statistics.total_types', user_lang, count=len(type_stats))}\n\n"
                )

                if type_stats:
                    stats_text += (
                        f"{translator.get('statistics.overview', user_lang)}\n"
                    )
                    for stat in type_stats:
                        type_name = translator.get_measurement_type_name(
                            stat["name"], user_lang
                        )
                        unit_name = translator.get_unit_name(stat["unit"], user_lang)
                        latest_info = ""
                        if stat["latest"]:
                            latest_info = translator.get(
                                "statistics.latest_info",
                                user_lang,
                                value=stat["latest"].value,
                                unit=unit_name,
                            )
                        stats_text += (
                            f"• {type_name}: {stat['count']} records{latest_info}\n"
                        )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.add_measurement", user_lang),
                            callback_data="add_measurement",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=translator.get("buttons.back_to_menu", user_lang),
                            callback_data="back_to_menu",
                        )
                    ],
                ]
            )

            await callback.message.edit_text(stats_text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in handle_statistics: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_back_to_menu(callback: CallbackQuery):
        """Handle back to main menu."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.add_measurement", user_lang),
                    callback_data="add_measurement",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.manage_types", user_lang),
                    callback_data="manage_types",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.view_progress", user_lang),
                    callback_data="view_progress",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.view_by_date", user_lang),
                    callback_data="view_by_date",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.statistics", user_lang),
                    callback_data="statistics",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.notifications", user_lang),
                    callback_data="notifications",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.language_settings", user_lang),
                    callback_data="language_settings",
                ),
            )
            keyboard.adjust(2)

            await callback.message.edit_text(
                translator.get("commands.menu.title", user_lang),
                reply_markup=keyboard.as_markup(),
            )
        except Exception as e:
            logger.error(f"Error in back_to_menu: {e}")
            await callback.answer(translator.get("common.error", "en"))

    @staticmethod
    async def handle_view_by_date(callback: CallbackQuery):
        """Handle view measurements by date callback - show time period options."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("view_by_date.last_7_days", user_lang),
                    callback_data="view_by_date_7",
                ),
                InlineKeyboardButton(
                    text=translator.get("view_by_date.last_30_days", user_lang),
                    callback_data="view_by_date_30",
                ),
                InlineKeyboardButton(
                    text=translator.get("view_by_date.last_90_days", user_lang),
                    callback_data="view_by_date_90",
                ),
                InlineKeyboardButton(
                    text=translator.get("view_by_date.all_time", user_lang),
                    callback_data="view_by_date_all",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="back_to_menu",
                ),
            )
            keyboard.adjust(2)

            await callback.message.edit_text(
                translator.get("view_by_date.select_period", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_view_by_date: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_view_by_date_period(callback: CallbackQuery):
        """Handle view measurements by date for specific period."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            # Extract days from callback data
            period = callback.data.split("_")[-1]
            if period == "all":
                days = -1
                period_text = translator.get("view_by_date.all_time", user_lang)
            else:
                days = int(period)
                if days == 7:
                    period_text = translator.get("view_by_date.last_7_days", user_lang)
                elif days == 30:
                    period_text = translator.get("view_by_date.last_30_days", user_lang)
                elif days == 90:
                    period_text = translator.get("view_by_date.last_90_days", user_lang)
                else:
                    period_text = f"Last {days} days"

            async def _get_measurements_by_date(session):
                return await MeasurementRepository.get_measurements_by_date(
                    session, user_id, days=days
                )

            measurements_by_date = await DatabaseManager.execute_with_session(
                _get_measurements_by_date
            )

            if not measurements_by_date:
                await callback.message.edit_text(
                    translator.get("view_by_date.no_measurements", user_lang),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=translator.get(
                                        "buttons.add_measurement", user_lang
                                    ),
                                    callback_data="add_measurement",
                                ),
                                InlineKeyboardButton(
                                    text=translator.get("buttons.back", user_lang),
                                    callback_data="view_by_date",
                                ),
                            ]
                        ]
                    ),
                )
                return

            # Format the message
            message_text = f"{translator.get('view_by_date.measurements_for_period', user_lang, period=period_text)}\n\n"

            # Sort dates in descending order (newest first)
            sorted_dates = sorted(
                measurements_by_date.keys(),
                key=lambda x: datetime.strptime(x, "%d.%m.%Y"),
                reverse=True,
            )

            for date_str in sorted_dates:
                measurements = measurements_by_date[date_str]
                message_text += f"📆 {date_str}\n"

                # Sort measurements by measurement type name
                measurements.sort(key=lambda m: m.measurement_type.name)

                for measurement in measurements:
                    type_name = translator.get_measurement_type_name(
                        measurement.measurement_type.name, user_lang
                    )
                    unit_name = translator.get_unit_name(
                        measurement.measurement_type.unit, user_lang
                    )
                    value_str = (
                        f"{measurement.value:.1f}"
                        if measurement.value % 1 != 0
                        else f"{int(measurement.value)}"
                    )

                    if measurement.notes:
                        entry_text = translator.get(
                            "view_by_date.measurement_entry",
                            user_lang,
                            type=type_name,
                            value=value_str,
                            unit=unit_name,
                            date="",
                            notes=measurement.notes,
                        )
                    else:
                        entry_text = translator.get(
                            "view_by_date.measurement_entry_no_notes",
                            user_lang,
                            type=type_name,
                            value=value_str,
                            unit=unit_name,
                            date="",
                        )
                    message_text += f"  • {type_name}: {value_str} {unit_name}"
                    if measurement.notes:
                        message_text += f" ({measurement.notes})"
                    message_text += "\n"

                message_text += "\n"

            # Limit message length to avoid Telegram limits
            if len(message_text) > 4000:
                message_text = (
                    message_text[:4000] + "...\n\n(Showing recent entries only)"
                )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(text="🔄 Refresh", callback_data=callback.data),
                InlineKeyboardButton(
                    text=translator.get("view_by_date.select_period", user_lang),
                    callback_data="view_by_date",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back_to_menu", user_lang),
                    callback_data="back_to_menu",
                ),
            )
            keyboard.adjust(2, 1)

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_view_by_date_period: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_notifications(callback: CallbackQuery):
        """Handle notifications menu."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_schedules(session):
                return await NotificationScheduleRepository.get_user_schedules(
                    session, user_id
                )

            schedules = await DatabaseManager.execute_with_session(_get_schedules)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("notifications.add_notification", user_lang),
                    callback_data="add_notification",
                ),
                InlineKeyboardButton(
                    text=translator.get(
                        "notifications.manage_notifications", user_lang
                    ),
                    callback_data="manage_notifications",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back_to_menu", user_lang),
                    callback_data="back_to_menu",
                ),
            )
            keyboard.adjust(1)

            if schedules:
                schedules_text = (
                    f"\n\n{translator.get('notifications.list_title', user_lang)}\n"
                )
                for schedule in schedules:
                    if schedule.day_of_week is None:
                        freq = translator.get(
                            "notifications.list_item_daily",
                            user_lang,
                            time=schedule.notification_time.strftime("%H:%M"),
                        )
                    else:
                        day_name = translator.get(
                            f"days.{['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][schedule.day_of_week]}",
                            user_lang,
                        )
                        freq = translator.get(
                            "notifications.list_item_weekly",
                            user_lang,
                            day=day_name,
                            time=schedule.notification_time.strftime("%H:%M"),
                        )

                    status = translator.get(
                        (
                            "notifications.list_status_active"
                            if schedule.is_active
                            else "notifications.list_status_inactive"
                        ),
                        user_lang,
                    )
                    schedules_text += f"• {freq} - {status}\n"

                message_text = (
                    translator.get("notifications.menu_title", user_lang)
                    + "\n"
                    + translator.get("notifications.menu_description", user_lang)
                    + schedules_text
                )
            else:
                message_text = (
                    translator.get("notifications.menu_title", user_lang)
                    + "\n"
                    + translator.get("notifications.menu_description", user_lang)
                    + "\n\n"
                    + translator.get("notifications.no_notifications", user_lang)
                )

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_notifications: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_add_notification(callback: CallbackQuery):
        """Handle add notification selection."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.daily", user_lang),
                    callback_data="notification_freq_daily",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.monday", user_lang),
                    callback_data="notification_freq_0",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.tuesday", user_lang),
                    callback_data="notification_freq_1",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.wednesday", user_lang),
                    callback_data="notification_freq_2",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.thursday", user_lang),
                    callback_data="notification_freq_3",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.friday", user_lang),
                    callback_data="notification_freq_4",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.saturday", user_lang),
                    callback_data="notification_freq_5",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.sunday", user_lang),
                    callback_data="notification_freq_6",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="notifications",
                ),
            )
            keyboard.adjust(1, 2, 2, 2, 1, 1)

            await callback.message.edit_text(
                translator.get("notifications.select_frequency", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_add_notification: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_notification_frequency(callback: CallbackQuery, state: FSMContext):
        """Handle notification frequency selection."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            # Extract frequency from callback data
            freq_data = callback.data.split("_")[
                -1
            ]  # notification_freq_daily or notification_freq_0

            if freq_data == "daily":
                day_of_week = None
            else:
                day_of_week = int(freq_data)

            # Store the frequency in state
            await state.update_data(day_of_week=day_of_week)
            await state.set_state(UserStates.waiting_for_notification_time)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.cancel", user_lang),
                    callback_data="notifications",
                ),
            )

            await callback.message.edit_text(
                translator.get("notifications.select_time", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_notification_frequency: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_notification_time(message: types.Message, state: FSMContext):
        """Handle notification time input."""
        try:
            user_id = await BotHandlers.get_or_create_user(message.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            # Validate time format
            time_pattern = re.compile(r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$")
            if not time_pattern.match(message.text):
                await message.answer(
                    translator.get("notifications.invalid_time", user_lang)
                )
                return

            # Parse time
            hour, minute = map(int, message.text.split(":"))
            notification_time = time(hour, minute)

            # Get stored frequency data
            data = await state.get_data()
            day_of_week = data.get("day_of_week")

            # Get user's timezone from Telegram (if available) or use UTC
            user_timezone = "UTC"
            if message.from_user.language_code:
                # Try to map language code to timezone - this is a simple mapping
                timezone_mapping = {
                    "uk": "Europe/Kiev",
                    "ru": "Europe/Moscow",
                    "en": "UTC",
                    "de": "Europe/Berlin",
                    "fr": "Europe/Paris",
                    "es": "Europe/Madrid",
                    "it": "Europe/Rome"
                }
                user_timezone = timezone_mapping.get(message.from_user.language_code, "UTC")

            async def _create_schedule(session):
                # Check if schedule already exists
                schedules = await NotificationScheduleRepository.get_user_schedules(
                    session, user_id
                )
                for schedule in schedules:
                    if (
                        schedule.day_of_week == day_of_week
                        and schedule.notification_time == notification_time
                    ):
                        return None  # Schedule exists

                # Create new schedule with timezone
                return await NotificationScheduleRepository.create_schedule(
                    session, user_id, day_of_week, notification_time, user_timezone
                )

            result = await DatabaseManager.execute_with_session(_create_schedule)

            await state.clear()

            if result is None:
                await message.answer(
                    translator.get("notifications.schedule_exists", user_lang)
                )
            else:
                if day_of_week is None:
                    frequency = translator.get(
                        "notifications.frequency_daily", user_lang
                    )
                else:
                    day_name = translator.get(
                        f"days.{['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][day_of_week]}",
                        user_lang,
                    )
                    frequency = translator.get(
                        "notifications.frequency_weekly", user_lang, day=day_name
                    )

                success_message = translator.get(
                    "notifications.success_created",
                    user_lang,
                    frequency=frequency,
                    time=message.text,
                )
                await message.answer(success_message)

            # Show notifications menu
            await BotHandlers.show_notifications_menu(message, user_id, user_lang)

        except Exception as e:
            logger.error(f"Error in handle_notification_time: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                message.from_user.id
            )
            await message.answer(translator.get("notifications.error", user_lang))
            await state.clear()

    @staticmethod
    async def handle_manage_notifications(callback: CallbackQuery):
        """Handle manage notifications selection."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)
            user_lang = await BotHandlers.get_user_language(user_id)

            async def _get_schedules(session):
                return await NotificationScheduleRepository.get_user_schedules(
                    session, user_id
                )

            schedules = await DatabaseManager.execute_with_session(_get_schedules)

            if not schedules:
                await callback.message.edit_text(
                    translator.get("notifications.no_notifications", user_lang),
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=translator.get("buttons.back", user_lang),
                                    callback_data="notifications",
                                )
                            ]
                        ]
                    ),
                )
                return

            keyboard = InlineKeyboardBuilder()
            for schedule in schedules:
                if schedule.day_of_week is None:
                    freq_text = translator.get(
                        "notifications.list_item_daily",
                        user_lang,
                        time=schedule.notification_time.strftime("%H:%M"),
                    )
                else:
                    day_names = [
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
                    day_name = translator.get(
                        f"days.{day_names[schedule.day_of_week]}", user_lang
                    )
                    freq_text = translator.get(
                        "notifications.list_item_weekly",
                        user_lang,
                        day=day_name,
                        time=schedule.notification_time.strftime("%H:%M"),
                    )

                status = "✅" if schedule.is_active else "❌"
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"{freq_text} {status}",
                        callback_data=f"manage_notification_{schedule.id}",
                    )
                )

            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="notifications",
                )
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                translator.get("notifications.select_to_manage", user_lang),
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_manage_notifications: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_manage_notification_detail(callback: CallbackQuery):
        """Handle individual notification management."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            schedule_id = int(callback.data.split("_")[-1])

            async def _get_schedule(session):
                return await NotificationScheduleRepository.get_schedule_by_id(
                    session, schedule_id
                )

            schedule = await DatabaseManager.execute_with_session(_get_schedule)

            if not schedule:
                await callback.answer(translator.get("common.error", user_lang))
                return

            if schedule.day_of_week is None:
                frequency = translator.get("notifications.frequency_daily", user_lang)
            else:
                day_name = translator.get(
                    f"days.{['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][schedule.day_of_week]}",
                    user_lang,
                )
                frequency = translator.get(
                    "notifications.frequency_weekly", user_lang, day=day_name
                )

            status = translator.get(
                (
                    "notifications.list_status_active"
                    if schedule.is_active
                    else "notifications.list_status_inactive"
                ),
                user_lang,
            )

            keyboard = InlineKeyboardBuilder()
            if schedule.is_active:
                keyboard.add(
                    InlineKeyboardButton(
                        text=translator.get("buttons.disable", user_lang),
                        callback_data=f"toggle_notification_{schedule_id}",
                    )
                )
            else:
                keyboard.add(
                    InlineKeyboardButton(
                        text=translator.get("buttons.enable", user_lang),
                        callback_data=f"toggle_notification_{schedule_id}",
                    )
                )

            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.delete", user_lang),
                    callback_data=f"delete_notification_{schedule_id}",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back", user_lang),
                    callback_data="manage_notifications",
                ),
            )
            keyboard.adjust(1, 2)

            message_text = (
                f"{translator.get('notifications.manage_title', user_lang)}\n\n"
                f"{translator.get('notifications.manage_schedule', user_lang, frequency=frequency, time=schedule.notification_time.strftime('%H:%M'))}\n"
                f"{translator.get('notifications.manage_status', user_lang, status=status)}"
            )

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_manage_notification_detail: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_toggle_notification(callback: CallbackQuery):
        """Handle notification toggle (enable/disable)."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            schedule_id = int(callback.data.split("_")[-1])

            async def _toggle_schedule(session):
                schedule = await NotificationScheduleRepository.get_schedule_by_id(
                    session, schedule_id
                )
                if schedule:
                    schedule.is_active = not schedule.is_active
                    await session.flush()
                    return schedule
                return None

            schedule = await DatabaseManager.execute_with_session(_toggle_schedule)

            if schedule:
                await callback.answer(
                    translator.get("notifications.success_updated", user_lang)
                )
                # Refresh the detail view
                callback.data = f"manage_notification_{schedule_id}"
                await BotHandlers.handle_manage_notification_detail(callback)
            else:
                await callback.answer(translator.get("notifications.error", user_lang))

        except Exception as e:
            logger.error(f"Error in handle_toggle_notification: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_delete_notification(callback: CallbackQuery):
        """Handle notification deletion confirmation."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            schedule_id = int(callback.data.split("_")[-1])

            async def _get_schedule(session):
                return await NotificationScheduleRepository.get_schedule_by_id(
                    session, schedule_id
                )

            schedule = await DatabaseManager.execute_with_session(_get_schedule)

            if not schedule:
                await callback.answer(translator.get("common.error", user_lang))
                return

            if schedule.day_of_week is None:
                frequency = translator.get("notifications.frequency_daily", user_lang)
            else:
                day_name = translator.get(
                    f"days.{['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][schedule.day_of_week]}",
                    user_lang,
                )
                frequency = translator.get(
                    "notifications.frequency_weekly", user_lang, day=day_name
                )

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("buttons.yes", user_lang),
                    callback_data=f"confirm_delete_notification_{schedule_id}",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.no", user_lang),
                    callback_data=f"manage_notification_{schedule_id}",
                ),
            )
            keyboard.adjust(2)

            confirm_text = translator.get(
                "notifications.confirm_delete",
                user_lang,
                frequency=frequency,
                time=schedule.notification_time.strftime("%H:%M"),
            )

            await callback.message.edit_text(
                confirm_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_delete_notification: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def handle_confirm_delete_notification(callback: CallbackQuery):
        """Handle confirmed notification deletion."""
        try:
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )

            schedule_id = int(callback.data.split("_")[-1])

            async def _delete_schedule(session):
                return await NotificationScheduleRepository.delete_schedule(
                    session, schedule_id
                )

            success = await DatabaseManager.execute_with_session(_delete_schedule)

            if success:
                await callback.answer(
                    translator.get("notifications.success_deleted", user_lang)
                )
                # Go back to main notifications menu
                await BotHandlers._show_notifications_menu_callback(callback, user_lang)
            else:
                await callback.answer(translator.get("notifications.error", user_lang))

        except Exception as e:
            logger.error(f"Error in handle_confirm_delete_notification: {e}")
            user_lang = await BotHandlers.get_user_language_by_telegram_id(
                callback.from_user.id
            )
            await callback.answer(translator.get("common.error", user_lang))

    @staticmethod
    async def show_notifications_menu(message, user_id: int, user_lang: str):
        """Helper method to show notifications menu."""

        async def _get_schedules(session):
            return await NotificationScheduleRepository.get_user_schedules(
                session, user_id
            )

        schedules = await DatabaseManager.execute_with_session(_get_schedules)

        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(
                text=translator.get("notifications.add_notification", user_lang),
                callback_data="add_notification",
            ),
            InlineKeyboardButton(
                text=translator.get("notifications.manage_notifications", user_lang),
                callback_data="manage_notifications",
            ),
            InlineKeyboardButton(
                text=translator.get("buttons.back_to_menu", user_lang),
                callback_data="back_to_menu",
            ),
        )
        keyboard.adjust(1)

        if schedules:
            schedules_text = (
                f"\n\n{translator.get('notifications.list_title', user_lang)}\n"
            )
            for schedule in schedules:
                if schedule.day_of_week is None:
                    freq = translator.get(
                        "notifications.list_item_daily",
                        user_lang,
                        time=schedule.notification_time.strftime("%H:%M"),
                    )
                else:
                    day_names = [
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
                    day_name = translator.get(
                        f"days.{day_names[schedule.day_of_week]}", user_lang
                    )
                    freq = translator.get(
                        "notifications.list_item_weekly",
                        user_lang,
                        day=day_name,
                        time=schedule.notification_time.strftime("%H:%M"),
                    )

                status = translator.get(
                    (
                        "notifications.list_status_active"
                        if schedule.is_active
                        else "notifications.list_status_inactive"
                    ),
                    user_lang,
                )
                schedules_text += f"• {freq} - {status}\n"

            message_text = (
                translator.get("notifications.menu_title", user_lang)
                + "\n"
                + translator.get("notifications.menu_description", user_lang)
                + schedules_text
            )
        else:
            message_text = (
                translator.get("notifications.menu_title", user_lang)
                + "\n"
                + translator.get("notifications.menu_description", user_lang)
                + "\n\n"
                + translator.get("notifications.no_notifications", user_lang)
            )

        await message.answer(message_text, reply_markup=keyboard.as_markup())

    @staticmethod
    async def _show_notifications_menu_callback(
        callback: CallbackQuery, user_lang: str
    ):
        """Helper method to show notifications menu for callbacks."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_schedules(session):
                return await NotificationScheduleRepository.get_user_schedules(
                    session, user_id
                )

            schedules = await DatabaseManager.execute_with_session(_get_schedules)

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text=translator.get("notifications.add_notification", user_lang),
                    callback_data="add_notification",
                ),
                InlineKeyboardButton(
                    text=translator.get(
                        "notifications.manage_notifications", user_lang
                    ),
                    callback_data="manage_notifications",
                ),
                InlineKeyboardButton(
                    text=translator.get("buttons.back_to_menu", user_lang),
                    callback_data="back_to_menu",
                ),
            )
            keyboard.adjust(1)

            if schedules:
                schedules_text = (
                    f"\n\n{translator.get('notifications.list_title', user_lang)}\n"
                )
                for schedule in schedules:
                    if schedule.day_of_week is None:
                        freq = translator.get(
                            "notifications.list_item_daily",
                            user_lang,
                            time=schedule.notification_time.strftime("%H:%M"),
                        )
                    else:
                        day_names = [
                            "monday",
                            "tuesday",
                            "wednesday",
                            "thursday",
                            "friday",
                            "saturday",
                            "sunday",
                        ]
                        day_name = translator.get(
                            f"days.{day_names[schedule.day_of_week]}", user_lang
                        )
                        freq = translator.get(
                            "notifications.list_item_weekly",
                            user_lang,
                            day=day_name,
                            time=schedule.notification_time.strftime("%H:%M"),
                        )

                    status = translator.get(
                        (
                            "notifications.list_status_active"
                            if schedule.is_active
                            else "notifications.list_status_inactive"
                        ),
                        user_lang,
                    )
                    schedules_text += f"• {freq} - {status}\n"

                message_text = (
                    translator.get("notifications.menu_title", user_lang)
                    + "\n"
                    + translator.get("notifications.menu_description", user_lang)
                    + schedules_text
                )
            else:
                message_text = (
                    translator.get("notifications.menu_title", user_lang)
                    + "\n"
                    + translator.get("notifications.menu_description", user_lang)
                    + "\n\n"
                    + translator.get("notifications.no_notifications", user_lang)
                )

            await callback.message.edit_text(
                message_text, reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in _show_notifications_menu_callback: {e}")
            await callback.answer(translator.get("notifications.error", user_lang))


# Register handlers
dp.message.register(BotHandlers.start_command, Command("start"))
dp.message.register(BotHandlers.menu_command, Command("menu"))
dp.message.register(
    BotHandlers.handle_measurement_value,
    StateFilter(UserStates.waiting_for_measurement_value),
)
dp.message.register(
    BotHandlers.handle_custom_type_name,
    StateFilter(UserStates.creating_custom_type_name),
)
dp.message.register(
    BotHandlers.handle_custom_type_unit,
    StateFilter(UserStates.creating_custom_type_unit),
)
dp.message.register(
    BotHandlers.handle_custom_type_description,
    StateFilter(UserStates.creating_custom_type_description),
)
dp.message.register(
    BotHandlers.handle_notification_time,
    StateFilter(UserStates.waiting_for_notification_time),
)

# Callback handlers
dp.callback_query.register(
    BotHandlers.handle_add_measurement, F.data == "add_measurement"
)
dp.callback_query.register(
    BotHandlers.handle_measure_type, F.data.startswith("measure_")
)
dp.callback_query.register(BotHandlers.handle_manage_types, F.data == "manage_types")
dp.callback_query.register(BotHandlers.handle_add_types, F.data == "add_types")
dp.callback_query.register(
    BotHandlers.handle_add_type_confirm, F.data.startswith("add_type_")
)
dp.callback_query.register(
    BotHandlers.handle_create_custom_type, F.data == "create_custom_type"
)
dp.callback_query.register(
    BotHandlers.handle_skip_description, F.data == "skip_description"
)
dp.callback_query.register(BotHandlers.handle_remove_types, F.data == "remove_types")
dp.callback_query.register(
    BotHandlers.handle_remove_type_confirm, F.data.startswith("remove_type_")
)
dp.callback_query.register(BotHandlers.handle_view_progress, F.data == "view_progress")
dp.callback_query.register(
    BotHandlers.handle_progress_detail, F.data.startswith("progress_")
)
dp.callback_query.register(BotHandlers.handle_statistics, F.data == "statistics")
dp.callback_query.register(BotHandlers.handle_view_by_date, F.data == "view_by_date")
dp.callback_query.register(
    BotHandlers.handle_view_by_date_period, F.data.startswith("view_by_date_")
)
dp.callback_query.register(
    BotHandlers.handle_language_settings, F.data == "language_settings"
)
dp.callback_query.register(
    BotHandlers.handle_set_language, F.data.startswith("set_language_")
)
dp.callback_query.register(BotHandlers.handle_back_to_menu, F.data == "back_to_menu")

# Notification handlers
dp.callback_query.register(BotHandlers.handle_notifications, F.data == "notifications")
dp.callback_query.register(
    BotHandlers.handle_add_notification, F.data == "add_notification"
)
dp.callback_query.register(
    BotHandlers.handle_notification_frequency, F.data.startswith("notification_freq_")
)
dp.callback_query.register(
    BotHandlers.handle_manage_notifications, F.data == "manage_notifications"
)
dp.callback_query.register(
    BotHandlers.handle_manage_notification_detail,
    F.data.startswith("manage_notification_"),
)
dp.callback_query.register(
    BotHandlers.handle_toggle_notification, F.data.startswith("toggle_notification_")
)
dp.callback_query.register(
    BotHandlers.handle_delete_notification, F.data.startswith("delete_notification_")
)
dp.callback_query.register(
    BotHandlers.handle_confirm_delete_notification,
    F.data.startswith("confirm_delete_notification_"),
)


async def init_measurement_types():
    """Initialize default measurement types with translation keys."""
    # Map translation keys to database names, units, and descriptions
    # Using translation keys as the canonical reference
    default_types = [
        ("weight", "kg", "Body weight"),
        ("height", "cm", "Body height"),
        ("waist", "cm", "Waist circumference"),
        ("chest", "cm", "Chest circumference"),
        ("hips", "cm", "Hip circumference"),
        ("bicep", "cm", "Bicep circumference"),
        ("thigh", "cm", "Thigh circumference"),
        ("neck", "cm", "Neck circumference"),
        ("forearm", "cm", "Forearm circumference"),
        ("calf", "cm", "Calf circumference"),
        ("shoulders", "cm", "Shoulder width"),
        ("body_fat", "%", "Body fat percentage"),
        ("muscle_mass", "kg", "Muscle mass"),
    ]

    async def _create_types(session):
        for translation_key, unit, description in default_types:
            existing = await MeasurementTypeRepository.get_type_by_name(
                session, translation_key
            )
            if not existing:
                await MeasurementTypeRepository.create_measurement_type(
                    session, translation_key, unit, description
                )

    await DatabaseManager.execute_with_session(_create_types)


async def main():
    """Main bot execution function."""
    try:
        logger.info("Starting EasyTrack bot...")

        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize default measurement types
        await init_measurement_types()
        logger.info("Default measurement types initialized")

        # Initialize and start notification scheduler
        scheduler = set_scheduler(bot)
        await scheduler.start()
        logger.info("Notification scheduler started")

        # Start bot
        logger.info("Bot is starting...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        # Stop scheduler
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.stop()
            logger.info("Notification scheduler stopped")

        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
