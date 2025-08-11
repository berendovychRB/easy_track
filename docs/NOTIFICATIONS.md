# Notification System Documentation

## Overview

The EasySize bot includes a comprehensive notification system that allows users to set up periodic reminders for taking their body measurements. Users can configure notifications to be sent daily or on specific days of the week at their preferred times.

## Features

### Scheduling Options
- **Daily Notifications**: Reminders sent every day at a specified time
- **Weekly Notifications**: Reminders sent on specific days of the week (Monday through Sunday)
- **Flexible Time Selection**: 24-hour format time input (HH:MM)
- **Multiple Schedules**: Users can create multiple notification schedules

### Management Capabilities
- **Enable/Disable**: Toggle notifications on/off without deleting them
- **Delete Schedules**: Permanently remove notification schedules
- **View All Schedules**: See all configured notifications with their status
- **Duplicate Prevention**: Prevents creating identical notification schedules

### Multilingual Support
- **English and Ukrainian**: Full support for both languages
- **Localized Messages**: All notification messages are properly localized
- **Time Format**: Consistent time display across languages

## User Interface

### Main Menu Access
Users can access the notification system through the main bot menu:
1. Send `/menu` command
2. Select "🔔 Notifications" button

### Notification Menu
The notification menu provides these options:
- **➕ Add Notification**: Create a new notification schedule
- **⚙️ Manage Notifications**: View and manage existing schedules
- **🔙 Back to Menu**: Return to main bot menu

### Adding Notifications

#### Step 1: Select Frequency
Users choose how often they want to receive notifications:
- **📅 Daily**: Every day at the specified time
- **📅 Monday** through **📅 Sunday**: Specific day of the week

#### Step 2: Set Time
Users enter the desired notification time in 24-hour format:
- Format: `HH:MM` (e.g., `09:00`, `14:30`, `21:00`)
- Range: `00:00` to `23:59`
- Validation: Invalid time formats are rejected with helpful error messages

#### Step 3: Confirmation
The system creates the schedule and provides confirmation with details:
- Frequency (daily or specific day)
- Time
- Reminder about Telegram notification settings

### Managing Notifications

#### View Schedules
Users can see all their notification schedules with:
- **Frequency**: Daily or specific day name
- **Time**: 24-hour format
- **Status**: Active (✅) or Inactive (❌)

#### Schedule Actions
For each notification schedule, users can:
- **✅ Enable/❌ Disable**: Toggle the schedule on/off
- **🗑️ Delete**: Remove the schedule permanently (with confirmation)

## Technical Implementation

### Database Schema

#### NotificationSchedule Model
```sql
CREATE TABLE notification_schedules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    day_of_week INTEGER NULL,  -- 0=Monday, 1=Tuesday, ..., 6=Sunday, NULL=Daily
    notification_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, day_of_week, notification_time)
);
```

### Background Scheduler

#### NotificationScheduler Class
- **Async Operation**: Runs as a background asyncio task
- **Minute-based Checking**: Checks for pending notifications every minute
- **Time Matching**: Matches current time and day with scheduled notifications
- **Error Handling**: Graceful error handling with logging

#### Scheduler Lifecycle
1. **Initialization**: Created when bot starts
2. **Background Loop**: Continuously checks for notifications to send
3. **Cleanup**: Properly stopped when bot shuts down

### Repository Pattern

#### NotificationScheduleRepository
- `create_schedule()`: Create new notification schedule
- `get_user_schedules()`: Get all schedules for a user
- `get_active_user_schedules()`: Get only active schedules
- `update_schedule_status()`: Enable/disable schedules
- `delete_schedule()`: Remove schedules
- `get_schedules_for_time()`: Find schedules matching specific time/day

### Bot Handlers

#### State Management
- **FSM States**: Uses aiogram's Finite State Machine for time input
- **State Data**: Temporarily stores frequency selection during setup
- **State Cleanup**: Proper cleanup on completion or cancellation

#### Callback Handlers
- `handle_notifications()`: Main notification menu
- `handle_add_notification()`: Frequency selection
- `handle_notification_frequency()`: Process frequency choice
- `handle_notification_time()`: Process time input
- `handle_manage_notifications()`: Schedule management
- `handle_manage_notification_detail()`: Individual schedule actions
- `handle_toggle_notification()`: Enable/disable schedules
- `handle_delete_notification()`: Delete confirmation
- `handle_confirm_delete_notification()`: Execute deletion

## Message Templates

