
# ****************************************  Nieuwenhuis et al. (2005) model *************************************************


"""
Overview
--------
This implements a model "The Role of the Locus Coeruleus in Mediating the Attentional Blink:
A Neurocomputational Theory", by Nieuwenhuis et al. (2005).
The attentional blink refers to the temporary impairment in perceiving the 2nd of 2 targets presented in close temporal
proximity.
<https://research.vu.nl/ws/files/2063874/Nieuwenhuis%20Journal%20of%20Experimental%20Psychology%20-%20General%20134(3)-2005%20u.pdf`.

During the attentional blink paradigm, on each trial a list of letters is presented to subjects, colored in black on a grey background.
Additionally, two numbers are presented during each trial and the task is to correctly identify which two digits were presented.
A vast amount of studies  showed that the accuracy of identifying both digits correctly depends on the lag between the two target stimuli.
Especially between 200 and 300 ms after T1 onset subjects accuracy decreases.
However, presenting the second target stimulus T2 right after the first target stimulus T1,
subjects performance is as accurate as with lags longer then 400ms between T1 and T2.

The model by Nieuwenhuis et al. (2005) shows that the findings on the attentional blink paradigm can be explained by the mechanics of the Locus Ceruleus.

With this model it is possible to simulate that identifying T2 accurately depends on:
    whether T1 was accurately identified
    the lag between T1 and T2
    the mode of the LC

This example illustrates Figure 3 from Nieuwenhuis et al. (2005) paper with Lag 2 and only one execution.
Note that in the Nieuwenhuis et al. (2005) paper the Figure shows the average Avtivation over 1000 execution.

The model constists of two networks. First, a behavioral network feeding forward information from the input layter,
to the decision layer, to the response layer.
Second, a LC control mechanism projects gain to both, the behavioral layer and the response layer.

COMMENT:
Describe what the LC actually does,i.e, FHN, Euler integration,

COMMENT

Creating Nieuwenhuis et al. (2005)
----------------------------------

Import dependencies
^^^^^^^^^^^^^^^^^^^
First import PsyNeuLink as pnl and other dependencies, such as numpy, and matplotlib.
To reproduce the MATLAB code you need scipy installed and the erfinv package.
However, if you don't need to use a compatible MATLAB noise generator you don't need the erfinv package::

    >>> from matplotlib import pyplot as plt
    >>> import psyneulink as pnl
    >>> import numpy as np
    >> from scipy.special import erfinv # Only needed to reproduce MATLAB noise generator


Setting global variables, weights and initial values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# WATCH OUT !!! In the paper the weight "Mutual inhibition among response units" is not defined, but needs to be set to 0 in order to reproduce the paper.


SD = 0.15       # noise determined by standard deviation (SD)
a = 0.50        # Parameter describing shape of the FitzHugh–Nagumo cubic nullcline for the fast excitation variable v
d = 0.5         # Uncorrelated Activity
k = 1.5         # Scaling factor for transforming NE release (u ) to gain (g ) on potentiated units
G = 0.5         # Base level of gain applied to decision and response units
dt = 0.02       # time step size
C = 0.90        # LC coherence (see Gilzenrat et al. (2002) on more details on LC coherence

initial_hv = 0.07                     # Initial value for h(v)
initial_w = 0.14                      # initial value u
initial_v = (initial_hv - (1-C)*d)/C  # get initial v from initial h(v)

# Weights:
inpwt = 1.5       # inpwt (Input to decision layer)
crswt = 1/3       # crswt (Crosstalk input to decision layer)
inhwt = 1.0       # inhwt (Mutual inhibition among decision units)
respinhwt = 0.0     # respinhwt (Mutual inhibition among response units)  !!! WATCH OUT: this parameter is not mentioned in the original paper, most likely since it was set 0
decwt = 3.5       # decwt (Target decision unit to response unit)
selfdwt = 2.5     # selfdwt (Self recurrent conn. for each decision unit)
selfrwt = 2.0     # selfrwt (Self recurrent conn. for response unit)
lcwt = 0.3        # lcwt (Target decision unit to LC)
decbias = 1.75    # decbias (Bias input to decision units)
respbias = 1.75   # respbias (Bias input to response units)
tau_v = 0.05    # Time constant for fast LC excitation variable v | NOTE: tau_v is misstated in the Gilzenrat paper(0.5)
tau_u = 5.00    # Time constant for slow LC recovery variable (‘NE release’) u
trials = 1100   # number of trials for one execution of the model to reproduce Figure 3 from Nieuwenhuis et al. (2005)


Set up Behavioral Network
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The behavioral network has 3 layers, i.e. INPUT LAYER, DECISION LAYER, and RESPONSE LAYER.
So how do we set up this network?
We define the input layer with TransferMechansim of size 3, and since the default function of the
TransferMechansim is a Linear function with the default slope set to 1.0 and the intercept set to 0.0,
the TransferMechanism's output state will be the same as it's input state.

COMMENT:
correct and implement this when logging works
If your curious and want to have a look what the RESULT values in this input_layer are,
simply type input_layer.log_items("RESULTS") after you created the input layer.

COMMENT

This is how you implement the INPUT LAYER:
Example:
    >>> input_layer = pnl.TransferMechanism(size = 3,               # Number of units in input layer
    ...                             initial_value= [[0.0,0.0,0.0]],  # Initial input values
    ...                             name='INPUT LAYER')              # Define the name of the layer; this is optional,
    ...                                                             # but will help you to overview your model later on

The next line of code will already be the implementation of the DECISION LAYER:
This layer needs a different mechanism. Here, each element is connected to every other element with mutually inhibitory
weights, and self-excitation weights. We take us of the `LCA` mechanism, and set the parameters to the ones in the
paper. Note that by default, <initial_values> is set to 0.0, so setting them here is not necessary. Leak is -1 since the
elements inhibit each other.
Example:
    >>> decision_layer = pnl.LCA(size=3,                   # Number of units in input layer
    ...                  initial_value= [[0.0,0.0,0.0]],    # Initial input values
    ...                  time_step_size=dt,                 # Integration step size
    ...                  leak=-1.0,                         # Sets off diagonals to negative values
    ...                  self_excitation=selfdwt,           # Set diagonals to self excitate
    ...                  competition=inhwt,                 # Set off diagonals to inhibit
    ...                  function=pnl.Logistic(bias=decbias),   # Set the Logistic function with bias = decbias
    ...                  noise=UniformToNormalDist(standard_dev = SD).function, # Set noise with seed generator compatible with MATLAB random seed generator 22 (rsg=22)
    ...                  integrator_mode=True,                                           # Please see https://github.com/jonasrauber/randn-matlab-python for further documentation
    ...                  name='DECISION LAYER')

The final step is to implement the RESPONSE LAYER:
The RESPONSE LAYER behaves the same way at the DECISION LAYER. So we take us of the `LCA` mechanism again and set the parameters.
Example:
    >>> response_layer = pnl.LCA(size=2,                   # Number of units in input layer
    ...                  initial_value= [[0.0,0.0]],        # Initial input values
    ...                  time_step_size=dt,                 # Integration step size
    ...                  leak=-1.0,                         # Sets off diagonals to negative values
    ...                  self_excitation=selfrwt,           # Set diagonals to self excitate
    ...                  competition=respinhwt,             # Set off diagonals to inhibit
    ...                  function=pnl.Logistic(bias=respbias),    # Set the Logistic function with bias = decbias
    ...                  noise=UniformToNormalDist(standard_dev = SD).function, # Set noise with seed generator compatible with MATLAB random seed generator 22 (rsg=22)
    ...                  integrator_mode=True,                                         # Please see https://github.com/jonasrauber/randn-matlab-python for further documentation
    ...                  name='RESPONSE LAYER')


So far we created 3 layers, let's connect them!

Set up weight matrices
^^^^^^^^^^^^^^^^^^^^^^
We need 2 weight matrices that connect the 3 behavioral layers.
To implement the first weight matrix from Input Layer to the DECISION LAYER, we simply create a numpy array with the rows
having the size of the INPUT LAYER and the columns having the size of the decision layer.
Example:
    >>> input_weights = np.array([[inpwt, crswt, crswt], # Input weights are diagonals, cross weights are off diagonals
    ...                          [crswt, inpwt, crswt],
    ...                          [crswt, crswt, inpwt]])

Then we set the second weight matrix from the DECISION LAYER to the RESPONSE LAYER.
Note that the distraction unit has no connection from the DECISION LAYER,
hence both weights of the 3rd row are set to 0.
Example:
    >>> output_weights = np.array([[decwt, 0.0],                            # Projection weight from decision layer from T1 and T2 but not distraction unit (row 3 set to all zeros) to response layer
    ...                           [0.0, decwt],                            # Need a 3 by 2 matrix, to project from decision layer with 3 units to response layer with 2 units
    ...                           [0.0, 0.0]])


So far we still haven't connected the layers and the weights. This will be

Connect behavioral network mechanisms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We will connect the layers and weights in the order we want them to be connected creating a `Process` and
constructing a <pathway>.
Example:
    >>> decision_process = pnl.Process(pathway=[input_layer,
    ...                                     input_weights,
    ...                                     decision_layer,
    ...                                     output_weights,
    ...                                     response_layer],
    ...                            name='DECISION PROCESS')

Now the behavioral network is set up.

Let's connect the LC to the DECISION LAYER and the RESPONSE LAYER.

LC implementation
^^^^^^^^^^^^^^^^^

This LCControlMechanism projects a gain control signal to the DECISION LAYER and the RESPONSE LAYER.
Example:
    >>> LC = pnl.LCControlMechanism(integration_method="EULER",             # Set the integration method to Euler like in the paper
    ...                         threshold_FHN=a,                            # Here we use the Euler method for integration and we want to set the parameters,
    ...                         uncorrelated_activity_FHN=d,                # for the FitzHugh–Nagumo system.
    ...                         time_step_size_FHN=dt,
    ...                         mode_FHN=C,
    ...                         time_constant_v_FHN=tau_v,
    ...                         time_constant_w_FHN=tau_u,
    ...                         a_v_FHN=-1.0,
    ...                         b_v_FHN=1.0,
    ...                         c_v_FHN=1.0,
    ...                         d_v_FHN=0.0,
    ...                         e_v_FHN=-1.0,
    ...                         f_v_FHN=1.0,
    ...                         a_w_FHN=1.0,
    ...                         b_w_FHN=-1.0,
    ...                         c_w_FHN=0.0,
    ...                         t_0_FHN=0.0,
    ...                         base_level_gain=G,        # Additionally, we set the parameters k and
    ...                         scaling_factor_gain=k,    # G to compute the gain function in the paper
    ...                         initial_v_FHN=initial_v,  # Initialize v
    ...                         initial_w_FHN=initial_w,  # Initialize w
    ...                         objective_mechanism= pnl.ObjectiveMechanism(function=pnl.Linear,
    ...                             monitored_output_states=[(decision_layer, # Project the output of T1 and T2 but
    ...#  not the distraction unit of the decision layer to the LC with a linear function.
    ...                             np.array([[lcwt],[lcwt],[0.0]]))],
    ...                             name='Combine values'),
    ...                         modulated_mechanisms=[decision_layer, response_layer],  # Modulate gain of decision &
    ...#  response layers
    ...                         name='LC') # Set the <name> of the LCControlMechanism

System
^^^^^^
Finally, we create a the model in a system calling the processes
(here just one process - the decision_process -  is called).
Example:
    >>> task = pnl.System(processes=[decision_process])


COMMENT:
Update this with new log version:
After you run the System, type input_layer.log.nparray() to see the logged values.

COMMENT

Creating Stimulus
^^^^^^^^^^^^^^^^^

In the paper, each period has 100 time steps, so we will create 11 time periods, with 100 time steps each. During the
first 3 time periods the distractor unit gets an input of 1. Then T1 gets turned on during time period 4 with an input
of 1. In this example T2 gets turns on with a lag of 2 time periods after T1 onset. Between T1 and T2 and after T2 the
distractor unit is on. There are many ways to implement this time series of stimuli. We create one array with 3 numbers,
one for each input unit and repeat this array 100 times for one time period. We do this 11 times. T1 is set to 1 for
time4, T2 is set to 1 for time7 to model Lag 2.
Example:
    >>> stepSize = 100  # Each stimulus is presented for two units of time which is equivalent to 100 time steps
    ... time1 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time2 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time3 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time4 = np.repeat(np.array([[1,0,0]]), stepSize,axis =0)    # Turn T1 on
    ... time5 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time6 = np.repeat(np.array([[0,1,0]]), stepSize,axis =0)    # Turn T2 on --> example for Lag 2
    ... time7 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time8 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time9 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time10 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
    ... time11 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)

Concatenate the 11 arrays to one array with 1100 rows and 3 colons.
Example:
    >>> time = np.concatenate((time1, time2, time3, time4, time5, time6, time7, time8, time9, time10, time11), axis = 0)

Assign inputs to input_layer (Origin Mechanism) for each trial
    >>> stim_list_dict = {input_layer:time}

Run model
^^^^^^^^^

Example:
    >>> task.run(stim_list_dict, num_trials= 1)


COMMENT:

log nparray here

Implement plotting in PsyNeuLink
COMMENT

COMMENT:

Plotting the results
^^^^^^^^^^^^^^^^^^^^
Plot figure for Nieuwenhuis et al. 2005 paper with Lag 2 -------------------------------------------

# x = np.linspace(0.0, len(LC_results_v), len(LC_results_v))     # Create array for x axis with same length then LC_results_v
# fig = plt.figure()                                             # Instantiate figure
# ax = plt.gca()                                                 # Get current axis for plotting
# ax2 = ax.twinx()                                               # Create twin axis to have a different y-axis on the right hand side of the figure
# ax.plot(x, LC_results_v, label="h(v)")                         # Plot h(v)
# ax2.plot(x, LC_results_w, label="w", color = 'red')            # Plot w
# h1, l1 = ax.get_legend_handles_labels()
# h2, l2 = ax2.get_legend_handles_labels()
# ax.legend(h1 + h2, l1 + l2, loc=2)                             # Create legend on one side
# # ax.plot(x, decision_layer_target, label="target")            # Uncomment these to plot decision units and response units
# # ax.plot(x, decision_layer_target2, label="target2")
# # ax.plot(x,decision_layer_distraction, label="distraction")
# # ax.plot(x, response, label="response")
# # ax.plot(x, response2, label="response2")
# ax.set_xlabel('time')                                          # Set x axis lable
# ax.set_ylabel('Activation h(v)')                               # Set left y axis label
# ax2.set_ylabel('Activation w')                                 # Set right y axis label
# plt.title('Nieuwenhuis 2005 PsyNeuLink Lag 2', fontweight='bold')   # Set title
# ax.set_ylim((-0.2,1.0))                                        # Set left y axis limits
# ax2.set_ylim((0.0, 0.4))                                       # Set right y axis limits
# plt.show()                                                     # Show the plot

COMMENT

This displays a diagram of the System
Example:
    >>> task.show_graph()


"""


#WATCH OUT: clear_registry() is still missing in the documentations. PLease add
# def clear_registry():
#     # Clear Registry to have a stable reference for indexed suffixes of default names
#     from psyneulink.components.component import DeferredInitRegistry
#     from psyneulink.components.mechanisms.mechanism import MechanismRegistry
#     from psyneulink.components.projections.projection import ProjectionRegistry
#     pnl.clear_registry(DeferredInitRegistry)
#     pnl.clear_registry(MechanismRegistry)
#     psyneulink.clear_registry(ProjectionRegistry)
#
#
# pnl.clear_registry()


# First, we have ti import all dependencies.
# Note: Please import matplotlib before importing any psyneulink dependencies.
from matplotlib import pyplot as plt
import sys
import numpy as np
# from scipy.special import erfinv


from psyneulink.components.functions.function import UniformToNormalDist
import psyneulink as pnl

# --------------------------------- Global Variables ----------------------------------------
# Now, we set the global variables, weights and initial values as in the paper.
# WATCH OUT !!! In the paper the weight "Mutual inhibition among response units" is not defined, but needs to be set to 0 in order to reproduce the paper.


SD = 0.15       # noise determined by standard deviation (SD)
a = 0.50        # Parameter describing shape of the FitzHugh–Nagumo cubic nullcline for the fast excitation variable v
d = 0.5         # Uncorrelated Activity
k = 1.5         # Scaling factor for transforming NE release (u ) to gain (g ) on potentiated units
G = 0.5         # Base level of gain applied to decision and response units
dt = 0.02       # time step size
C = 0.90        # LC coherence (see Gilzenrat et al. (2002) on more details on LC coherence

initial_hv = 0.07                     # Initial value for h(v)
initial_w = 0.14                      # initial value u
initial_v = (initial_hv - (1-C)*d)/C  # get initial v from initial h(v)

# Weights:
inpwt = 1.5       # inpwt (Input to decision layer)
crswt = 1/3       # crswt (Crosstalk input to decision layer)
inhwt = 1.0       # inhwt (Mutual inhibition among decision units)
respinhwt = 0     # respinhwt (Mutual inhibition among response units)  !!! WATCH OUT: this parameter is not mentioned in the original paper, most likely since it was set 0
decwt = 3.5       # decwt (Target decision unit to response unit)
selfdwt = 2.5     # selfdwt (Self recurrent conn. for each decision unit)
selfrwt = 2.0     # selfrwt (Self recurrent conn. for response unit)
lcwt = 0.3        # lcwt (Target decision unit to LC)
decbias = 1.75    # decbias (Bias input to decision units)
respbias = 1.75   # respbias (Bias input to response units)
tau_v = 0.05    # Time constant for fast LC excitation variable v | NOTE: tau_v is misstated in the Gilzenrat paper(0.5)
tau_u = 5.00    # Time constant for slow LC recovery variable (‘NE release’) u
trials = 1100   # number of trials to reproduce Figure 3 from Nieuwenhuis et al. (2005)

# Create mechanisms ---------------------------------------------------------------------------------------------------

# Input Layer --- [ Target 1, Target 2, Distractor ]

# First, we create the 3 layers of the behavioral network, i.e. INPUT LAYER, DECISION LAYER, and RESPONSE LAYER.
# To do that, we define the input layer with TransferMEchansim of size 3.
# Since the default function of the TransferMechansim is set to be Linear with default slope set to 1.0 and intercept
# set to 0.0, this TransferMechanism will take the input pattern as they are set to with no further manipulation.
# If your curious and want to have a look what the RESULT values in this input_layer are,
# simply type input_layer.log_items("RESULTS") after you created the input layer.
# After you run the System, type input_layer.log.nparray() to see the logged values.

input_layer = pnl.TransferMechanism(size = 3,                       # Number of units in input layer
                                initial_value= [[0.0,0.0,0.0]],     # Initial input values
                                name='INPUT LAYER')                 # Define the name of the layer; this is optional,
                                                                    # but will help you to overview your model later on

# Create Decision Layer  --- [ Target 1, Target 2, Distractor ]

# The decision layer from the paper requires an integrator function, a self recurrent connections for each unit,
# and mutually inhibitory connections to each other unit.
# The LCA mechanism implemented in PsyNeuLink can be set up the same way as equation (3) in the appendix of the paper.

