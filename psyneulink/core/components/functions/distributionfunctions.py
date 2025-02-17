#
# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
#
# ****************************************   DISTRIBUTION FUNCTIONS   **************************************************
"""

* `NormalDist`
* `UniformToNormalDist`
* `ExponentialDist`
* `UniformDist`
* `GammaDist`
* `WaldDist`

Overview
--------

Functions that return one or more samples from a distribution.

"""
from enum import IntEnum

import numpy as np
import typecheck as tc

from psyneulink.core.components.functions.function import Function_Base, FunctionError
from psyneulink.core.globals.keywords import \
    ADDITIVE_PARAM, DIST_FUNCTION_TYPE, BETA, DIST_MEAN, DIST_SHAPE, DRIFT_DIFFUSION_ANALYTICAL_FUNCTION, \
    EXPONENTIAL_DIST_FUNCTION, GAMMA_DIST_FUNCTION, HIGH, LOW, MULTIPLICATIVE_PARAM, NOISE, NORMAL_DIST_FUNCTION, \
    SCALE, STANDARD_DEVIATION, THRESHOLD, UNIFORM_DIST_FUNCTION, WALD_DIST_FUNCTION
from psyneulink.core.globals.context import ContextFlags
from psyneulink.core.globals.utilities import parameter_spec
from psyneulink.core.globals.preferences.basepreferenceset import is_pref_set

from psyneulink.core.globals.parameters import Parameter

__all__ = [
    'DistributionFunction', 'DRIFT_RATE', 'DRIFT_RATE_VARIABILITY', 'DriftDiffusionAnalytical', 'ExponentialDist',
    'GammaDist', 'NON_DECISION_TIME', 'NormalDist', 'STARTING_POINT', 'STARTING_POINT_VARIABILITY',
    'THRESHOLD_VARIABILITY', 'UniformDist', 'UniformToNormalDist', 'WaldDist',
]


class DistributionFunction(Function_Base):
    componentType = DIST_FUNCTION_TYPE


