from ninja import NinjaAPI

from core.api import router as core_router

api = NinjaAPI(title="TelemetryTaco API", version="1.1.0")
api.add_router("/", core_router)
