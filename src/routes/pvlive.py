"""Get GSP boundary data from eso """
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import GSPYield
from sqlalchemy.orm.session import Session

from database import get_session, get_truth_values_for_a_specific_gsp_from_database

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/{gsp_id}/", response_model=List[GSPYield])
async def get_truths_for_a_specific_gsp(
    gsp_id: int, regime: Optional[str] = None, session: Session = Depends(get_session)
) -> List[GSPYield]:
    """Get PV live values for a specific GSP id, for yesterday and today

    See https://www.solar.sheffield.ac.uk/pvlive/ for more details.
    Regime can "in-day" or "day-after",
    as new values are calculated around midnight when more data is available.
    If regime is not specific, the latest gsp yield is loaded.

    The OCF Forecast is trying to predict the PV live 'day-after' value.
    """

    logger.info(f"Get PV Live estimates values for gsp id {gsp_id} and regime {regime}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )
