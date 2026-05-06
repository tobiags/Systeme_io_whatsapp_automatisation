EVALUATION_DATASETS: dict[str, list[dict]] = {}


def register_dataset(name: str, samples: list[dict]) -> None:
    EVALUATION_DATASETS[name] = samples


def get_dataset(name: str) -> list[dict]:
    return EVALUATION_DATASETS.get(name, [])
