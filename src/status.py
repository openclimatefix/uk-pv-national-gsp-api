"""Get Status from database """
import logging

from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Status
from sqlalchemy.orm.session import Session

from database import get_latest_status_from_database, get_session

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/status", response_model=Status)
async def get_status(session: Session = Depends(get_session)) -> Status:
    """Get the status of the solar forecasts"""

    logger.debug("Get status")
    return get_latest_status_from_database(session=session)
