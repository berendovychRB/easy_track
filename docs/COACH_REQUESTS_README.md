# Coach Request System

## Overview

The Coach Request System is a new feature that adds a secure approval mechanism for coach-athlete relationships. Instead of coaches being able to directly add any athlete to their supervision, athletes now receive requests that they can accept or reject.

## How It Works

### 1. Coach Sends Request
- Coach uses the existing "Add Athlete" functionality
- Instead of directly adding the athlete, a request is created and sent to the athlete
- The athlete receives a notification with details about the coaching request

### 2. Athlete Receives Notification
- Athlete gets a Telegram message with coach information
- Message includes coach name, date, and optional message
- Athlete can accept or reject the request directly from the notification

### 3. Request Processing
- **Accept**: Creates a coach-athlete relationship, coach can now view athlete's measurements
- **Reject**: Request is marked as rejected, no relationship is created
- **Expire**: Requests automatically expire after 7 days if not responded to

## Database Schema

### New Table: `athlete_coach_requests`
```sql
CREATE TABLE athlete_coach_requests (
    id SERIAL PRIMARY KEY,
    coach_id INTEGER NOT NULL REFERENCES users(id),
    athlete_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    message TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    responded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT check_no_self_request CHECK (coach_id != athlete_id),
    CONSTRAINT uq_coach_athlete_request UNIQUE (coach_id, athlete_id, status)
);
```

### Request Status Values
- `pending`: Request is waiting for athlete response
- `accepted`: Request was accepted by athlete
- `rejected`: Request was rejected by athlete
- `expired`: Request expired without response

## User Interface Changes

### For Athletes
- New "📩 Coach Requests" button appears in main menu when pending requests exist
- Shows count of pending requests: "📩 Coach Requests (2)"
- Detailed view of each request with Accept/Reject buttons
- Notifications sent immediately when requests are received

### For Coaches
- "Add Athlete" flow now sends requests instead of direct addition
- Success message indicates request was sent, not that athlete was added
- Coaches receive notifications when requests are accepted or rejected
- Pending requests are tracked and can be viewed

## API Changes

### New Repository: `AthleteCoachRequestRepository`

#### Key Methods:
- `create_request(coach_id, athlete_id, message, expires_in_days=7)`: Create new request
- `accept_request(request_id)`: Accept a pending request
- `reject_request(request_id)`: Reject a pending request
- `get_athlete_pending_requests(athlete_id)`: Get requests for athlete
- `get_coach_pending_requests(coach_id)`: Get requests from coach
- `expire_old_requests()`: Mark expired requests

### Modified Coach Flow
The existing coach functionality remains the same from a user perspective, but the backend now:
1. Creates a request instead of direct relationship
2. Sends notification to athlete
3. Waits for athlete response
4. Creates relationship only after acceptance

## Security Improvements

### Privacy Protection
- Athletes must explicitly consent to coach supervision
- No coach can access athlete data without permission
- Athletes can see who is requesting to coach them

### Spam Prevention
- Only one pending request per coach-athlete pair
- Requests expire automatically after 7 days
- Clear rejection mechanism

## Translation Support

### New Translation Keys Added:
- `coach.requests.incoming_title`
- `coach.requests.incoming_request`
- `coach.requests.accept` / `coach.requests.reject`
- `coach.requests.accepted` / `coach.requests.rejected`
- `coach.requests.coach_accepted` / `coach.requests.coach_rejected`
- `coach.add_athlete.request_sent`
- `coach.add_athlete.request_pending`

### Supported Languages:
- English (en)
- Ukrainian (uk)

## Usage Examples

### Coach Sending Request
```python
# Coach tries to add athlete
await AthleteCoachRequestRepository.create_request(
    session,
    coach_id=1,
    athlete_id=2,
    message="I'd like to help you track your fitness progress!"
)
```

### Athlete Accepting Request
```python
# Athlete accepts the request
request = await AthleteCoachRequestRepository.accept_request(session, request_id)
# This automatically creates the coach-athlete relationship
```

### Checking Pending Requests
```python
# Get all pending requests for an athlete
requests = await AthleteCoachRequestRepository.get_athlete_pending_requests(
    session, athlete_id
)
```

## Testing

### Demo Script
Run the demo script to test the full flow:
```bash
python test_coach_requests_demo.py
```

### Unit Tests
```bash
pytest tests/test_coach_requests/
```

## Migration

### Database Migration
The system includes an Alembic migration that:
- Creates the `athlete_coach_requests` table
- Adds necessary constraints and indexes
- Is backward compatible with existing data

### Existing Relationships
- Current coach-athlete relationships are unaffected
- New requests only apply to future coaching relationships
- Existing coaches maintain access to their current athletes

## Backward Compatibility

The system maintains full backward compatibility:
- Existing coach-athlete relationships continue to work
- All existing coach functionality remains unchanged
- New request system only affects new coaching relationships

## Future Enhancements

### Potential Improvements:
1. **Batch Requests**: Allow coaches to send requests to multiple athletes
2. **Request Templates**: Pre-written messages for common coaching scenarios
3. **Request History**: View all past requests and their outcomes
4. **Reminder System**: Gentle reminders for pending requests
5. **Coach Profiles**: Allow coaches to add more information about their services

## Configuration

### Environment Variables
No new environment variables are required. The system uses existing database configuration.

### Default Settings
- Request expiration: 7 days
- Maximum pending requests per coach-athlete pair: 1
- Automatic cleanup of expired requests: Yes (via background job)

## Error Handling

The system includes comprehensive error handling for:
- Database connection issues
- Invalid user IDs
- Duplicate requests
- Expired requests
- Network issues during notification sending

## Logging

All request operations are logged with appropriate levels:
- INFO: Request creation, acceptance, rejection
- DEBUG: Detailed flow information
- ERROR: Failed operations with full stack traces

## Performance Considerations

- Database queries are optimized with proper indexes
- Batch operations for request expiration
- Efficient notification system
- Minimal impact on existing functionality

This system significantly improves the security and user experience of the coach-athlete relationship management while maintaining the simplicity of the existing interface.
