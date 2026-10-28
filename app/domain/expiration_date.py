from datetime import datetime, timedelta


def generate_expiration_date(created_at: datetime) -> datetime:
    expiration_date = created_at + timedelta(minutes=5)
    
    return expiration_date