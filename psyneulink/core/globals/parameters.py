"""

.. _Parameter_Attributes:

PsyNeuLink `parameters <Parameter>` are objects that represent the user-modifiable parameters of a `Component`. `Parameter`\\ s have
names, default values, and other attributes that define how they are used in models. `Parameter` \\s also maintain and provide
access to the data used in actual computations - `default values <Parameter_Defaults>`, `current values <Parameter_portfulness>`, `previous values <Parameter.history>`,
and `logged values <Log>`.


.. _Parameter_Defaults:

Defaults
========

Parameters have two types of defaults: *instance* defaults and *class* defaults. Class defaults belong to a PNL class, and suggest
valid types and shapes of Parameter values. Instance defaults belong to an instance of a PNL class, and are used to validate
compatibility between this instance and other PNL objects. Given a `TransferMechanism` *t*:

    - instance defaults are accessible by ``t.defaults``
    - class defaults are accessible by ``t.class_defaults`` or ``TransferMechanism.defaults``


.. note::
    ``t.defaults.noise`` is shorthand for ``t.parameters.noise.default_value``, and they both refer to the default noise value for *t*


.. _Parameter_portfulness:

Statefulness of Parameters
==========================

Parameters can have different values in different `execution contexts <Run_Scope_of_Execution>` in order to ensure correctness
of and allow access to `simulation <OptimizationControlMechanism_Execution>` calculations. As a result, to inspect and use the values
of a parameter, in general you need to know the execution context in which you are interested. Much of the time, this execution context
is likely to be a Composition:

::

        >>> import psyneulink as pnl
        >>> c = pnl.Composition()
        >>> d = pnl.Composition()
        >>> t = pnl.TransferMechanism()
        >>> c.add_node(t)
        >>> d.add_node(t)

        >>> c.run({t: 5})
        [[array([5.])]]
        >>> print(t.value)
        [[5.]]

        >>> d.run({t: 10})
        [[array([10.])]]
        >>> print(t.value)
        [[10.]]

        >>> print(t.parameters.value.get(c))
        [[5.]]
        >>> print(t.parameters.value.get(d))
        [[10.]]


The TransferMechanism in the above snippet has a different `value <Component.value>` for each Composition it is run in. This holds
true for all of its `stateful Parameters <Component.stateful_parameters>`, so they can behave differently in different execution contexts
and be modulated during `control <System_Execution_Control>`.

.. _Parameter_Dot_Notation:

.. note::
    The "dot notation" version - ``t.value`` - refers to the most recent execution context in which *t* was executed. In
    many cases, you can use this to get or set using the execution context you'd expect. However, in complex situations,
    if there is doubt, it is best to explicitly specify the execution context.

For Developers
--------------

Developers must keep in mind state when writing new components for PNL. Any parameters or values that may change during a `run <Run_Overview>`
must become stateful Parameters, or they are at risk of computational errors like those encountered in parallel programming.


Creating Parameters
^^^^^^^^^^^^^^^

To create new Parameters, reference this example of a new class *B*

::

    class B(A):
        class Parameters(A.Parameters):
            p = 1.0
            q = Parameter(1.0, modulable=True)


- create an inner class Parameters on the Component, inheriting from the parent Component's Parameters class
- an instance of *B*.Parameters will be assigned to the parameters attribute of the class *B* and all instances of *B*
- each attribute on *B*.Parameters becomes a parameter (instance of the Parameter class)
    - as with *p*, specifying only a value uses default values for the attributes of the Parameter
    - as with *q*, specifying an explicit instance of the Parameter class allows you to modify the `Parameter attributes <Parameter_Attributes_Table>`
- if you want assignments to parameter *p* to be validated, add a method _validate_p(value), that returns None if value is a valid assignment, or an error string if value is not a valid assignment
- if you want all values set to *p* to be parsed beforehand, add a method _parse_p(value) that returns the parsed value
    - for example, convert to a numpy array or float

        ::

            def _parse_p(value):
                return np.asarray(value)

- setters and getters (used for more advanced behavior than parsing) should both return the final value to return (getter) or set (setter)

    For example, `costs <ControlMechanism.costs>` of `ControlMechanism <ControlMechanism>` has a special
    getter method, which computes the cost on-the-fly:

        ::

            def _modulatory_mechanism_costs_getter(owning_component=None, context=None):
                try:
                    return [c.compute_costs(c.parameters.variable._get(context), context=context) for c in owning_component.control_signals]
                except TypeError:
                    return None

    and `matrix <RecurrentTransferMechanism.matrix>` of `RecurrentTransferMechanism` has a special setter method,
    which updates its `auto <RecurrentTransferMechanism.auto>` and `hetero <RecurrentTransferMechanism.hetero>` parameter values accordingly

        ::

            def _recurrent_transfer_mechanism_matrix_setter(value, owning_component=None, context=None):
                try:
                    value = get_matrix(value, owning_component.size[0], owning_component.size[0])
                except AttributeError:
                    pass

                if value is not None:
                    temp_matrix = value.copy()
                    owning_component.parameters.auto._set(np.diag(temp_matrix).copy(), context)
                    np.fill_diagonal(temp_matrix, 0)
                    owning_component.parameters.hetero._set(temp_matrix, context)

                return value

.. note::
    The specification of Parameters is intended to mirror the PNL class hierarchy. So, it is only necessary for each new class to declare
    Parameters that are new, or whose specification has changed from their parent's. Parameters not present in a given class can be inherited
    from parents, but will be overridden if necessary, without affecting the parents.


Using Parameters
^^^^^^^^^^^^

Methods that are called during runtime in general must take *context* as an argument and must pass this *context* along to other
PNL methods. The most likely place this will come up would be for the *function* method on a PNL `Function` class, or *_execute* method on other
`Components`. Any getting and setting of stateful parameter values must use this *context*, and using standard attributes to store data
must be avoided at risk of causing computation errors. You may use standard attributes only when their values will never change during a
`Run <TimeScale.RUN>`.

You should avoid using `dot notation <Parameter_Dot_Notation>` in internal code, as it is ambiguous and can potentially break statefulness.

.. _Parameter_Attributes_Table:

`Parameter` **attributes**:

.. table:: **`Parameter` attributes**

+------------------+---------------+--------------------------------------------+-----------------------------------------+
|  Attribute Name  | Default value |                Description                 |                Dev notes                |
|                  |               |                                            |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|  default_value   |     None      |the default value of the Parameter          |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|       name       |     None      |the name of the Parameter                   |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|     stateful     |     True      |whether the parameter has different values  |                                         |
|                  |               |based on execution context                  |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|    modulable     |     False     |if True, the parameter can be modulated     |Currently this does not determine what   |
|                  |               |(if it belongs to a Mechanism or Projection |gets a ParameterPort, but in the future |
|                  |               | it is assigned a `ParameterPort`)         |it should                                |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|    read_only     |     False     |whether the user should be able to set the  |Can be manually set, but will trigger a  |
|                  |               |value or not (e.g. variable and value are   |warning unless override=True             |
|                  |               |just for informational purposes).           |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|     aliases      |     None      |other names by which the parameter goes     |specify as a list of strings             |
|                  |               |(e.g. allocation is the same as variable for|                                         |
|                  |               |ControlSignal).                             |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|       user       |     True      |whether the parameter is something the user |                                         |
|                  |               |will care about (e.g. NOT context)          |                                         |
|                  |               |                                            |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|      values      |     None      |stores the parameter's values under         |                                         |
|                  |               |different execution contexts                |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|      getter      |     None      |hook that allows overriding the retrieval of|kwargs self, owning_component, and       |
|                  |               |values based on a supplied method           |context will be passed in if your        |
|                  |               |(e.g. _output_port_variable_getter)        |method uses them. self - the Parameter   |
|                  |               |                                            |calling the setter; owning_component -   |
|                  |               |                                            |the Component to which the Parameter     |
|                  |               |                                            |belongs; context - the context           |
|                  |               |                                            |the setter is called with; should return |
|                  |               |                                            |the value                                |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|      setter      |     None      |hook that allows overriding the setting of  |should take a positional argument; kwargs|
|                  |               |values based on a supplied method (e.g.     |self, owning_component, and context      |
|                  |               |_recurrent_transfer_mechanism_matrix_setter)|will be passed in if your method uses    |
|                  |               |                                            |them. self - the Parameter calling the   |
|                  |               |                                            |setter; owning_component - the Component |
|                  |               |                                            |to which the Parameter belongs;          |
|                  |               |                                            |context - the context the                |
|                  |               |                                            |setter is called with; should return the |
|                  |               |                                            |value to be set                          |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|     loggable     |     True      |whether the parameter can be logged         |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|       log        |     None      |stores the log of the parameter if          |                                         |
|                  |               |applicable                                  |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|  log_condition   |     `OFF`     |the `LogCondition` for which the parameter  |                                         |
|                  |               |should be logged                            |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|     history      |     None      |stores the history of the parameter         |                                         |
|                  |               |(previous values)                           |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
|history_max_length|       1       |the maximum length of the stored history    |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+
| fallback_default |     False     |if False, the Parameter will return None if |                                         |
|                  |               |a requested value is not present for a given|                                         |
|                  |               |execution context; if True, the Parameter's |                                         |
|                  |               |default_value will be returned instead      |                                         |
+------------------+---------------+--------------------------------------------+-----------------------------------------+





Class Reference
===============

"""

