from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator


class WeatherAlignmentRequest(BaseModel):
    storm_event: str
    event_time: str
    zip_code_severity_index: str
    drone_weather_alignment: Literal["Aligned", "Not Aligned", "Partial"]


class DroneAnalysisRequest(BaseModel):
    roof_condition: str
    weather_event_match: Literal["Yes", "No"]
    drone_match_percent: int
    geo_match: Literal["Full", "Partial", "None"]
    damage_inflation_index: Literal["Low", "Medium", "High"]
    tamper_indicator: Literal["None", "Possible", "Likely"]
    drone_image_urls: Optional[List[str]] = None
    drone_capture_time: Optional[str] = None

    @field_validator("drone_match_percent")
    @classmethod
    def validate_match_percent(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("drone_match_percent must be between 0 and 100")
        return v
