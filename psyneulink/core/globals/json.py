"""

Contents
--------

  * `JSON_Overview`
  * `JSON_Examples`
  * `JSON_Model_Specification`

.. _JSON_Overview:


Overview
--------

The developers of PsyNeuLink are collaborating with the scientific community, as part of the `OpenNeuro effort
<https://openneuro.org>`_, to create a standard, JSON-based format for the description and exchange of computational
models of brain and psychological function across different simulation environments. As part of this effort,
PsyNeuLink includes the ability to export models into, and import valid Python scripts from this JSON format.

Each Component can be exported to the JSON format using its `json_summary` method, which uses its `_dict_summary
<Component._dict_summary>`. Passing this output into `generate_script_from_json` produced a valid Python script
replicating the original PsyNeuLink model.

.. _JSON_Examples:

Model Examples
--------------

Below is an example of a script that implements a PsyNeuLink model of the Stroop model with conflict monitoring,
and its output in JSON. Running `generate_script_from_json` on the output will produce another PsyNeuLink script
that will give the same results when run on the same input as the original.

:download:`Download stroop_conflict_monitoring.py
<../../tests/json/stroop_conflict_monitoring.py>`

:download:`Download stroop_conflict_monitoring.json
<../../docs/source/_static/stroop_conflict_monitoring.json>`

.. _JSON_Model_Specification:

JSON Model Specification
------------------------

.. note::
    The JSON format is in early development, and is subject to change.


The outermost level of a JSON model is a dictionary with entry ``graphs``, a list of Composition objects.

Each Component's JSON object contains multiple entries. Those that are common to all are:

* ``name`` : a label for the Component

* ``parameters`` (non-`Function`\\ s) / ``args`` (`Function`\\ s) : a dictionary where each entry is either a
  `Parameter` name and value, or a subdictionary of modeling-environment specific parameters. For PsyNeuLink,
  this is indicated by `PNL`:


.. code-block:: javascript

    "args": {
        "PNL": {
            "execution_count": 0,
            "has_initializers": false,
            "variable": [
                0.01
            ]
        },
        "bounds": null,
        "intercept": 0.0,
        "slope": 1.0
    }

Note that the value of a parameter may be a long-form dictionary when it corresponds to a `ParameterPort`.
In this case, it will indicate the ParameterPort in a `source<>` field:

.. code-block:: javascript

    "intercept": {
        "source": "A.input_ports.intercept",
        "type": "float",
        "value": 2.0
    }

* ``type`` : a dictionary with entries based on modeling environment to describe the type of the object.
  The `generic` entry is populated if the object has a universal name (such as a linear function).
  Modeling-environment-specific entries are populated when relevant.

.. code-block:: javascript

    "type": {
        "PNL": "Composition",
        "generic": "graph"
    }


**Mechanisms**, **Projections**, and **Ports** each have:

* ``functions`` : a list of primary `Function` JSON objects. In \
PsyNeuLink, only one primary function is allowed.

.. code-block:: javascript

    "functions": [
        {
            "args": {
                "intercept": {
                    "source": "A.input_ports.intercept",
                    "type": "float",
                    "value": 2.0
                },
                "slope": {
                    "source": "A.input_ports.slope",
                    "type": "float",
                    "value": 5.0
                }
            },
            "name": "Linear Function-1",
            "type": {
                "generic": "Linear"
            }
        }
    ]

**Mechanisms** have:

* ``input_ports`` : a list of InputPort and ParameterPort JSON objects

* ``output_ports`` : a list of OutputPort JSON objects

**Projections** have:

* ``sender`` : the name of the Component it projects from

* ``sender_port`` : the name of the port on the ``sender`` to which it \
connects

* ``receiver`` : the name of the Component it projects to

* ``receiver_port`` : the name of the port on the ``receiver`` to \
which it connects

**Ports** have:

* ``dtype`` : the type of accepted input/output for the Port. This \
corresponds to `numpy.dtype <https://docs.scipy.org/doc/numpy/ \
reference/generated/numpy.dtype.html>`_

* ``shape`` : the shape of the accepted input/output. This corresponds \
to numpy ndarray shapes. (`numpy.zeros(<shape>)` would produce an \
array with the correct shape)

**Compositions** have:

* ``nodes`` : a dictionary of Mechanisms or Compositions keyed on \
their names that are part of the Composition

* ``edges`` : a dictionary of Projections keyed on their names that \
connect nodes of the Composition

* ``controller`` : the name of the Mechanism in the Composition's \
nodes that serves as the Composition's \
`controller <Composition_Controller>`, if it exists


"""

