from pydantic import BaseModel, model_validator
from hashlib import blake2b
from json import dumps as json_dumps

class Song(BaseModel):
    id: str
    artist: str
    title: str
    wanted: bool = None
    downloaded: bool = None
    diff_band: int = -1
    diff_drums: int = -1
    diff_guitar: int = -1
    diff_bass: int = -1
    diff_vocals: int = -1
    diff_keys: int = -1
    diff_real_guitar: int = -1
    diff_real_bass: int = -1
    diff_real_keys: int = -1
    download_url: str = None
    content: str = None

    @model_validator(mode='before')
    @classmethod
    def generate_id_if_missing(cls, data: dict):
        if data.get("id") or "id" in list(data.keys()):
            return data

        data_str = json_dumps(data, sort_keys=True, default=str).encode()
        generated_id = blake2b(data_str, usedforsecurity=False).hexdigest()

        data["id"] = generated_id
        return data