import collections
import copy
import logging
import types
import warnings
import weakref

from psyneulink.core.globals.keywords import MULTIPLICATIVE
from psyneulink.core.globals.context import Context, ContextError, ContextFlags, _get_time, handle_external_context
from psyneulink.core.globals.context import time as time_object
from psyneulink.core.globals.log import LogCondition, LogEntry, LogError
from psyneulink.core.globals.utilities import call_with_pruned_args, copy_iterable_with_shared, get_alias_property_getter, get_alias_property_setter, get_deepcopy_with_shared, unproxy_weakproxy

__all__ = [
    'Defaults', 'get_validator_by_function', 'Parameter', 'ParameterAlias', 'ParameterError',
    'ParametersBase', 'parse_context',
]

logger = logging.getLogger(__name__)


class ParameterError(Exception):
    pass


def get_validator_by_function(function):
    """
        Arguments
        ---------
            function
                a function that takes exactly one positional argument and returns `True` if that argument
                is a valid assignment, or `False` if that argument is not a valid assignment

        :return: A validation method for use with Parameters classes that rejects any assignment for which **function** returns False
        :rtype: types.FunctionType
    """
    def validator(self, value):
        if function(value):
            return None
        else:
            return '{0} returned False'.format(function.__name__)

    return validator


def parse_context(context):
    """
        Arguments
        ---------
            context
                An execution context (context, Composition)

        :return: the context associated with **context**
    """
    try:
        return context.default_execution_id
    except AttributeError:
        return context


