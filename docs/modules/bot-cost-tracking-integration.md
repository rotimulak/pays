# Bot Cost Tracking Integration

Version: 1.0
Status: Implementation Ready
Created: 2026-01-13
API: track_cost event

## Overview

Specification for Telegram bot integration with Runner Framework cost tracking system.

## Event: `track_cost`

Runner Framework sends `track_cost` event to bot after track execution completes. Bot should handle this event to display cost information to users.

## Event Data Structure

### Python Callback Signature

```python
def bot_output_callback(output_type: str, **kwargs):
    """
    Handle bot output events from Runner Framework.

    Args:
        output_type: Event type identifier
        **kwargs: Event-specific parameters
    """
    if output_type == "track_cost":
        # Handle cost tracking event
        handle_track_cost(**kwargs)
```

### Event Parameters

When `output_type == "track_cost"`, the following parameters are provided:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `total_cost` | float | Total cost in currency units | 0.004 |
| `currency` | str | Currency code | "RUB" |
| `api_calls` | int | Number of API calls made | 3 |
| `free_requests` | int | Number of free API requests | 0 |
| `node_costs` | dict | Cost breakdown by node name | {"greeting": 0.001, "farewell": 0.001} |
| `prompt_tokens` | int | Total prompt tokens used | 76 |
| `completion_tokens` | int | Total completion tokens used | 90 |
| `total_tokens` | int | Total tokens used | 166 |

### Complete Example

```python
# Example event data received by bot
{
    "total_cost": 0.004,
    "currency": "RUB",
    "api_calls": 3,
    "free_requests": 0,
    "node_costs": {
        "greeting": 0.001,
        "farewell": 0.001,
        "cost_summary": 0.002
    },
    "prompt_tokens": 76,
    "completion_tokens": 90,
    "total_tokens": 166
}
```

## Bot Implementation Requirements

### 1. Event Handler Registration

Bot must register callback with Runner Framework:

```python
from runner import get_runner

# Get runner instance
runner = get_runner()

# Register bot callback
runner.set_bot_output_callback(handle_bot_output)

def handle_bot_output(output_type: str, **kwargs):
    """Process bot output events."""
    if output_type == "track_cost":
        send_cost_summary_to_user(kwargs)
    elif output_type == "text":
        send_text_to_user(kwargs)
    # ... other event types
```

### 2. Cost Summary Message

Bot should format and send cost information to user. Recommended format:

```python
def send_cost_summary_to_user(cost_data: dict):
    """
    Send cost tracking summary to Telegram user.

    Args:
        cost_data: Dictionary with cost tracking parameters
    """
    total_cost = cost_data.get("total_cost", 0.0)
    currency = cost_data.get("currency", "RUB")
    api_calls = cost_data.get("api_calls", 0)
    total_tokens = cost_data.get("total_tokens", 0)
    free_requests = cost_data.get("free_requests", 0)

    # Format message
    message = f"""
Обработка завершена

Стоимость: {total_cost:.3f} {currency}
Запросов к API: {api_calls}
Токенов использовано: {total_tokens}
"""

    # Add free requests info if any
    if free_requests > 0:
        message += f"Бесплатных запросов: {free_requests}\n"

    # Send to user
    send_telegram_message(user_id, message)
```

### 3. Detailed Cost Breakdown (Optional)

For advanced users, bot can provide detailed breakdown:

```python
def send_detailed_cost_breakdown(cost_data: dict):
    """Send detailed cost breakdown by node."""
    node_costs = cost_data.get("node_costs", {})

    message = "Детализация по узлам:\n\n"

    for node_name, cost in node_costs.items():
        message += f"{node_name}: {cost:.4f} RUB\n"

    message += f"\nВсего: {cost_data.get('total_cost', 0.0):.4f} RUB"

    send_telegram_message(user_id, message)
```

## Message Formatting Examples

### Basic Format (Recommended)

```
Обработка завершена ✅

💰 Стоимость: 0.004 RUB
📊 Запросов: 3
🔤 Токенов: 166
```

### Detailed Format

```
Обработка резюме завершена ✅

💰 Общая стоимость: 0.025 RUB

📊 Детализация:
  • extract_text: 0.002 RUB
  • analyze_cv: 0.015 RUB
  • generate_recommendations: 0.008 RUB

🔤 Использовано токенов: 850
  • Промпт: 450
  • Ответ: 400
```

### Compact Format

