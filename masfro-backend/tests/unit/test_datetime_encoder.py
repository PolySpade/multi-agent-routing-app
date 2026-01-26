import json
from datetime import datetime
from decimal import Decimal

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def to_json_serializable(data):
    return json.dumps(data, cls=DateTimeEncoder)

# Test
test_data = {
    "type": "flood_update",
    "data": {"test": "value"},
    "timestamp": datetime.now(),
    "source": "flood_agent"
}

try:
    result = to_json_serializable(test_data)
    print("SUCCESS!")
    print(f"Result: {result}")
except Exception as e:
    print(f"ERROR: {e}")