import abc
import base64
import binascii
import dill
import enum
import json
import numpy
import pickle
import psyneulink
import re
import types

from psyneulink.core.globals.keywords import MODEL_SPEC_ID_COMPOSITION, MODEL_SPEC_ID_GENERIC, MODEL_SPEC_ID_NODES, MODEL_SPEC_ID_PARAMETER_SOURCE, MODEL_SPEC_ID_PARAMETER_VALUE, MODEL_SPEC_ID_PROJECTIONS, MODEL_SPEC_ID_PSYNEULINK, MODEL_SPEC_ID_RECEIVER_MECH, MODEL_SPEC_ID_SENDER_MECH, MODEL_SPEC_ID_TYPE
from psyneulink.core.globals.sampleiterator import SampleIterator
from psyneulink.core.globals.utilities import get_all_explicit_arguments, parse_string_to_psyneulink_object_string, parse_valid_identifier, safe_equals

__all__ = [
    'PNLJSONError', 'JSONDumpable', 'PNLJSONEncoder',
    'generate_script_from_json'
]


class PNLJSONError(Exception):
    pass


class JSONDumpable:
    @property
    @abc.abstractmethod
    def _dict_summary(self):
        pass

    @property
    def json_summary(self):
        return json.dumps(
            self._dict_summary,
            sort_keys=True,
            indent=4,
            separators=(',', ': '),
            cls=PNLJSONEncoder
        )


class PNLJSONEncoder(json.JSONEncoder):
    """
        A `JSONEncoder
        <https://docs.python.org/3/library/json.html#json.JSONEncoder>`_
        that parses `_dict_summary <Component._dict_summary>` output
        into a more JSON-friendly format.
    """
    def default(self, o):
        from psyneulink.core.components.component import Component, ComponentsMeta

        if isinstance(o, ComponentsMeta):
            return o.__name__
        elif isinstance(o, (type, types.BuiltinFunctionType)):
            if o.__module__ == 'builtins':
                # just give standard type, like float or int
                return f'{o.__name__}'
            elif o is numpy.ndarray:
                return f'{o.__module__}.array'
            else:
                # some builtin modules are internally "_module"
                # but are imported with "module"
                return f"{o.__module__.lstrip('_')}.{o.__name__}"
        elif isinstance(o, (enum.Enum, types.FunctionType)):
            return str(o)
        elif o is NotImplemented:
            return None
        elif isinstance(o, Component):
            return o.name
        elif isinstance(o, SampleIterator):
            return f'{o.__class__.__name__}({repr(o.specification)})'
        elif isinstance(o, numpy.ndarray):
            return list(o)
        elif isinstance(o, numpy.random.RandomState):
            return f'numpy.random.RandomState({o.seed})'
        else:
            try:
                # convert numpy number type to python type
                return o.item()
            except AttributeError:
                pass

        return super().default(o)


def _parse_component_type(component_dict):
    try:
        type_str = component_dict[MODEL_SPEC_ID_TYPE][MODEL_SPEC_ID_PSYNEULINK]
    except (TypeError, KeyError):
        try:
            type_str = component_dict[MODEL_SPEC_ID_TYPE][MODEL_SPEC_ID_GENERIC]
        except (TypeError, KeyError) as e:
            raise PNLJSONError(
                f'{component_dict} not a Component type'
            ) from e

    try:
        # gets the actual psyneulink type (Component, etc..) from the module
        return getattr(psyneulink, type_str)
    except AttributeError as e:
        raise PNLJSONError(
            'Invalid PsyNeuLink type specified for JSON object: {0}'.format(
                component_dict
            )
        ) from e


