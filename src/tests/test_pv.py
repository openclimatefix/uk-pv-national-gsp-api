# """ Test for main app """
# from datetime import datetime
#
# from fastapi.testclient import TestClient
# from freezegun import freeze_time
# from nowcasting_datamodel.models import PVSystem, PVSystemSQL, PVYield
#
# from main import app
#
# client = TestClient(app)
#
#
# @freeze_time("2022-01-02")
# def test_read_latest_pv(db_session, api_client):
#     """Check main pv route works"""
#
#     pv_yield_1 = PVYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
#     pv_yield_1_sql = pv_yield_1.to_orm()
#
#     pv_yield_2 = PVYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=2)
#     pv_yield_2_sql = pv_yield_2.to_orm()
#
#     # this one wont get returned as its longer than 1 hour ago
#     pv_yield_3 = PVYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=3)
#     pv_yield_3_sql = pv_yield_3.to_orm()
#
#     pv_system_sql_1: PVSystemSQL = PVSystem(
#         pv_system_id=1, provider="pvoutput.org", status_interval_minutes=5
#     ).to_orm()
#     pv_system_sql_2: PVSystemSQL = PVSystem(
#         pv_system_id=2, provider="pvoutput.org", status_interval_minutes=5
#     ).to_orm()
#     pv_system_sql_3: PVSystemSQL = PVSystem(
#         pv_system_id=3, provider="pvoutput.org", status_interval_minutes=5
#     ).to_orm()
#
#     # add pv system to yield object
#     pv_yield_1_sql.pv_system = pv_system_sql_1
#     pv_yield_2_sql.pv_system = pv_system_sql_1
#     pv_yield_3_sql.pv_system = pv_system_sql_3
#
#     # add to database
#     db_session.add(pv_yield_1_sql)
#     db_session.add(pv_yield_2_sql)
#     db_session.add(pv_system_sql_1)
#     db_session.add(pv_system_sql_2)
#
#     db_session.commit()
#
#     response = api_client.get("/v0/GB/solar/pv/pv_latest")
#     assert response.status_code == 200
#
#     r_json = response.json()
#     pv_yields = [PVYield(**i) for i in r_json]
#     assert len(pv_yields) == 2