class NormalDist(DistributionFunction):
    """
    NormalDist(                      \
             mean=0.0,               \
             standard_deviation=1.0, \
             params=None,            \
             owner=None,             \
             prefs=None              \
             )

    .. _NormalDist:

    Return a random sample from a normal distribution using numpy.random.normal;

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `standard_deviation <NormalDist.standard_deviation>`
    | *ADDITIVE_PARAM:* `mean <NormalDist.mean>`
    |

    Arguments
    ---------

    mean : float : default 0.0
        The mean or center of the normal distribution

    standard_deviation : float : default 1.0
        Standard deviation of the normal distribution. Must be > 0.0

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    mean : float : default 0.0
        The mean or center of the normal distribution.

    standard_deviation : float : default 1.0
        Standard deviation of the normal distribution; if it is 0.0, returns `mean <NormalDist.mean>`.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    """

    componentName = NORMAL_DIST_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                mean
                    see `mean <NormalDist.mean>`

                    :default value: 0.0
                    :type: float

                standard_deviation
                    see `standard_deviation <NormalDist.standard_deviation>`

                    :default value: 1.0
                    :type: float

        """
        mean = Parameter(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        standard_deviation = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 mean=0.0,
                 standard_deviation=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(mean=mean,
                                                  standard_deviation=standard_deviation,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )

    def _validate_params(self, request_set, target_set=None, context=None):
        super()._validate_params(request_set=request_set, target_set=target_set, context=context)

        if STANDARD_DEVIATION in target_set:
            if target_set[STANDARD_DEVIATION] < 0.0:
                raise FunctionError("The standard_deviation parameter ({}) of {} must be greater than zero.".
                                    format(target_set[STANDARD_DEVIATION], self.name))

    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):
        mean = self.get_current_function_param(DIST_MEAN, context)
        standard_deviation = self.get_current_function_param(STANDARD_DEVIATION, context)

        result = np.random.normal(mean, standard_deviation)

        return self.convert_output_type(result)


class UniformToNormalDist(DistributionFunction):
    """
    UniformToNormalDist(             \
             mean=0.0,               \
             standard_deviation=1.0, \
             params=None,            \
             owner=None,             \
             prefs=None              \
             )

    .. _UniformToNormalDist:

    Return a random sample from a normal distribution using first np.random.rand(1) to generate a sample from a uniform
    distribution, and then converting that sample to a sample from a normal distribution with the following equation:

    .. math::

        normal\\_sample = \\sqrt{2} \\cdot standard\\_dev \\cdot scipy.special.erfinv(2 \\cdot uniform\\_sample - 1)  + mean

    The uniform --> normal conversion allows for a more direct comparison with MATLAB scripts.

    .. note::

        This function requires `SciPy <https://pypi.python.org/pypi/scipy>`_.

    (https://github.com/jonasrauber/randn-matlab-python)

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `standard_deviation <UniformToNormalDist.standard_deviation>`
    | *ADDITIVE_PARAM:* `mean <UniformToNormalDist.mean>`
    |

    Arguments
    ---------

    mean : float : default 0.0
        The mean or center of the normal distribution

    standard_deviation : float : default 1.0
        Standard deviation of the normal distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    mean : float : default 0.0
        The mean or center of the normal distribution

    standard_deviation : float : default 1.0
        Standard deviation of the normal distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    """

    componentName = NORMAL_DIST_FUNCTION

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                variable
                    see `variable <UniformToNormalDist.variable>`

                    :default value: numpy.array([0])
                    :type: numpy.ndarray
                    :read only: True

                mean
                    see `mean <UniformToNormalDist.mean>`

                    :default value: 0.0
                    :type: float

                standard_deviation
                    see `standard_deviation <UniformToNormalDist.standard_deviation>`

                    :default value: 1.0
                    :type: float

        """
        variable = Parameter(np.array([0]), read_only=True, pnl_internal=True, constructor_argument='default_variable')
        mean = Parameter(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        standard_deviation = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 mean=0.0,
                 standard_deviation=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(mean=mean,
                                                  standard_deviation=standard_deviation,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )


    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):

        try:
            from scipy.special import erfinv
        except:
            raise FunctionError("The UniformToNormalDist function requires the SciPy package.")

        mean = self.get_current_function_param(DIST_MEAN, context)
        standard_deviation = self.get_current_function_param(STANDARD_DEVIATION, context)

        sample = np.random.rand(1)[0]
        result = ((np.sqrt(2) * erfinv(2 * sample - 1)) * standard_deviation) + mean

        return self.convert_output_type(result)


class ExponentialDist(DistributionFunction):
    """
    ExponentialDist(                \
             beta=1.0,              \
             params=None,           \
             owner=None,            \
             prefs=None             \
             )

    .. _ExponentialDist:

    Return a random sample from a exponential distribution using numpy.random.exponential

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `beta <ExponentialDist.beta>`
    |

    Arguments
    ---------

    beta : float : default 1.0
        The scale parameter of the exponential distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    beta : float : default 1.0
        The scale parameter of the exponential distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    """
    componentName = EXPONENTIAL_DIST_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                beta
                    see `beta <ExponentialDist.beta>`

                    :default value: 1.0
                    :type: float

        """
        beta = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 beta=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(beta=beta,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )


    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):

        beta = self.get_current_function_param(BETA, context)
        result = np.random.exponential(beta)

        return self.convert_output_type(result)


class UniformDist(DistributionFunction):
    """
    UniformDist(                      \
             low=0.0,             \
             high=1.0,             \
             params=None,           \
             owner=None,            \
             prefs=None             \
             )

    .. _UniformDist:

    Return a random sample from a uniform distribution using numpy.random.uniform

    Arguments
    ---------

    low : float : default 0.0
        Lower bound of the uniform distribution

    high : float : default 1.0
        Upper bound of the uniform distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    low : float : default 0.0
        Lower bound of the uniform distribution

    high : float : default 1.0
        Upper bound of the uniform distribution

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    """
    componentName = UNIFORM_DIST_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                high
                    see `high <UniformDist.high>`

                    :default value: 1.0
                    :type: float

                low
                    see `low <UniformDist.low>`

                    :default value: 0.0
                    :type: float

        """
        low = Parameter(0.0, modulable=True)
        high = Parameter(1.0, modulable=True)

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 low=0.0,
                 high=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(low=low,
                                                  high=high,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )


    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):

        low = self.get_current_function_param(LOW, context)
        high = self.get_current_function_param(HIGH, context)
        result = np.random.uniform(low, high)

        return self.convert_output_type(result)


