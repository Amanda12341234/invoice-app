from slowapi import Limiter
from slowapi.util import get_remote_address

# Centralized limiter instance (憲章原則六: 集中實作，參數透過 .env 設定)
limiter = Limiter(key_func=get_remote_address)
