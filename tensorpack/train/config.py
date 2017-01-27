# -*- coding: utf-8 -*-
# File: config.py
# Author: Yuxin Wu <ppwwyyxxc@gmail.com>

import tensorflow as tf

from ..callbacks import (
        Callbacks, SummaryMovingAverage,
        StatPrinter, ProgressBar,
        MaintainStepCounter)
from ..dataflow.base import DataFlow
from ..models import ModelDesc
from ..utils import logger
from ..tfutils import (JustCurrentSession,
                       get_default_sess_config, SessionInit)
from .input_data import InputData

__all__ = ['TrainConfig']


class TrainConfig(object):
    """
    Config for trainer.
    """

    def __init__(self, dataflow=None, data=None,
                 model=None, optimizer=None,
                 callbacks=None, extra_callbacks=None,
                 session_config=get_default_sess_config(),
                 session_init=None,
                 starting_epoch=1, steps_per_epoch=None, max_epoch=99999,
                 nr_tower=1, tower=None, predict_tower=[0],
                 **kwargs):
        """
        Args:
            dataflow (DataFlow): the dataflow to train.
            data (InputData): an `InputData` instance. Only one of ``dataflow``
                or ``data`` has to be present.
            model (ModelDesc): the model to train.
            optimizer (tf.train.Optimizer): the optimizer for trainig.
            callbacks (list): a list of :class:`Callback` to perform during training.
            extra_callbacks (list): the same as ``callbacks``. This argument
                is only used to provide the defaults. The defaults are
                ``[SummaryMovingAverage(), ProgressBar(), StatPrinter()]``. The list of
                callbacks that will be used in the end are ``callbacks + extra_callbacks``.
                Note that ``StatPrinter`` should be the last one to be able to print
                stats generated by other callbacks.
            session_config (tf.ConfigProto): the config used to instantiate the session.
            session_init (SessionInit): how to initialize variables of a session. Defaults to a new session.
            starting_epoch (int): The index of the first epoch.
            steps_per_epoch (int): the number of steps (defined by :meth:`Trainer.run_step`) to run in each epoch.
                Defaults to the input data size.
            max_epoch (int): maximum number of epoch to run training.
            nr_tower (int): number of training towers.
            tower (list of int): list of training towers in relative id.
            predict_tower (list of int): list of prediction towers in their relative gpu id. Use -1 for cpu.
        """

        # TODO type checker decorator
        def assert_type(v, tp):
            assert isinstance(v, tp), v.__class__

        # process data
        if 'dataset' in kwargs:
            dataflow = kwargs.pop('dataset')
            logger.warn("[Deprecated] TrainConfig.dataset has been deprecated. Use TrainConfig.dataflow instead.")
        if dataflow is not None:
            assert data is None, "dataflow and data cannot be both presented in TrainConfig!"
            self.dataflow = dataflow
            assert_type(self.dataflow, DataFlow)
            self.data = None
        else:
            self.data = data
            assert_type(self.data, InputData)
            self.dataflow = None

        self.optimizer = optimizer
        assert_type(self.optimizer, tf.train.Optimizer)

        if isinstance(callbacks, Callbacks):
            # keep quiet now because I haven't determined the final API yet.
            logger.warn("[Deprecated] API of TrainConfig(callbacks=) has changed!")
            logger.warn("[Deprecated] Please change the argument 'callbacks=' to a *list* of "
                        "callbacks without StatPrinter().")
            callbacks = callbacks.cbs[:-1]  # the last one is StatPrinter()
        assert_type(callbacks, list)
        if extra_callbacks is None:
            extra_callbacks = [
                    SummaryMovingAverage(),
                    ProgressBar(),
                    StatPrinter()]
        self.callbacks = [MaintainStepCounter()] + callbacks + extra_callbacks
        assert_type(self.callbacks, list)
        self.callbacks = Callbacks(self.callbacks)

        self.model = model
        assert_type(self.model, ModelDesc)

        self.session_config = session_config
        assert_type(self.session_config, tf.ConfigProto)
        if session_init is None:
            session_init = JustCurrentSession()
        self.session_init = session_init
        assert_type(self.session_init, SessionInit)

        if steps_per_epoch is None:
            steps_per_epoch = kwargs.pop('step_per_epoch', None)
            if steps_per_epoch is not None:
                # TODO deprecate @Mar.27
                logger.warn("[Deprecated] Use steps_per_epoch instead of step_per_epoch!")
        if steps_per_epoch is None:
            try:
                if dataflow is not None:
                    steps_per_epoch = self.dataflow.size()
                else:
                    steps_per_epoch = self.data.size()
            except NotImplementedError:
                logger.exception("You must set `steps_per_epoch` if dataset.size() is not implemented.")
        else:
            steps_per_epoch = int(steps_per_epoch)
        self.steps_per_epoch = steps_per_epoch

        self.starting_epoch = int(starting_epoch)
        self.max_epoch = int(max_epoch)
        assert self.steps_per_epoch >= 0 and self.max_epoch > 0

        self.nr_tower = nr_tower
        if tower is not None:
            assert self.nr_tower == 1, "Cannot set both nr_tower and tower in TrainConfig!"
            self.tower = tower

        self.predict_tower = predict_tower
        if isinstance(self.predict_tower, int):
            self.predict_tower = [self.predict_tower]

        assert len(kwargs) == 0, 'Unknown arguments: {}'.format(str(kwargs.keys()))

    def set_tower(self, nr_tower=None, tower=None):
        # this is a deprecated function
        logger.warn("config.set_tower is deprecated. set config.tower or config.nr_tower directly")
        assert nr_tower is None or tower is None, "Cannot set both nr_tower and tower!"
        if nr_tower:
            tower = list(range(nr_tower))
        else:
            if isinstance(tower, int):
                tower = list(range(tower))
        self.tower = tower
        assert isinstance(self.tower, list)

    @property
    def nr_tower(self):
        return len(self.tower)

    @nr_tower.setter
    def nr_tower(self, value):
        self.tower = list(range(value))
