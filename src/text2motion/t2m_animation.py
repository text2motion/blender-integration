from typing import Dict, List

from pydantic import BaseModel, Field

T2M_SAVE_FILE_VERSION_1_0 = "1.0"


class T2MSaveFile(BaseModel):
    version: str
    content: str


class T2MTrack(BaseModel):
    rotation: Dict[str, List[float]] = Field(default_factory=dict)
    position: Dict[str, List[float]] = Field(default_factory=dict)


class T2MFrames(BaseModel):
    duration: float
    bones: Dict[str, T2MTrack]
    prompt: str = None
