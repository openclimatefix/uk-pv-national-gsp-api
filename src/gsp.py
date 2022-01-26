"""Get GSP boundary data from eso """
import geopandas as gpd
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_shape_from_eso


def get_gsp_boundaries_from_eso() -> gpd.GeoDataFrame:
    """Get GSP boundaries"""

    return get_gsp_shape_from_eso()
