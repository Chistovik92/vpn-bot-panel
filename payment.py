"""Совместимость: платежи переехали в app.payment."""
from app.payment import (  # noqa: F401
    PaymentProcessor,
    PaymentManager,
    YooMoneyProcessor,
    CryptoBotProcessor,
)