def _parse_parameter_value(value, component_identifiers=None):
    if component_identifiers is None:
        component_identifiers = {}

    exec('import numpy')

    if isinstance(value, list):
        value = [_parse_parameter_value(x, component_identifiers) for x in value]
        value = f"[{', '.join([str(x) for x in value])}]"
    elif isinstance(value, dict):
        if (
            MODEL_SPEC_ID_PARAMETER_SOURCE in value
            and MODEL_SPEC_ID_PARAMETER_VALUE in value
        ):
            # handle ParameterPort spec
            try:
                value_type = eval(value[MODEL_SPEC_ID_TYPE])
            except Exception as e:
                raise PNLJSONError(
                    'Invalid python type specified in JSON object: {0}'.format(
                        value[MODEL_SPEC_ID_TYPE]
                    )
                ) from e

            value = _parse_parameter_value(
                value[MODEL_SPEC_ID_PARAMETER_VALUE],
                component_identifiers
            )

            # handle tuples and numpy arrays, which both are dumped
            # as lists in JSON form
            if value_type is tuple:
                # convert list brackets to tuple brackets
                assert value[0] == '[' and value[-1] == ']'
                value = f'({value[1:-1]})'
            elif value_type is numpy.ndarray:
                value = f'{value[MODEL_SPEC_ID_TYPE]}({value})'

        else:
            # it is either a Component spec or just a plain dict
            try:
                # try handling as a Component spec
                identifier = parse_valid_identifier(value['name'])
                if (
                    identifier in component_identifiers
                    and component_identifiers[identifier]
                ):
                    # if this spec is already created as a node elsewhere,
                    # then just use a reference
                    value = identifier
                else:
                    value = _generate_component_string(
                        value,
                        component_identifiers
                    )
            except (PNLJSONError, KeyError):
                # standard dict handling
                value = '{{{0}}}'.format(
                    ', '.join([
                        '{0}: {1}'.format(
                            str(_parse_parameter_value(k, component_identifiers)),
                            str(_parse_parameter_value(v, component_identifiers))
                        )
                        for k, v in value.items()
                    ])
                )

    elif isinstance(value, str):
        obj_string = parse_string_to_psyneulink_object_string(value)
        if obj_string is not None:
            return f'psyneulink.{obj_string}'

        # handle dill string
        try:
            dill_str = base64.decodebytes(bytes(value, 'utf-8'))
            dill.loads(dill_str)
            return f'dill.loads({dill_str})'
        except (binascii.Error, pickle.UnpicklingError, EOFError):
            pass

        # handle IO port specification
        match = re.match(r'(.+)\.(.+)_ports\.(.+)', value)
        if match is not None:
            comp_name, port_type, name = match.groups()
            comp_identifer = parse_valid_identifier(comp_name)

            if comp_identifer in component_identifiers:
                name_as_kw = parse_string_to_psyneulink_object_string(name)
                if name_as_kw is not None:
                    name = f'psyneulink.{name_as_kw}'
                else:
                    name = f"'{name}'"

                return f'{comp_identifer}.{port_type}_ports[{name}]'

        # if value is just a non-fixed component name, use the fixed name
        identifier = parse_valid_identifier(value)
        if identifier in component_identifiers:
            value = identifier

        evaluates = False
        try:
            eval(value)
            evaluates = True
        except (TypeError, NameError, SyntaxError):
            pass

        # handle generic string
        if (
            value not in component_identifiers
            # assume a string that contains a dot is a command, not a raw
            # string, this is definitely imperfect and can't handle the
            # legitimate case, but don't know how to distinguish..
            and '.' not in value
            and not evaluates
        ):
            value = f"'{value}'"

    return value


