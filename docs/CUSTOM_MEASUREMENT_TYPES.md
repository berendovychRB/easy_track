# Custom Measurement Types Feature

This document describes the new custom measurement types feature that allows users to create their own measurement types in addition to the predefined system types.

## Overview

The EasyTrack bot now supports user-created custom measurement types. Users can create their own measurement types with custom names, units, and descriptions, which are private to each user.

## Features

### ✨ Create Custom Types
- Users can create custom measurement types with:
  - **Name**: Custom name for the measurement (e.g., "Blood Pressure", "Body Temperature")
  - **Unit**: Unit of measurement (e.g., "mmHg", "°C", "%")
  - **Description**: Optional description explaining what the measurement is for

### 🔒 Privacy & Security
- Custom types are **private** to each user - other users cannot see or use them
- Each user can only create types with unique names within their own collection
- System-wide uniqueness is enforced per user (User A and User B can both have a "Blood Pressure" type)

### 🎯 Automatic Integration
- Custom types are automatically added to the user's tracking list upon creation
- Custom types appear alongside system types in all relevant menus
- Custom types are visually distinguished with a 🔧 icon vs 📏 for system types

## User Flow

### Creating a Custom Type

1. **Access the Feature**
   - Go to Main Menu → Manage Types → Add Types
   - Click "✨ Create Custom Type"

2. **Enter Name**
   - Bot prompts for measurement type name
   - Name must be 2-50 characters long
   - Cannot duplicate existing names (system or user's custom types)

3. **Enter Unit**
   - Bot prompts for unit of measurement
   - Unit must be 1-10 characters long
   - Common examples: cm, kg, mmHg, °C, %, etc.

4. **Optional Description**
   - Bot prompts for optional description
   - Can skip by clicking "⏭️ Skip Description"
   - Description limited to 200 characters

5. **Automatic Activation**
   - Custom type is created and automatically added to tracking list
   - User can immediately start adding measurements

### Using Custom Types

Once created, custom types work exactly like system types:
- Appear in measurement type selection menus
- Can be used to record measurements
- Show up in progress tracking and statistics
- Can be managed (added/removed from tracking list)

## Technical Implementation

### Database Schema Changes

New columns added to `measurement_types` table:
- `is_custom` (Boolean): Identifies user-created vs system types
- `created_by_user_id` (Integer, FK): Links custom types to their creator
- Unique constraint on `(name, created_by_user_id)` for name uniqueness per user

### Repository Methods

New methods in `MeasurementTypeRepository`:
- `create_custom_measurement_type()`: Create new custom type
- `get_user_custom_types()`: Get user's custom types
- `get_available_types_for_user()`: Get all types available to user
- `check_custom_type_name_exists()`: Check for duplicate names
- `delete_custom_measurement_type()`: Soft delete custom type

### Bot Handlers

New FSM states and handlers:
- `creating_custom_type_name`: Collecting type name
- `creating_custom_type_unit`: Collecting unit
- `creating_custom_type_description`: Collecting description
- Handler chain for validation and creation flow

## UI Changes

### Add Types Menu
- Shows both system and custom types with different icons
- "✨ Create Custom Type" button always available
- Handles empty state with helpful message

### Visual Indicators
- 🔧 icon for custom measurement types
- 📏 icon for system measurement types
- Clear labeling in type lists

### Error Handling
- Validation messages for invalid input
- Duplicate name detection with helpful error messages
- Graceful error recovery with cancel options

### Multilingual Support
- Full translation support for English and Ukrainian
- All UI text, error messages, and prompts are localized
- User's language preference is automatically applied
- Fallback to English for unsupported languages

## Migration

The feature includes database migrations that:
- `9db39a53df76_add_custom_measurement_types_support.py`: Adds new columns with proper defaults for existing data, updates constraints to allow per-user uniqueness, maintains backward compatibility with existing measurement types
- `73194f9f38be_fix_telegram_id_bigint.py`: Updates `telegram_id` field from INTEGER to BIGINT to support large Telegram IDs (fixes issues with Telegram IDs > 2.1 billion)

## Example Usage

1. User creates "Blood Pressure" measurement type with unit "mmHg"
2. Type appears in their tracking list immediately
3. User can record measurements like "120 mmHg" with optional notes
4. Other users don't see this custom type in their lists
5. User can create additional custom types as needed

## Validation Rules

### Name Validation
- Minimum 2 characters
- Maximum 50 characters
- Must be unique within user's types (case-insensitive)
- Cannot duplicate system type names

### Unit Validation
- Minimum 1 character
- Maximum 10 characters
- No specific format restrictions (allows flexibility)

### Description Validation
- Optional field
- Maximum 200 characters when provided

## Technical Notes

### Large Telegram ID Support
The system supports large Telegram IDs (> 2.1 billion) by using BIGINT in the database. This was necessary because some Telegram bot IDs exceed the 32-bit INTEGER range, causing database errors during user creation and custom type operations.

## Future Enhancements

Potential future improvements:
- Edit existing custom types
- Share custom types between users
- Import/export custom type collections
- Categories or tags for custom types
- Custom type templates or suggestions