```
✅ Готово | 💰 0.004 RUB | 📊 3 запроса | 🔤 166 токенов
```

## Error Handling

### Missing Cost Data

If `_cost_tracking` is not in context (old tracks, errors), event won't be sent. Bot should handle absence of cost event gracefully.

```python
# Track completed without cost tracking
# Don't show cost message, only completion status
```

### Zero Cost

Free requests or local models may return 0.0 cost. Bot should handle this:

```python
if total_cost == 0.0 and free_requests > 0:
    message = "Обработка завершена (бесплатно)"
elif total_cost == 0.0:
    message = "Обработка завершена (локальная модель)"
else:
    message = f"Обработка завершена | Стоимость: {total_cost} RUB"
```

## Database Integration (Optional)

Bot may store cost data for analytics:

```sql
CREATE TABLE track_costs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    track_name VARCHAR(255),
    total_cost DECIMAL(10, 4),
    currency VARCHAR(10),
    api_calls INT,
    total_tokens INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert cost data
INSERT INTO track_costs (user_id, track_name, total_cost, currency, api_calls, total_tokens)
VALUES (%s, %s, %s, %s, %s, %s);

-- Get user total spending
SELECT SUM(total_cost) FROM track_costs WHERE user_id = %s;
```

## User Features

### Cost Tracking Dashboard

```python
@bot.command("/costs")
async def show_cost_dashboard(message):
    """Show user's cost statistics."""
    user_id = message.from_user.id

    # Get from database
    stats = get_user_cost_stats(user_id)

    message = f"""
📊 Ваша статистика

Всего потрачено: {stats['total_spent']} RUB
Треков выполнено: {stats['tracks_count']}
Средняя стоимость: {stats['avg_cost']} RUB

За последние 30 дней:
Потрачено: {stats['month_spent']} RUB
Треков: {stats['month_tracks']}
"""

    await bot.send_message(user_id, message)
```

### Cost Limits

```python
# Check cost limit before track execution
def check_cost_limit(user_id: int) -> bool:
    """Check if user hasn't exceeded daily cost limit."""
    today_cost = get_today_cost(user_id)
    user_limit = get_user_limit(user_id)  # e.g., 10.0 RUB per day

    if today_cost >= user_limit:
        send_message(user_id, "Превышен дневной лимит расходов")
        return False

    return True
```

## Testing

### Test Event Data

```python
# Test with sample data
test_event = {
    "total_cost": 0.123,
    "currency": "RUB",
    "api_calls": 5,
    "free_requests": 1,
    "node_costs": {
        "node1": 0.050,
        "node2": 0.073
    },
    "prompt_tokens": 250,
    "completion_tokens": 180,
    "total_tokens": 430
}

# Trigger callback
handle_bot_output("track_cost", **test_event)
```

### Test Scenarios

1. **Normal track execution**
   - Verify cost message sent
   - Verify correct formatting
   - Verify data saved to database

2. **Free requests**
   - total_cost = 0.0
   - free_requests > 0
   - Verify "бесплатно" message

3. **Local model**
   - total_cost = 0.0
   - free_requests = 0
   - Verify "локальная модель" message

4. **Large costs**
   - total_cost > 10.0
   - Verify formatting (e.g., 15.450 RUB)

5. **Many nodes**
   - 10+ nodes in node_costs
   - Verify detailed breakdown formatting

## Integration Checklist

- [ ] Implement `handle_bot_output` callback
- [ ] Register callback with Runner Framework
- [ ] Format cost summary message
- [ ] Test with sample data
- [ ] Add database storage (optional)
- [ ] Implement cost dashboard (optional)
- [ ] Add cost limits (optional)
- [ ] Handle edge cases (zero cost, free requests)
- [ ] Add error handling
- [ ] Deploy and test with real tracks

## Related Documentation

- [Cost Tracking Specification](../specifications/cost-tracking-spec.md) - Technical implementation
- [Cost Tracking Guide](../guides/cost-tracking.md) - User documentation
- [Bot Integration API](./bot-integration.md) - Full bot API reference
- [Track Execution](../guides/tracks/track-execution.md) - Track lifecycle

## Support

For questions or issues:
- Check [Cost Tracking FAQ](../guides/cost-tracking.md#faq)
- Review [Bot Integration Examples](./bot-integration.md#examples)
- File issue: [GitHub Issues](https://github.com/your-org/runner/issues)
