import functools
import numpy as np
import psyneulink as pnl
import psyneulink.core.components.functions.distributionfunctions
import pytest
import re

from psyneulink.core.components.functions.optimizationfunctions import OptimizationFunctionError
from psyneulink.core.globals.sampleiterator import SampleIterator, SampleIteratorError, SampleSpec
from psyneulink.core.globals.keywords import ALLOCATION_SAMPLES, PROJECTIONS

class TestControlSpecification:
    # These test the coordination of adding a node with a control specification to a Composition
    #    with adding a controller that may also specify control of that node.
    # Principles:
    #    1) there should be no redundant ControlSignals or ControlProjections created;
    #    2) specification of control in controller supercedes any conflicting specification on a node;
    #    3) order of addition to the composition does not matter (i.e., Principle 2 always applies)

    # FIX: OUTSTANDING ISSUES -
    #      When control is specified in a controller for a Mechanism that is not yet a node in the Composition
    #          it neverhtless gets activated (in call to controller._activate_projections_for_compositions;
    #          instead, it should either be put in deferred_init or added to node's aux_components attribute

    def test_add_node_with_control_specified_then_add_controller(self):
        # First add Mechanism with control specification to Composition,
        #    then add controller with NO control specification to Composition
        # ControlProjection specified on Mechanism should initially be in deferred_init,
        #    but then initialized and added to controller when the Mechanism is added.
        ddm = pnl.DDM(function=pnl.DriftDiffusionAnalytical(
                                drift_rate=(1.0,
                                            pnl.ControlProjection(
                                                  function=pnl.Linear,
                                                  control_signal_params={ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}))))
        ctl_mech = pnl.ControlMechanism()
        comp = pnl.Composition()
        comp.add_node(ddm)
        comp.add_controller(ctl_mech)
        assert ddm.parameter_ports['drift_rate'].mod_afferents[0].sender.owner == comp.controller
        assert comp.controller.control_signals[0].efferents[0].receiver == ddm.parameter_ports['drift_rate']
        assert np.allclose(comp.controller.control[0].allocation_samples(),
                           [0.1, 0.4, 0.7000000000000001, 1.0000000000000002])

    def test_add_controller_in_comp_constructor_then_add_node_with_control_specified(self):
        # First create Composition with controller that has NO control specification,
        #    then add Mechanism with control specification to Composition;
        # ControlProjection specified on Mechanism should initially be in deferred_init,
        #    but then initialized and added to controller when the Mechanism is added.
        ddm = pnl.DDM(function=pnl.DriftDiffusionAnalytical(
                                # drift_rate=(1.0,
                                #             pnl.ControlProjection(
                                #                   function=pnl.Linear,
                                #                   control_signal_params={ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}))))
                                drift_rate=(1.0,
                                            pnl.ControlSignal(allocation_samples=np.arange(0.1, 1.01, 0.3),
                                                              intensity_cost_function=pnl.Linear))))
        ctl_mech = pnl.ControlMechanism()
        comp = pnl.Composition(controller=ctl_mech)
        comp.add_node(ddm)
        assert comp.controller.control[0].efferents[0].receiver == ddm.parameter_ports['drift_rate']
        assert ddm.parameter_ports['drift_rate'].mod_afferents[0].sender.owner == comp.controller
        assert np.allclose(comp.controller.control[0].allocation_samples(),
                           [0.1, 0.4, 0.7000000000000001, 1.0000000000000002])

    def test_redundant_control_spec_add_node_with_control_specified_then_controller_in_comp_constructor(self):
        # First add Mechanism with control specification to Composition,
        #    then add controller WITH redundant control specification to Composition
        # Control specification on controller should replace one on Mechanism
        ddm = pnl.DDM(function=pnl.DriftDiffusionAnalytical(
                                drift_rate=(1.0,
                                            pnl.ControlProjection(
                                                  function=pnl.Linear,
                                                  control_signal_params={ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}))))
        comp = pnl.Composition()
        comp.add_node(ddm)
        comp.add_controller(pnl.ControlMechanism(control_signals=("drift_rate", ddm)))
        assert comp.controller.control_signals[0].efferents[0].receiver == ddm.parameter_ports['drift_rate']
        assert ddm.parameter_ports['drift_rate'].mod_afferents[0].sender.owner == comp.controller
        assert comp.controller.control_signals[0].allocation_samples is None

    def test_redundant_control_spec_add_controller_in_comp_constructor_then_add_node_with_control_specified(self):
        # First create Composition with controller that has HAS control specification,
        #    then add Mechanism with control specification to Composition;
        # Control specification on controller should supercede one on Mechanism (which should be ignored)
        ddm = pnl.DDM(function=pnl.DriftDiffusionAnalytical(
                                drift_rate=(1.0,
                                            pnl.ControlProjection(
                                                  function=pnl.Linear,
                                                  control_signal_params={ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}))))
        comp = pnl.Composition(controller=pnl.ControlMechanism(control_signals=("drift_rate", ddm)))
        comp.add_node(ddm)
        assert comp.controller.control_signals[0].efferents[0].receiver == ddm.parameter_ports['drift_rate']
        assert ddm.parameter_ports['drift_rate'].mod_afferents[0].sender.owner == comp.controller
        assert comp.controller.control_signals[0].allocation_samples is None

    def test_redundant_control_spec_add_controller_in_comp_constructor_then_add_node_with_alloc_samples_specified(self):
        # First create Composition with controller that has HAS control specification,
        #    then add Mechanism with control specification to Composition;
        # Control specification on controller should supercede one on Mechanism (which should be ignored)
        ddm = pnl.DDM(function=pnl.DriftDiffusionAnalytical(
                                drift_rate=(1.0,
                                            pnl.ControlProjection(
                                                  function=pnl.Linear,
                                                  control_signal_params={ALLOCATION_SAMPLES: np.arange(0.1, 1.01,0.3)}))))
        comp = pnl.Composition(controller=pnl.ControlMechanism(control_signals={ALLOCATION_SAMPLES:np.arange(0.2,1.01, 0.3),
                                                                                PROJECTIONS:('drift_rate', ddm)}))
        comp.add_node(ddm)
        assert comp.controller.control_signals[0].efferents[0].receiver == ddm.parameter_ports['drift_rate']
        assert ddm.parameter_ports['drift_rate'].mod_afferents[0].sender.owner == comp.controller
        assert np.allclose(comp.controller.control[0].allocation_samples(), [0.2, 0.5, 0.8])

