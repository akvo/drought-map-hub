"""Dataset metadata lookup (DIH-7).

Label / unit / source / description belong to the dataset key, not to each
row — they live in ``country.json -> datasets`` (DIH-4). That pack is not in
this repo yet, so the lookup degrades to the key as its own label.

ponytail: read label/unit/source from country.json datasets once DIH-4 lands;
until then the API returns ``{"label": key, "unit": None}``.
"""

from typing import Dict, Optional


def dataset_meta(key: str) -> Dict[str, Optional[str]]:
    """Return display metadata for a dataset key.

    Degrades to the key as its own label while ``country.json`` is absent.
    """
    return {"label": key, "unit": None}