def copy_parameter_value(value, shared_types=None, memo=None):
    """
        Returns a copy of **value** used as the value or spec of a
        Parameter, with exceptions.

        For example, we assume that if we have a Component in an
        iterable, it is meant to be a pointer rather than something
        used in computation requiring it to be a "real" instance
        (like `Component.function`)

        e.g. in spec attribute or Parameter `Mechanism.input_ports_spec`
    """
    from psyneulink.core.components.component import Component, ComponentsMeta

    if shared_types is None:
        shared_types = (Component, ComponentsMeta, types.MethodType)
    else:
        shared_types = tuple(shared_types)

    try:
        return copy_iterable_with_shared(
            value,
            shared_types=shared_types,
            memo=memo
        )
    except TypeError:
        # this will attempt to copy the current object if it
        # is referenced in a parameter, such as
        # ComparatorMechanism, which does this for input_ports
        if not isinstance(value, shared_types):
            return copy.deepcopy(value, memo)
        else:
            return value


class ParametersTemplate:
    _deepcopy_shared_keys = ['_parent', '_params', '_owner', '_children']
    _values_default_excluded_attrs = {'user': False}

    def __init__(self, owner, parent=None):
        # using weakref to allow garbage collection of unused objects of this type
        self._owner = weakref.proxy(owner)
        self._parent = parent
        if isinstance(self._parent, ParametersTemplate):
            # using weakref to allow garbage collection of unused children
            self._parent._children.add(weakref.ref(self))

        # create list of params currently existing
        self._params = set()
        try:
            parent_keys = list(self._parent._params)
        except AttributeError:
            parent_keys = dir(type(self))
        source_keys = dir(self) + parent_keys
        for k in source_keys:
            if self._is_parameter(k):
                self._params.add(k)

        self._children = set()

    def __repr__(self):
        return '{0} :\n{1}'.format(super().__repr__(), str(self))

    def __str__(self):
        return self.show()

    __deepcopy__ = get_deepcopy_with_shared(_deepcopy_shared_keys)

    def __iter__(self):
        return iter([getattr(self, k) for k in self.values(show_all=True).keys()])

    def _is_parameter(self, param_name):
        if param_name[0] == '_':
            return False
        else:
            try:
                return not isinstance(getattr(self, param_name), (types.MethodType, types.BuiltinMethodType))
            except AttributeError:
                return True

    def _register_parameter(self, param_name):
        self._params.add(param_name)
        to_remove = set()

        for child in self._children:
            if child() is None:
                to_remove.add(child)
            else:
                child()._register_parameter(param_name)

        for rem in to_remove:
            self._children.remove(rem)

    def values(self, show_all=False):
        """
            Arguments
            ---------
                show_all : False
                    if `True`, includes non-`user<Parameter.user` parameters

            :return: a dictionary with {parameter name: parameter value} key-value pairs for each Par
        """
        result = {}
        for k in self._params:
            val = getattr(self, k)

            if show_all:
                result[k] = val
            else:
                # exclude any values that have an attribute/value pair listed in ParametersTemplate._values_default_excluded_attrs
                for excluded_key, excluded_val in self._values_default_excluded_attrs.items():
                    try:
                        if getattr(val, excluded_key) == excluded_val:
                            break
                    except AttributeError:
                        pass
                else:
                    result[k] = val

        return result

    def show(self, show_all=False):
        vals = self.values(show_all=show_all)
        return '(\n\t{0}\n)'.format('\n\t'.join(sorted(['{0} = {1},'.format(k, vals[k]) for k in vals])))

    def names(self, show_all=False):
        return sorted([p for p in self.values(show_all)])


class Defaults(ParametersTemplate):
    """
        A class to simplify display and management of default values associated with the `Parameter`\\ s
        in a :class:`Parameters` class.

        With an instance of the Defaults class, *defaults*, *defaults.<param_name>* may be used to
        get or set the default value of the associated :class:`Parameters` object

        Attributes
        ----------
            owner
                the :class:`Parameters` object associated with this object
    """
    def __init__(self, owner, **kwargs):
        super().__init__(owner)

        try:
            vals = sorted(self.values(show_all=True).items())
            for k, v in vals:
                try:
                    setattr(self, k, kwargs[k])
                except KeyError:
                    pass
        except AttributeError:
            # this may occur if this ends up being assigned to a "base" parameters object
            # in this case it's not necessary to support kwargs assignment
            pass

    def __getattr__(self, attr):
        return getattr(self._owner.parameters, attr).default_value

    def __setattr__(self, attr, value):
        if (attr[:1] != '_'):
            param = getattr(self._owner.parameters, attr)
            param._inherited = False
            param.default_value = value
        else:
            super().__setattr__(attr, value)

    def values(self, show_all=False):
        """
            Arguments
            ---------
                show_all : False
                    if `True`, includes non-`user<Parameter.user>` parameters

            :return: a dictionary with {parameter name: parameter value} key-value pairs corresponding to `owner`
        """
        return {k: v.default_value for (k, v) in self._owner.parameters.values(show_all=show_all).items()}


