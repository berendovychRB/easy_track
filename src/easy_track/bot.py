import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
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
    UserRepository, MeasurementTypeRepository,
    UserMeasurementTypeRepository, MeasurementRepository
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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


class BotHandlers:
    """Main bot handlers class."""

    @staticmethod
    async def get_or_create_user(telegram_user: types.User) -> int:
        """Get or create user and return user ID."""
        async def _get_or_create(session):
            user = await UserRepository.get_user_by_telegram_id(session, telegram_user.id)
            if not user:
                user = await UserRepository.create_user(
                    session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name
                )
            return user.id

        return await DatabaseManager.execute_with_session(_get_or_create)

    @staticmethod
    async def start_command(message: types.Message):
        """Handle /start command."""
        try:
            user_id = await BotHandlers.get_or_create_user(message.from_user)

            welcome_text = (
                f"👋 Welcome to EasyTrack, {message.from_user.first_name}!\n\n"
                "📊 Track your body measurements easily:\n"
                "• Choose which measurements to track\n"
                "• Log your progress regularly\n"
                "• View your improvement over time\n\n"
                "Use /menu to see all available options."
            )

            await message.answer(welcome_text)
            await BotHandlers.show_main_menu(message)

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("❌ Sorry, something went wrong. Please try again.")

    @staticmethod
    async def show_main_menu(message: types.Message):
        """Show main menu with options."""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(text="📝 Add Measurement", callback_data="add_measurement"),
            InlineKeyboardButton(text="⚙️ Manage Types", callback_data="manage_types"),
            InlineKeyboardButton(text="📊 View Progress", callback_data="view_progress"),
            InlineKeyboardButton(text="📅 View by Date", callback_data="view_by_date"),
            InlineKeyboardButton(text="📈 Statistics", callback_data="statistics")
        )
        keyboard.adjust(2)

        await message.answer(
            "🏠 Main Menu - Choose an option:",
            reply_markup=keyboard.as_markup()
        )

    @staticmethod
    async def menu_command(message: types.Message):
        """Handle /menu command."""
        await BotHandlers.show_main_menu(message)

    @staticmethod
    async def handle_add_measurement(callback: CallbackQuery):
        """Handle add measurement callback."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.message.edit_text(
                    "❌ You haven't selected any measurement types to track yet.\n"
                    "Please configure your measurement types first.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="⚙️ Manage Types", callback_data="manage_types"),
                        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
                    ]])
                )
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                keyboard.add(InlineKeyboardButton(
                    text=f"{user_type.measurement_type.name} ({user_type.measurement_type.unit})",
                    callback_data=f"measure_{user_type.measurement_type.id}"
                ))
            keyboard.add(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu"))
            keyboard.adjust(1)

            await callback.message.edit_text(
                "📝 Select measurement type to add:",
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_add_measurement: {e}")
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

            async def _get_type_info(session):
                return await MeasurementTypeRepository.get_type_by_id(session, measurement_type_id)

            measurement_type = await DatabaseManager.execute_with_session(_get_type_info)

            if not measurement_type:
                await callback.answer("❌ Measurement type not found.")
                return

            await state.update_data(measurement_type_id=measurement_type_id)
            await state.set_state(UserStates.waiting_for_measurement_value)

            # Get latest measurement for reference
            async def _get_latest(session):
                return await MeasurementRepository.get_latest_measurement(session, user_id, measurement_type_id)

            latest = await DatabaseManager.execute_with_session(_get_latest)

            latest_text = ""
            if latest:
                latest_text = f"\n📌 Last recorded: {latest.value} {measurement_type.unit} on {latest.measurement_date.strftime('%Y-%m-%d')}"

            await callback.message.edit_text(
                f"📏 Enter your {measurement_type.name} measurement in {measurement_type.unit}:{latest_text}\n\n"
                "💡 Send me just the number (e.g., 75.5)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="❌ Cancel", callback_data="add_measurement")
                ]])
            )

        except Exception as e:
            logger.error(f"Error in handle_measure_type: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Callback data: {callback.data}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_measurement_value(message: types.Message, state: FSMContext):
        """Handle measurement value input."""
        try:
            data = await state.get_data()
            measurement_type_id = data.get("measurement_type_id")

            if not measurement_type_id:
                await message.answer("❌ Session expired. Please start over.")
                await state.clear()
                return

            # Validate numeric input
            try:
                value = float(message.text.strip())
                if value <= 0:
                    raise ValueError("Value must be positive")
            except ValueError:
                await message.answer("❌ Please enter a valid positive number.")
                return

            user_id = await BotHandlers.get_or_create_user(message.from_user)

            async def _save_measurement(session):
                measurement = await MeasurementRepository.create_measurement(
                    session, user_id, measurement_type_id, value
                )
                measurement_type = await MeasurementTypeRepository.get_type_by_id(session, measurement_type_id)
                return measurement, measurement_type

            measurement, measurement_type = await DatabaseManager.execute_with_session(_save_measurement)

            await state.clear()

            success_text = (
                f"✅ Measurement saved successfully!\n\n"
                f"📏 {measurement_type.name}: {value} {measurement_type.unit}\n"
                f"📅 Date: {measurement.measurement_date.strftime('%Y-%m-%d %H:%M')}"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Add Another", callback_data="add_measurement")],
                [InlineKeyboardButton(text="📊 View Progress", callback_data="view_progress")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_to_menu")]
            ])

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

            async def _get_data(session):
                user_types = await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)
                all_types = await MeasurementTypeRepository.get_all_active_types(session)
                return user_types, all_types

            user_types, all_types = await DatabaseManager.execute_with_session(_get_data)

            user_type_ids = {ut.measurement_type_id for ut in user_types}
            available_types = [t for t in all_types if t.id not in user_type_ids]

            keyboard = InlineKeyboardBuilder()

            if user_types:
                keyboard.add(InlineKeyboardButton(text="➖ Remove Types", callback_data="remove_types"))

            if available_types:
                keyboard.add(InlineKeyboardButton(text="➕ Add Types", callback_data="add_types"))

            keyboard.add(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu"))
            keyboard.adjust(1)

            current_types_text = ""
            if user_types:
                current_types_text = "\n\n📋 Currently tracking:\n" + "\n".join([
                    f"• {ut.measurement_type.name} ({ut.measurement_type.unit})"
                    for ut in user_types
                ])
            else:
                current_types_text = "\n\n📋 No measurement types selected yet."

            await callback.message.edit_text(
                f"⚙️ Manage Measurement Types{current_types_text}",
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_manage_types: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_add_types(callback: CallbackQuery):
        """Handle adding measurement types to user."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_available_types(session):
                user_types = await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)
                all_types = await MeasurementTypeRepository.get_all_active_types(session)
                user_type_ids = {ut.measurement_type_id for ut in user_types}
                return [t for t in all_types if t.id not in user_type_ids]

            available_types = await DatabaseManager.execute_with_session(_get_available_types)

            if not available_types:
                await callback.answer("✅ You're already tracking all available measurement types!")
                return

            keyboard = InlineKeyboardBuilder()
            for mtype in available_types:
                keyboard.add(InlineKeyboardButton(
                    text=f"➕ {mtype.name} ({mtype.unit})",
                    callback_data=f"add_type_{mtype.id}"
                ))
            keyboard.add(InlineKeyboardButton(text="🔙 Back", callback_data="manage_types"))
            keyboard.adjust(1)

            await callback.message.edit_text(
                "➕ Select measurement types to add:",
                reply_markup=keyboard.as_markup()
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
                return await MeasurementTypeRepository.get_type_by_id(session, measurement_type_id)

            measurement_type = await DatabaseManager.execute_with_session(_add_type)

            await callback.answer(f"✅ Added {measurement_type.name} to your tracking list!")
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
                return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.answer("❌ No measurement types to remove!")
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                keyboard.add(InlineKeyboardButton(
                    text=f"➖ {user_type.measurement_type.name}",
                    callback_data=f"remove_type_{user_type.measurement_type.id}"
                ))
            keyboard.add(InlineKeyboardButton(text="🔙 Back", callback_data="manage_types"))
            keyboard.adjust(1)

            await callback.message.edit_text(
                "➖ Select measurement types to remove:",
                reply_markup=keyboard.as_markup()
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
                measurement_type = await MeasurementTypeRepository.get_type_by_id(session, measurement_type_id)
                return success, measurement_type

            success, measurement_type = await DatabaseManager.execute_with_session(_remove_type)

            if success:
                await callback.answer(f"✅ Removed {measurement_type.name} from your tracking list!")
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

            async def _get_user_types(session):
                return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

            user_types = await DatabaseManager.execute_with_session(_get_user_types)

            if not user_types:
                await callback.message.edit_text(
                    "❌ You haven't selected any measurement types to track yet.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="⚙️ Manage Types", callback_data="manage_types"),
                        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
                    ]])
                )
                return

            keyboard = InlineKeyboardBuilder()
            for user_type in user_types:
                keyboard.add(InlineKeyboardButton(
                    text=f"📊 {user_type.measurement_type.name}",
                    callback_data=f"progress_{user_type.measurement_type.id}"
                ))
            keyboard.add(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu"))
            keyboard.adjust(1)

            await callback.message.edit_text(
                "📊 Select measurement type to view progress:",
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_view_progress: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_progress_detail(callback: CallbackQuery):
        """Handle detailed progress view for a measurement type."""
        try:
            measurement_type_id = int(callback.data.split("_")[1])
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_progress_data(session):
                measurement_type = await MeasurementTypeRepository.get_type_by_id(session, measurement_type_id)
                measurements = await MeasurementRepository.get_user_measurements(
                    session, user_id, measurement_type_id, limit=10
                )
                stats = await MeasurementRepository.get_measurement_stats(session, user_id, measurement_type_id)
                return measurement_type, measurements, stats

            measurement_type, measurements, stats = await DatabaseManager.execute_with_session(_get_progress_data)

            if not measurements:
                progress_text = f"📊 {measurement_type.name} Progress\n\n❌ No measurements recorded yet."
            else:
                latest = measurements[0]
                progress_text = (
                    f"📊 {measurement_type.name} Progress\n\n"
                    f"📈 Latest: {latest.value} {measurement_type.unit}\n"
                    f"📅 Date: {latest.measurement_date.strftime('%Y-%m-%d')}\n\n"
                    f"📊 Statistics:\n"
                    f"• Total records: {stats['count']}\n"
                    f"• Average: {stats['average']} {measurement_type.unit}\n"
                    f"• Minimum: {stats['minimum']} {measurement_type.unit}\n"
                    f"• Maximum: {stats['maximum']} {measurement_type.unit}\n\n"
                    f"📋 Recent measurements:\n"
                )

                for i, measurement in enumerate(measurements[:5], 1):
                    progress_text += f"{i}. {measurement.value} {measurement_type.unit} - {measurement.measurement_date.strftime('%m/%d')}\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Add Measurement", callback_data=f"measure_{measurement_type_id}")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="view_progress")]
            ])

            await callback.message.edit_text(progress_text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in handle_progress_detail: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Measurement type ID: {callback.data}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_statistics(callback: CallbackQuery):
        """Handle statistics overview."""
        try:
            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_stats_overview(session):
                user_types = await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)
                total_measurements = 0
                type_stats = []

                for user_type in user_types:
                    measurements = await MeasurementRepository.get_user_measurements(
                        session, user_id, user_type.measurement_type_id
                    )
                    stats = await MeasurementRepository.get_measurement_stats(
                        session, user_id, user_type.measurement_type_id
                    )
                    total_measurements += stats['count']
                    if stats['count'] > 0:
                        type_stats.append({
                            'name': user_type.measurement_type.name,
                            'unit': user_type.measurement_type.unit,
                            'count': stats['count'],
                            'latest': measurements[0] if measurements else None
                        })

                return total_measurements, type_stats

            total_measurements, type_stats = await DatabaseManager.execute_with_session(_get_stats_overview)

            if total_measurements == 0:
                stats_text = "📈 Statistics\n\n❌ No measurements recorded yet.\nStart tracking to see your progress!"
            else:
                stats_text = (
                    f"📈 Your Statistics\n\n"
                    f"🎯 Total measurements: {total_measurements}\n"
                    f"📊 Tracking {len(type_stats)} measurement types\n\n"
                )

                if type_stats:
                    stats_text += "📋 Overview:\n"
                    for stat in type_stats:
                        latest_info = ""
                        if stat['latest']:
                            latest_info = f" (Latest: {stat['latest'].value} {stat['unit']})"
                        stats_text += f"• {stat['name']}: {stat['count']} records{latest_info}\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 View Progress", callback_data="view_progress")],
                [InlineKeyboardButton(text="📝 Add Measurement", callback_data="add_measurement")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")]
            ])

            await callback.message.edit_text(stats_text, reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error in handle_statistics: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_back_to_menu(callback: CallbackQuery):
        """Handle back to main menu."""
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(text="📝 Add Measurement", callback_data="add_measurement"),
            InlineKeyboardButton(text="⚙️ Manage Types", callback_data="manage_types"),
            InlineKeyboardButton(text="📊 View Progress", callback_data="view_progress"),
            InlineKeyboardButton(text="📅 View by Date", callback_data="view_by_date"),
            InlineKeyboardButton(text="📈 Statistics", callback_data="statistics")
        )
        keyboard.adjust(2)

        await callback.message.edit_text(
            "🏠 Main Menu - Choose an option:",
            reply_markup=keyboard.as_markup()
        )

    @staticmethod
    async def handle_view_by_date(callback: CallbackQuery):
        """Handle view measurements by date callback - show time period options."""
        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(text="📅 Last 7 days", callback_data="view_by_date_7"),
                InlineKeyboardButton(text="📅 Last 30 days", callback_data="view_by_date_30"),
                InlineKeyboardButton(text="📅 Last 90 days", callback_data="view_by_date_90"),
                InlineKeyboardButton(text="📅 All time", callback_data="view_by_date_all"),
                InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
            )
            keyboard.adjust(2)

            await callback.message.edit_text(
                "📅 Select time period to view measurements by date:",
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_view_by_date: {e}")
            await callback.answer("❌ Error occurred. Please try again.")

    @staticmethod
    async def handle_view_by_date_period(callback: CallbackQuery):
        """Handle view measurements by date for specific period."""
        try:
            # Extract days from callback data
            period = callback.data.split("_")[-1]
            if period == "all":
                days = -1
                period_text = "All time"
            else:
                days = int(period)
                period_text = f"Last {days} days"

            user_id = await BotHandlers.get_or_create_user(callback.from_user)

            async def _get_measurements_by_date(session):
                return await MeasurementRepository.get_measurements_by_date(session, user_id, days=days)

            measurements_by_date = await DatabaseManager.execute_with_session(_get_measurements_by_date)

            if not measurements_by_date:
                await callback.message.edit_text(
                    f"❌ No measurements found for {period_text.lower()}.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="📝 Add Measurement", callback_data="add_measurement"),
                        InlineKeyboardButton(text="🔙 Back", callback_data="view_by_date")
                    ]])
                )
                return

            # Format the message
            message_text = f"📅 Your Measurements by Date ({period_text}):\n\n"

            # Sort dates in descending order (newest first)
            sorted_dates = sorted(measurements_by_date.keys(),
                                key=lambda x: datetime.strptime(x, "%d.%m.%Y"),
                                reverse=True)

            for date_str in sorted_dates:
                measurements = measurements_by_date[date_str]
                message_text += f"📆 {date_str}\n"

                # Sort measurements by measurement type name
                measurements.sort(key=lambda m: m.measurement_type.name)

                for measurement in measurements:
                    value_str = f"{measurement.value:.1f}" if measurement.value % 1 != 0 else f"{int(measurement.value)}"
                    message_text += f"  • {measurement.measurement_type.name}: {value_str} {measurement.measurement_type.unit}"
                    if measurement.notes:
                        message_text += f" ({measurement.notes})"
                    message_text += "\n"

                message_text += "\n"

            # Limit message length to avoid Telegram limits
            if len(message_text) > 4000:
                message_text = message_text[:4000] + "...\n\n(Showing recent entries only)"

            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(text="🔄 Refresh", callback_data=callback.data),
                InlineKeyboardButton(text="📅 Change Period", callback_data="view_by_date"),
                InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
            )
            keyboard.adjust(2)

            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard.as_markup()
            )

        except Exception as e:
            logger.error(f"Error in handle_view_by_date_period: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await callback.answer("❌ Error occurred. Please try again.")


# Register handlers
dp.message.register(BotHandlers.start_command, Command("start"))
dp.message.register(BotHandlers.menu_command, Command("menu"))
dp.message.register(BotHandlers.handle_measurement_value, StateFilter(UserStates.waiting_for_measurement_value))

# Callback handlers
dp.callback_query.register(BotHandlers.handle_add_measurement, F.data == "add_measurement")
dp.callback_query.register(BotHandlers.handle_measure_type, F.data.startswith("measure_"))
dp.callback_query.register(BotHandlers.handle_manage_types, F.data == "manage_types")
dp.callback_query.register(BotHandlers.handle_add_types, F.data == "add_types")
dp.callback_query.register(BotHandlers.handle_add_type_confirm, F.data.startswith("add_type_"))
dp.callback_query.register(BotHandlers.handle_remove_types, F.data == "remove_types")
dp.callback_query.register(BotHandlers.handle_remove_type_confirm, F.data.startswith("remove_type_"))
dp.callback_query.register(BotHandlers.handle_view_progress, F.data == "view_progress")
dp.callback_query.register(BotHandlers.handle_progress_detail, F.data.startswith("progress_"))
dp.callback_query.register(BotHandlers.handle_statistics, F.data == "statistics")
dp.callback_query.register(BotHandlers.handle_view_by_date, F.data == "view_by_date")
dp.callback_query.register(BotHandlers.handle_view_by_date_period, F.data.startswith("view_by_date_"))
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
