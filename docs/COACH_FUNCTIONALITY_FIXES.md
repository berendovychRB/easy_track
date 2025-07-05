# Coach Functionality Fixes

## Problem Description

The Coach functionality was working inconsistently with the following issues:
1. Menu buttons appearing/disappearing randomly
2. "Become Coach" button showing even when user was already a coach
3. Coach menu buttons not responding to clicks
4. Inconsistent behavior between `/menu` command calls

## Root Cause Analysis

### 1. Callback Handler Mismatch
The main issue was a mismatch between callback data and registered handlers:
- **Main Menu Button**: `callback_data="coach_progress"`
- **Registered Handler**: `F.data == "view_all_athletes_progress"`

This caused the "Athletes Progress" button to be unresponsive, leaving users in an inconsistent state.

### 2. Missing User Language Variables
Several coach-related functions were missing `user_lang` variable declarations, causing runtime errors:
- `handle_waiting_for_athlete_username`
- `handle_toggle_coach_notification`
- `handle_coach_notification_history`
- `handle_coach_stats`
- `handle_coach_guide`

### 3. Type Safety Issues
- `create_custom_measurement_type` function expected a string for `description` parameter but could receive `None`

## Fixes Applied

### 1. Fixed Callback Handler Mismatch
**File**: `easy_track/src/easy_track/bot.py`

**Change**: Updated callback data in main menu and athlete list to match registered handlers:
```python
# Before
callback_data="coach_progress"

# After
callback_data="view_all_athletes_progress"
```

**Lines changed**: 188, 295

### 2. Added Missing User Language Variables
**File**: `easy_track/src/easy_track/bot.py`

Added `user_lang` variable declarations in:
- `handle_waiting_for_athlete_username` (moved `user_id` and `user_lang` before cancel check)
- `handle_toggle_coach_notification` (added after `user_id` declaration)
- `handle_coach_notification_history` (added after `user_id` declaration)
- `handle_coach_stats` (added after `user_id` declaration)
- `handle_coach_guide` (added `user_id` and `user_lang` declarations)

### 3. Fixed Type Safety Issue
**File**: `easy_track/src/easy_track/bot.py`

**Change**: Added null coalescing for description parameter:
```python
# Before
session, name, unit, user_id, description

# After
session, name, unit, user_id, description or ""
```

**Line changed**: 1992

## Expected Behavior After Fixes

### For Regular Users (Athletes)
- `/menu` command shows "Become Coach" button
- Button is consistently displayed on every menu call
- Clicking "Become Coach" properly updates user role and shows coach menu

### For Coaches
- `/menu` command shows coach-specific buttons:
  - "My Athletes" (callback: `coach_athletes`)
  - "Athletes Progress" (callback: `view_all_athletes_progress`)
  - "Coach Notifications" (callback: `coach_notifications`)
- All coach buttons are responsive and lead to their respective functions
- Menu display is consistent between calls

### For Users with Both Roles
- Same behavior as coaches (coach buttons are shown)
- Can still access athlete functionality through regular menu options

## Testing Recommendations

1. **Test Role Transitions**:
   - Create new user → should show "Become Coach"
   - Click "Become Coach" → should show coach buttons
   - Use `/menu` multiple times → should consistently show coach buttons

2. **Test Button Responsiveness**:
   - Click "My Athletes" → should show athlete management
   - Click "Athletes Progress" → should show progress overview
   - Click "Coach Notifications" → should show notification settings

3. **Test Database Consistency**:
   - Check that role changes are properly persisted
   - Verify role detection works across different sessions

## Files Modified

1. `easy_track/src/easy_track/bot.py` - Main fixes for callback handlers and missing variables
2. `easy_track/debug_scripts/test_coach_functionality.py` - Test script for verification (created)

## Additional Notes

- The fixes maintain backward compatibility
- No database migrations are required
- All existing coach functionality remains intact
- The fixes address both UI inconsistencies and runtime errors

## Testing Script

A comprehensive test script has been created at `easy_track/debug_scripts/test_coach_functionality.py` that can be used to verify:
- Role detection consistency
- Database session handling
- Menu logic simulation
- Callback handler registration

Run with: `python debug_scripts/test_coach_functionality.py`