class TestControlMechanisms:

    def test_modulation_of_control_signal_intensity_cost_function_MULTIPLICATIVE(self):
        # tests multiplicative modulation of default intensity_cost_function (Exponential) of
        #    a ControlMechanism's default function (TransferWithCosts);
        #    intensity_cost should = e ^ (allocation (3) * value of ctl_mech_B (also 3)) = e^9
        mech = pnl.ProcessingMechanism()
        ctl_mech_A = pnl.ControlMechanism(monitor_for_control=mech,
                                      control_signals=pnl.ControlSignal(modulates=(pnl.INTERCEPT,mech),
                                                                        cost_options=pnl.CostFunctions.INTENSITY))
        ctl_mech_B = pnl.ControlMechanism(monitor_for_control=mech,
                                          control_signals=pnl.ControlSignal(
                                                              modulates=ctl_mech_A.control_signals[0],
                                                              modulation=pnl.INTENSITY_COST_FCT_MULTIPLICATIVE_PARAM))
        comp = pnl.Composition()
        comp.add_linear_processing_pathway(pathway=[mech,
                                                    ctl_mech_A,
                                                    ctl_mech_B
                                                    ])

        comp.run(inputs={mech:[3]}, num_trials=2)
        assert np.allclose(ctl_mech_A.control_signals[0].intensity_cost, 8103.083927575384008)

    def test_feedback_assignment_for_multiple_control_projections_to_same_mechanism(self):
        """Test that multiple ControlProjections from a ControlMechanism to the same Mechanism are treated
        same as a single Controlprojection to that Mechanism.
        Note: Even though both mech and control_mech don't receive pathway inputs, since control_mech projects to mech,
        control_mech is assigned as NodeRole.INPUT (can be overridden with assignments in add_nodes)
        """
        mech = pnl.ProcessingMechanism(input_ports=['A','B','C'])
        control_mech = pnl.ControlMechanism(control=mech.input_ports[0])
        comp = pnl.Composition()
        comp.add_nodes([mech, control_mech])
        result = comp.run(inputs={control_mech:[2]}, num_trials=3)
        # assert np.allclose(result, [[2],[2],[2]])
        assert pnl.NodeRole.INPUT not in comp.get_roles_by_node(mech)
        assert pnl.NodeRole.INPUT in comp.get_roles_by_node(control_mech)

        # Should produce same result as above
        mech = pnl.ProcessingMechanism(input_ports=['A','B','C'])
        control_mech = pnl.ControlMechanism(control=mech.input_ports) # Note multiple parallel ControlProjections
        comp = pnl.Composition()
        comp.add_nodes([mech, control_mech])
        comp.run(inputs={control_mech:[2]}, num_trials=3)
        assert pnl.NodeRole.INPUT not in comp.get_roles_by_node(mech)
        assert pnl.NodeRole.INPUT in comp.get_roles_by_node(control_mech)

    def test_modulation_of_control_signal_intensity_cost_function_ADDITIVE(self):
        # tests additive modulation of default intensity_cost_function (Exponential) of
        #    a ControlMechanism's default function (TransferWithCosts)
        #    intensity_cost should = e ^ (allocation (3) + value of ctl_mech_B (also 3)) = e^6
        mech = pnl.ProcessingMechanism()
        ctl_mech_A = pnl.ControlMechanism(monitor_for_control=mech,
                                      control_signals=pnl.ControlSignal(modulates=(pnl.INTERCEPT,mech),
                                                                        cost_options=pnl.CostFunctions.INTENSITY))
        ctl_mech_B = pnl.ControlMechanism(monitor_for_control=mech,
                                          control_signals=pnl.ControlSignal(
                                                              modulates=ctl_mech_A.control_signals[0],
                                                              modulation=pnl.INTENSITY_COST_FCT_ADDITIVE_PARAM))
        comp = pnl.Composition()
        comp.add_linear_processing_pathway(pathway=[mech,
                                                    ctl_mech_A,
                                                    ctl_mech_B
                                                    ])

        comp.run(inputs={mech:[3]}, num_trials=2)
        assert np.allclose(ctl_mech_A.control_signals[0].intensity_cost, 403.428793492735123)

    def test_lvoc(self):
        m1 = pnl.TransferMechanism(input_ports=["InputPort A", "InputPort B"])
        m2 = pnl.TransferMechanism()
        c = pnl.Composition()
        c.add_node(m1, required_roles=pnl.NodeRole.INPUT)
        c.add_node(m2, required_roles=pnl.NodeRole.INPUT)
        c._analyze_graph()
        lvoc = pnl.OptimizationControlMechanism(agent_rep=pnl.RegressionCFA,
                                                features=[m1.input_ports[0], m1.input_ports[1], m2.input_port],
                                                objective_mechanism=pnl.ObjectiveMechanism(
                                                    monitor=[m1, m2]),
                                                function=pnl.GridSearch(max_iterations=1),
                                                control_signals=[
                                                    {PROJECTIONS: (pnl.SLOPE, m1),
                                                     ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)},
                                                    {PROJECTIONS: (pnl.SLOPE, m2),
                                                     ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}])
        c.add_node(lvoc)
        input_dict = {m1: [[1], [1]], m2: [1]}

        c.run(inputs=input_dict)

        assert len(lvoc.input_ports) == 4

    def test_lvoc_both_predictors_specs(self):
        m1 = pnl.TransferMechanism(input_ports=["InputPort A", "InputPort B"])
        m2 = pnl.TransferMechanism()
        c = pnl.Composition()
        c.add_node(m1, required_roles=pnl.NodeRole.INPUT)
        c.add_node(m2, required_roles=pnl.NodeRole.INPUT)
        c._analyze_graph()
        lvoc = pnl.OptimizationControlMechanism(agent_rep=pnl.RegressionCFA,
                                                features=[m1.input_ports[0], m1.input_ports[1], m2.input_port, m2],
                                                objective_mechanism=pnl.ObjectiveMechanism(
                                                    monitor=[m1, m2]),
                                                function=pnl.GridSearch(max_iterations=1),
                                                control_signals=[
                                                    {PROJECTIONS: (pnl.SLOPE, m1),
                                                     ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)},
                                                    {PROJECTIONS: (pnl.SLOPE, m2),
                                                     ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}])
        c.add_node(lvoc)
        input_dict = {m1: [[1], [1]], m2: [1]}

        c.run(inputs=input_dict)

        assert len(lvoc.input_ports) == 5

    def test_lvoc_features_function(self):
        m1 = pnl.TransferMechanism(input_ports=["InputPort A", "InputPort B"])
        m2 = pnl.TransferMechanism()
        c = pnl.Composition()
        c.add_node(m1, required_roles=pnl.NodeRole.INPUT)
        c.add_node(m2, required_roles=pnl.NodeRole.INPUT)
        c._analyze_graph()
        lvoc = pnl.OptimizationControlMechanism(agent_rep=pnl.RegressionCFA,
                                                features=[m1.input_ports[0], m1.input_ports[1], m2.input_port, m2],
                                                feature_function=pnl.LinearCombination(offset=10.0),
                                                objective_mechanism=pnl.ObjectiveMechanism(
                                                    monitor=[m1, m2]),
                                                function=pnl.GradientOptimization(max_iterations=1),
                                                control_signals=[(pnl.SLOPE, m1), (pnl.SLOPE, m2)])
        c.add_node(lvoc)
        input_dict = {m1: [[1], [1]], m2: [1]}

        c.run(inputs=input_dict)

        assert len(lvoc.input_ports) == 5

        for i in range(1,5):
            assert lvoc.input_ports[i].function.offset == 10.0

    def test_default_lc_control_mechanism(self):
        G = 1.0
        k = 0.5
        starting_value_LC = 2.0
        user_specified_gain = 1.0

        A = pnl.TransferMechanism(function=pnl.Logistic(gain=user_specified_gain), name='A')
        B = pnl.TransferMechanism(function=pnl.Logistic(gain=user_specified_gain), name='B')
        # B.output_ports[0].value *= 0.0  # Reset after init | Doesn't matter here b/c default var = zero, no intercept

        LC = pnl.LCControlMechanism(
            modulated_mechanisms=[A, B],
            base_level_gain=G,
            scaling_factor_gain=k,
            objective_mechanism=pnl.ObjectiveMechanism(
                function=pnl.Linear,
                monitor=[B],
                name='LC ObjectiveMechanism'
            )
        )
        for output_port in LC.output_ports:
            output_port.value *= starting_value_LC

        path = [A, B, LC]
        S = pnl.Composition()
        S.add_node(A, required_roles=pnl.NodeRole.INPUT)
        S.add_linear_processing_pathway(pathway=path)
        S.add_node(LC)
        S.show_graph()
        LC.reinitialize_when = pnl.Never()

        gain_created_by_LC_output_port_1 = []
        mod_gain_assigned_to_A = []
        base_gain_assigned_to_A = []
        mod_gain_assigned_to_B = []
        base_gain_assigned_to_B = []
        A_value = []
        B_value = []
        LC_value = []

        def report_trial(system):
            gain_created_by_LC_output_port_1.append(LC.output_port.parameters.value.get(system)[0])
            mod_gain_assigned_to_A.append(A.get_mod_gain(system))
            mod_gain_assigned_to_B.append(B.get_mod_gain(system))
            base_gain_assigned_to_A.append(A.function.parameters.gain.get())
            base_gain_assigned_to_B.append(B.function.parameters.gain.get())
            A_value.append(A.parameters.value.get(system))
            B_value.append(B.parameters.value.get(system))
            LC_value.append(LC.parameters.value.get(system))

        result = S.run(inputs={A: [[1.0], [1.0], [1.0], [1.0], [1.0]]},
                      call_after_trial=functools.partial(report_trial, S))

        # (1) First value of gain in mechanisms A and B must be whatever we hardcoded for LC starting value
        assert mod_gain_assigned_to_A[0] == starting_value_LC

        # (2) _gain should always be set to user-specified value
        for i in range(5):
            assert base_gain_assigned_to_A[i] == user_specified_gain
            assert base_gain_assigned_to_B[i] == user_specified_gain

        # (3) LC output on trial n becomes gain of A and B on trial n + 1
        assert np.allclose(mod_gain_assigned_to_A[1:], gain_created_by_LC_output_port_1[0:-1])

        # (4) mechanisms A and B should always have the same gain values (b/c they are identical)
        assert np.allclose(mod_gain_assigned_to_A, mod_gain_assigned_to_B)

        # # (5) validate output of each mechanism (using original "devel" output as a benchmark)
        # expected_A_value = [np.array([[0.88079708]]),
        #                     np.array([[0.73133331]]),
        #                     np.array([[0.73162414]]),
        #                     np.array([[0.73192822]]),
        #                     np.array([[0.73224618]])]
        #
        # assert np.allclose(A_value, expected_A_value)
        #
        # expected_B_value = [np.array([[0.8534092]]),
        #                     np.array([[0.67532197]]),
        #                     np.array([[0.67562328]]),
        #                     np.array([[0.67593854]]),
        #                     np.array([[0.67626842]])]
        # assert np.allclose(B_value, expected_B_value)
        #
        # expected_LC_value = [np.array([[[1.00139776]], [[0.04375488]], [[0.00279552]], [[0.05]]]),
        #                      np.array([[[1.00287843]], [[0.08047501]], [[0.00575686]], [[0.1]]]),
        #                      np.array([[[1.00442769]], [[0.11892843]], [[0.00885538]], [[0.15]]]),
        #                      np.array([[[1.00604878]], [[0.15918152]], [[0.01209756]], [[0.2]]]),
        #                      np.array([[[1.00774507]], [[0.20129484]], [[0.01549014]], [[0.25]]])]
        # assert np.allclose(LC_value, expected_LC_value)

    # UNSTABLE OUTPUT:
    # def test_control_mechanism(self):
    #     Tx = pnl.TransferMechanism(name='Tx')
    #     Ty = pnl.TransferMechanism(name='Ty')
    #     Tz = pnl.TransferMechanism(name='Tz')
    #     C = pnl.ControlMechanism(default_variable=[1],
    #                              monitor_for_control=Ty,
    #                              control_signals=pnl.ControlSignal(modulation=pnl.OVERRIDE,
    #                                                                projections=(pnl.SLOPE, Tz)))
    #     comp = pnl.Composition()
    #     # sched = pnl.Scheduler(omp)
    #     # sched.add_condition(Tz, pnl.AllHaveRun([C]))
    #     comp.add_linear_processing_pathway([Tx, Tz])
    #     comp.add_linear_processing_pathway([Ty, C])
    #     comp._analyze_graph()
    #     comp._scheduler.add_condition(Tz, pnl.AllHaveRun(C))
    #
    #     # assert Tz.parameter_ports[pnl.SLOPE].mod_afferents[0].sender.owner == C
    #     result = comp.run(inputs={Tx: [1, 1],
    #                               Ty: [4, 4]})
    #     assert np.allclose(result, [[[4.], [4.]],
    #                                 [[4.], [4.]]])

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Multilevel GridSearch")
    @pytest.mark.parametrize("mode", ["Python"])
    def test_multilevel_ocm_gridsearch_conflicting_directions(self, mode, benchmark):
        oa = pnl.TransferMechanism(name='oa')
        ob = pnl.TransferMechanism(name='ob')
        ocomp = pnl.Composition(name='ocomp', controller_mode=pnl.BEFORE)
        ia = pnl.TransferMechanism(name='ia')
        ib = pnl.ProcessingMechanism(name='ib',
                                     function=lambda x: abs(x - 75))
        icomp = pnl.Composition(name='icomp', controller_mode=pnl.BEFORE)
        ocomp.add_node(oa, required_roles=pnl.NodeRole.INPUT)
        ocomp.add_node(ob)
        ocomp.add_node(icomp)
        icomp.add_node(ia, required_roles=pnl.NodeRole.INPUT)
        icomp.add_node(ib)
        ocomp._analyze_graph()
        icomp._analyze_graph()
        ocomp.add_projection(pnl.MappingProjection(), sender=oa, receiver=ia)
        icomp.add_projection(pnl.MappingProjection(), sender=ia, receiver=ib)
        ocomp.add_projection(pnl.MappingProjection(), sender=ib, receiver=ob)

        ocomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=ocomp,
                features=[oa.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MINIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0, stop=5.0, num=5))])
        )
        icomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=icomp,
                features=[ia.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MAXIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0, stop=5.0, num=5))])
        )
        results = ocomp.run([5], bin_execute=mode)
        assert np.allclose(results, [[50]])
        benchmark(ocomp.run, [5], bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Multilevel GridSearch")
    @pytest.mark.parametrize("mode", ["Python"])
    def test_multilevel_ocm_gridsearch_maximize(self, mode, benchmark):
        oa = pnl.TransferMechanism(name='oa')
        ob = pnl.TransferMechanism(name='ob')
        ocomp = pnl.Composition(name='ocomp', controller_mode=pnl.BEFORE)
        ia = pnl.TransferMechanism(name='ia')
        ib = pnl.ProcessingMechanism(name='ib',
                                     function=lambda x: abs(x - 75))
        icomp = pnl.Composition(name='icomp', controller_mode=pnl.BEFORE)
        ocomp.add_node(oa, required_roles=pnl.NodeRole.INPUT)
        ocomp.add_node(ob)
        ocomp.add_node(icomp)
        icomp.add_node(ia, required_roles=pnl.NodeRole.INPUT)
        icomp.add_node(ib)
        ocomp._analyze_graph()
        icomp._analyze_graph()
        ocomp.add_projection(pnl.MappingProjection(), sender=oa, receiver=ia)
        icomp.add_projection(pnl.MappingProjection(), sender=ia, receiver=ib)
        ocomp.add_projection(pnl.MappingProjection(), sender=ib, receiver=ob)

        ocomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=ocomp,
                features=[oa.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MAXIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0,
                                                                                     stop=5.0,
                                                                                     num=5))])
        )
        icomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=icomp,
                features=[ia.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MAXIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0,
                                                                                     stop=5.0,
                                                                                     num=5))])
        )
        results = ocomp.run([5], bin_execute=mode)
        assert np.allclose(results, [[70]])
        benchmark(ocomp.run, [5], bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Multilevel GridSearch")
    @pytest.mark.parametrize("mode", ["Python"])
    def test_multilevel_ocm_gridsearch_minimize(self, mode, benchmark):
        oa = pnl.TransferMechanism(name='oa')
        ob = pnl.TransferMechanism(name='ob')
        ocomp = pnl.Composition(name='ocomp', controller_mode=pnl.BEFORE)
        ia = pnl.TransferMechanism(name='ia')
        ib = pnl.ProcessingMechanism(name='ib',
                                     function=lambda x: abs(x - 70))
        icomp = pnl.Composition(name='icomp', controller_mode=pnl.BEFORE)
        ocomp.add_node(oa, required_roles=pnl.NodeRole.INPUT)
        ocomp.add_node(ob)
        ocomp.add_node(icomp)
        icomp.add_node(ia, required_roles=pnl.NodeRole.INPUT)
        icomp.add_node(ib)
        ocomp._analyze_graph()
        icomp._analyze_graph()
        ocomp.add_projection(pnl.MappingProjection(), sender=oa, receiver=ia)
        icomp.add_projection(pnl.MappingProjection(), sender=ia, receiver=ib)
        ocomp.add_projection(pnl.MappingProjection(), sender=ib, receiver=ob)

        ocomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=ocomp,
                features=[oa.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MINIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0,
                                                                                     stop=5.0,
                                                                                     num=5))])
        )
        icomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=icomp,
                features=[ia.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                ),
                function=pnl.GridSearch(direction=pnl.MINIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0,
                                                                                     stop=5.0,
                                                                                     num=5))])
        )
        results = ocomp.run([5], bin_execute=mode)
        assert np.allclose(results, [[5]])
        benchmark(ocomp.run, [5], bin_execute=mode)

    def test_two_tier_ocm(self):
        integrationConstant = 0.8  # Time Constant
        DRIFT = 0.25  # Drift Rate
        STARTING_POINT = 0.0  # Starting Point
        THRESHOLD = 0.05  # Threshold
        NOISE = 0.1  # Noise
        T0 = 0.2  # T0
        congruentWeight = 0.2

        # Task Layer: [Color, Motion] {0, 1} Mutually Exclusive
        taskLayer = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                          # size=2,
                                          function=pnl.Linear(slope=1, intercept=0),
                                          output_ports=[pnl.RESULT],
                                          name='Task Input [I1, I2]')

        # Stimulus Layer: [Color Stimulus, Motion Stimulus]
        stimulusInfo = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                             # size=2,
                                             function=pnl.Linear(slope=1, intercept=0),
                                             output_ports=[pnl.RESULT],
                                             name="Stimulus Input [S1, S2]")

        congruenceWeighting = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                                    size=2,
                                                    function=pnl.Linear(slope=congruentWeight, intercept=0),
                                                    name='Congruence * Automatic Component')

        # Activation Layer: [Color Activation, Motion Activation]
        activation = pnl.RecurrentTransferMechanism(default_variable=[[0.0, 0.0]],
                                                    function=pnl.Logistic(gain=1.0),
                                                    matrix=[[1.0, -1.0],
                                                            [-1.0, 1.0]],
                                                    integrator_mode=True,
                                                    integrator_function=pnl.AdaptiveIntegrator(
                                                        rate=integrationConstant),
                                                    initial_value=np.array([[0.0, 0.0]]),
                                                    output_ports=[pnl.RESULT],
                                                    name='Task Activations [Act1, Act2]')

        activation.set_log_conditions([pnl.RESULT, "mod_gain"])

        # Hadamard product of Activation and Stimulus Information
        nonAutomaticComponent = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                                      size=2,
                                                      function=pnl.Linear(slope=1, intercept=0),
                                                      input_ports=pnl.InputPort(combine=pnl.PRODUCT),
                                                      output_ports=[pnl.RESULT],
                                                      name='Non-Automatic Component')

        # Summation of nonAutomatic and Automatic Components
        ddmCombination = pnl.TransferMechanism(size=1,
                                               function=pnl.Linear(slope=1, intercept=0),
                                               input_ports=pnl.InputPort(combine=pnl.SUM),
                                               output_ports=[pnl.RESULT],
                                               name="Drift = Wa*(S1 + S2) + (S1*Act1 + S2*Act2)")

        decisionMaker = pnl.DDM(function=pnl.DriftDiffusionAnalytical(drift_rate=DRIFT,
                                                                      starting_point=STARTING_POINT,
                                                                      threshold=THRESHOLD,
                                                                      noise=NOISE,
                                                                      t0=T0),
                                output_ports=[pnl.DECISION_VARIABLE, pnl.RESPONSE_TIME,
                                               pnl.PROBABILITY_UPPER_THRESHOLD,
                                               pnl.PROBABILITY_LOWER_THRESHOLD],
                                name='DDM')

        weightingFunction = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                                  size=2,
                                                  function=pnl.Linear(slope=1, intercept=0),
                                                  input_ports=pnl.InputPort(combine=pnl.PRODUCT),
                                                  output_ports=[pnl.RESULT],
                                                  name='Bias')

        topCorrect = pnl.TransferMechanism(size=1,
                                           function=pnl.Linear(slope=1, intercept=0),
                                           input_ports=pnl.InputPort(combine=pnl.PRODUCT),
                                           output_ports=[pnl.RESULT],
                                           name="weightDDMInput")

        stabilityFlexibility = pnl.Composition(name='inner', controller_mode=pnl.BEFORE)

        # Linear pathway from the task input origin node to the DDM
        stabilityFlexibility.add_linear_processing_pathway(pathway=[taskLayer,
                                                                    activation,
                                                                    nonAutomaticComponent,
                                                                    ddmCombination,
                                                                    topCorrect,
                                                                    decisionMaker])

        # Linear pathway from the stimulus input origin node to the DDM
        stabilityFlexibility.add_linear_processing_pathway(pathway=[stimulusInfo,
                                                                    nonAutomaticComponent,
                                                                    ddmCombination,
                                                                    topCorrect,
                                                                    decisionMaker])

        # Linear pathway from the stimulus input origin node to the DDM with congruence
        stabilityFlexibility.add_linear_processing_pathway(pathway=[stimulusInfo,
                                                                    congruenceWeighting,
                                                                    ddmCombination,
                                                                    topCorrect,
                                                                    decisionMaker])

        stabilityFlexibility.add_linear_processing_pathway(pathway=[taskLayer,
                                                                    weightingFunction,
                                                                    topCorrect,
                                                                    decisionMaker])

        stabilityFlexibility.add_linear_processing_pathway(pathway=[stimulusInfo,
                                                                    weightingFunction,
                                                                    topCorrect,
                                                                    decisionMaker])

        stabilityFlexibility.add_controller(
            pnl.OptimizationControlMechanism(agent_rep=stabilityFlexibility,
                                             features=[taskLayer.input_port,
                                                       stimulusInfo.input_port],
                                             feature_function=pnl.Buffer(history=2),
                                             name="Controller",
                                             objective_mechanism=pnl.ObjectiveMechanism(
                                                 monitor=[(pnl.PROBABILITY_UPPER_THRESHOLD,
                                                           decisionMaker)],
                                                 function=pnl.SimpleIntegrator,
                                                 name="Controller Objective Mechanism"),
                                             function=pnl.GridSearch(),
                                             control_signals=[pnl.ControlSignal(
                                                 projections=[(pnl.GAIN, activation)],
                                                 function=pnl.Linear,
                                                 variable=1.0,
                                                 intensity_cost_function=pnl.Linear(
                                                     slope=0.0),
                                                 allocation_samples=pnl.SampleSpec(
                                                     start=1.0,
                                                     stop=5.0,
                                                     num=2))]
                                             )
        )
        outerComposition = pnl.Composition(name='outer',
                                           controller_mode=pnl.AFTER,
                                           retain_old_simulation_data=True)
        outerComposition.add_node(stabilityFlexibility)
        outerComposition.add_controller(
            pnl.OptimizationControlMechanism(agent_rep=stabilityFlexibility,
                                             features=[taskLayer.input_port, stimulusInfo.input_port],
                                             feature_function=pnl.Buffer(history=2),
                                             name="OuterController",
                                             objective_mechanism=pnl.ObjectiveMechanism(
                                                 monitor=[(pnl.PROBABILITY_UPPER_THRESHOLD, decisionMaker)],
                                                 function=pnl.SimpleIntegrator,
                                                 name="Controller Objective Mechanism"),
                                             function=pnl.GridSearch(),
                                             control_signals=[
                                                 pnl.ControlSignal(
                                                     projections=[(pnl.THRESHOLD, decisionMaker)],
                                                     function=pnl.Linear,
                                                     variable=1.0,
                                                     intensity_cost_function=pnl.Linear(
                                                         slope=0.0),
                                                     allocation_samples=pnl.SampleSpec(
                                                         start=0.5,
                                                         stop=2.0,
                                                         num=3))
                                             ])
        )
        taskTrain = [[0, 1], [0, 1], [0, 1]]
        stimulusTrain = [[1, -1], [1, -1], [1, -1]]
        zipTrain = list(zip(taskTrain, stimulusTrain))
        outerComposition.run(zipTrain)
        assert np.allclose(outerComposition.results,
                           [[[0.05], [0.42357798], [0.76941918], [0.23058082]],
                            [[0.1], [0.64721378], [0.98737278], [0.01262722]],
                            [[0.1], [0.60232676], [0.9925894], [0.0074106]]])

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Multilevel")
    @pytest.mark.parametrize("mode", ["Python",
                                      pytest.param("LLVM", marks=pytest.mark.llvm),
                                      pytest.param("LLVMExec", marks=pytest.mark.llvm),
                                      pytest.param("LLVMRun", marks=pytest.mark.llvm),
                                     ])
    def test_multilevel_control(self, mode, benchmark):
        oA = pnl.TransferMechanism(
            name='OuterA',
        )
        oB = pnl.TransferMechanism(
            name='OuterB',
        )
        iA = pnl.TransferMechanism(
            name='InnerA',
        )
        iB = pnl.TransferMechanism(
            name='InnerB',
        )
        iComp = pnl.Composition(name='InnerComp')
        iComp.add_node(iA)
        iComp.add_node(iB)
        iComp.add_projection(pnl.MappingProjection(), iA, iB)
        oComp = pnl.Composition(name='OuterComp')
        oComp.add_node(oA)
        oComp.add_node(oB)
        oComp.add_node(iComp)
        oComp.add_projection(pnl.MappingProjection(), oA, iComp)
        oComp.add_projection(pnl.MappingProjection(), iB, oB)
        oController = pnl.ControlMechanism(
            name='Outer Controller',
            control_signals=[
                pnl.ControlSignal(
                    name='ControllerTransfer',
                    function=pnl.Linear(slope=2),
                    modulates=(pnl.SLOPE, iA),
                )
            ],
        )
        oComp.add_controller(oController)
        assert oComp.controller == oController
        iController = pnl.ControlMechanism(
            name='Inner Controller',
            control_signals=[
                pnl.ControlSignal(
                    name='ControllerTransfer',
                    function=pnl.Linear(slope=4),
                    modulates=(pnl.SLOPE, iB)
                )
            ],
        )
        iComp.add_controller(iController)
        assert iComp.controller == iController
        assert oComp.controller == oController
        res = oComp.run(inputs=[5], bin_execute=mode)
        assert np.allclose(res, [40])
        benchmark(oComp.run, [5], bin_execute=mode)

