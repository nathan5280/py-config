"""
Configuration loader that creates specialized subclass objects.

All classes are derived from the BaseElementCfg or BaseContainerCfg class.
This classes have pre and post root validators that search their children
fields and specialize them as required.

The BaseElementCfg root validator that takes all the arguments and packs them into a generic
kwargs attribute.   When specialize is called by the post validator on this object it
creates an object of the type specified in class_path.

Example:
    BaseCfg
        BaseItem
            Item
                arg1: str
    config = {"class_name": "module.Item", "item": {"arg1": "arg1"}}
    obj = BaseItem(**config).specialize()

    obj will be of type Item

    Container
        item: BaseItem

    config = {"item": {"class_name": "module.Item", "item": {"arg1": "arg1"}}}
    container = Container(**config)

    container.item will be of type Item.

    See base_config_test for a working example.
"""
import importlib
import inspect
from typing import Dict, Type, Any, Optional, List

import pydantic
from pydantic import root_validator
from pydantic.main import BaseModel

from py_config import ConfigurationError


def class_from_name(class_path: str) -> Type:
    """Get a class object for the fully qualified class_path"""
    try:
        module_name, class_name = class_path.rsplit(".", 1)
    except ValueError:
        # Deal with the class being in the main global scope.
        module_name, class_name = "__main__", class_path
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls


class BaseContainerCfg(BaseModel):
    """
    Configuration object that knows how to iterate over fields of lists and dictionaries or BaseElementCfg
    objects to make sure that everything that should be specialized is.

    Derive classes in the configuration hierarchy that aren't already derived from BaseElementCfg from
    this class to make sure everything gets specialized.
    """

    @root_validator
    def specialize(cls, values):
        """
        Post validator that specializes any objects in values that are of derived from BaseElementCfg
        and set class_name, base_class and kwargs to None so they can be easily excluded from dumps
        of the configuration.
        """
        specialized_values = dict()
        for k, v in values.items():
            # Work through the list of values and make spacialized objects as required.
            if isinstance(v, List):
                # These are already specialized so all we need to do is clean them up.
                elements = list()
                for element in v:
                    element.class_path = element.base_class = element.kwargs = None
                    elements.append(element)
                specialized_values[k] = elements
                continue
            if isinstance(v, Dict):
                elements = dict()
                for kk, element in v.items():
                    if isinstance(element, BaseElementCfg):
                        # Only clean up elements that derived from BaseElementCfg.
                        # Other dicts come through here and if things are cleaned up now
                        # kwargs and class_path won't be around when they are needed.
                        element.class_path = element.base_class = element.kwargs = None
                        elements[kk] = element
                    else:
                        elements[kk] = element
                specialized_values[k] = elements
                continue
            if isinstance(v, BaseElementCfg):
                # Regular field that needs specialization.
                specialized_values[k] = v.specialize_field()
                continue
            # Just a plain old field.
            specialized_values[k] = v
        return specialized_values


class BaseElementCfg(BaseContainerCfg):
    """Base class for all configuration classes that can be specialized."""

    # Actually required, but optional so we can delete.
    class_path: Optional[str] = None
    # Marker for clean up.   It's existance is the trigger.
    base_class: Optional[bool] = None
    # Temporary storage of all the arguments for the specialized class when it is constructed
    # in the post validator.
    kwargs: Dict[str, Any] = None

    @root_validator(pre=True)
    def args_to_kwargs(cls, values):
        """Pack the arguments into kwargs so that the BaseConfig object can be instantiated."""
        if "class_path" not in values:
            raise ConfigurationError(
                "'class_path' is required for configurable object."
            )
        # Hack to know if this is the specialization object, and can delete fields
        if "base_class" not in values:
            values["kwargs"] = {
                k: v for k, v in values.items() if k not in ["class_path", "base_class"]
            }
        else:
            del values["base_class"]
            del values["class_path"]
        return values

    def specialize_field(self):
        """Convert the BaseCfg object to a specialized config object."""
        specialized_cls = class_from_name(self.class_path)
        if self.__class__ not in inspect.getmro(specialized_cls):
            raise ConfigurationError(
                f"Specialization '{specialized_cls}' must be a subclass of '{self.__class__}'."
            )
        # This will implicitly drop the kwargs field in the specialized class as we don't pass it.
        args = {
            "class_path": specialized_cls.__name__,
            **self.kwargs,
            "base_class": False,
        }
        obj = pydantic.parse_obj_as(specialized_cls, args)
        return obj
