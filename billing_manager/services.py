from .models import WalletCollection
from typing import Any, Dict

class WalletService:
    @staticmethod
    def update_wallet(user, temple, date, counter_cash, coin_counts, note_counts):
        WalletCollection.objects.update_or_create(
            user=user,
            temple=temple,
            date=date,
            defaults={
                "counter_cash": counter_cash,
                "coin_counts": coin_counts,
                "note_counts": note_counts,
            },
        )

    @staticmethod
    def get_wallet_by_date(user, temple, date):
        return WalletCollection.objects.filter(user=user, temple=temple, date=date).first()