class TestModelBasedOptimizationControlMechanisms:

    def test_evc(self):
        # Mechanisms
        Input = pnl.TransferMechanism(name='Input')
        reward = pnl.TransferMechanism(output_ports=[pnl.RESULT, pnl.MEAN, pnl.VARIANCE],
                                       name='reward')
        Decision = pnl.DDM(function=pnl.DriftDiffusionAnalytical(drift_rate=(1.0,
                                                                             pnl.ControlProjection(function=pnl.Linear,
                                                                                                   control_signal_params={pnl.ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)})),
                                                                 threshold=(1.0,
                                                                            pnl.ControlProjection(function=pnl.Linear,
                                                                                                  control_signal_params={pnl.ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)})),
                                                                 noise=0.5,
                                                                 starting_point=0,
                                                                 t0=0.45),
                           output_ports=[pnl.DECISION_VARIABLE,
                                        pnl.RESPONSE_TIME,
                                        pnl.PROBABILITY_UPPER_THRESHOLD],
                           name='Decision')

        comp = pnl.Composition(name="evc", retain_old_simulation_data=True)
        comp.add_node(reward, required_roles=[pnl.NodeRole.OUTPUT])
        comp.add_node(Decision, required_roles=[pnl.NodeRole.OUTPUT])
        task_execution_pathway = [Input, pnl.IDENTITY_MATRIX, Decision]
        comp.add_linear_processing_pathway(task_execution_pathway)

        comp.add_controller(controller=pnl.OptimizationControlMechanism(
                                                agent_rep=comp,
                                                features=[Input.input_port, reward.input_port],
                                                feature_function=pnl.AdaptiveIntegrator(rate=0.5),
                                                objective_mechanism=pnl.ObjectiveMechanism(
                                                        function=pnl.LinearCombination(operation=pnl.PRODUCT),
                                                        monitor=[reward,
                                                                 Decision.output_ports[pnl.PROBABILITY_UPPER_THRESHOLD],
                                                                 (Decision.output_ports[pnl.RESPONSE_TIME], -1, 1)]),
                                                function=pnl.GridSearch(),
                                                control_signals=[{PROJECTIONS: ("drift_rate", Decision),
                                                                  ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)},
                                                                 {PROJECTIONS: ("threshold", Decision),
                                                                  ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)}])
                                       )

        comp.enable_controller = True

        comp._analyze_graph()

        stim_list_dict = {
            Input: [0.5, 0.123],
            reward: [20, 20]
        }

        comp.run(inputs=stim_list_dict)

        # Note: Removed decision variable OutputPort from simulation results because sign is chosen randomly
        expected_sim_results_array = [
            [[10.], [10.0], [0.0], [0.48999867], [0.50499983]],
            [[10.], [10.0], [0.0], [1.08965888], [0.51998934]],
            [[10.], [10.0], [0.0], [2.40680493], [0.53494295]],
            [[10.], [10.0], [0.0], [4.43671978], [0.549834]],
            [[10.], [10.0], [0.0], [0.48997868], [0.51998934]],
            [[10.], [10.0], [0.0], [1.08459402], [0.57932425]],
            [[10.], [10.0], [0.0], [2.36033556], [0.63645254]],
            [[10.], [10.0], [0.0], [4.24948962], [0.68997448]],
            [[10.], [10.0], [0.0], [0.48993479], [0.53494295]],
            [[10.], [10.0], [0.0], [1.07378304], [0.63645254]],
            [[10.], [10.0], [0.0], [2.26686573], [0.72710822]],
            [[10.], [10.0], [0.0], [3.90353015], [0.80218389]],
            [[10.], [10.0], [0.0], [0.4898672], [0.549834]],
            [[10.], [10.0], [0.0], [1.05791834], [0.68997448]],
            [[10.], [10.0], [0.0], [2.14222978], [0.80218389]],
            [[10.], [10.0], [0.0], [3.49637662], [0.88079708]],
            [[15.], [15.0], [0.0], [0.48999926], [0.50372993]],
            [[15.], [15.0], [0.0], [1.08981011], [0.51491557]],
            [[15.], [15.0], [0.0], [2.40822035], [0.52608629]],
            [[15.], [15.0], [0.0], [4.44259627], [0.53723096]],
            [[15.], [15.0], [0.0], [0.48998813], [0.51491557]],
            [[15.], [15.0], [0.0], [1.0869779], [0.55939819]],
            [[15.], [15.0], [0.0], [2.38198336], [0.60294711]],
            [[15.], [15.0], [0.0], [4.33535807], [0.64492386]],
            [[15.], [15.0], [0.0], [0.48996368], [0.52608629]],
            [[15.], [15.0], [0.0], [1.08085171], [0.60294711]],
            [[15.], [15.0], [0.0], [2.32712843], [0.67504223]],
            [[15.], [15.0], [0.0], [4.1221271], [0.7396981]],
            [[15.], [15.0], [0.0], [0.48992596], [0.53723096]],
            [[15.], [15.0], [0.0], [1.07165729], [0.64492386]],
            [[15.], [15.0], [0.0], [2.24934228], [0.7396981]],
            [[15.], [15.0], [0.0], [3.84279648], [0.81637827]]
        ]

        for simulation in range(len(expected_sim_results_array)):
            assert np.allclose(expected_sim_results_array[simulation],
                               # Note: Skip decision variable OutputPort
                               comp.simulation_results[simulation][0:3] + comp.simulation_results[simulation][4:6])

        expected_results_array = [
            [[20.0], [20.0], [0.0], [1.0], [2.378055160151634], [0.9820137900379085]],
            [[20.0], [20.0], [0.0], [0.1], [0.48999967725112503], [0.5024599801509442]]
        ]

        for trial in range(len(expected_results_array)):
            np.testing.assert_allclose(comp.results[trial], expected_results_array[trial], atol=1e-08, err_msg='Failed on expected_output[{0}]'.format(trial))

    def test_evc_gratton(self):
        # Stimulus Mechanisms
        target_stim = pnl.TransferMechanism(name='Target Stimulus',
                                            function=pnl.Linear(slope=0.3324))
        flanker_stim = pnl.TransferMechanism(name='Flanker Stimulus',
                                             function=pnl.Linear(slope=0.3545221843))

        # Processing Mechanisms (Control)
        Target_Rep = pnl.TransferMechanism(name='Target Representation')
        Flanker_Rep = pnl.TransferMechanism(name='Flanker Representation')

        # Processing Mechanism (Automatic)
        Automatic_Component = pnl.TransferMechanism(name='Automatic Component')

        # Decision Mechanism
        Decision = pnl.DDM(name='Decision',
                           function=pnl.DriftDiffusionAnalytical(drift_rate=(1.0),
                                                                 threshold=(0.2645),
                                                                 noise=(0.5),
                                                                 starting_point=(0),
                                                                 t0=0.15),
                           output_ports=[pnl.DECISION_VARIABLE,
                                          pnl.RESPONSE_TIME,
                                          pnl.PROBABILITY_UPPER_THRESHOLD]
                           )

        # Outcome Mechanism
        reward = pnl.TransferMechanism(name='reward')

        # Pathways
        target_control_pathway = [target_stim, Target_Rep, Decision]
        flanker_control_pathway = [flanker_stim, Flanker_Rep, Decision]
        target_automatic_pathway = [target_stim, Automatic_Component, Decision]
        flanker_automatic_pathway = [flanker_stim, Automatic_Component, Decision]
        pathways = [target_control_pathway, flanker_control_pathway, target_automatic_pathway,
                    flanker_automatic_pathway]

        # Composition
        evc_gratton = pnl.Composition(name="EVCGratton")
        evc_gratton.add_node(Decision, required_roles=pnl.NodeRole.OUTPUT)
        for path in pathways:
            evc_gratton.add_linear_processing_pathway(path)
        evc_gratton.add_node(reward, required_roles=pnl.NodeRole.OUTPUT)

        # Control Signals
        signalSearchRange = pnl.SampleSpec(start=1.0, stop=1.8, step=0.2)

        target_rep_control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, Target_Rep)],
                                                      function=pnl.Linear,
                                                      variable=1.0,
                                                      intensity_cost_function=pnl.Exponential(rate=0.8046),
                                                      allocation_samples=signalSearchRange)

        flanker_rep_control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, Flanker_Rep)],
                                                       function=pnl.Linear,
                                                       variable=1.0,
                                                       intensity_cost_function=pnl.Exponential(rate=0.8046),
                                                       allocation_samples=signalSearchRange)

        objective_mech = pnl.ObjectiveMechanism(function=pnl.LinearCombination(operation=pnl.PRODUCT),
                                                monitor=[reward,
                                                                         (Decision.output_ports[
                                                                              pnl.PROBABILITY_UPPER_THRESHOLD], 1, -1)])
        # Model Based OCM (formerly controller)
        evc_gratton.add_controller(controller=pnl.OptimizationControlMechanism(agent_rep=evc_gratton,
                                                                                         features=[target_stim.input_port,
                                                                                                   flanker_stim.input_port,
                                                                                                   reward.input_port],
                                                                                         feature_function=pnl.AdaptiveIntegrator(
                                                                                             rate=1.0),
                                                                                         objective_mechanism=objective_mech,
                                                                                         function=pnl.GridSearch(),
                                                                                         control_signals=[
                                                                                             target_rep_control_signal,
                                                                                             flanker_rep_control_signal]))
        evc_gratton.enable_controller = True

        targetFeatures = [1, 1, 1]
        flankerFeatures = [1, -1, 1]
        rewardValues = [100, 100, 100]

        stim_list_dict = {target_stim: targetFeatures,
                          flanker_stim: flankerFeatures,
                          reward: rewardValues}

        evc_gratton.run(inputs=stim_list_dict)

        expected_results_array = [[[0.32257752863413636], [0.9481940753514433], [100.]],
                                  [[0.42963678062444666], [0.47661180945923376], [100.]],
                                  [[0.300291026852769], [0.97089165101931], [100.]]]

        expected_sim_results_array = [
            [[0.32257753], [0.94819408], [100.]],
            [[0.31663196], [0.95508757], [100.]],
            [[0.31093566], [0.96110142], [100.]],
            [[0.30548947], [0.96633839], [100.]],
            [[0.30029103], [0.97089165], [100.]],
            [[0.3169957], [0.95468427], [100.]],
            [[0.31128378], [0.9607499], [100.]],
            [[0.30582202], [0.96603252], [100.]],
            [[0.30060824], [0.9706259], [100.]],
            [[0.29563774], [0.97461444], [100.]],
            [[0.31163288], [0.96039533], [100.]],
            [[0.30615555], [0.96572397], [100.]],
            [[0.30092641], [0.97035779], [100.]],
            [[0.2959409], [0.97438178], [100.]],
            [[0.29119255], [0.97787196], [100.]],
            [[0.30649004], [0.96541272], [100.]],
            [[0.30124552], [0.97008732], [100.]],
            [[0.29624499], [0.97414704], [100.]],
            [[0.29148205], [0.97766847], [100.]],
            [[0.28694892], [0.98071974], [100.]],
            [[0.30156558], [0.96981445], [100.]],
            [[0.29654999], [0.97391021], [100.]],
            [[0.29177245], [0.97746315], [100.]],
            [[0.28722523], [0.98054192], [100.]],
            [[0.28289958], [0.98320731], [100.]],
            [[0.42963678], [0.47661181], [100.]],
            [[0.42846471], [0.43938586], [100.]],
            [[0.42628176], [0.40282965], [100.]],
            [[0.42314468], [0.36732207], [100.]],
            [[0.41913221], [0.333198], [100.]],
            [[0.42978939], [0.51176048], [100.]],
            [[0.42959394], [0.47427693], [100.]],
            [[0.4283576], [0.43708106], [100.]],
            [[0.4261132], [0.40057958], [100.]],
            [[0.422919], [0.36514906], [100.]],
            [[0.42902209], [0.54679323], [100.]],
            [[0.42980788], [0.50942101], [100.]],
            [[0.42954704], [0.47194318], [100.]],
            [[0.42824656], [0.43477897], [100.]],
            [[0.42594094], [0.3983337], [100.]],
            [[0.42735293], [0.58136855], [100.]],
            [[0.42910149], [0.54447221], [100.]],
            [[0.42982229], [0.50708112], [100.]],
            [[0.42949608], [0.46961065], [100.]],
            [[0.42813159], [0.43247968], [100.]],
            [[0.42482049], [0.61516258], [100.]],
            [[0.42749136], [0.57908829], [100.]],
            [[0.42917687], [0.54214925], [100.]],
            [[0.42983261], [0.50474093], [100.]],
            [[0.42944107], [0.46727945], [100.]],
            [[0.32257753], [0.94819408], [100.]],
            [[0.31663196], [0.95508757], [100.]],
            [[0.31093566], [0.96110142], [100.]],
            [[0.30548947], [0.96633839], [100.]],
            [[0.30029103], [0.97089165], [100.]],
            [[0.3169957], [0.95468427], [100.]],
            [[0.31128378], [0.9607499], [100.]],
            [[0.30582202], [0.96603252], [100.]],
            [[0.30060824], [0.9706259], [100.]],
            [[0.29563774], [0.97461444], [100.]],
            [[0.31163288], [0.96039533], [100.]],
            [[0.30615555], [0.96572397], [100.]],
            [[0.30092641], [0.97035779], [100.]],
            [[0.2959409], [0.97438178], [100.]],
            [[0.29119255], [0.97787196], [100.]],
            [[0.30649004], [0.96541272], [100.]],
            [[0.30124552], [0.97008732], [100.]],
            [[0.29624499], [0.97414704], [100.]],
            [[0.29148205], [0.97766847], [100.]],
            [[0.28694892], [0.98071974], [100.]],
            [[0.30156558], [0.96981445], [100.]],
            [[0.29654999], [0.97391021], [100.]],
            [[0.29177245], [0.97746315], [100.]],
            [[0.28722523], [0.98054192], [100.]],
            [[0.28289958], [0.98320731], [100.]],
        ]

        for trial in range(len(evc_gratton.results)):
            assert np.allclose(expected_results_array[trial],
                               # Note: Skip decision variable OutputPort
                               evc_gratton.results[trial][1:])
        for simulation in range(len(evc_gratton.simulation_results)):
            assert np.allclose(expected_sim_results_array[simulation],
                               # Note: Skip decision variable OutputPort
                               evc_gratton.simulation_results[simulation][1:])

    @pytest.mark.control
    @pytest.mark.composition
    def test_laming_validation_specify_control_signals(self):
        # Mechanisms
        Input = pnl.TransferMechanism(name='Input')
        reward = pnl.TransferMechanism(
            output_ports=[pnl.RESULT, pnl.MEAN, pnl.VARIANCE],
            name='reward'
        )
        Decision = pnl.DDM(
            function=pnl.DriftDiffusionAnalytical(
                drift_rate=1.0,
                threshold=1.0,
                noise=0.5,
                starting_point=0,
                t0=0.45
            ),
            output_ports=[
                pnl.DECISION_VARIABLE,
                pnl.RESPONSE_TIME,
                pnl.PROBABILITY_UPPER_THRESHOLD
            ],
            name='Decision'
        )

        comp = pnl.Composition(name="evc", retain_old_simulation_data=True)
        comp.add_node(reward, required_roles=[pnl.NodeRole.OUTPUT])
        comp.add_node(Decision, required_roles=[pnl.NodeRole.OUTPUT])
        task_execution_pathway = [Input, pnl.IDENTITY_MATRIX, Decision]
        comp.add_linear_processing_pathway(task_execution_pathway)

        comp.add_controller(
            controller=pnl.OptimizationControlMechanism(
                agent_rep=comp,
                features=[Input.input_port, reward.input_port],
                feature_function=pnl.AdaptiveIntegrator(rate=0.5),
                objective_mechanism=pnl.ObjectiveMechanism(
                    function=pnl.LinearCombination(operation=pnl.PRODUCT),
                    monitor=[
                        reward,
                        Decision.output_ports[pnl.PROBABILITY_UPPER_THRESHOLD],
                        (Decision.output_ports[pnl.RESPONSE_TIME], -1, 1)
                    ]
                ),
                function=pnl.GridSearch(),
                control_signals=[
                    {
                        PROJECTIONS: (pnl.DRIFT_RATE, Decision),
                        ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                    },
                    {
                        PROJECTIONS: (pnl.THRESHOLD, Decision),
                        ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                    }
                ],
            )
        )

        stim_list_dict = {
            Input: [0.5, 0.123],
            reward: [20, 20]
        }

        comp.run(inputs=stim_list_dict)

        # Note: Removed decision variable OutputPort from simulation results
        # because sign is chosen randomly
        expected_sim_results_array = [
            [[10.], [10.0], [0.0], [0.48999867], [0.50499983]],
            [[10.], [10.0], [0.0], [1.08965888], [0.51998934]],
            [[10.], [10.0], [0.0], [2.40680493], [0.53494295]],
            [[10.], [10.0], [0.0], [4.43671978], [0.549834]],
            [[10.], [10.0], [0.0], [0.48997868], [0.51998934]],
            [[10.], [10.0], [0.0], [1.08459402], [0.57932425]],
            [[10.], [10.0], [0.0], [2.36033556], [0.63645254]],
            [[10.], [10.0], [0.0], [4.24948962], [0.68997448]],
            [[10.], [10.0], [0.0], [0.48993479], [0.53494295]],
            [[10.], [10.0], [0.0], [1.07378304], [0.63645254]],
            [[10.], [10.0], [0.0], [2.26686573], [0.72710822]],
            [[10.], [10.0], [0.0], [3.90353015], [0.80218389]],
            [[10.], [10.0], [0.0], [0.4898672], [0.549834]],
            [[10.], [10.0], [0.0], [1.05791834], [0.68997448]],
            [[10.], [10.0], [0.0], [2.14222978], [0.80218389]],
            [[10.], [10.0], [0.0], [3.49637662], [0.88079708]],
            [[15.], [15.0], [0.0], [0.48999926], [0.50372993]],
            [[15.], [15.0], [0.0], [1.08981011], [0.51491557]],
            [[15.], [15.0], [0.0], [2.40822035], [0.52608629]],
            [[15.], [15.0], [0.0], [4.44259627], [0.53723096]],
            [[15.], [15.0], [0.0], [0.48998813], [0.51491557]],
            [[15.], [15.0], [0.0], [1.0869779], [0.55939819]],
            [[15.], [15.0], [0.0], [2.38198336], [0.60294711]],
            [[15.], [15.0], [0.0], [4.33535807], [0.64492386]],
            [[15.], [15.0], [0.0], [0.48996368], [0.52608629]],
            [[15.], [15.0], [0.0], [1.08085171], [0.60294711]],
            [[15.], [15.0], [0.0], [2.32712843], [0.67504223]],
            [[15.], [15.0], [0.0], [4.1221271], [0.7396981]],
            [[15.], [15.0], [0.0], [0.48992596], [0.53723096]],
            [[15.], [15.0], [0.0], [1.07165729], [0.64492386]],
            [[15.], [15.0], [0.0], [2.24934228], [0.7396981]],
            [[15.], [15.0], [0.0], [3.84279648], [0.81637827]]
        ]

        for simulation in range(len(expected_sim_results_array)):
            assert np.allclose(
                expected_sim_results_array[simulation],
                # Note: Skip decision variable OutputPort
                comp.simulation_results[simulation][0:3] + comp.simulation_results[simulation][4:6]
            )

        expected_results_array = [
            [[20.0], [20.0], [0.0], [1.0], [2.378055160151634], [0.9820137900379085]],
            [[20.0], [20.0], [0.0], [0.1], [0.48999967725112503], [0.5024599801509442]]
        ]

        for trial in range(len(expected_results_array)):
            np.testing.assert_allclose(
                comp.results[trial],
                expected_results_array[trial],
                atol=1e-08,
                err_msg='Failed on expected_output[{0}]'.format(trial)
            )

    @pytest.mark.control
    @pytest.mark.composition
    def test_stateful_mechanism_in_simulation(self):
        # Mechanisms
        Input = pnl.TransferMechanism(name='Input', integrator_mode=True)
        reward = pnl.TransferMechanism(
            output_ports=[pnl.RESULT, pnl.MEAN, pnl.VARIANCE],
            name='reward'
        )
        Decision = pnl.DDM(
            function=pnl.DriftDiffusionAnalytical(
                drift_rate=(
                    1.0,
                    pnl.ControlProjection(
                        function=pnl.Linear,
                        control_signal_params={
                            ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                        },
                    ),
                ),
                threshold=(
                    1.0,
                    pnl.ControlProjection(
                        function=pnl.Linear,
                        control_signal_params={
                            ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                        },
                    ),
                ),
                noise=(0.5),
                starting_point=(0),
                t0=0.45
            ),
            output_ports=[
                pnl.DECISION_VARIABLE,
                pnl.RESPONSE_TIME,
                pnl.PROBABILITY_UPPER_THRESHOLD
            ],
            name='Decision',
        )

        comp = pnl.Composition(name="evc", retain_old_simulation_data=True)
        comp.add_node(reward, required_roles=[pnl.NodeRole.OUTPUT])
        comp.add_node(Decision, required_roles=[pnl.NodeRole.OUTPUT])
        task_execution_pathway = [Input, pnl.IDENTITY_MATRIX, Decision]
        comp.add_linear_processing_pathway(task_execution_pathway)

        comp.add_controller(
            controller=pnl.OptimizationControlMechanism(
                agent_rep=comp,
                features=[Input.input_port, reward.input_port],
                feature_function=pnl.AdaptiveIntegrator(rate=0.5),
                objective_mechanism=pnl.ObjectiveMechanism(
                    function=pnl.LinearCombination(operation=pnl.PRODUCT),
                    monitor=[
                        reward,
                        Decision.output_ports[pnl.PROBABILITY_UPPER_THRESHOLD],
                        (Decision.output_ports[pnl.RESPONSE_TIME], -1, 1)
                    ]
                ),
                function=pnl.GridSearch(),
                control_signals=[
                    {
                        PROJECTIONS: (pnl.DRIFT_RATE, Decision),
                        ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                    },
                    {
                        PROJECTIONS: (pnl.THRESHOLD, Decision),
                        ALLOCATION_SAMPLES: np.arange(0.1, 1.01, 0.3)
                    }
                ],
            )
        )

        stim_list_dict = {
            Input: [0.5, 0.123],
            reward: [20, 20]
        }
        Input.reinitialize_when = pnl.Never()

        comp.run(inputs=stim_list_dict)

        # Note: Removed decision variable OutputPort from simulation results
        # because sign is chosen randomly
        expected_sim_results_array = [
            [[10.], [10.0], [0.0], [0.48999867], [0.50499983]],
            [[10.], [10.0], [0.0], [1.08965888], [0.51998934]],
            [[10.], [10.0], [0.0], [2.40680493], [0.53494295]],
            [[10.], [10.0], [0.0], [4.43671978], [0.549834]],
            [[10.], [10.0], [0.0], [0.48997868], [0.51998934]],
            [[10.], [10.0], [0.0], [1.08459402], [0.57932425]],
            [[10.], [10.0], [0.0], [2.36033556], [0.63645254]],
            [[10.], [10.0], [0.0], [4.24948962], [0.68997448]],
            [[10.], [10.0], [0.0], [0.48993479], [0.53494295]],
            [[10.], [10.0], [0.0], [1.07378304], [0.63645254]],
            [[10.], [10.0], [0.0], [2.26686573], [0.72710822]],
            [[10.], [10.0], [0.0], [3.90353015], [0.80218389]],
            [[10.], [10.0], [0.0], [0.4898672], [0.549834]],
            [[10.], [10.0], [0.0], [1.05791834], [0.68997448]],
            [[10.], [10.0], [0.0], [2.14222978], [0.80218389]],
            [[10.], [10.0], [0.0], [3.49637662], [0.88079708]],
            [[15.], [15.0], [0.0], [0.48999926], [0.50372993]],
            [[15.], [15.0], [0.0], [1.08981011], [0.51491557]],
            [[15.], [15.0], [0.0], [2.40822035], [0.52608629]],
            [[15.], [15.0], [0.0], [4.44259627], [0.53723096]],
            [[15.], [15.0], [0.0], [0.48998813], [0.51491557]],
            [[15.], [15.0], [0.0], [1.0869779], [0.55939819]],
            [[15.], [15.0], [0.0], [2.38198336], [0.60294711]],
            [[15.], [15.0], [0.0], [4.33535807], [0.64492386]],
            [[15.], [15.0], [0.0], [0.48996368], [0.52608629]],
            [[15.], [15.0], [0.0], [1.08085171], [0.60294711]],
            [[15.], [15.0], [0.0], [2.32712843], [0.67504223]],
            [[15.], [15.0], [0.0], [4.1221271], [0.7396981]],
            [[15.], [15.0], [0.0], [0.48992596], [0.53723096]],
            [[15.], [15.0], [0.0], [1.07165729], [0.64492386]],
            [[15.], [15.0], [0.0], [2.24934228], [0.7396981]],
            [[15.], [15.0], [0.0], [3.84279648], [0.81637827]]
        ]

        for simulation in range(len(expected_sim_results_array)):
            assert np.allclose(
                expected_sim_results_array[simulation],
                # Note: Skip decision variable OutputPort
                comp.simulation_results[simulation][0:3] + comp.simulation_results[simulation][4:6]
            )

        expected_results_array = [
            [[20.0], [20.0], [0.0], [1.0], [3.4963766238230596], [0.8807970779778824]],
            [[20.0], [20.0], [0.0], [0.1], [0.4899992579951842], [0.503729930808051]]
        ]

        for trial in range(len(expected_results_array)):
            np.testing.assert_allclose(
                comp.results[trial],
                expected_results_array[trial],
                atol=1e-08,
                err_msg='Failed on expected_output[{0}]'.format(trial)
            )

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Model Based OCM")
    @pytest.mark.parametrize("mode", ["Python",
                                      pytest.param("LLVM", marks=pytest.mark.llvm),
                                      pytest.param("LLVMExec", marks=pytest.mark.llvm),
                                      pytest.param("LLVMRun", marks=pytest.mark.llvm)])
    def test_model_based_ocm_after(self, benchmark, mode):

        A = pnl.ProcessingMechanism(name='A')
        B = pnl.ProcessingMechanism(name='B')

        comp = pnl.Composition(name='comp',
                               controller_mode=pnl.AFTER)
        comp.add_linear_processing_pathway([A, B])

        search_range = pnl.SampleSpec(start=0.25, stop=0.75, step=0.25)
        control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, A)],
                                           function=pnl.Linear,
                                           variable=1.0,
                                           allocation_samples=search_range,
                                           intensity_cost_function=pnl.Linear(slope=0.))

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(agent_rep=comp,
                                               features=[A.input_port],
                                               objective_mechanism=objective_mech,
                                               function=pnl.GridSearch(),
                                               control_signals=[control_signal])
        # objective_mech.log.set_log_conditions(pnl.OUTCOME)

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]], [[2.0]], [[3.0]]]}

        comp.run(inputs=inputs, bin_execute=mode)

        # objective_mech.log.print_entries(pnl.OUTCOME)
        assert np.allclose(comp.results, [[np.array([1.])], [np.array([1.5])], [np.array([2.25])]])
        benchmark(comp.run, inputs, bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Model Based OCM")
    @pytest.mark.parametrize("mode", ["Python",
                                      pytest.param("LLVM", marks=pytest.mark.llvm),
                                      pytest.param("LLVMExec", marks=pytest.mark.llvm),
                                      pytest.param("LLVMRun", marks=pytest.mark.llvm)])
    def test_model_based_ocm_before(self, benchmark, mode):

        A = pnl.ProcessingMechanism(name='A')
        B = pnl.ProcessingMechanism(name='B')

        comp = pnl.Composition(name='comp',
                               controller_mode=pnl.BEFORE)
        comp.add_linear_processing_pathway([A, B])

        search_range = pnl.SampleSpec(start=0.25, stop=0.75, step=0.25)
        control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, A)],
                                           function=pnl.Linear,
                                           variable=1.0,
                                           allocation_samples=search_range,
                                           intensity_cost_function=pnl.Linear(slope=0.))

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(agent_rep=comp,
                                               features=[A.input_port],
                                               objective_mechanism=objective_mech,
                                               function=pnl.GridSearch(),
                                               control_signals=[control_signal])
        # objective_mech.log.set_log_conditions(pnl.OUTCOME)

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]], [[2.0]], [[3.0]]]}

        comp.run(inputs=inputs, bin_execute=mode)

        # objective_mech.log.print_entries(pnl.OUTCOME)
        assert np.allclose(comp.results, [[np.array([0.75])], [np.array([1.5])], [np.array([2.25])]])
        benchmark(comp.run, inputs, bin_execute=mode)

    def test_model_based_ocm_with_buffer(self):

        A = pnl.ProcessingMechanism(name='A')
        B = pnl.ProcessingMechanism(name='B')

        comp = pnl.Composition(name='comp',
                               controller_mode=pnl.BEFORE,
                               retain_old_simulation_data=True,
                               )
        comp.add_linear_processing_pathway([A, B])

        search_range = pnl.SampleSpec(start=0.25, stop=0.75, step=0.25)
        control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, A)],
                                           function=pnl.Linear,
                                           variable=1.0,
                                           allocation_samples=search_range,
                                           intensity_cost_function=pnl.Linear(slope=0.))

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(agent_rep=comp,
                                               features=[A.input_port],
                                               feature_function=pnl.Buffer(history=2),
                                               objective_mechanism=objective_mech,
                                               function=pnl.GridSearch(),
                                               control_signals=[control_signal])
        objective_mech.log.set_log_conditions(pnl.OUTCOME)

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]], [[2.0]], [[3.0]]]}

        for i in range(1, len(ocm.input_ports)):
            ocm.input_ports[i].function.reinitialize()
        comp.run(inputs=inputs)

        log = objective_mech.log.nparray_dictionary()

        # "outer" composition
        assert np.allclose(log["comp"][pnl.OUTCOME], [[0.75], [1.5], [2.25]])

        # preprocess to ignore control allocations
        log_parsed = {}
        for key, value in log.items():
            cleaned_key = re.sub(r'comp-sim-(\d).*', r'\1', key)
            log_parsed[cleaned_key] = value

        # First round of simulations is only one trial.
        # (Even though the feature fn is a Buffer, there is no history yet)
        for i in range(0, 3):
            assert len(log_parsed[str(i)]["Trial"]) == 1

        # Second and third rounds of simulations are two trials.
        # (The buffer has history = 2)
        for i in range(3, 9):
            assert len(log_parsed[str(i)]["Trial"]) == 2

    def test_stability_flexibility_susan_and_sebastian(self):

        # computeAccuracy(trialInformation)
        # Inputs: trialInformation[0, 1, 2, 3]
        # trialInformation[0] - Task Dimension : [0, 1] or [1, 0]
        # trialInformation[1] - Stimulus Dimension: Congruent {[1, 1] or [-1, -1]} // Incongruent {[-1, 1] or [1, -1]}
        # trialInformation[2] - Upper Threshold: Probability of DDM choosing upper bound
        # trialInformation[3] - Lower Threshold: Probability of DDM choosing lower bound

        def computeAccuracy(trialInformation):

            # Unload contents of trialInformation
            # Origin Node Inputs
            taskInputs = trialInformation[0]
            stimulusInputs = trialInformation[1]

            # DDM Outputs
            upperThreshold = trialInformation[2]
            lowerThreshold = trialInformation[3]

            # Keep Track of Accuracy
            accuracy = []

            # Beginning of Accuracy Calculation
            colorTrial = (taskInputs[0] == 1)
            motionTrial = (taskInputs[1] == 1)

            # Based on the task dimension information, decide which response is "correct"
            # Obtain accuracy probability from DDM thresholds in "correct" direction
            if colorTrial:
                if stimulusInputs[0] == 1:
                    accuracy.append(upperThreshold)
                elif stimulusInputs[0] == -1:
                    accuracy.append(lowerThreshold)

            if motionTrial:
                if stimulusInputs[1] == 1:
                    accuracy.append(upperThreshold)
                elif stimulusInputs[1] == -1:
                    accuracy.append(lowerThreshold)

            # Accounts for initialization runs that have no variable input
            if len(accuracy) == 0:
                accuracy = [0]

            # print("Accuracy: ", accuracy[0])
            # print()

            return [accuracy]

        # BEGIN: Composition Construction

        # Constants as defined in Musslick et al. 2018
        tau = 0.9  # Time Constant
        DRIFT = 1  # Drift Rate
        STARTING_POINT = 0.0  # Starting Point
        THRESHOLD = 0.0475  # Threshold
        NOISE = 0.04  # Noise
        T0 = 0.2  # T0

        # Task Layer: [Color, Motion] {0, 1} Mutually Exclusive
        # Origin Node
        taskLayer = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                          size=2,
                                          function=pnl.Linear(slope=1, intercept=0),
                                          output_ports=[pnl.RESULT],
                                          name='Task Input [I1, I2]')

        # Stimulus Layer: [Color Stimulus, Motion Stimulus]
        # Origin Node
        stimulusInfo = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                             size=2,
                                             function=pnl.Linear(slope=1, intercept=0),
                                             output_ports=[pnl.RESULT],
                                             name="Stimulus Input [S1, S2]")

        # Activation Layer: [Color Activation, Motion Activation]
        # Recurrent: Self Excitation, Mutual Inhibition
        # Controlled: Gain Parameter
        activation = pnl.RecurrentTransferMechanism(default_variable=[[0.0, 0.0]],
                                                    function=pnl.Logistic(gain=1.0),
                                                    matrix=[[1.0, -1.0],
                                                            [-1.0, 1.0]],
                                                    integrator_mode=True,
                                                    integrator_function=pnl.AdaptiveIntegrator(rate=(tau)),
                                                    initial_value=np.array([[0.0, 0.0]]),
                                                    output_ports=[pnl.RESULT],
                                                    name='Task Activations [Act 1, Act 2]')

        # Hadamard product of Activation and Stimulus Information
        nonAutomaticComponent = pnl.TransferMechanism(default_variable=[[0.0, 0.0]],
                                                      size=2,
                                                      function=pnl.Linear(slope=1, intercept=0),
                                                      input_ports=pnl.InputPort(combine=pnl.PRODUCT),
                                                      output_ports=[pnl.RESULT],
                                                      name='Non-Automatic Component [S1*Activity1, S2*Activity2]')

        # Summation of nonAutomatic and Automatic Components
        ddmCombination = pnl.TransferMechanism(size=1,
                                               function=pnl.Linear(slope=1, intercept=0),
                                               input_ports=pnl.InputPort(combine=pnl.SUM),
                                               output_ports=[pnl.RESULT],
                                               name="Drift = (S1 + S2) + (S1*Activity1 + S2*Activity2)")

        decisionMaker = pnl.DDM(function=pnl.DriftDiffusionAnalytical(drift_rate=DRIFT,
                                                                      starting_point=STARTING_POINT,
                                                                      threshold=THRESHOLD,
                                                                      noise=NOISE,
                                                                      t0=T0),
                                output_ports=[pnl.DECISION_VARIABLE, pnl.RESPONSE_TIME,
                                               pnl.PROBABILITY_UPPER_THRESHOLD,
                                               pnl.PROBABILITY_LOWER_THRESHOLD],
                                name='DDM')

        taskLayer.set_log_conditions([pnl.RESULT])
        stimulusInfo.set_log_conditions([pnl.RESULT])
        activation.set_log_conditions([pnl.RESULT, "mod_gain"])
        nonAutomaticComponent.set_log_conditions([pnl.RESULT])
        ddmCombination.set_log_conditions([pnl.RESULT])
        decisionMaker.set_log_conditions([pnl.PROBABILITY_UPPER_THRESHOLD, pnl.PROBABILITY_LOWER_THRESHOLD,
                                          pnl.DECISION_VARIABLE, pnl.RESPONSE_TIME])

        # Composition Creation

        stabilityFlexibility = pnl.Composition(controller_mode=pnl.BEFORE)

        # Node Creation
        stabilityFlexibility.add_node(taskLayer)
        stabilityFlexibility.add_node(activation)
        stabilityFlexibility.add_node(nonAutomaticComponent)
        stabilityFlexibility.add_node(stimulusInfo)
        stabilityFlexibility.add_node(ddmCombination)
        stabilityFlexibility.add_node(decisionMaker)

        # Projection Creation
        stabilityFlexibility.add_projection(sender=taskLayer, receiver=activation)
        stabilityFlexibility.add_projection(sender=activation, receiver=nonAutomaticComponent)
        stabilityFlexibility.add_projection(sender=stimulusInfo, receiver=nonAutomaticComponent)
        stabilityFlexibility.add_projection(sender=stimulusInfo, receiver=ddmCombination)
        stabilityFlexibility.add_projection(sender=nonAutomaticComponent, receiver=ddmCombination)
        stabilityFlexibility.add_projection(sender=ddmCombination, receiver=decisionMaker)

        # Beginning of Controller

        # Grid Search Range
        searchRange = pnl.SampleSpec(start=1.0, stop=1.9, num=10)

        # Modulate the GAIN parameter from activation layer
        # Initalize cost function as 0
        signal = pnl.ControlSignal(projections=[(pnl.GAIN, activation)],
                                   function=pnl.Linear,
                                   variable=1.0,
                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                   allocation_samples=searchRange)

        # Use the computeAccuracy function to obtain selection values
        # Pass in 4 arguments whenever computeRewardRate is called
        objectiveMechanism = pnl.ObjectiveMechanism(monitor=[taskLayer, stimulusInfo,
                                                             (pnl.PROBABILITY_UPPER_THRESHOLD, decisionMaker),
                                                             (pnl.PROBABILITY_LOWER_THRESHOLD, decisionMaker)],
                                                    function=computeAccuracy,
                                                    name="Controller Objective Mechanism")

        #  Sets trial history for simulations over specified signal search parameters
        metaController = pnl.OptimizationControlMechanism(agent_rep=stabilityFlexibility,
                                                          features=[taskLayer.input_port, stimulusInfo.input_port],
                                                          feature_function=pnl.Buffer(history=10),
                                                          name="Controller",
                                                          objective_mechanism=objectiveMechanism,
                                                          function=pnl.GridSearch(),
                                                          control_signals=[signal])

        stabilityFlexibility.add_controller(metaController)
        stabilityFlexibility.enable_controller = True
        # stabilityFlexibility.model_based_optimizer_mode = pnl.BEFORE

        for i in range(1, len(stabilityFlexibility.controller.input_ports)):
            stabilityFlexibility.controller.input_ports[i].function.reinitialize()
        # Origin Node Inputs
        taskTrain = [[1, 0], [0, 1], [1, 0], [0, 1]]
        stimulusTrain = [[1, -1], [-1, 1], [1, -1], [-1, 1]]

        inputs = {taskLayer: taskTrain, stimulusInfo: stimulusTrain}
        stabilityFlexibility.run(inputs)

    def test_model_based_num_estimates(self):

        A = pnl.ProcessingMechanism(name='A')
        B = pnl.ProcessingMechanism(name='B',
                                    function=pnl.SimpleIntegrator(rate=1))

        comp = pnl.Composition(name='comp')
        comp.add_linear_processing_pathway([A, B])

        search_range = pnl.SampleSpec(start=0.25, stop=0.75, step=0.25)
        control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, A)],
                                           function=pnl.Linear,
                                           variable=1.0,
                                           allocation_samples=search_range,
                                           intensity_cost_function=pnl.Linear(slope=0.))

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(agent_rep=comp,
                                               features=[A.input_port],
                                               objective_mechanism=objective_mech,
                                               function=pnl.GridSearch(),
                                               num_estimates=5,
                                               control_signals=[control_signal])

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]]]}

        comp.run(inputs=inputs,
                 num_trials=2)

        assert np.allclose(comp.simulation_results,
                           [[np.array([2.25])], [np.array([3.5])], [np.array([4.75])], [np.array([3.])], [np.array([4.25])], [np.array([5.5])]])
        assert np.allclose(comp.results,
                           [[np.array([1.])], [np.array([1.75])]])

    def test_model_based_ocm_no_simulations(self):
        A = pnl.ProcessingMechanism(name='A')
        B = pnl.ProcessingMechanism(name='B', function=pnl.SimpleIntegrator(rate=1))

        comp = pnl.Composition(name='comp')
        comp.add_linear_processing_pathway([A, B])

        control_signal = pnl.ControlSignal(
            projections=[(pnl.SLOPE, A)],
            function=pnl.Linear,
            variable=1.0,
            allocation_samples=[1, 2, 3],
            intensity_cost_function=pnl.Linear(slope=0.)
        )

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(
            agent_rep=comp,
            features=[A.input_port],
            objective_mechanism=objective_mech,
            function=pnl.GridSearch(),
            num_estimates=1,
            control_signals=[control_signal],
            search_statefulness=False,
        )

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]]]}

        comp.run(inputs=inputs, num_trials=1)

        # initial 1 + each allocation sample (1, 2, 3) integrated
        assert B.parameters.value.get(comp) == 7

    def test_grid_search_random_selection(self):
        A = pnl.ProcessingMechanism(name='A')

        A.log.set_log_conditions(items="mod_slope")
        B = pnl.ProcessingMechanism(name='B',
                                    function=pnl.Logistic())

        comp = pnl.Composition(name='comp')
        comp.add_linear_processing_pathway([A, B])

        search_range = pnl.SampleSpec(start=15., stop=35., step=5)
        control_signal = pnl.ControlSignal(projections=[(pnl.SLOPE, A)],
                                           function=pnl.Linear,
                                           variable=1.0,
                                           allocation_samples=search_range,
                                           intensity_cost_function=pnl.Linear(slope=0.))

        objective_mech = pnl.ObjectiveMechanism(monitor=[B])
        ocm = pnl.OptimizationControlMechanism(agent_rep=comp,
                                               features=[A.input_port],
                                               objective_mechanism=objective_mech,
                                               function=pnl.GridSearch(select_randomly_from_optimal_values=True),
                                               control_signals=[control_signal])

        comp.add_controller(ocm)

        inputs = {A: [[[1.0]]]}

        comp.run(inputs=inputs,
                 num_trials=10,
                 context='outer_comp')

        log_arr = A.log.nparray_dictionary()

        # control signal value (mod slope) is chosen randomly from all of the control signal values
        # that correspond to a net outcome of 1
        assert np.allclose([[1.], [15.], [15.], [20.], [20.], [15.], [20.], [25.], [15.], [35.]],
                           log_arr['outer_comp']['mod_slope'])