class GammaDist(DistributionFunction):
    """
    GammaDist(\
             scale=1.0,\
             dist_shape=1.0,\
             params=None,\
             owner=None,\
             prefs=None\
             )

    .. _GammaDist:

    Return a random sample from a gamma distribution using numpy.random.gamma

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `scale <GammaDist.scale>`
    | *ADDITIVE_PARAM:* `dist_shape <GammaDist.dist_shape>`
    |

    Arguments
    ---------

    scale : float : default 1.0
        The scale of the gamma distribution. Should be greater than zero.

    dist_shape : float : default 1.0
        The shape of the gamma distribution. Should be greater than zero.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    Attributes
    ----------

    scale : float : default 1.0
        The scale of the gamma distribution. Should be greater than zero.

    dist_shape : float : default 1.0
        The shape of the gamma distribution. Should be greater than zero.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    """

    componentName = GAMMA_DIST_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                dist_shape
                    see `dist_shape <GammaDist.dist_shape>`

                    :default value: 1.0
                    :type: float

                scale
                    see `scale <GammaDist.scale>`

                    :default value: 1.0
                    :type: float

        """
        scale = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        dist_shape = Parameter(1.0, modulable=True, aliases=[ADDITIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 scale=1.0,
                 dist_shape=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(scale=scale,
                                                  dist_shape=dist_shape,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )


    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):

        scale = self.get_current_function_param(SCALE, context)
        dist_shape = self.get_current_function_param(DIST_SHAPE, context)

        result = np.random.gamma(dist_shape, scale)

        return self.convert_output_type(result)


class WaldDist(DistributionFunction):
    """
     WaldDist(             \
              scale=1.0,\
              mean=1.0,\
              params=None,\
              owner=None,\
              prefs=None\
              )

     .. _WaldDist:

     Return a random sample from a Wald distribution using numpy.random.wald

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `scale <WaldDist.scale>`
    | *ADDITIVE_PARAM:* `mean <WaldDist.mean>`
    |

     Arguments
     ---------

     scale : float : default 1.0
         Scale parameter of the Wald distribution. Should be greater than zero.

     mean : float : default 1.0
         Mean of the Wald distribution. Should be greater than or equal to zero.

     params : Dict[param keyword: param value] : default None
         a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
         function.  Values specified for parameters in the dictionary override any assigned to those parameters in
         arguments of the constructor.

     owner : Component
         `component <Component>` to which to assign the Function.

     prefs : PreferenceSet or specification dict : default Function.classPreferences
         the `PreferenceSet` for the Function. If it is not specified, a default is assigned using `classPreferences`
         defined in __init__.py (see :doc:`PreferenceSet <LINK>` for details).


     Attributes
     ----------

     scale : float : default 1.0
         Scale parameter of the Wald distribution. Should be greater than zero.

     mean : float : default 1.0
         Mean of the Wald distribution. Should be greater than or equal to zero.

     params : Dict[param keyword: param value] : default None
         a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
         function.  Values specified for parameters in the dictionary override any assigned to those parameters in
         arguments of the constructor.

     owner : Component
         `component <Component>` to which to assign the Function.

     prefs : PreferenceSet or specification dict : default Function.classPreferences
         the `PreferenceSet` for the Function. If it is not specified, a default is assigned using `classPreferences`
         defined in __init__.py (see :doc:`PreferenceSet <LINK>` for details).


     """

    componentName = WALD_DIST_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                mean
                    see `mean <WaldDist.mean>`

                    :default value: 1.0
                    :type: float

                scale
                    see `scale <WaldDist.scale>`

                    :default value: 1.0
                    :type: float

        """
        scale = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        mean = Parameter(1.0, modulable=True, aliases=[ADDITIVE_PARAM])

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 scale=1.0,
                 mean=1.0,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None):
        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(scale=scale,
                                                  mean=mean,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )


    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):

        scale = self.get_current_function_param(SCALE, context)
        mean = self.get_current_function_param(DIST_MEAN, context)

        result = np.random.wald(mean, scale)

        return self.convert_output_type(result)


# Note:  For any of these that correspond to args, value must match the name of the corresponding arg in __init__()
DRIFT_RATE = 'drift_rate'
DRIFT_RATE_VARIABILITY = 'DDM_DriftRateVariability'
THRESHOLD_VARIABILITY = 'DDM_ThresholdRateVariability'
STARTING_POINT = 'starting_point'
STARTING_POINT_VARIABILITY = "DDM_StartingPointVariability"
NON_DECISION_TIME = 't0'