class Parameter(types.SimpleNamespace):
    """
    COMMENT:
        KDM 11/30/18: using nonstandard formatting below to ensure developer notes is below type in html
    COMMENT

    Attributes
    ----------
        default_value
            the default value of the Parameter.

            :default: None

        name
            the name of the Parameter.

            :default: None

        stateful
            whether the parameter has different values based on execution context.

            :default: True

        modulable
            if True, the parameter can be modulated; if the Parameter belongs to a `Mechanism <Mechanism>` or
            `Projection <Projection>`, it is assigned a `ParameterPort`.

            :default: False

            :Developer Notes: Currently this does not determine what gets a ParameterPort, but in the future it should

        modulation_combination_function
            specifies the function used in Port._get_combined_mod_val() to combine values for the parameter if
            it receives more than one ModulatoryProjections;  must be either the keyword *MULTIPLICATIVE*,
            *PRODUCT*, *ADDITIVE*, *SUM*, or a function that accepts an n dimensional array and retursn an n-1
            dimensional array.  If it is None, the an attempt is made to determine it from the an alias for the
            Parameter's name (i.e., if that is MULTIPLICATIVE_PARAM or ADDITIVE_PARAM);  otherwise the default
            behavior is determined by Port._get_combined_mod_val().

            :default: None

        read_only
            whether the user should be able to set the value or not
            (e.g. variable and value are just for informational purposes).

            :default: False

            :Developer Notes: Can be manually set, but will trigger a warning unless override=True

        pnl_internal
            whether the parameter is an idiosyncrasy of PsyNeuLink or it is more intrinsic to the conceptual operation
            of the Component on which it resides

            :default: False

        aliases
            other names by which the parameter goes (e.g. allocation is the same as variable for ControlSignal).

            :type: list
            :default: None

            :Developer Notes: specify as a list of strings

        user
            whether the parameter is something the user will care about (e.g. NOT context).

            :default: True

        values
            stores the parameter's values under different execution contexts.

            :type: dict{execution_id: value}
            :default: None

        getter
            hook that allows overriding the retrieval of values based on a supplied method
            (e.g. _output_port_variable_getter).

            :type: types.FunctionType
            :default: None

            :Developer Notes: kwargs self, owning_component, and context will be passed in if your method uses them. self - the Parameter calling the setter; owning_component - the Component to which the Parameter belongs; context - the context the setter is called with; should return the value

        setter
            hook that allows overriding the setting of values based on a supplied method
            (e.g.  _recurrent_transfer_mechanism_matrix_setter).

            :type: types.FunctionType
            :default: None

            :Developer Notes: should take a positional argument; kwargs self, owning_component, and context will be passed in if your method uses them. self - the Parameter calling the setter; owning_component - the Component to which the Parameter belongs; context - the context the setter is called with; should return the value to be set

        loggable
            whether the parameter can be logged.

            :default: True

        log
            stores the log of the parameter if applicable.

            :type: dict{execution_id: deque([LogEntry])}
            :default: None

        log_condition
            the LogCondition for which the parameter should be logged.

            :type: `LogCondition`
            :default: `OFF <LogCondition.OFF>`

        history
            stores the history of the parameter (previous values). Also see `get_previous`.

            :type: dict{execution_id: deque([LogEntry])}
            :default: None

        history_max_length
            the maximum length of the stored history.

            :default: 1

        history_min_length
            the minimum length of the stored history. generally this does not need to be
            overridden, but is used to indicate if parameter history is necessary to computation.

            :default: 0

        fallback_default
            if False, the Parameter will return None if a requested value is not present for a given execution context;
            if True, the Parameter's default_value will be returned instead.

            :default: False

        retain_old_simulation_data
            if False, the Parameter signals to other PNL objects that any values generated during simulations may be
            deleted after they are no longer needed for computation; if True, the values should be saved for later
            inspection.

            :default: False

        constructor_argument
            if not None, this indicates the argument in the owning Component's
            constructor that this Parameter corresponds to. Typically this is
            used in Parameters that save specification types, as in
            `input_ports_spec <Mechanism.input_ports_spec>` and
            `output_ports_spec <Mechanism.output_ports_spec>`

            :default: None

        valid_types
            if not None, this contains a tuple of `type`\\ s that are acceptable
            for values of this Parameter

            :default: None

    """
    # The values of these attributes will never be inherited from parent Parameters
    # KDM 7/12/18: consider inheriting ONLY default_value?
    _uninherited_attrs = {'name', 'values', 'history', 'log'}

    # for user convenience - these attributes will be hidden from the repr
    # display if the function is True based on the value of the attribute
    _hidden_if_unset_attrs = {
        'aliases', 'getter', 'setter', 'constructor_argument', 'spec',
        'modulation_combination_function', 'valid_types'
    }
    _hidden_if_false_attrs = {'read_only', 'modulable', 'fallback_default', 'retain_old_simulation_data'}
    _hidden_when = {
        **{k: lambda self, val: val is None for k in _hidden_if_unset_attrs},
        **{k: lambda self, val: val is False for k in _hidden_if_false_attrs},
        **{k: lambda self, val: self.loggable is False or self.log_condition is LogCondition.OFF for k in ['log', 'log_condition']},
        **{k: lambda self, val: self.modulable is False for k in ['modulation_combination_function']},
    }

    # for user convenience - these "properties" (see note below in _set_history_max_length)
    # will be included as "param attrs" - the attributes of a Parameter that may be of interest to/settable by users
    # To add an additional property-like param attribute, add its name here, and a _set_<param_name> method
    # (see _set_history_max_length)
    _additional_param_attr_properties = {
        'default_value',
        'history_max_length',
        'log_condition',
        'spec',
    }

    def __init__(
        self,
        default_value=None,
        name=None,
        stateful=True,
        modulable=False,
        structural=False,
        modulation_combination_function=None,
        read_only=False,
        function_arg=True,
        pnl_internal=False,
        aliases=None,
        user=True,
        values=None,
        getter=None,
        setter=None,
        loggable=True,
        log=None,
        log_condition=LogCondition.OFF,
        history=None,
        history_max_length=1,
        history_min_length=0,
        fallback_default=False,
        retain_old_simulation_data=False,
        constructor_argument=None,
        spec=None,
        parse_spec=False,
        valid_types=None,
        _owner=None,
        _inherited=False,
        _user_specified=False,
    ):
        if isinstance(aliases, str):
            aliases = [aliases]

        if values is None:
            values = {}

        if history is None:
            history = {}

        if loggable and log is None:
            log = {}

        if valid_types is not None:
            if isinstance(valid_types, list):
                valid_types = tuple(valid_types)
            else:
                valid_types = (valid_types, )

        super().__init__(
            default_value=default_value,
            name=name,
            stateful=stateful,
            modulable=modulable,
            structural=structural,
            modulation_combination_function=modulation_combination_function,
            read_only=read_only,
            function_arg=function_arg,
            pnl_internal=pnl_internal,
            aliases=aliases,
            user=user,
            values=values,
            getter=getter,
            setter=setter,
            loggable=loggable,
            log=log,
            log_condition=log_condition,
            history=history,
            history_max_length=history_max_length,
            history_min_length=history_min_length,
            fallback_default=fallback_default,
            retain_old_simulation_data=retain_old_simulation_data,
            constructor_argument=constructor_argument,
            spec=spec,
            parse_spec=parse_spec,
            valid_types=valid_types,
            _inherited=_inherited,
            _user_specified=_user_specified,
        )

        if _owner is None:
            self._owner = None
        else:
            try:
                self._owner = weakref.proxy(_owner)
            except TypeError:
                self._owner = _owner

        self._param_attrs = [k for k in self.__dict__ if k[0] != '_'] \
            + [k for k in self.__class__.__dict__ if k in self._additional_param_attr_properties]
        self._inherited_attrs_cache = {}
        self.__inherited = False
        self._inherited = _inherited

    def __repr__(self):
        return '{0} :\n{1}'.format(super(types.SimpleNamespace, self).__repr__(), str(self))

    def __str__(self):
        # modified from types.SimpleNamespace to exclude _-prefixed attrs
        try:
            items = (
                "{}={!r}".format(k, getattr(self, k)) for k in self._param_attrs
                if k not in self._hidden_when or not self._hidden_when[k](self, getattr(self, k))
            )

            return "{}(\n\t\t{}\n\t)".format(type(self).__name__, "\n\t\t".join(items))
        except AttributeError:
            return super().__str__()

    def __lt__(self, other):
        return self.name < other.name

    def __deepcopy__(self, memo):
        result = Parameter(
            **{
                k: copy_parameter_value(getattr(self, k), memo=memo)
                for k in self._param_attrs
            },
            _owner=self._owner,
            _inherited=self._inherited,
            _user_specified=self._user_specified,
        )
        memo[id(self)] = result

        return result

    def __getattr__(self, attr):
        # runs when the object doesn't have an attr attribute itself
        # attempt to get from its parent, which is also a Parameter
        try:
            return getattr(self._parent, attr)
        except AttributeError:
            raise AttributeError("Parameter '%s' has no attribute '%s'" % (self.name, attr)) from None

    def __setattr__(self, attr, value):
        if attr in self._additional_param_attr_properties:
            try:
                getattr(self, '_set_{0}'.format(attr))(value)
            except AttributeError:
                super().__setattr__(attr, value)
        else:
            super().__setattr__(attr, value)

    def reset(self):
        """
            Resets *default_value* to the value specified in its `Parameters` class declaration, or
            inherits from parent `Parameters` classes if it is not explicitly specified.
        """
        try:
            self.default_value = self._owner.__class__.__dict__[self.name].default_value
        except (AttributeError, KeyError):
            try:
                self.default_value = self._owner.__class__.__dict__[self.name]
            except KeyError:
                if self._parent is not None:
                    self._inherited = True
                else:
                    raise ParameterError(
                        'Parameter {0} cannot be reset, as it does not have a default specification '
                        'or a parent. This may occur if it was added dynamically rather than in an'
                        'explict Parameters inner class on a Component'
                    )

    def _register_alias(self, name):
        if self.aliases is None:
            self.aliases = [name]
        elif name not in self.aliases:
            self.aliases.append(name)

    @property
    def _inherited(self):
        return self.__inherited

    @_inherited.setter
    def _inherited(self, value):
        if value is not self._inherited:
            if value:
                for attr in self._param_attrs:
                    if attr not in self._uninherited_attrs:
                        self._inherited_attrs_cache[attr] = getattr(self, attr)
                        delattr(self, attr)
            else:
                for attr in self._param_attrs:
                    if (
                        attr not in self._uninherited_attrs
                        and getattr(self, attr) is getattr(self._parent, attr)
                    ):
                        setattr(self, attr, self._inherited_attrs_cache[attr])

            self.__inherited = value

    def _cache_inherited_attrs(self):
        for attr in self._param_attrs:
            if attr not in self._uninherited_attrs:
                self._inherited_attrs_cache[attr] = getattr(self, attr)

    @property
    def _parent(self):
        try:
            return getattr(self._owner._parent, self.name)
        except AttributeError:
            return None

    def _validate(self, value):
        return self._owner._validate(self.name, value)

    def _parse(self, value):
        return self._owner._parse(self.name, value)

    @property
    def _default_getter_kwargs(self):
        # self._owner: the Parameters object it belongs to
        # self._owner._owner: the Component the Parameters object belongs to
        # self._owner._owner.owner: that Component's owner if it exists
        kwargs = {
            'self': self,
            'owning_component': self._owner._owner
        }
        try:
            kwargs['owner'] = self._owner._owner.owner
        except AttributeError:
            pass

        return kwargs

    @property
    def _default_setter_kwargs(self):
        return self._default_getter_kwargs

    @handle_external_context()
    def get(self, context=None, **kwargs):
        """
            Gets the value of this `Parameter` in the context of **context**
            If no context is specified, attributes on the associated `Component` will be used

            Arguments
            ---------

                context : Context, execution_id, Composition
                    the context for which the value is stored; if a Composition, uses **context**.default_execution_id
                kwargs
                    any additional arguments to be passed to this `Parameter`'s `getter` if it exists
        """
        return self._get(context, **kwargs)

    def _get(self, context=None, **kwargs):
        if not self.stateful:
            execution_id = None
        else:
            try:
                execution_id = context.execution_id
            except AttributeError as e:
                raise ParameterError(
                    '_get must pass in a Context object as the context '
                    'argument. To get parameter values using only an '
                    'execution id, use get.'
                ) from e

        if self.getter is not None:
            kwargs = {**self._default_getter_kwargs, **kwargs}
            value = call_with_pruned_args(self.getter, context=context, **kwargs)
            if self.stateful:
                self._set_value(value, execution_id=execution_id, context=context)
            return value
        else:
            try:
                return self.values[execution_id]
            except KeyError:
                logger.info('Parameter \'{0}\' has no value for execution_id {1}'.format(self.name, execution_id))
                if self.fallback_default:
                    return self.default_value
                else:
                    return None

    @handle_external_context()
    def get_previous(self, context=None, index=1):
        """
            Gets the value set before the current value of this `Parameter` in the context of **context**

            Arguments
            ---------

                context : Context, execution_id, Composition
                    the context for which the value is stored; if a Composition, uses **context**.default_execution_id

                index : int : 1
                    how far back to look into the history. A value of 1 means the first previous value

        """
        try:
            return self.history[context.execution_id][-1 * index]
        except (KeyError, IndexError):
            return None

    @handle_external_context()
    def get_delta(self, context=None):
        """
            Gets the difference between the current value and previous value of `Parameter` in the context of **context**

            Arguments
            ---------

                context : Context, execution_id, Composition
                    the context for which the value is stored; if a Composition, uses **context**.default_execution_id
        """
        try:
            return self.get(context) - self.get_previous(context)
        except TypeError as e:
            raise TypeError(
                "Parameter '{0}' value mismatch between current ({1}) and previous ({2}) values".format(
                    self.name,
                    self.get(context),
                    self.get_previous(context)
                )
            ) from e

    @handle_external_context()
    def set(self, value, context=None, override=False, skip_history=False, skip_log=False, **kwargs):
        """
            Sets the value of this `Parameter` in the context of **context**
            If no context is specified, attributes on the associated `Component` will be used

            Arguments
            ---------

                context : Context, execution_id, Composition
                    the context for which the value is stored; if a Composition, uses **context**.default_execution_id
                override : False
                    if True, ignores a warning when attempting to set a *read-only* Parameter
                skip_history : False
                    if True, does not modify the Parameter's *history*
                skip_log : False
                    if True, does not modify the Parameter's *log*
                kwargs
                    any additional arguments to be passed to this `Parameter`'s `setter` if it exists
        """
        if not override and self.read_only:
            raise ParameterError('Parameter \'{0}\' is read-only. Set at your own risk. Pass override=True to force set.'.format(self.name))

        self._set(self._parse(value), context, skip_history, skip_log, **kwargs)

    def _set(self, value, context=None, skip_history=False, skip_log=False, **kwargs):
        if not self.stateful:
            execution_id = None
        else:
            try:
                execution_id = context.execution_id
            except AttributeError as e:
                raise ParameterError(
                    '_set must pass in a Context object as the context '
                    'argument. To set parameter values using only an '
                    'execution id, use set.'
                ) from e

        if self.setter is not None:
            kwargs = {
                **self._default_setter_kwargs,
                **kwargs
            }
            value = call_with_pruned_args(self.setter, value, context=context, **kwargs)

        self._set_value(value, execution_id=execution_id, context=context, skip_history=skip_history, skip_log=skip_log)

    def _set_value(self, value, execution_id=None, context=None, skip_history=False, skip_log=False):
        # store history
        if not skip_history:
            if execution_id in self.values:
                try:
                    self.history[execution_id].append(self.values[execution_id])
                except KeyError:
                    self.history[execution_id] = collections.deque([self.values[execution_id]], maxlen=self.history_max_length)

        # log value
        if not skip_log and self.loggable:
            self._log_value(value, context)

        # set value
        self.values[execution_id] = value

    @handle_external_context()
    def delete(self, context=None):
        try:
            del self.values[context.execution_id]
        except KeyError:
            pass

        try:
            del self.history[context.execution_id]
        except KeyError:
            pass

        self.clear_log(context.execution_id)

    def _log_value(self, value, context=None):
        # manual logging
        if context is not None and context.source is ContextFlags.COMMAND_LINE:
            try:
                time = _get_time(self._owner._owner, context)
            except (AttributeError, ContextError):
                time = time_object(None, None, None, None)

            # this branch only ran previously when context was ContextFlags.COMMAND_LINE
            context_str = ContextFlags._get_context_string(ContextFlags.COMMAND_LINE)
            log_condition_satisfied = True

        # standard logging
        else:
            if self.log_condition is None or self.log_condition is LogCondition.OFF:
                return

            if context is None:
                context = self._owner._owner.most_recent_context

            time = _get_time(self._owner._owner, context)
            context_str = ContextFlags._get_context_string(context.flags)
            log_condition_satisfied = self.log_condition & context.flags

        if (
            not log_condition_satisfied
            and self.log_condition & LogCondition.INITIALIZATION
            and self._owner._owner.initialization_status is ContextFlags.INITIALIZING
        ):
            log_condition_satisfied = True

        if log_condition_satisfied:
            if not self.stateful:
                execution_id = None
            else:
                execution_id = context.execution_id

            if execution_id not in self.log:
                self.log[execution_id] = collections.deque([])

            self.log[execution_id].append(
                LogEntry(time, context_str, value)
            )

    def clear_log(self, contexts=NotImplemented):
        """
            Clears the log of this Parameter for every context in **contexts**
        """
        if contexts is NotImplemented:
            self.log.clear()
            return

        if not isinstance(contexts, list):
            contexts = [contexts]

        contexts = [parse_context(c) for c in contexts]
        execution_ids = [
            c.execution_id if hasattr(c, 'execution_id') else c
            for c in contexts
        ]

        try:
            for eid in execution_ids:
                self.log.pop(eid, None)
        except TypeError:
            self.log.pop(execution_ids, None)

    def _initialize_from_context(self, context=None, base_context=Context(execution_id=None), override=True):
        from psyneulink.core.components.component import Component

        try:
            try:
                cur_val = self.values[context.execution_id]
            except KeyError:
                cur_val = None

            if cur_val is None or override:
                try:
                    new_val = self.values[base_context.execution_id]
                except KeyError:
                    return

                try:
                    new_history = self.history[base_context.execution_id]
                except KeyError:
                    new_history = NotImplemented

                shared_types = (Component, types.MethodType)

                if isinstance(new_val, (dict, list)):
                    new_val = copy_iterable_with_shared(new_val, shared_types)
                elif not isinstance(new_val, shared_types):
                    new_val = copy.deepcopy(new_val)

                self.values[context.execution_id] = new_val

                if new_history is None:
                    raise ParameterError('history should always be a collections.deque if it exists')
                elif new_history is not NotImplemented:
                    # shallow copy is OK because history should not change
                    self.history[context.execution_id] = copy.copy(new_history)

        except ParameterError as e:
            raise ParameterError('Error when attempting to initialize from {0}: {1}'.format(base_context.execution_id, e))

    # KDM 7/30/18: the below is weird like this in order to use this like a property, but also include it
    # in the interface for user simplicity: that is, inheritable (by this Parameter's children or from its parent),
    # visible in a Parameter's repr, and easily settable by the user
    def _set_default_value(self, value):
        self._validate(value)

        super().__setattr__('default_value', self._parse(value))

    def _set_history_max_length(self, value):
        if value < self.history_min_length:
            raise ParameterError(f'Parameter {self._owner._owner}.{self.name} requires history of length at least {self.history_min_length}.')
        super().__setattr__('history_max_length', value)
        for execution_id in self.history:
            self.history[execution_id] = collections.deque(self.history[execution_id], maxlen=value)

    def _set_log_condition(self, value):
        if not isinstance(value, LogCondition):
            if value is True:
                value = LogCondition.ALL_ASSIGNMENTS
            else:
                try:
                    value = LogCondition.from_string(value)
                except (AttributeError, LogError):
                    try:
                        value = LogCondition(value)
                    except ValueError:
                        # if this fails, value can't be interpreted as a LogCondition
                        raise

        super().__setattr__('log_condition', value)

    def _set_spec(self, value):
        if self.parse_spec:
            value = self._parse(value)
        super().__setattr__('spec', value)