def _generate_component_string(
    component_dict,
    component_identifiers,
    assignment=False,
):
    component_type = _parse_component_type(component_dict)

    name = component_dict['name']
    parameters = dict(component_dict[component_type._model_spec_id_parameters])

    # If there is a parameter that is the psyneulink identifier string
    # (as of this comment, 'pnl'), then expand these parameters as
    # normal ones. We don't check and expand for other
    # special strings here, because we assume that these are specific
    # to other modeling platforms.
    try:
        parameters.update(parameters[MODEL_SPEC_ID_PSYNEULINK])
        del parameters[MODEL_SPEC_ID_PSYNEULINK]
    except KeyError:
        pass

    # pnl objects only have one function unless specified in another way
    # than just "function"
    try:
        parameters['function'] = component_dict['functions'][0]
    except KeyError:
        pass

    assignment_str = f'{parse_valid_identifier(name)} = ' if assignment else ''

    additional_arguments = []
    # get the nonvariable arg and keyword arguments for the component's
    # constructor
    constructor_arguments = get_all_explicit_arguments(
        component_type,
        '__init__'
    )

    # put name as first argument
    if 'name' in constructor_arguments:
        additional_arguments.append(f"name='{name}'")

    # sort on arg name
    for arg, val in sorted(parameters.items(), key=lambda p: p[0]):
        try:
            constructor_parameter_name = getattr(component_type.parameters, arg).constructor_argument
            # Some Parameters may be stored just to be replicated here, and
            # they may have different names than are used in the
            # constructor of the object.
            # Examples:
            #   ControlMechanism.control_spec / control_signals
            #   Mechanism.input_ports_spec / input_ports
            #   Mechanism.output_ports_spec / output_ports
            if constructor_parameter_name is not None:
                constructor_arg = constructor_parameter_name
            else:
                constructor_arg = arg
        except AttributeError:
            constructor_arg = arg

        if constructor_arg in constructor_arguments:
            val = _parse_parameter_value(val, component_identifiers)
            default_val = getattr(component_type.defaults, arg)

            evaled_val = NotImplemented

            # see if val is a psyneulink class instantiation
            # if so, do not instantiate it (avoid offsetting rng for
            # testing - see if you can bypass another way?)
            try:
                eval(re.match(r'(psyneulink\.\w+)\(', val).group(1))
                is_pnl_instance = True
            except (AttributeError, TypeError, NameError, ValueError):
                is_pnl_instance = False

            if not is_pnl_instance:
                # val may be a string that evaluates to the default value
                # also skip listing in constructor in this case
                try:
                    evaled_val = eval(val)
                except (TypeError, NameError, ValueError):
                    pass
                except Exception:
                    # Assume this occurred in creation of a Component
                    # that probably needs some hidden/automatic modification.
                    # Special handling here?
                    # still relevant after testing for instance above?
                    pass

            # skip specifying parameters that match the class defaults
            if (
                not safe_equals(val, default_val)
                and (
                    evaled_val is NotImplemented
                    or not safe_equals(evaled_val, default_val)
                )
            ):
                # test for dill use/equivalence
                try:
                    is_dill_str = val[:5] == 'dill.'
                except TypeError:
                    is_dill_str = False

                if (
                    not is_dill_str
                    or dill.dumps(eval(val)) != dill.dumps(default_val)
                ):
                    additional_arguments.append(f'{constructor_arg}={val}')

    output = '{0}psyneulink.{1}{2}{3}{4}'.format(
        assignment_str,
        component_type.__name__,
        '(' if len(additional_arguments) > 0 else '',
        ', '.join(additional_arguments),
        ')' if len(additional_arguments) > 0 else '',
    )

    return output


def _generate_scheduler_string(
    scheduler_id,
    scheduler_dict,
    component_identifiers,
    blacklist=[]
):
    output = []
    for node, condition in scheduler_dict['conditions']['node'].items():
        if node not in blacklist:
            output.append(
                '{0}.add_condition({1}, {2})'.format(
                    scheduler_id,
                    parse_valid_identifier(node),
                    _generate_condition_string(
                        condition,
                        component_identifiers
                    )
                )
            )

    output.append('')

    termination_str = []
    for scale, cond in scheduler_dict['conditions']['termination'].items():
        termination_str.insert(
            1,
            'psyneulink.{0}: {1}'.format(
                scale,
                _generate_condition_string(cond, component_identifiers)
            )
        )

    output.append(
        '{0}.termination_conds = {{{1}}}'.format(
            scheduler_id,
            ', '.join(termination_str)
        )
    )

    return '\n'.join(output)