decision_layer = pnl.LCA(size=3,                            # Number of units in input layer
                     initial_value= [[0.0,0.0,0.0]],    # Initial input values
                     time_step_size=dt,                 # Integration step size
                     leak=-1.0,                         # Sets off diagonals to negative values
                     self_excitation=selfdwt,           # Set diagonals to self excitate
                     competition=inhwt,                 # Set off diagonals to inhibit
                     function=pnl.Logistic(bias=decbias),   # Set the Logistic function with bias = decbias
                     noise=UniformToNormalDist(standard_dev = SD).function, # Set noise with seed generator compatible with MATLAB random seed generator 22 (rsg=22)
                     integrator_mode=True,                                           # Please see https://github.com/jonasrauber/randn-matlab-python for further documentation
                     name='DECISION LAYER')

for output_state in decision_layer.output_states:
    output_state.value *= 0.0                                       # Set initial output values for decision layer to 0

# decision_layer.loggable_items
#
decision_layer.log_items("RESULT")



# Create Response Layer  --- [ Target1, Target2 ]
response_layer = pnl.LCA(size=2,                                        # Number of units in input layer
                     initial_value= [[0.0,0.0]],                    # Initial input values
                     time_step_size=dt,                             # Integration step size
                     leak=-1.0,                                     # Sets off diagonals to negative values
                     self_excitation=selfrwt,                       # Set diagonals to self excitate
                     competition=respinhwt,                         # Set off diagonals to inhibit
                     function=pnl.Logistic(bias=respbias),    # Set the Logistic function with bias = decbias
                     noise=UniformToNormalDist(standard_dev = SD).function, # Set noise with seed generator compatible with MATLAB random seed generator 22 (rsg=22)
                     integrator_mode=True,                                         # Please see https://github.com/jonasrauber/randn-matlab-python for further documentation
                     name='RESPONSE LAYER')