class _ParameterAliasMeta(type):
    # these will not be taken from the source
    _unshared_attrs = ['name', 'aliases']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k in Parameter().__dict__:
            if k not in self._unshared_attrs:
                setattr(
                    self,
                    k,
                    property(
                        fget=get_alias_property_getter(k, attr='source'),
                        fset=get_alias_property_setter(k, attr='source')
                    )
                )


# TODO: may not completely work with history/history_max_length
class ParameterAlias(types.SimpleNamespace, metaclass=_ParameterAliasMeta):
    """
        A counterpart to `Parameter` that represents a pseudo-Parameter alias that
        refers to another `Parameter`, but has a different name
    """
    def __init__(self, source=None, name=None):
        super().__init__(name=name)
        try:
            self.source = weakref.proxy(source)
        except TypeError:
            # source is already a weakref proxy, coming from another ParameterAlias
            self.source = source

        try:
            source._register_alias(name)
        except AttributeError:
            pass

    def __lt__(self, other):
        return self.name < other.name

    def __getattr__(self, attr):
        return getattr(self.source, attr)


# KDM 6/29/18: consider assuming that ALL parameters are stateful
#   and that anything that you would want to set as not stateful
#   are actually just "settings" or "preferences", like former prefs,
#   PROJECTION_TYPE, PROJECTION_SENDER
# classifications:
#   stateful = False : Preference
#   read_only = True : "something", computationally relevant but just for information
#   user = False     : not something the user cares about but uses same infrastructure
#
# only current candidate for separation seems to be on stateful
# for now, leave everything together. separate later if necessary
class ParametersBase(ParametersTemplate):
    """
        Base class for inner `Parameters` classes on Components (see `Component.Parameters` for example)
    """
    _parsing_method_prefix = '_parse_'
    _validation_method_prefix = '_validate_'

    def __init__(self, owner, parent=None):
        super().__init__(owner=owner, parent=parent)

        aliases_to_create = set()
        for param_name, param_value in self.values(show_all=True).items():
            if (
                param_name in self.__class__.__dict__
                and (
                    param_name not in self._parent.__class__.__dict__
                    or self._parent.__class__.__dict__[param_name] is not self.__class__.__dict__[param_name]
                )
            ):
                # KDM 6/25/18: NOTE: this may need special handling if you're creating a ParameterAlias directly
                # in a class's Parameters class
                setattr(self, param_name, param_value)
            else:
                if isinstance(getattr(self._parent, param_name), ParameterAlias):
                    # store aliases we need to create here and then create them later, because
                    # the param that the alias is going to refer to may not have been created yet
                    # (the alias then may refer to the parent Parameter instead of the Parameter associated with this
                    # Parameters class)
                    aliases_to_create.add(param_name)
                else:
                    new_param = Parameter(name=param_name, _owner=self, _inherited=True)
                    # store the parent's values as the default "uninherited" attr values
                    new_param._cache_inherited_attrs()
                    setattr(self, param_name, new_param)

        for alias_name in aliases_to_create:
            setattr(self, alias_name, ParameterAlias(name=alias_name, source=getattr(self, alias_name).source))

        for param, value in self.values(show_all=True).items():
            self._validate(param, value.default_value)

    def __getattr__(self, attr):
        try:
            return getattr(self._parent, attr)
        except AttributeError:
            try:
                param_owner = self._owner
                if isinstance(param_owner, type):
                    owner_string = f' of {param_owner}'
                else:
                    owner_string = f' of {param_owner.name}'
                if hasattr(param_owner, 'owner') and param_owner.owner:
                    owner_string += f' for {param_owner.owner.name}'
                    if hasattr(param_owner.owner, 'owner') and param_owner.owner.owner:
                        owner_string += f' of {param_owner.owner.owner.name}'
            except AttributeError:
                owner_string = ''

            raise AttributeError(f"No attribute '{attr}' exists in the parameter hierarchy{owner_string}.") from None

    def __setattr__(self, attr, value):
        # handles parsing: Parameter or ParameterAlias housekeeping if assigned, or creation of a Parameter
        # if just a value is assigned
        if not self._is_parameter(attr):
            super().__setattr__(attr, value)
        else:
            if isinstance(value, Parameter):
                if value.name is None:
                    value.name = attr

                value._owner = self
                super().__setattr__(attr, value)

                if value.aliases is not None:
                    for alias in value.aliases:
                        # the alias doesn't exist, or it's an alias on the
                        # parent
                        if (
                            not hasattr(self, alias)
                            or not hasattr(getattr(self, alias), '_owner')
                            or unproxy_weakproxy(getattr(self, alias)._owner) is not self
                        ):
                            super().__setattr__(alias, ParameterAlias(source=getattr(self, attr), name=alias))
                            self._register_parameter(alias)

            elif isinstance(value, ParameterAlias):
                if value.name is None:
                    value.name = attr
                if isinstance(value.source, str):
                    try:
                        value.source = getattr(self, value.source)
                        value.source._register_alias(attr)
                    except AttributeError:
                        # developer error
                        raise ParameterError(
                            '{0}: Attempted to create an alias named {1} to {2} but attr {2} does not exist'.format(
                                self, attr, value.source
                            )
                        )
                super().__setattr__(attr, value)
            else:
                # assign value to default_value
                if hasattr(self, attr) and isinstance(getattr(self, attr), Parameter):
                    current_param = getattr(self, attr)
                    # construct a copy because the original may be used as a base for reset()
                    new_param = copy.deepcopy(current_param)
                    # set _inherited before default_value because it will
                    # restore from cache
                    new_param._inherited = False
                    new_param.default_value = value
                else:
                    new_param = Parameter(name=attr, default_value=value, _owner=self)

                super().__setattr__(attr, new_param)

            self._validate(attr, getattr(self, attr).default_value)
            self._register_parameter(attr)

    def _get_prefixed_method(
        self,
        parse=False,
        validate=False,
        modulable=False,
        parameter_name=None
    ):
        """
            Returns the parsing or validation method for the Parameter named
            **parameter_name** or for any modulable Parameter
        """

        if (
            parse and validate
            or (not parse and not validate)
        ):
            raise ValueError('Exactly one of parse or validate must be True')

        if parse:
            prefix = self._parsing_method_prefix
        elif validate:
            prefix = self._validation_method_prefix

        if (
            modulable and parameter_name is not None
            or not modulable and parameter_name is None
        ):
            raise ValueError('modulable must be True or parameter_name must be specified, but not both.')

        if modulable:
            suffix = 'modulable'
        elif parameter_name is not None:
            suffix = parameter_name

        return getattr(self, '{0}{1}'.format(prefix, suffix))

    def _validate(self, attr, value):
        err_msg = None

        valid_types = getattr(self, attr).valid_types
        if valid_types is not None:
            if not isinstance(value, valid_types):
                err_msg = '{0} is an invalid type. Valid types are: {1}'.format(
                    type(value),
                    valid_types
                )

        try:
            validation_method = self._get_prefixed_method(validate=True, parameter_name=attr)
            err_msg = validation_method(value)
            if err_msg is False:
                err_msg = '{0} returned False'.format(validation_method)

        except AttributeError:
            # parameter does not have a validation method
            pass

        if err_msg is not None:
            raise ParameterError(
                "Value ({0}) assigned to parameter '{1}' of {2}.parameters is not valid: {3}".format(
                    value,
                    attr,
                    self._owner,
                    err_msg
                )
            )

    def _parse(self, attr, value):
        try:
            return self._get_prefixed_method(parse=True, parameter_name=attr)(value)
        except AttributeError:
            return value