def _generate_condition_string(condition_dict, component_identifiers):
    def _parse_condition_arg_value(value):
        pnl_str = parse_string_to_psyneulink_object_string(value)
        try:
            identifier = parse_valid_identifier(value)
        except TypeError:
            identifier = None

        if identifier in component_identifiers:
            return identifier
        elif pnl_str is not None:
            return f'psyneulink.{pnl_str}'
        else:
            return str(value)

    args_str = ''

    if len(condition_dict['args']) > 0:
        arg_str_list = []
        for arg in condition_dict['args']:
            # handle nested Conditions
            try:
                arg = _generate_condition_string(arg, component_identifiers)
            except TypeError:
                pass

            arg_str_list.append(_parse_condition_arg_value(arg))
        args_str = f", {', '.join(arg_str_list)}"

    kwargs_str = ''
    if len(condition_dict['kwargs']) > 0:
        kwarg_str_list = []
        for key, val in condition_dict['kwargs'].items():
            kwarg_str_list.append(f'{key}={_parse_condition_arg_value(val)}')
        kwargs_str = f", {', '.join(kwarg_str_list)}"

    arguments_str = '{0}{1}{2}'.format(
        condition_dict['function'] if condition_dict['function'] is not None else '',
        args_str,
        kwargs_str
    )
    if len(arguments_str) > 0 and arguments_str[0] == ',':
        arguments_str = arguments_str[2:]

    return f'psyneulink.{condition_dict[MODEL_SPEC_ID_TYPE]}({arguments_str})'


