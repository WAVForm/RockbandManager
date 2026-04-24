from pydantic import BaseModel, model_validator
from hashlib import blake2b
from json import dumps as json_dumps

class Song(BaseModel):
    id: str
    artist: str
    title: str
    wanted: bool
    downloaded: bool
    type: str
    diff_drums: int | None
    diff_guitar: int | None
    diff_bass: int | None
    diff_vocals: int | None
    download_url: str| None

    @model_validator(mode='before')
    @classmethod
    def generate_id_if_missing(cls, data: dict):
        if data.get("id") or "id" in list(data.keys()):
            return data

        data_str = json_dumps(data, sort_keys=True, default=str).encode()
        generated_id = blake2b(data_str, usedforsecurity=False).hexdigest()

        data["id"] = generated_id
        return data