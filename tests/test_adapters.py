from __future__ import annotations

import json

import pytest

from py_reports.adapters import JsonAdapter, ListDictAdapter
from py_reports.exceptions import InputAdapterError


def test_list_dict_adapter_normalizes_dict_records() -> None:
    adapter = ListDictAdapter()
    data = [{"id": "1"}, {"id": "2"}]

    result = list(adapter.adapt(data))

    assert result == data


def test_list_dict_adapter_rejects_non_mapping_items() -> None:
    adapter = ListDictAdapter()

    with pytest.raises(InputAdapterError):
        list(adapter.adapt([{"id": "1"}, 2]))


def test_json_adapter_accepts_json_text_array() -> None:
    adapter = JsonAdapter()
    payload = json.dumps([{"id": "1"}, {"id": "2"}])

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_json_adapter_extracts_items_from_object_payload() -> None:
    adapter = JsonAdapter()
    payload = {"items": [{"id": "1"}, {"id": "2"}]}

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_json_adapter_wraps_single_object_payload() -> None:
    adapter = JsonAdapter()
    payload = {"id": "1"}

    result = list(adapter.adapt(payload))

    assert result == [{"id": "1"}]


def test_json_adapter_rejects_invalid_payload_type() -> None:
    adapter = JsonAdapter()

    with pytest.raises(InputAdapterError):
        list(adapter.adapt(123))
