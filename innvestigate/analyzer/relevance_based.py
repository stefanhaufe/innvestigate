# Begin: Python 2/3 compatibility header small
# Get Python 3 functionality:
from __future__ import\
    absolute_import, print_function, division, unicode_literals
from future.utils import raise_with_traceback, raise_from
# catch exception with: except Exception as e
from builtins import range, map, zip, filter
from io import open
import six
# End: Python 2/3 compatability header small


###############################################################################
###############################################################################
###############################################################################


import keras.backend as K
import keras.models
import keras


from . import base
from .. import layers as ilayers
from .. import utils
from ..utils import keras as kutils
from ..utils.keras import graph as kgraph


__all__ = [
    "BaselineLRPZ",
]


###############################################################################
###############################################################################
###############################################################################


class BaselineLRPZ(base.AnalyzerNetworkBase):

    properties = {
        "name": "BaselineLRP-Z",
        "show_as": "rgb",
    }

    def _create_analysis(self, model):
        gradients = utils.listify(ilayers.Gradient()(
            model.inputs+[model.outputs[0], ]))
        return [keras.layers.Multiply()([i, g])
                for i, g in zip(model.inputs, gradients)]


class BaseLRP(base.ReverseAnalyzerBase):

    properties = {
        "name": "Deconvnet",
        # todo: set right value
        "show_as": "rgb",
    }

    def __init__(self,
                 model, *args, rule=None,
                 first_layer_rule=None, first_layer_use_ZB=False, **kwargs):

        if rule is None:
            raise ValueError("Need LRP rule.")

        if first_layer_rule is None:
            if first_layer_use_ZB is True:
                # todo: add ZB layer here
                raise NotImplementedError()
            else:
                first_layer_rule = rule

        layer_cache = {}

        def reverse(Xs, Ys, Rs, reverse_state):
            layer = reverse_state["layer"]
            # activations do not affect relevances
            # also biases are not used
            # remove them on the backway

            # layers can be applied to several nodes.
            # but we need to revert it only once.
            if layer in layer_cache:
                layer = layer_cache[layer]
                Ys = kutils.easy_apply(layer_wo_acti, Xs)
            else:
                config = layer.get_config()
                config["name"] = "reversed_%s" % config["name"]
                if "activation" in config:
                    config["activation"] = None
                if "bias" in config:
                    config["use_bias"] = False
                new_layer = layer.__class__.from_config(config)
                new_Ys = kutils.easy_apply(layer, Xs)
                # filter bias weights
                # todo: this is not a secure way.
                new_layer.set_weights([W for W in layer.get_weights()
                                       if len(W.shape) > 1])
                layer_cache[layer] = new_layer

                layer = new_layer
                Ys = new_Ys    

            if kgraph.contains_kernel(layer):
                if any([tmp in model.inputs for tmp in Xs]):
                    current_rule = first_layer_rule
                else:
                    current_rule = rule
            else:
                current_rule = identity_rule
            return ilayers.LRP(len(Xs), layer, rule)(Xs+Ys+Rs)

        self.default_reverse = reverse
        return super(BaseLRP, self).__init__(*args, **kwargs)

    def _head_mapping(self, X):
        return ilayers.OnesLike()(X)