for output_state in response_layer.output_states:
    output_state.value *= 0.0                                       # Set initial output values for response layer to 0

# Connect mechanisms --------------------------------------------------------------------------------------------------

# Now, we create 2 weight matrices that connect the 3 behavioral layers.
# Weight matrix from Input Layer --> Decision Layer
input_weights = np.array([[inpwt, crswt, crswt],                    # Input weights are diagonals, cross weights are off diagonals
                          [crswt, inpwt, crswt],
                          [crswt, crswt, inpwt]])

# Weight matrix from Decision Layer --> Response Layer
output_weights = np.array([[decwt, 0.0],                            # Projection weight from decision layer from T1 and T2 but not distraction unit (row 3 set to all zeros) to response layer
                           [0.0, decwt],                            # Need a 3 by 2 matrix, to project from decision layer with 3 units to response layer with 2 units
                           [0.0, 0.0]])

# The process will connect the layers and weights.
decision_process = pnl.Process(pathway=[input_layer,
                                    input_weights,
                                    decision_layer,
                                    output_weights,
                                    response_layer],
                           name='DECISION PROCESS')

decision_layer.log_items('RESULT')

# Abstracted LC to modulate gain --------------------------------------------------------------------

# This LCControlMechanism modulates gain.
LC = pnl.LCControlMechanism(integration_method="EULER",                 # We set the integration method to Euler like in the paper
                        threshold_FHN=a,                            # Here we use the Euler method for integration and we want to set the parameters,
                        uncorrelated_activity_FHN=d,                # for the FitzHugh–Nagumo system.
                        time_step_size_FHN=dt,
                        mode_FHN=C,
                        time_constant_v_FHN=tau_v,
                        time_constant_w_FHN=tau_u,
                        a_v_FHN=-1.0,
                        b_v_FHN=1.0,
                        c_v_FHN=1.0,
                        d_v_FHN=0.0,
                        e_v_FHN=-1.0,
                        f_v_FHN=1.0,
                        a_w_FHN=1.0,
                        b_w_FHN=-1.0,
                        c_w_FHN=0.0,
                        t_0_FHN=0.0,
                        base_level_gain=G,                          # Additionally, we set the parameters k and G to compute the gain equation.
                        scaling_factor_gain=k,
                        initial_v_FHN=initial_v,                    # Initialize v
                        initial_w_FHN=initial_w,                    # Initialize w (WATCH OUT !!!: In the Gilzenrat paper the authors set this parameter to be u, so that one does not think about a small w as if it would represent a weight
                        objective_mechanism= pnl.ObjectiveMechanism(function=pnl.Linear,
                            monitored_output_states=[(decision_layer, # Project the output of T1 and T2 but not the distraction unit of the decision layer to the LC with a linear function.
                            np.array([[lcwt],[lcwt],[0.0]]))],
                            name='Combine values'),
                        modulated_mechanisms=[decision_layer, response_layer],  # Modulate gain of decision & response layers
                        name='LC')

# default input to objective_mechanism: [(decision_layer, np.array([[lcwt],[lcwt], [0,0]]), 1)],
LC.loggable_items
# LC.log_items('DECISION LAYER[gain] ControlSignal')
# LC.log_items('value')

for output_state in LC.output_states:
	output_state.value *= G + k*initial_w          # Set initial gain to G + k*initial_w, when the System runs the very first time, since the decison layer executes before the LC and hence needs one initial gain value to start with.





# Now, we specify the processes of the System, which in this case is just the decision_process
task = pnl.System(processes=[decision_process])

# Create Stimulus -----------------------------------------------------------------------------------------------------

# In the paper, each period has 100 time steps, so we will create 11 time periods.
# As described in the paper in figure 3, during the first 3 time periods the distractor units are given an input fixed to 1.
# Then T1 gets turned on during time period 4 with an input of 1.
# T2 gets turns on with some lag from T1 onset on, in this example we turn T2 on with Lag 2 and an input of 1
# Between T1 and T2 and after T2 the distractor unit is on.
# We create one array with 3 numbers, one for each input unit and repeat this array 100 times for one time period
# We do this 11 times. T1 is on for time4, T2 is on for time7 to model Lag3
stepSize = 100  # Each stimulus is presented for two units of time which is equivalent to 100 time steps
time1 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time2 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time3 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time4 = np.repeat(np.array([[1,0,0]]), stepSize,axis =0)    # Turn T1 on
time5 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time6 = np.repeat(np.array([[0,1,0]]), stepSize,axis =0)    # Turn T2 on --> example for Lag 2
time7 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time8 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time9 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time10 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)
time11 = np.repeat(np.array([[0,0,1]]), stepSize,axis =0)