def _generate_composition_string(composition_list, component_identifiers):
    control_mechanism_types = (psyneulink.ControlMechanism, )
    # these are not actively added to a Composition
    implicit_types = (
        psyneulink.ObjectiveMechanism,
        psyneulink.ControlProjection,
        psyneulink.AutoAssociativeProjection
    )
    output = []

    # may be given multiple compositions
    for composition_dict in composition_list:
        comp_type = _parse_component_type(composition_dict)
        comp_name = composition_dict['name']
        comp_identifer = parse_valid_identifier(comp_name)

        # get order in which nodes were added
        # may be node names or dictionaries
        try:
            node_order = composition_dict[comp_type._model_spec_id_parameters][MODEL_SPEC_ID_PSYNEULINK]['node_ordering']
            node_order = {
                parse_valid_identifier(node['name']) if isinstance(node, dict)
                else parse_valid_identifier(node): node_order.index(node)
                for node in node_order
            }
            assert all([
                (parse_valid_identifier(node) in node_order)
                for node in composition_dict[MODEL_SPEC_ID_NODES]
            ])
        except (KeyError, TypeError, AssertionError):
            # if no node_ordering attribute exists, fall back to
            # alphabetical order
            alphabetical = enumerate(
                sorted(composition_dict[MODEL_SPEC_ID_NODES])
            )
            node_order = {
                parse_valid_identifier(item[1]): item[0]
                for item in alphabetical
            }

        # clean up pnl-specific and other software-specific items
        pnl_specific_items = {}
        keys_to_delete = []

        for name, node in composition_dict[MODEL_SPEC_ID_NODES].items():
            try:
                _parse_component_type(node)
            except PNLJSONError:
                # node isn't a node dictionary, but a dict of dicts,
                # indicating a software-specific set of nodes or
                # a composition
                if name == MODEL_SPEC_ID_PSYNEULINK:
                    pnl_specific_items = node

                if MODEL_SPEC_ID_COMPOSITION not in node:
                    keys_to_delete.append(name)

        for nodes_dict in pnl_specific_items:
            for name, node in nodes_dict.items():
                composition_dict[MODEL_SPEC_ID_NODES][name] = node

        for name_to_delete in keys_to_delete:
            del composition_dict[MODEL_SPEC_ID_NODES][name_to_delete]

        pnl_specific_items = {}
        keys_to_delete = []
        for name, edge in composition_dict[MODEL_SPEC_ID_PROJECTIONS].items():
            try:
                _parse_component_type(edge)
            except PNLJSONError:
                if name == MODEL_SPEC_ID_PSYNEULINK:
                    pnl_specific_items = edge

                keys_to_delete.append(name)

        for name, edge in pnl_specific_items.items():
            # exclude CIM projections because they are automatically
            # generated
            if (
                edge[MODEL_SPEC_ID_SENDER_MECH] != comp_name
                and edge[MODEL_SPEC_ID_RECEIVER_MECH] != comp_name
            ):
                composition_dict[MODEL_SPEC_ID_PROJECTIONS][name] = edge

        for name_to_delete in keys_to_delete:
            del composition_dict[MODEL_SPEC_ID_PROJECTIONS][name_to_delete]

        # generate string for Composition itself
        output.append(
            "{0} = {1}\n".format(
                comp_identifer,
                _generate_component_string(
                    composition_dict,
                    component_identifiers
                )
            )
        )
        component_identifiers[comp_identifer] = True

        mechanisms = []
        compositions = []
        control_mechanisms = []
        implicit_mechanisms = []

        # add nested compositions and mechanisms in order they were added
        # to this composition
        for name, node in sorted(
            composition_dict[MODEL_SPEC_ID_NODES].items(),
            key=lambda item: node_order[parse_valid_identifier(item[0])]
        ):
            if MODEL_SPEC_ID_COMPOSITION in node:
                compositions.append(node[MODEL_SPEC_ID_COMPOSITION])
            else:
                component_type = _parse_component_type(node)
                identifier = parse_valid_identifier(name)
                if issubclass(component_type, control_mechanism_types):
                    control_mechanisms.append(node)
                    component_identifiers[identifier] = True
                elif issubclass(component_type, implicit_types):
                    implicit_mechanisms.append(node)
                else:
                    mechanisms.append(node)
                    component_identifiers[identifier] = True

        implicit_names = [
            x['name']
            for x in implicit_mechanisms + control_mechanisms
        ]

        for mech in mechanisms:
            output.append(
                _generate_component_string(
                    mech,
                    component_identifiers,
                    assignment=True,
                )
            )
        if len(mechanisms) > 0:
            output.append('')

        for mech in control_mechanisms:
            output.append(
                _generate_component_string(
                    mech,
                    component_identifiers,
                    assignment=True,
                )
            )

        if len(control_mechanisms) > 0:
            output.append('')

        # recursively generate string for inner Compositions
        for comp in compositions:
            output.append(
                _generate_composition_string(
                    comp,
                    component_identifiers
                )
            )
        if len(compositions) > 0:
            output.append('')

        # generate string to add the nodes to this Composition
        node_roles = {
            parse_valid_identifier(node): role for (node, role) in
            composition_dict[comp_type._model_spec_id_parameters][MODEL_SPEC_ID_PSYNEULINK]['required_node_roles']
        }

        # do not add the controller as a normal node
        if composition_dict['controller'] is not None:
            try:
                controller_name = composition_dict['controller']['name']
            except TypeError:
                controller_name = composition_dict['controller']
        else:
            controller_name = None

        for name in sorted(
            composition_dict[MODEL_SPEC_ID_NODES],
            key=lambda item: node_order[parse_valid_identifier(item)]
        ):
            if (
                name not in implicit_names
                and name != controller_name
            ):
                name = parse_valid_identifier(name)

                output.append(
                    '{0}.add_node({1}{2})'.format(
                        comp_identifer,
                        name,
                        ', {0}'.format(
                            _parse_parameter_value(
                                node_roles[name],
                                component_identifiers
                            )
                        ) if name in node_roles else ''
                    )
                )
        if len(composition_dict[MODEL_SPEC_ID_NODES]) > 0:
            output.append('')

        # generate string to add the projections
        for name, projection_dict in composition_dict[MODEL_SPEC_ID_PROJECTIONS].items():
            projection_type = _parse_component_type(projection_dict)

            if (
                not issubclass(projection_type, implicit_types)
                and projection_dict[MODEL_SPEC_ID_SENDER_MECH] not in implicit_names
                and projection_dict[MODEL_SPEC_ID_RECEIVER_MECH] not in implicit_names
            ):
                output.append(
                    '{0}.add_projection(projection={1}, sender={2}, receiver={3})'.format(
                        comp_identifer,
                        _generate_component_string(
                            projection_dict,
                            component_identifiers
                        ),
                        parse_valid_identifier(
                            projection_dict[MODEL_SPEC_ID_SENDER_MECH]
                        ),
                        parse_valid_identifier(
                            projection_dict[MODEL_SPEC_ID_RECEIVER_MECH]
                        ),
                    )
                )

        # add controller if it exists (must happen after projections)
        if controller_name is not None:
            output.append(
                '{0}.add_controller({1})'.format(
                    comp_identifer,
                    parse_valid_identifier(controller_name)
                )
            )

        # add schedulers
        try:
            schedulers = composition_dict[comp_type._model_spec_id_parameters][MODEL_SPEC_ID_PSYNEULINK]['schedulers']

            ContextFlags = psyneulink.core.globals.context.ContextFlags
            scheduler_attr_mappings = {
                str(ContextFlags.PROCESSING): 'scheduler',
                str(ContextFlags.LEARNING): 'scheduler_learning',
            }

            for phase, sched_dict in schedulers.items():
                try:
                    sched_attr = scheduler_attr_mappings[phase]
                except KeyError as e:
                    raise PNLJSONError(
                        f'Invalid scheduler phase in JSON: {phase}'
                    ) from e

                # blacklist automatically generated nodes because they will
                # not exist in the script namespace
                output.append('')
                output.append(
                    _generate_scheduler_string(
                        f'{comp_identifer}.{sched_attr}',
                        sched_dict,
                        component_identifiers,
                        blacklist=implicit_names
                    )
                )

        except KeyError:
            pass

    return '\n'.join(output)


