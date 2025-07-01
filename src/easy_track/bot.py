import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from .database import DatabaseManager, init_db, close_db
from .repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
    MeasurementRepository,
)
from .i18n import translator

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
            await callback.answer(translator.get("common.error", user_lang))

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
            await callback.answer("❌ Error occurred. Please try again.")

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
            await message.answer("❌ Error saving measurement. Please try again.")
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
                all_types = await MeasurementTypeRepository.get_all_active_types(
                    session
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
                    current_types_list.append(f"• {type_name} ({unit_name})")
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

            async def _get_available_types(session):
                user_types = (
                    await UserMeasurementTypeRepository.get_user_measurement_types(
                        session, user_id
                    )
                )
                all_types = await MeasurementTypeRepository.get_all_active_types(
                    session
                )
                user_type_ids = {ut.measurement_type_id for ut in user_types}
                return [t for t in all_types if t.id not in user_type_ids]

            available_types = await DatabaseManager.execute_with_session(
                _get_available_types
            )

            if not available_types:
                await callback.answer(
                    "✅ You're already tracking all available measurement types!"
                )
                return

            keyboard = InlineKeyboardBuilder()
            for mtype in available_types:
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"➕ {mtype.name} ({mtype.unit})",
                        callback_data=f"add_type_{mtype.id}",
                    )
                )
            keyboard.add(
                InlineKeyboardButton(text="🔙 Back", callback_data="manage_types")
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                "➕ Select measurement types to add:", reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_add_types: {e}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_add_type_confirm(callback: CallbackQuery):
        """Handle confirmation of adding a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[2])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _add_type(session):
                await UserMeasurementTypeRepository.add_measurement_type_to_user(
                    session, user_id, measurement_type_id
                )
                return await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )

            measurement_type = await DatabaseManager.execute_with_session(_add_type)

            await callback.answer(
                f"✅ Added {measurement_type.name} to your tracking list!"
            )
            await BotHandlers.handle_add_types(callback)

        except Exception as e:
            logger.error(f"Error in handle_add_type_confirm: {e}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_remove_types(callback: CallbackQuery):
        """Handle removing measurement types from user."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, user_id
                )

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.answer("❌ No measurement types to remove!")
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"➖ {user_type.measurement_type.name}",
                        callback_data=f"remove_type_{user_type.measurement_type.id}",
                    )
                )
            keyboard.add(
                InlineKeyboardButton(text="🔙 Back", callback_data="manage_types")
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                "➖ Select measurement types to remove:",
                reply_markup=keyboard.as_markup(),
            )

        except Exception as e:
            logger.error(f"Error in handle_remove_types: {e}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_remove_type_confirm(callback: CallbackQuery):
        """Handle confirmation of removing a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[2])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _remove_type(session):
                success = await UserMeasurementTypeRepository.remove_measurement_type_from_user(
                    session, user_id, measurement_type_id
                )
                measurement_type = await MeasurementTypeRepository.get_type_by_id(
                    session, measurement_type_id
                )
                return success, measurement_type

            success, measurement_type = await DatabaseManager.execute_with_session(
                _remove_type
            )

            if success:
                await callback.answer(
                    f"✅ Removed {measurement_type.name} from your tracking list!"
                )
            else:
                await callback.answer("❌ Failed to remove measurement type.")

            await BotHandlers.handle_remove_types(callback)

        except Exception as e:
            logger.error(f"Error in handle_remove_type_confirm: {e}")
            await callback.answer("❌ Error occurred. Please try again.")

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


# Register handlers
dp.message.register(BotHandlers.start_command, Command("start"))
dp.message.register(BotHandlers.menu_command, Command("menu"))
dp.message.register(
    BotHandlers.handle_measurement_value,
    StateFilter(UserStates.waiting_for_measurement_value),
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


async def init_measurement_types():
    """Initialize default measurement types."""
    default_types = [
        ("Weight", "kg", "Body weight"),
        ("Waist", "cm", "Waist circumference"),
        ("Chest", "cm", "Chest circumference"),
        ("Biceps", "cm", "Bicep circumference"),
        ("Thigh", "cm", "Thigh circumference"),
        ("Hip", "cm", "Hip circumference"),
        ("Neck", "cm", "Neck circumference"),
        ("Body Fat %", "%", "Body fat percentage"),
        ("Muscle Mass", "kg", "Muscle mass"),
    ]

    async def _create_types(session):
        for name, unit, description in default_types:
            existing = await MeasurementTypeRepository.get_type_by_name(session, name)
            if not existing:
                await MeasurementTypeRepository.create_measurement_type(
                    session, name, unit, description
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

        # Start bot
        logger.info("Bot is starting...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