# Concatenate the 11 arrays to one array with 1100 rows and 3 colons.
time = np.concatenate((time1, time2, time3, time4, time5, time6, time7, time8, time9, time10, time11), axis = 0)

# assign inputs to input_layer (Origin Mechanism) for each trial
stim_list_dict = {input_layer:time}

## Record results & run model ------------------------------------------------------------------------------------------

# Function to compute h(v) from LC's v value
def h_v(v,C,d):
    return C*v + (1-C)*d

# Initialize output arrays for plotting
LC_results_v = [h_v(initial_v,C,d)]
LC_results_w = [initial_w]
decision_layer_target = [0.5]
decision_layer_target2 = [0.5]
decision_layer_distraction = [0.5]
response = [0.5]
response2 = [0.5]
LC_gain = [0.5]
decision_layer_gain = [0.5]
decision_layer_output = [0.0]


# Old way:
# def record_trial():
#     LC_results_v.append(h_v(LC.value[2][0], C, d))
#     LC_results_w.append(LC.value[3][0])
#     decision_layer_target.append(decision_layer.value[0][0])
#     decision_layer_target2.append(decision_layer.value[0][1])
#     decision_layer_distraction.append(decision_layer.value[0][2])
#     response.append(response_layer.value[0][0])
#     response2.append(response_layer.value[0][1])
#     LC_gain.append(LC.value[0][0])
#     decision_layer_gain.append(decision_layer.function_object.gain)
#     decision_layer_output.append(decision_layer.output_states[0].value)
#
#     current_trial_num = len(LC_results_v)
#     if current_trial_num%50 == 0:
#         percent = int(round((float(current_trial_num) / trials)*100))
#         sys.stdout.write("\r"+ str(percent) +"% complete")
#         sys.stdout.flush()
#
# sys.stdout.write("\r0% complete")
# sys.stdout.flush()



## Run model ------------------------------------------------------------------------------------------
np.random.seed(22)


task.run(stim_list_dict, num_trials= 1)


# New way with logging:
# array = np.asarray(decision_layer.log.nparray(header=False)[1])
# z=zip(*array)
# a = list(z)
#
# x1 = a[0]
# x2 = a[1]
# x3 = a[2]


## Plot figure for Nieuwenhuis et al. 2005 paper with Lag 2 -------------------------------------------

# x = np.linspace(0.0, len(LC_results_v), len(LC_results_v))     # Create array for x axis with same length then LC_results_v
# fig = plt.figure()                                             # Instantiate figure
# ax = plt.gca()                                                 # Get current axis for plotting
# ax2 = ax.twinx()                                               # Create twin axis to have a different y-axis on the right hand side of the figure
# ax.plot(x, LC_results_v, label="h(v)")                         # Plot h(v)
# ax2.plot(x, LC_results_w, label="w", color = 'red')            # Plot w
# h1, l1 = ax.get_legend_handles_labels()
# h2, l2 = ax2.get_legend_handles_labels()
# ax.legend(h1 + h2, l1 + l2, loc=2)                             # Create legend on one side
# # ax.plot(x, decision_layer_target, label="target")            # Uncomment these to plot decision units and response units
# # ax.plot(x, decision_layer_target2, label="target2")
# # ax.plot(x,decision_layer_distraction, label="distraction")
# # ax.plot(x, response, label="response")
# # ax.plot(x, response2, label="response2")
# ax.set_xlabel('time')                                          # Set x axis lable
# ax.set_ylabel('Activation h(v)')                               # Set left y axis label
# ax2.set_ylabel('Activation w')                                 # Set right y axis label
# plt.title('Nieuwenhuis 2005 PsyNeuLink Lag 2', fontweight='bold')   # Set title
# ax.set_ylim((-0.2,1.0))                                        # Set left y axis limits
# ax2.set_ylim((0.0, 0.4))                                       # Set right y axis limits
# plt.show()                                                     # Show the plot
#
# # This displays a diagram of the System
# task.show_graph()