def generate_script_from_json(model_input):
    """
        Generates a Python script from JSON **model_input** in the
        `general JSON format <JSON_Model_Specification>`

        Arguments
        ---------

            model_input : str
                a JSON string in the proper format, or a filename
                containing such
    """

    def get_declared_identifiers(composition_list):
        names = set()

        for composition_dict in composition_list:
            names.add(parse_valid_identifier(composition_dict['name']))
            for name, node in composition_dict[MODEL_SPEC_ID_NODES].items():
                if MODEL_SPEC_ID_COMPOSITION in node:
                    names.update(
                        get_declared_identifiers(
                            node[MODEL_SPEC_ID_COMPOSITION]
                        )
                    )

                names.add(parse_valid_identifier(name))

        return names

    # accept either json string or filename
    try:
        model_input = open(model_input, 'r').read()
    except (FileNotFoundError, OSError):
        pass
    model_input = json.loads(model_input)

    imports_str = ''
    if MODEL_SPEC_ID_COMPOSITION in model_input:
        # maps declared names to whether they are accessible in the script
        # locals. that is, each of these will be names specified in the
        # composition and subcomposition nodes, and their value in this dict
        # will correspond to True if they can be referenced by this name in the
        # script
        component_identifiers = {
            i: False
            for i in get_declared_identifiers(model_input[MODEL_SPEC_ID_COMPOSITION])
        }

        comp_str = _generate_composition_string(
            model_input[MODEL_SPEC_ID_COMPOSITION],
            component_identifiers
        )
    else:
        comp_str = _generate_component_string(
            model_input,
            component_identifiers={},
            assignment=True
        )

    module_friendly_name_mapping = {
        'psyneulink': 'pnl',
        'dill': 'dill',
        'numpy': 'np'
    }

    module_names = set()
    potential_module_names = set(re.findall(r'([A-Za-z]+?)\.', comp_str))
    for module in potential_module_names:
        try:
            exec(f'import {module}')
            module_names.add(module)
        except (ImportError, ModuleNotFoundError, SyntaxError):
            pass

    for module in module_names:
        try:
            friendly_name = module_friendly_name_mapping[module]
            comp_str = re.sub(f'{module}\\.', f'{friendly_name}.', comp_str)
        except KeyError:
            friendly_name = module

        if f'{friendly_name}.' in comp_str:
            imports_str += 'import {0}{1}\n'.format(
                module,
                f' as {friendly_name}' if friendly_name != module else ''
            )

    model_output = '{0}{1}{2}'.format(
        imports_str,
        '\n' if len(imports_str) > 0 else '',
        comp_str
    )

    return model_output