class TestSampleIterator:

    def test_int_step(self):
        spec = SampleSpec(step=2,
                          start=0,
                          stop=10)
        sample_iterator = SampleIterator(specification=spec)

        expected = [0, 2, 4, 6, 8, 10]

        for i in range(6):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

        sample_iterator.reset()

        for i in range(6):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

    def test_int_num(self):
        spec = SampleSpec(num=6,
                          start=0,
                          stop=10)
        sample_iterator = SampleIterator(specification=spec)

        expected = [0, 2, 4, 6, 8, 10]

        for i in range(6):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

        sample_iterator.reset()

        for i in range(6):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

    def test_neither_num_nor_step(self):
        with pytest.raises(SampleIteratorError) as error_text:
            SampleSpec(start=0,
                       stop=10)
        assert "Must specify one of 'step', 'num' or 'function'" in str(error_text.value)

    def test_float_step(self):
        # Need to decide whether stop should be exclusive
        spec = SampleSpec(step=2.79,
                          start=0.65,
                          stop=10.25)
        sample_iterator = SampleIterator(specification=spec)

        expected = [0.65, 3.44, 6.23, 9.02]

        for i in range(4):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

        sample_iterator.reset()

        for i in range(4):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

    def test_function(self):
        fun = pnl.NormalDist(mean=5.0).function
        spec = SampleSpec(function=fun)
        sample_iterator = SampleIterator(specification=spec)

        expected = [5.978737984105739, 7.240893199201458, 6.867557990149967, 4.022722120123589, 5.950088417525589]

        for i in range(5):
            assert np.allclose(next(sample_iterator), expected[i])

    def test_function_with_num(self):
        fun = pnl.NormalDist(mean=5.0).function
        spec = SampleSpec(function=fun,
                          num=4)
        sample_iterator = SampleIterator(specification=spec)

        expected = [5.978737984105739, 7.240893199201458, 6.867557990149967, 4.022722120123589, 5.950088417525589]

        for i in range(4):
            assert np.allclose(next(sample_iterator), expected[i])

        assert next(sample_iterator, None) is None

    def test_list(self):
        sample_list = [1, 2.0, 3.456, 7.8]
        sample_iterator = SampleIterator(specification=sample_list)

        for i in range(len(sample_list)):
            assert np.allclose(next(sample_iterator), sample_list[i])

        assert next(sample_iterator, None) is None

        sample_iterator.reset()

        for i in range(len(sample_list)):
            assert np.allclose(next(sample_iterator), sample_list[i])

        assert next(sample_iterator, None) is None

        assert sample_iterator.start == 1
        assert sample_iterator.stop is None
        assert sample_iterator.num == len(sample_list)

