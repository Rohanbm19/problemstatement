from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(
    prefix="/forecast",
    tags=["Forecasting"]
)

ML_SERVICE_URL = "http://127.0.0.1:8001"


# ============================================================
# FORECAST BY ITEM ID
# ============================================================

@router.post("/{item_id}")
async def generate_forecast(
    item_id: str,
    horizon: int = 7
):

    # --------------------------------------------------------
    # Validate item ID
    # --------------------------------------------------------

    if not item_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Item ID is required"
        )

    # --------------------------------------------------------
    # Validate forecast horizon
    # --------------------------------------------------------

    if horizon <= 0:
        raise HTTPException(
            status_code=400,
            detail="Forecast horizon must be greater than 0"
        )

    if horizon > 30:
        raise HTTPException(
            status_code=400,
            detail="Forecast horizon cannot be greater than 30 days"
        )

    # --------------------------------------------------------
    # TEMPORARY HISTORICAL DEMAND
    #
    # Later this should come from your database.
    # --------------------------------------------------------

    history = [
        {
            "date": "2026-08-01",
            "demand": 12
        },
        {
            "date": "2026-08-02",
            "demand": 15
        },
        {
            "date": "2026-08-03",
            "demand": 11
        },
        {
            "date": "2026-08-04",
            "demand": 18
        },
        {
            "date": "2026-08-05",
            "demand": 14
        },
        {
            "date": "2026-08-06",
            "demand": 16
        },
        {
            "date": "2026-08-07",
            "demand": 13
        }
    ]

    # --------------------------------------------------------
    # Call ML SERVICE
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                f"{ML_SERVICE_URL}/forecast",
                json={
                    "item_id": item_id,
                    "horizon": horizon,
                    "history": history
                }
            )

    except httpx.ConnectError:

        raise HTTPException(
            status_code=503,
            detail=(
                "ML service is not running. "
                "Start the ML service on port 8001."
            )
        )

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="ML forecasting service timed out."
        )

    except httpx.RequestError as e:

        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to ML service: {str(e)}"
        )

    # --------------------------------------------------------
    # HANDLE ML SERVICE ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        try:
            error_data = response.json()

        except Exception:
            error_data = {}

        raise HTTPException(
            status_code=502,
            detail=error_data.get(
                "detail",
                "ML forecasting service failed"
            )
        )

    # --------------------------------------------------------
    # GET ML RESULT
    # --------------------------------------------------------

    result = response.json()

    # --------------------------------------------------------
    # RETURN FORECAST TO FRONTEND
    # --------------------------------------------------------

    return {
        "success": True,
        "item_id": result.get(
            "item_id",
            item_id
        ),
        "model": result.get(
            "model",
            "Unknown"
        ),
        "horizon": result.get(
            "horizon",
            horizon
        ),
        "forecast": result.get(
            "forecast",
            []
        )
    }