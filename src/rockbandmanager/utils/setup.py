import logging
from pathlib import Path
from json import load

logger = logging.getLogger("Utilities")

def run(project_root_dir:Path, temp_dir:Path, owner:str) -> dict[str, str]:
    try:
        config= open(project_root_dir.joinpath("config.json"))
        if not config:
            raise Exception("Config file not found")
        config = load(config)
        if not config:
            raise Exception("Config file not in JSON serializable format")
        valid_owners = ["client","server"] 
        if owner not in valid_owners:
            raise ValueError(f"Variable 'owner' improperly set in call, expected '{valid_owners}' and got '{owner}'")
        config = config[owner]
        match owner:
            case "client":
                root_game_path:str = config["root_game_path"]
                if not isinstance(root_game_path, str):
                    raise ValueError(f"'root_game_path' is not a valid string: {root_game_path} ({type(root_game_path)})")
                dl_cache_path:str = config["dl_cache_path"]
                if not isinstance(dl_cache_path, str):
                    raise ValueError(f"'dl_cache_path' is not a valid string: {dl_cache_path} ({type(dl_cache_path)})")
                dl_cache_path = dl_cache_path.replace("%TEMP%", str(temp_dir))
                dl_cache_path = dl_cache_path.replace("%PROJECT%", str(project_root_dir))
                ul_cache_path:str = config["ul_cache_path"]
                if not isinstance(ul_cache_path,str):
                    raise ValueError(f"'ul_cache_path' is not a valid string: {ul_cache_path} ({type(ul_cache_path)})")
                ul_cache_path = ul_cache_path.replace("%TEMP%", str(temp_dir))
                ul_cache_path = ul_cache_path.replace("%PROJECT%", str(project_root_dir))

                return {
                    "root_game_path":root_game_path,
                    "dl_cache_path":dl_cache_path,
                    "ul_cache_path":ul_cache_path
                }
        raise Exception("Reached the end of setup unsuccessfully")
    except Exception as e:
        logger.error(f"Failed setting up: {e}")
        raise