from typing import List, Dict

import pytest

from py_config import ConfigurationError
from py_config.base_config import BaseElementCfg, BaseContainerCfg


class BaseItem(BaseElementCfg):
    def run(self):
        pass


class Item1(BaseItem):
    arg1: str

    def run(self):
        return self.arg1


class Item2(Item1):
    arg2: str

    def run(self):
        return dict(arg1=self.arg1, arg2=self.arg2)


class ContainerCfg(BaseContainerCfg):
    item1: BaseItem
    item2: BaseItem


def test_base_config():
    args = {
        "item1": {"class_path": "base_config_test.Item1", "arg1": "arg1"},
        "item2": {
            "class_path": "base_config_test.Item2",
            "arg1": "arg1",
            "arg2": "arg2",
        },
    }
    obj = ContainerCfg(**args)
    assert "arg1" == obj.item1.run()
    print(obj.json(indent=2, exclude_none=True))
    assert {"arg1": "arg1", "arg2": "arg2"} == obj.item2.run()
    assert isinstance(obj.item1, Item1)
    assert isinstance(obj.item2, Item2)


def test_missing_class_path():
    args = {
        "item1": {"arg1": "arg1"},
        "item2": {
            "class_path": "base_config_test.Item2",
            "arg1": "arg1",
            "arg2": "arg2",
        },
    }
    with pytest.raises(ConfigurationError):
        ContainerCfg(**args)


class ItemX(BaseElementCfg):
    arg1: str


class ContainerX(BaseContainerCfg):
    item: BaseItem


def test_not_subclass():
    args = {"item": {"class_path": "base_config_test.ItemX", "arg1": "arg1"}}
    with pytest.raises(ConfigurationError):
        ContainerX(**args)


class ContainerList(BaseContainerCfg):
    items: List[Item1]


class ContainerDict(BaseContainerCfg):
    items: Dict[str, Item1]


def test_list():
    cfg = {
        "items": [
            {"class_path": "base_config_test.Item1", "arg1": "arg1.1"},
            {"class_path": "base_config_test.Item1", "arg1": "arg1.2"},
        ]
    }
    c = ContainerList(**cfg)
    print(c.json(indent=2))
    assert c.items[0].arg1 == "arg1.1"
    assert c.items[1].arg1 == "arg1.2"


def test_dict():
    print()
    cfg = {
        "items": {
            "a": {"class_path": "p_test.Item", "arg1": "arg1.1"},
            "b": {"class_path": "p_test.Item", "arg1": "arg1.2"},
        },
    }
    c = ContainerDict(**cfg)
    print(c)
    print(c.json(indent=2))
    assert c.items["a"].arg1 == "arg1.1"
    assert c.items["b"].arg1 == "arg1.2"