### Reminder Message
The notification reminder message includes:
- **Icon**: 🔔 for visual recognition
- **Title**: "Measurement Reminder!"
- **Main Message**: "It's time to take your measurements!"
- **Motivation**: Encouragement for consistent tracking
- **Call to Action**: Instruction to use /menu

### Example Messages

#### English
```
🔔 Measurement Reminder!

📊 It's time to take your measurements!

💡 Track your progress consistently to see better results.

📱 Use /menu to add your measurements now.
```

#### Ukrainian
```
🔔 Нагадування про вимірювання!

📊 Час проводити ваші вимірювання!

💡 Відстежуйте свій прогрес регулярно для кращих результатів.

📱 Використовуйте /menu щоб додати ваші вимірювання зараз.
```

## Configuration

### Environment Variables
No additional environment variables required. The notification system uses the same database connection as the main bot.

### Dependencies
- **aiogram**: For bot handlers and FSM
- **SQLAlchemy**: For database operations
- **asyncio**: For background scheduler
- **pytz**: For timezone handling (future enhancement)

## Usage Examples

### Common Notification Patterns

1. **Daily Morning Reminder**
   - Frequency: Daily
   - Time: 09:00
   - Use case: Morning measurement routine

2. **Weekly Check-in**
   - Frequency: Friday
   - Time: 18:00
   - Use case: End-of-week progress review

3. **Weekend Tracking**
   - Frequency: Sunday
   - Time: 11:00
   - Use case: Weekend measurement routine

4. **Evening Reminder**
   - Frequency: Daily
   - Time: 21:00
   - Use case: Evening measurement routine

## Error Handling

### Input Validation
- **Time Format**: Validates HH:MM format with appropriate range
- **Duplicate Prevention**: Prevents identical schedule creation
- **Database Errors**: Graceful handling of database constraints

### User Feedback
- **Clear Error Messages**: User-friendly error descriptions
- **Success Confirmations**: Confirmation messages for successful operations
- **Status Updates**: Real-time status updates for schedule changes

### Logging
- **Debug Information**: Detailed logging for troubleshooting
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Monitoring**: Scheduler operation logging

## Testing

### Test Coverage
- **Unit Tests**: Repository methods and validation logic
- **Integration Tests**: End-to-end notification flow
- **Scheduler Tests**: Background task functionality
- **Localization Tests**: Translation accuracy

### Test Script
Use `test_notifications.py` to verify system functionality:
```bash
python test_notifications.py
```

The test script validates:
- Database operations
- Schedule creation and management
- Scheduler logic
- Translation system
- Error handling

## Future Enhancements

### Planned Features
- **Timezone Support**: User-specific timezone handling
- **Custom Messages**: Personalized notification messages
- **Reminder Snooze**: Temporary postponement of notifications
- **Notification History**: Track sent notifications
- **Advanced Scheduling**: More complex scheduling patterns

### Technical Improvements
- **Performance Optimization**: More efficient scheduler implementation
- **Database Indexing**: Optimized queries for large user bases
- **Failover Handling**: Robust error recovery mechanisms
- **Metrics Collection**: Usage analytics and performance metrics

## Troubleshooting

### Common Issues

#### Notifications Not Received
1. Check if schedule is active (✅ status)
2. Verify correct time format and timezone
3. Ensure Telegram notifications are enabled
4. Check bot logs for delivery errors

#### Database Errors
1. Verify database connection
2. Check for migration issues
3. Validate unique constraints
4. Review error logs for details

#### Scheduler Issues
1. Check if scheduler started successfully
2. Verify background task is running
3. Review scheduler logs for errors
4. Restart bot if necessary

### Debug Commands
```bash
# Check database migration status
make db-upgrade

# View bot logs
make docker-logs

# Test notification system
python test_notifications.py

# Database shell access
make db-shell
```

## Security Considerations

### Data Protection
- **User Privacy**: Notification schedules are user-specific and private
- **Database Security**: Proper access controls and validation
- **Input Sanitization**: All user inputs are validated and sanitized

### Rate Limiting
- **Scheduler Frequency**: Limited to once-per-minute checks
- **Duplicate Prevention**: Prevents spam through unique constraints
- **Error Backoff**: Graceful handling of delivery failures

## Performance Considerations

### Efficiency
- **Optimized Queries**: Efficient database queries for schedule retrieval
- **Minimal Resource Usage**: Lightweight background scheduler
- **Batch Processing**: Efficient handling of multiple notifications

### Scalability
- **Database Indexing**: Proper indexes for performance
- **Connection Pooling**: Efficient database connection management
- **Async Operations**: Non-blocking notification delivery
