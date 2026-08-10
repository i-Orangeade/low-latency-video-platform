from app.services.zlm_service import zlm_service


async def collect_stream_status(stream_id: str) -> dict:
    return await zlm_service.get_stream_status(stream_id)