def _DriftDiffusionAnalytical_bias_getter(owning_component=None, context=None):
    starting_point = owning_component.parameters.starting_point._get(context)
    threshold = owning_component.parameters.threshold._get(context)
    try:
        return (starting_point + threshold) / (2 * threshold)
    except TypeError:
        return None


# QUESTION: IF VARIABLE IS AN ARRAY, DOES IT RETURN AN ARRAY FOR EACH RETURN VALUE (RT, ER, ETC.)
class DriftDiffusionAnalytical(DistributionFunction):  # -------------------------------------------------------------------------------
    """
    DriftDiffusionAnalytical(   \
        default_variable=None,  \
        drift_rate=1.0,         \
        threshold=1.0,          \
        starting_point=0.0,     \
        t0=0.2                  \
        noise=0.5,              \
        params=None,            \
        owner=None,             \
        prefs=None              \
        )

    .. _DriftDiffusionAnalytical:

    Return terminal value of decision variable, mean accuracy, and mean response time computed analytically for the
    drift diffusion process as described in `Bogacz et al (2006) <https://www.ncbi.nlm.nih.gov/pubmed/17014301>`_.

    *Modulatory Parameters:*

    | *MULTIPLICATIVE_PARAM:* `drift_rate <DriftDiffusionAnalytical.drift_rate>`
    | *ADDITIVE_PARAM:* `starting_point <DriftDiffusionAnalytical.starting_point>`
    |

    Arguments
    ---------

    default_variable : number, list or array : default class_defaults.variable
        specifies a template for decision variable(s);  if it is list or array, a separate solution is computed
        independently for each element.

    drift_rate : float, list or 1d array : default 1.0
        specifies the drift_rate of the drift diffusion process.  If it is a list or array,
        it must be the same length as `default_variable <DriftDiffusionAnalytical.default_variable>`.

    threshold : float, list or 1d array : default 1.0
        specifies the threshold (boundary) of the drift diffusion process.  If it is a list or array,
        it must be the same length as `default_variable <DriftDiffusionAnalytical.default_variable>`.

    starting_point : float, list or 1d array : default 1.0
        specifies the initial value of the decision variable for the drift diffusion process.  If it is a list or
        array, it must be the same length as `default_variable <DriftDiffusionAnalytical.default_variable>`.

    noise : float, list or 1d array : default 0.0
        specifies the noise term (corresponding to the diffusion component) of the drift diffusion process.
        If it is a float, it must be a number from 0 to 1.  If it is a list or array, it must be the same length as
        `default_variable <DriftDiffusionAnalytical.default_variable>` and all elements must be floats from 0 to 1.

    t0 : float, list or 1d array : default 0.2
        specifies the non-decision time for solution. If it is a float, it must be a number from 0 to 1.  If it is a
        list or array, it must be the same length as  `default_variable <DriftDiffusionAnalytical.default_variable>` and all
        elements must be floats from 0 to 1.

    params : Dict[param keyword: param value] : default None
        a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
        function.  Values specified for parameters in the dictionary override any assigned to those parameters in
        arguments of the constructor.

    owner : Component
        `component <Component>` to which to assign the Function.

    name : str : default see `name <Function.name>`
        specifies the name of the Function.

    prefs : PreferenceSet or specification dict : default Function.classPreferences
        specifies the `PreferenceSet` for the Function (see `prefs <Function_Base.prefs>` for details).

    shenhav_et_al_compat_mode: bool : default False
        whether Shenhav et al. compatibility mode is set. See shenhav_et_al_compat_mode property.


    Attributes
    ----------

    variable : number or 1d array
        holds initial value assigned to :keyword:`default_variable` argument;
        ignored by `function <BogaczEtal.function>`.

    drift_rate : float or 1d array
        determines the drift component of the drift diffusion process.

    threshold : float or 1d array
        determines the threshold (boundary) of the drift diffusion process (i.e., at which the integration
        process is assumed to terminate).

    starting_point : float or 1d array
        determines the initial value of the decision variable for the drift diffusion process.

    noise : float or 1d array
        determines the diffusion component of the drift diffusion process (used to specify the variance of a
        Gaussian random process).

    t0 : float or 1d array
        determines the assumed non-decision time to determine the response time returned by the solution.

    bias : float or 1d array
        normalized starting point:
        (`starting_point <DriftDiffusionAnalytical.starting_point>` + `threshold <DriftDiffusionAnalytical.threshold>`) /
        (2 * `threshold <DriftDiffusionAnalytical.threshold>`)

    owner : Component
        `component <Component>` to which the Function has been assigned.

    name : str
        the name of the Function; if it is not specified in the **name** argument of the constructor, a
        default is assigned by FunctionRegistry (see `Naming` for conventions used for default and duplicate names).

    prefs : PreferenceSet or specification dict : Function.classPreferences
        the `PreferenceSet` for function; if it is not specified in the **prefs** argument of the Function's
        constructor, a default is assigned using `classPreferences` defined in __init__.py (see :doc:`PreferenceSet
        <LINK>` for details).

    """

    componentName = DRIFT_DIFFUSION_ANALYTICAL_FUNCTION

    paramClassDefaults = Function_Base.paramClassDefaults.copy()

    class Parameters(DistributionFunction.Parameters):
        """
            Attributes
            ----------

                bias
                    see `bias <DriftDiffusionAnalytical.bias>`

                    :default value: 0.5
                    :type: float
                    :read only: True

                drift_rate
                    see `drift_rate <DriftDiffusionAnalytical.drift_rate>`

                    :default value: 1.0
                    :type: float

                noise
                    see `noise <DriftDiffusionAnalytical.noise>`

                    :default value: 0.5
                    :type: float

                starting_point
                    see `starting_point <DriftDiffusionAnalytical.starting_point>`

                    :default value: 0.0
                    :type: float

                t0
                    see `t0 <DriftDiffusionAnalytical.t0>`

                    :default value: 0.2
                    :type: float

                threshold
                    see `threshold <DriftDiffusionAnalytical.threshold>`

                    :default value: 1.0
                    :type: float

        """
        drift_rate = Parameter(1.0, modulable=True, aliases=[MULTIPLICATIVE_PARAM])
        starting_point = Parameter(0.0, modulable=True, aliases=[ADDITIVE_PARAM])
        threshold = Parameter(1.0, modulable=True)
        noise = Parameter(0.5, modulable=True)
        t0 = .200
        bias = Parameter(0.5, read_only=True, getter=_DriftDiffusionAnalytical_bias_getter)

    @tc.typecheck
    def __init__(self,
                 default_variable=None,
                 drift_rate: parameter_spec = 1.0,
                 starting_point: parameter_spec = 0.0,
                 threshold: parameter_spec = 1.0,
                 noise: parameter_spec = 0.5,
                 t0: parameter_spec = .200,
                 params=None,
                 owner=None,
                 prefs: is_pref_set = None,
                 shenhav_et_al_compat_mode=False):

        self._shenhav_et_al_compat_mode = shenhav_et_al_compat_mode

        # Assign args to params and functionParams dicts
        params = self._assign_args_to_param_dicts(drift_rate=drift_rate,
                                                  starting_point=starting_point,
                                                  threshold=threshold,
                                                  noise=noise,
                                                  t0=t0,
                                                  params=params)

        super().__init__(default_variable=default_variable,
                         params=params,
                         owner=owner,
                         prefs=prefs,
                         )

    @property
    def output_type(self):
        return self._output_type

    @output_type.setter
    def output_type(self, value):
        # disabled because it happens during normal execution, may be confusing
        # warnings.warn('output_type conversion disabled for {0}'.format(self.__class__.__name__))
        self._output_type = None

    @property
    def shenhav_et_al_compat_mode(self):
        """
        Get whether the function is set to Shenhav et al. compatibility mode. This mode allows
        the analytic computations of mean error rate and reaction time to match exactly the
        computations made in the MATLAB DDM code (Matlab/ddmSimFRG.m). These compatibility changes
        should only effect edges cases that involve the following cases:

            - Floating point overflows and underflows are ignored when computing mean RT and mean ER
            - Exponential expressions used in cacluating mean RT and mean ER are bounded by 1e-12 to 1e12.
            - Decision time is not permitted to be negative and will be set to 0 in these cases. Thus RT
              will be RT = non-decision-time in these cases.

        Returns
        -------
        Shenhav et al. compatible mode setting : (bool)

        """
        return self._shenhav_et_al_compat_mode

    @shenhav_et_al_compat_mode.setter
    def shenhav_et_al_compat_mode(self, value):
        """
        Set whether the function is set to Shenhav et al. compatibility mode. This mode allows
        the analytic computations of mean error rate and reaction time to match exactly the
        computations made in the MATLAB DDM code (Matlab/ddmSimFRG.m). These compatibility chages
        should only effect edges cases that involve the following cases:

            - Floating point overflows and underflows are ignored when computing mean RT and mean ER
            - Exponential expressions used in cacluating mean RT and mean ER are bounded by 1e-12 to 1e12.
            - Decision time is not permitted to be negative and will be set to 0 in these cases. Thus RT
              will be RT = non-decision-time in these cases.

        Arguments
        ---------

        value : bool
            Set True to turn on Shenhav et al. compatibility mode, False for off.
        """
        self._shenhav_et_al_compat_mode = value

    def _function(self,
                 variable=None,
                 context=None,
                 params=None,
                 ):
        """
        Return: terminal value of decision variable (equal to threshold), mean accuracy (error rate; ER) and mean
        response time (RT)

        Arguments
        ---------

        variable : 2d array
            ignored.

        params : Dict[param keyword: param value] : default None
            a `parameter dictionary <ParameterPort_Specification>` that specifies the parameters for the
            function.  Values specified for parameters in the dictionary override any assigned to those parameters in
            arguments of the constructor.


        Returns
        -------
        Decision variable, mean ER, mean RT : (float, float, float)

        """

        attentional_drift_rate = float(self.get_current_function_param(DRIFT_RATE, context))
        stimulus_drift_rate = float(variable)
        drift_rate = attentional_drift_rate * stimulus_drift_rate
        threshold = self.get_current_function_param(THRESHOLD, context)
        starting_point = float(self.get_current_function_param(STARTING_POINT, context))
        noise = float(self.get_current_function_param(NOISE, context))
        t0 = float(self.get_current_function_param(NON_DECISION_TIME, context))

        # drift_rate = float(self.drift_rate) * float(variable)
        # threshold = float(self.threshold)
        # starting_point = float(self.starting_point)
        # noise = float(self.noise)
        # t0 = float(self.t0)

        bias = (starting_point + threshold) / (2 * threshold)

        # Prevents div by 0 issue below:
        if bias <= 0:
            bias = 1e-8
        if bias >= 1:
            bias = 1 - 1e-8

        # drift_rate close to or at 0 (avoid float comparison)
        if np.abs(drift_rate) < 1e-8:
            # back to absolute bias in order to apply limit
            bias_abs = bias * 2 * threshold - threshold
            # use expression for limit a->0 from Srivastava et al. 2016
            rt = t0 + (threshold ** 2 - bias_abs ** 2) / (noise ** 2)
            er = (threshold - bias_abs) / (2 * threshold)
        else:
            drift_rate_normed = np.abs(drift_rate)
            ztilde = threshold / drift_rate_normed
            atilde = (drift_rate_normed / noise) ** 2

            is_neg_drift = drift_rate < 0
            bias_adj = (is_neg_drift == 1) * (1 - bias) + (is_neg_drift == 0) * bias
            y0tilde = ((noise ** 2) / 2) * np.log(bias_adj / (1 - bias_adj))
            if np.abs(y0tilde) > threshold:
                # First difference between Shenhav et al. DDM code and PNL's.
                if self.shenhav_et_al_compat_mode:
                    y0tilde = -1 * (y0tilde < 0) * threshold + (y0tilde >=0 ) * threshold
                else:
                    y0tilde = -1 * (is_neg_drift == 1) * threshold + (is_neg_drift == 0) * threshold

            x0tilde = y0tilde / drift_rate_normed

            # Whether we should ignore or raise floating point over and underflow exceptions.
            # Shenhav et al. MATLAB code ignores them.
            ignore_or_raise = "raise"
            if self.shenhav_et_al_compat_mode:
                ignore_or_raise = "ignore"

            with np.errstate(over=ignore_or_raise, under=ignore_or_raise):
                try:
                    # Lets precompute these common sub-expressions
                    exp_neg2_x0tilde_atilde = np.exp(-2 * x0tilde * atilde)
                    exp_2_ztilde_atilde = np.exp(2 * ztilde * atilde)
                    exp_neg2_ztilde_atilde = np.exp(-2 * ztilde * atilde)

                    if self.shenhav_et_al_compat_mode:
                        exp_neg2_x0tilde_atilde = np.nanmax([1e-12, exp_neg2_x0tilde_atilde])
                        exp_2_ztilde_atilde = np.nanmin([1e12, exp_2_ztilde_atilde])
                        exp_neg2_ztilde_atilde = np.nanmax([1e-12, exp_neg2_ztilde_atilde])

                    rt = ztilde * np.tanh(ztilde * atilde) + \
                         ((2 * ztilde * (1 - exp_neg2_x0tilde_atilde)) / (
                                 exp_2_ztilde_atilde - exp_neg2_ztilde_atilde) - x0tilde)
                    er = 1 / (1 + exp_2_ztilde_atilde) - \
                         ((1 - exp_neg2_x0tilde_atilde) / (exp_2_ztilde_atilde - exp_neg2_ztilde_atilde))

                    # Fail safe to prevent negative mean RT's. Shenhav et al. do this.
                    if self.shenhav_et_al_compat_mode:
                        if rt < 0:
                            rt = 0

                    rt = rt + t0

                except FloatingPointError:
                    # Per Mike Shvartsman:
                    # If ±2*ztilde*atilde (~ 2*z*a/(c^2) gets very large, the diffusion vanishes relative to drift
                    # and the problem is near-deterministic. Without diffusion, error rate goes to 0 or 1
                    # depending on the sign of the drift, and so decision time goes to a point mass on z/a – x0, and
                    # generates a "RuntimeWarning: overflow encountered in exp"
                    er = 0
                    rt = ztilde / atilde - x0tilde + t0

            # This last line makes it report back in terms of a fixed reference point
            #    (i.e., closer to 1 always means higher p(upper boundary))
            # If you comment this out it will report errors in the reference frame of the drift rate
            #    (i.e., reports p(upper) if drift is positive, and p(lower if drift is negative)
            er = (is_neg_drift == 1) * (1 - er) + (is_neg_drift == 0) * (er)

        # Compute moments (mean, variance, skew) of condiational response time distributions
        moments = DriftDiffusionAnalytical._compute_conditional_rt_moments(drift_rate, noise, threshold, bias, t0)

        return rt, er, \
               moments['mean_rt_plus'], moments['var_rt_plus'], moments['skew_rt_plus'], \
               moments['mean_rt_minus'], moments['var_rt_minus'], moments['skew_rt_minus']

    @staticmethod
    def _compute_conditional_rt_moments(drift_rate, noise, threshold, starting_point, t0):
        """
        This is a helper function for computing the conditional decison time moments for the DDM.
        It is based completely off of Matlab\\DDMFunctions\\ddm_metrics_cond_Mat.m.

        :param drift_rate: The drift rate of the DDM
        :param noise: The diffusion rate.
        :param threshold: The symmetric threshold of the DDM
        :param starting_point: The initial condition.
        :param t0: The non decision time.
        :return: A dictionary containing the following key value pairs:
         mean_rt_plus: The mean RT of positive responses.
         mean_rt_minus: The mean RT of negative responses.
         var_rt_plus: The variance of RT of positive responses.
         var_rt_minus: The variance of RT of negative responses.
         skew_rt_plus: The skew of RT of positive responses.
         skew_rt_minus: The skew of RT of negative responses.
        """

        #  transform starting point to be centered at 0
        starting_point = (starting_point - 0.5) * 2.0 * threshold

        if abs(drift_rate) < 0.01:
            drift_rate = 0.01

        X = drift_rate * starting_point / noise**2
        Z = drift_rate * threshold / noise**2

        X = max(-100, min(100, X))

        Z = max(-100, min(100, Z))

        if abs(Z) < 0.0001:
            Z = 0.0001

        def coth(x):
            return 1 / np.tanh(x)

        def csch(x):
            return 1 / np.sinh(x)

        moments = {}

        # Lets ignore any divide by zeros we get or NaN errors. This will allow the NaN's to propogate.
        with np.errstate(divide='ignore', invalid='ignore'):
            moments["mean_rt_plus"] = noise**2. / (drift_rate**2) * (2 * Z * coth(2 * Z) - (X + Z) * coth(X + Z))

            moments["mean_rt_minus"] = noise**2. / (drift_rate**2) * (2 * Z * coth(2 * Z) - (-X + Z) * coth(-X + Z))

            moments["var_rt_plus"] = noise**4. / (drift_rate**4) * \
                              (4 * Z**2. * (csch(2 * Z))**2 + 2 * Z * coth(2 * Z) - (Z + X)**2. *
                               (csch(Z + X))**2 - (Z + X) * coth(Z + X))

            moments["var_rt_minus"] = noise**4. / (drift_rate**4) * \
                               (4 * Z**2. * (csch(2 * Z)) ** 2 + 2 * Z * coth(2 * Z) - (Z - X)**2. *
                                (csch(Z - X))**2 - (Z - X) * coth(Z - X))

            moments["skew_rt_plus"] = noise**6. / (drift_rate** 6) * \
                               (12 * Z**2. * (csch(2 * Z))**2 + 16 * Z**3. * coth(2 * Z) * (csch(2 * Z))**2 +
                                6 * Z * coth(2 * Z) - 3 * (Z + X)**2. * (csch(Z + X))**2 -
                                2 * (Z + X)**3. * coth(Z + X) * (csch(Z + X))**2 - 3 * (Z + X) * coth(Z + X))

            moments["skew_rt_minus"] = noise**6. / (drift_rate**6) * \
                                (12 * Z**2. * (csch(2 * Z))**2 + 16 * Z**3. * coth(2 * Z) *
                                 (csch(2 * Z))**2 + 6 * Z * coth(2 * Z) - 3 * (Z - X)**2. *
                                 (csch(Z - X))**2 - 2 * (Z - X)**3. * coth(Z - X) *
                                 (csch(Z - X))**2 - 3 * (Z - X) * coth(Z - X))

            # divide third central moment by var_rt**1.5 to get skewness
            moments['skew_rt_plus'] /= moments['var_rt_plus']**1.5
            moments['skew_rt_minus'] /= moments['var_rt_minus']**1.5

            # Add the non-decision time to the mean RTs
            moments['mean_rt_plus'] += t0
            moments['mean_rt_minus'] += t0


        return moments

    def derivative(self, output=None, input=None, context=None):
        """
        derivative(output, input)

        Calculate the derivative of :math:`\\frac{1}{reward rate}` with respect to the threshold (**output** arg)
        and drift_rate (**input** arg).  Reward rate (:math:`RR`) is assumed to be:

            :math:`RR = delay_{ITI} + \\frac{Z}{A} + ED`;

        the derivative of :math:`\\frac{1}{RR}` with respect to the `threshold <DriftDiffusionAnalytical.threshold>` is:

            :math:`\\frac{1}{A} - \\frac{E}{A} - 2\\frac{A}{c^2}ED`;

        and the derivative of 1/RR with respect to the `drift_rate <DriftDiffusionAnalytical.drift_rate>` is:

            :math:`-\\frac{Z}{A^2} + \\frac{Z}{A^2}E - \\frac{2Z}{c^2}ED`

        where:

            *A* = `drift_rate <DriftDiffusionAnalytical.drift_rate>`,

            *Z* = `threshold <DriftDiffusionAnalytical.threshold>`,

            *c* = `noise <DriftDiffusionAnalytical.noise>`,

            *E* = :math:`e^{-2\\frac{ZA}{c^2}}`,

            *D* = :math:`delay_{ITI} + delay_{penalty} - \\frac{Z}{A}`,

            :math:`delay_{ITI}` is the intertrial interval and :math:`delay_{penalty}` is a penalty delay.


        Returns
        -------

        derivatives :  List[float, float)
            of :math:`\\frac{1}{RR}` with respect to `threshold <DriftDiffusionAnalytical.threshold>` and `drift_rate
            <DriftDiffusionAnalytical.drift_rate>`.

        """
        Z = output or self.get_current_function_param(THRESHOLD, context)
        A = input or self.get_current_function_param(DRIFT_RATE, context)
        c = self.get_current_function_param(NOISE, context)
        c_sq = c ** 2
        E = np.exp(-2 * Z * A / c_sq)
        D_iti = 0
        D_pen = 0
        D = D_iti + D_pen
        # RR =  1/(D_iti + Z/A + (E*D))

        dRR_dZ = 1 / A + E / A + (2 * A / c_sq) * E * D
        dRR_dA = -Z / A ** 2 + (Z / A ** 2) * E - (2 * Z / c_sq) * E * D

        return [dRR_dZ, dRR_dA]
