import sys
sys.path.insert(0, '/workspace/projects/workspace/tasks/T01-a-stock-leader-selection')
from database.models import get_session, TrackedResult

session = get_session()
try:
    count = session.query(TrackedResult).count()
    print(f"Tracked results count: {count}")
    
    # Also check ML training records count
    from database.models import MLTrainingRecord
    ml_count = session.query(MLTrainingRecord).count()
    print(f"ML training records count: {ml_count}")
finally:
    session.close()