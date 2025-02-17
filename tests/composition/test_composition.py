import functools
import logging

from timeit import timeit

import numpy as np
import pytest

from itertools import product

import psyneulink.core.llvm as pnlvm
import psyneulink as pnl
from psyneulink.core.components.functions.statefulfunctions.integratorfunctions import AdaptiveIntegrator, SimpleIntegrator
from psyneulink.core.components.functions.transferfunctions import Linear, Logistic
from psyneulink.core.components.functions.combinationfunctions import LinearCombination
from psyneulink.core.components.functions.userdefinedfunction import UserDefinedFunction
from psyneulink.core.components.mechanisms.processing.integratormechanism import IntegratorMechanism
from psyneulink.core.components.mechanisms.processing.objectivemechanism import ObjectiveMechanism
from psyneulink.core.components.mechanisms.processing.processingmechanism import ProcessingMechanism
from psyneulink.core.components.mechanisms.processing.transfermechanism import TransferMechanism
from psyneulink.core.components.projections.pathway.mappingprojection import MappingProjection
from psyneulink.core.components.ports.inputport import InputPort
from psyneulink.core.compositions.composition import Composition, CompositionError
from psyneulink.core.compositions.pathwaycomposition import PathwayComposition
from psyneulink.core.compositions.systemcomposition import SystemComposition
from psyneulink.core.globals.keywords import \
    ADDITIVE, ALLOCATION_SAMPLES, DISABLE, INPUT_PORT, NAME, PROJECTIONS, RESULT, OVERRIDE, TARGET_MECHANISM, VARIANCE
from psyneulink.core.globals.utilities import NodeRole
from psyneulink.core.scheduling.condition import AfterNCalls
from psyneulink.core.scheduling.condition import EveryNCalls
from psyneulink.core.scheduling.scheduler import Scheduler
from psyneulink.core.scheduling.time import TimeScale
from psyneulink.library.components.mechanisms.modulatory.control.agt.lccontrolmechanism import LCControlMechanism
from psyneulink.library.components.mechanisms.processing.transfer.recurrenttransfermechanism import \
    RecurrentTransferMechanism

logger = logging.getLogger(__name__)

# All tests are set to run. If you need to skip certain tests,
# see http://doc.pytest.org/en/latest/skipping.html


def record_values(d, time_scale, *mechs, comp=None):
    if time_scale not in d:
        d[time_scale] = {}
    for mech in mechs:
        if mech not in d[time_scale]:
            d[time_scale][mech] = []
        mech_value = mech.parameters.value.get(comp)
        if mech_value is None:
            d[time_scale][mech].append(np.nan)
        else:
            d[time_scale][mech].append(mech_value[0][0])

# Unit tests for each function of the Composition class #######################
# Unit tests for Composition.Composition(


class TestConstructor:

    def test_no_args(self):
        comp = Composition()
        assert isinstance(comp, Composition)

    def test_two_calls_no_args(self):
        comp = Composition()
        assert isinstance(comp, Composition)

        comp_2 = Composition()
        assert isinstance(comp, Composition)

    @pytest.mark.stress
    @pytest.mark.parametrize(
        'count', [
            10000,
        ]
    )
    def test_timing_no_args(self, count):
        t = timeit('comp = Composition()', setup='from psyneulink.core.compositions.composition import Composition', number=count)
        print()
        logger.info('completed {0} creation{2} of Composition() in {1:.8f}s'.format(count, t, 's' if count != 1 else ''))


class TestAddMechanism:

    def test_add_once(self):
        comp = Composition()
        comp.add_node(TransferMechanism())
    def test_add_twice(self):
        comp = Composition()
        comp.add_node(TransferMechanism())
        comp.add_node(TransferMechanism())

    def test_add_same_twice(self):
        comp = Composition()
        mech = TransferMechanism()
        comp.add_node(mech)
        comp.add_node(mech)

    def test_add_multiple_projections_at_once(self):
        comp = Composition(name='comp')
        a = TransferMechanism(name='a')
        b = TransferMechanism(name='b',
                              function=Linear(slope=2.0))
        c = TransferMechanism(name='a',
                              function=Linear(slope=4.0))
        nodes = [a, b, c]
        comp.add_nodes(nodes)

        ab = MappingProjection(sender=a, receiver=b)
        bc = MappingProjection(sender=b, receiver=c, matrix=[[3.0]])
        projections = [ab, bc]
        comp.add_projections(projections)

        comp.run(inputs={a: 1.0})

        assert np.allclose(a.value, [[1.0]])
        assert np.allclose(b.value, [[2.0]])
        assert np.allclose(c.value, [[24.0]])
        assert ab in comp.projections
        assert bc in comp.projections

    def test_add_multiple_projections_no_sender(self):
        comp = Composition(name='comp')
        a = TransferMechanism(name='a')
        b = TransferMechanism(name='b',
                              function=Linear(slope=2.0))
        c = TransferMechanism(name='a',
                              function=Linear(slope=4.0))
        nodes = [a, b, c]
        comp.add_nodes(nodes)

        ab = MappingProjection(sender=a, receiver=b)
        bc = MappingProjection(sender=b)
        projections = [ab, bc]
        with pytest.raises(CompositionError) as err:
            comp.add_projections(projections)
        assert "The add_projections method of Composition requires a list of Projections" in str(err.value)

    def test_add_multiple_projections_no_receiver(self):
        comp = Composition(name='comp')
        a = TransferMechanism(name='a')
        b = TransferMechanism(name='b',
                              function=Linear(slope=2.0))
        c = TransferMechanism(name='a',
                              function=Linear(slope=4.0))
        nodes = [a, b, c]
        comp.add_nodes(nodes)

        ab = MappingProjection(sender=a, receiver=b)
        bc = MappingProjection(receiver=c)
        projections = [ab, bc]
        with pytest.raises(CompositionError) as err:
            comp.add_projections(projections)
        assert "The add_projections method of Composition requires a list of Projections" in str(err.value)

    def test_add_multiple_projections_not_a_proj(self):
        comp = Composition(name='comp')
        a = TransferMechanism(name='a')
        b = TransferMechanism(name='b',
                              function=Linear(slope=2.0))
        c = TransferMechanism(name='a',
                              function=Linear(slope=4.0))
        nodes = [a, b, c]
        comp.add_nodes(nodes)

        ab = MappingProjection(sender=a, receiver=b)
        bc = [[3.0]]
        projections = [ab, bc]
        with pytest.raises(CompositionError) as err:
            comp.add_projections(projections)
        assert "The add_projections method of Composition requires a list of Projections" in str(err.value)

    def test_add_multiple_nodes_at_once(self):
        comp = Composition()
        a = TransferMechanism()
        b = TransferMechanism()
        c = TransferMechanism()
        nodes = [a, b, c]
        comp.add_nodes(nodes)
        output = comp.run(inputs={a: [1.0],
                                  b: [2.0],
                                  c: [3.0]})
        assert set(comp.get_nodes_by_role(NodeRole.INPUT)) == set(nodes)
        assert set(comp.get_nodes_by_role(NodeRole.OUTPUT)) == set(nodes)
        assert np.allclose(output, [[1.0], [2.0], [3.0]])
    @pytest.mark.stress
    @pytest.mark.parametrize(
        'count', [
            100,
        ]
    )
    def test_timing_stress(self, count):
        t = timeit(
            'comp.add_node(TransferMechanism())',
            setup="""

from psyneulink.core.components.mechanisms.processing.transfermechanism import TransferMechanism
from psyneulink.core.compositions.composition import Composition
comp = Composition()
""",
            number=count
        )
        print()
        logger.info('completed {0} addition{2} of a Mechanism to a Composition in {1:.8f}s'.
                    format(count, t, 's' if count != 1 else ''))


class TestAddProjection:

    def test_add_once(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(), A, B)

    def test_add_twice(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(), A, B)
        comp.add_projection(MappingProjection(), A, B)
    #
    # def test_add_same_twice(self):
    #     comp = Composition()
    #     A = TransferMechanism(name='composition-pytests-A')
    #     B = TransferMechanism(name='composition-pytests-B')
    #     comp.add_node(A)
    #     comp.add_node(B)
    #     proj = MappingProjection()
    #     comp.add_projection(proj, A, B)
    #     with pytest.raises(CompositionError) as error_text:
    #         comp.add_projection(proj, A, B)
    #     assert "This Projection is already in the Composition" in str(error_text.value)

    def test_add_fully_specified_projection_object(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        proj = MappingProjection(sender=A, receiver=B)
        comp.add_projection(proj)

    def test_add_proj_sender_and_receiver_only(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B',
                              function=Linear(slope=2.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(sender=A, receiver=B)
        result = comp.run(inputs={A: [1.0]})
        assert np.allclose(result, [[np.array([2.])]])

    def test_add_proj_missing_sender(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B',
                              function=Linear(slope=2.0))
        comp.add_node(A)
        comp.add_node(B)
        with pytest.raises(CompositionError) as error_text:
            comp.add_projection(receiver=B)
        assert "a sender must be specified" in str(error_text.value)

    def test_add_proj_missing_receiver(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B',
                              function=Linear(slope=2.0))
        comp.add_node(A)
        comp.add_node(B)
        with pytest.raises(CompositionError) as error_text:
            comp.add_projection(sender=A)
        assert "a receiver must be specified" in str(error_text.value)

    def test_add_proj_invalid_projection_spec(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B',
                              function=Linear(slope=2.0))
        comp.add_node(A)
        comp.add_node(B)
        with pytest.raises(CompositionError) as error_text:
            comp.add_projection("projection")
        assert "Invalid projection" in str(error_text.value)

    # KAM commented out this test 7/24/18 because it does not work. Should it work?
    # Or should the add_projection method of Composition only consider composition nodes as senders and receivers

    # def test_add_proj_states_as_sender_and_receiver(self):
    #     comp = Composition()
    #     A = TransferMechanism(name='composition-pytests-A',
    #                           default_variable=[[0.], [0.]])
    #     B = TransferMechanism(name='composition-pytests-B',
    #                           function=Linear(slope=2.0),
    #                           default_variable=[[0.], [0.]])
    #     comp.add_node(A)
    #     comp.add_node(B)
    #
    #     comp.add_projection(sender=A.output_ports[0], receiver=B.input_ports[0])
    #     comp.add_projection(sender=A.output_ports[1], receiver=B.input_ports[1])
    #
    #     print(comp.run(inputs={A: [[1.0], [2.0]]}))

    def test_add_proj_weights_only(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A',
                              default_variable=[[0., 0., 0.]])
        B = TransferMechanism(name='composition-pytests-B',
                              default_variable=[[0., 0.]],
                              function=Linear(slope=2.0))
        weights = [[1., 2.], [3., 4.], [5., 6.]]
        comp.add_node(A)
        comp.add_node(B)
        proj = comp.add_projection(weights, A, B)
        comp.run(inputs={A: [[1.1, 1.2, 1.3]]})
        assert np.allclose(A.parameters.value.get(comp), [[1.1, 1.2, 1.3]])
        assert np.allclose(B.get_input_values(comp), [[11.2,  14.8]])
        assert np.allclose(B.parameters.value.get(comp), [[22.4,  29.6]])
        assert np.allclose(proj.matrix, weights)

    def test_add_linear_processing_pathway_with_noderole_specified_in_tuple(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        C = TransferMechanism(name='composition-pytests-C')
        comp.add_linear_processing_pathway([
            (A,pnl.NodeRole.AUTOASSOCIATIVE_LEARNING),
            (B,pnl.NodeRole.AUTOASSOCIATIVE_LEARNING),
            C
        ])
        comp._analyze_graph()
        autoassociative_learning_nodes = comp.get_nodes_by_role(pnl.NodeRole.AUTOASSOCIATIVE_LEARNING)
        assert A in autoassociative_learning_nodes
        assert B in autoassociative_learning_nodes

    def test_add_linear_processing_pathway_containing_nodes_with_existing_projections(self):
        """ Test that add_linear_processing_pathway uses MappingProjections already specified for
                Hidden_layer_2 and Output_Layer in the pathway it creates within the Composition"""
        Input_Layer = TransferMechanism(name='Input Layer', size=2)
        Hidden_Layer_1 = TransferMechanism(name='Hidden Layer_1', size=5)
        Hidden_Layer_2 = TransferMechanism(name='Hidden Layer_2', size=4)
        Output_Layer = TransferMechanism(name='Output Layer', size=3)
        Input_Weights_matrix = (np.arange(2 * 5).reshape((2, 5)) + 1) / (2 * 5)
        Middle_Weights_matrix = (np.arange(5 * 4).reshape((5, 4)) + 1) / (5 * 4)
        Output_Weights_matrix = (np.arange(4 * 3).reshape((4, 3)) + 1) / (4 * 3)
        Input_Weights = MappingProjection(name='Input Weights', matrix=Input_Weights_matrix)
        Middle_Weights = MappingProjection(name='Middle Weights',sender=Hidden_Layer_1, receiver=Hidden_Layer_2,
                                           matrix=Middle_Weights_matrix),
        Output_Weights = MappingProjection(name='Output Weights',sender=Hidden_Layer_2,receiver=Output_Layer,
                                           matrix=Output_Weights_matrix)
        pathway = [Input_Layer, Input_Weights, Hidden_Layer_1, Hidden_Layer_2, Output_Layer]
        comp = Composition()
        comp.add_linear_processing_pathway(pathway=pathway)
        stim_list = {Input_Layer: [[-1, 30]]}
        results = comp.run(num_trials=2, inputs=stim_list)

    def test_add_backpropagation_learning_pathway_containing_nodes_with_existing_projections(self):
        """ Test that add_backpropagation_learning_pathway uses MappingProjections already specified for
                Hidden_layer_2 and Output_Layer in the pathway it creates within the Composition"""
        Input_Layer = TransferMechanism(name='Input Layer', size=2)
        Hidden_Layer_1 = TransferMechanism(name='Hidden Layer_1', size=5)
        Hidden_Layer_2 = TransferMechanism(name='Hidden Layer_2', size=4)
        Output_Layer = TransferMechanism(name='Output Layer', size=3)
        Input_Weights_matrix = (np.arange(2 * 5).reshape((2, 5)) + 1) / (2 * 5)
        Middle_Weights_matrix = (np.arange(5 * 4).reshape((5, 4)) + 1) / (5 * 4)
        Output_Weights_matrix = (np.arange(4 * 3).reshape((4, 3)) + 1) / (4 * 3)
        Input_Weights = MappingProjection(name='Input Weights', matrix=Input_Weights_matrix)
        Middle_Weights = MappingProjection(name='Middle Weights',sender=Hidden_Layer_1, receiver=Hidden_Layer_2,
                                           matrix=Middle_Weights_matrix),
        Output_Weights = MappingProjection(name='Output Weights',sender=Hidden_Layer_2,receiver=Output_Layer,
                                           matrix=Output_Weights_matrix)
        pathway = [Input_Layer, Input_Weights, Hidden_Layer_1, Hidden_Layer_2, Output_Layer]
        comp = Composition()
        learning_components = comp.add_backpropagation_learning_pathway(pathway=pathway)
        stim_list = {
            Input_Layer: [[-1, 30]],
            learning_components[TARGET_MECHANISM]: [[0, 0, 1]]}
        results = comp.run(num_trials=2, inputs=stim_list)

    def test_linear_processing_pathway_weights_only(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A',
                              default_variable=[[0., 0., 0.]])
        B = TransferMechanism(name='composition-pytests-B',
                              default_variable=[[0., 0.]],
                              function=Linear(slope=2.0))
        weights = [[1., 2.], [3., 4.], [5., 6.]]
        comp.add_linear_processing_pathway([A, weights, B])
        comp.run(inputs={A: [[1.1, 1.2, 1.3]]})
        assert np.allclose(A.parameters.value.get(comp), [[1.1, 1.2, 1.3]])
        assert np.allclose(B.get_input_values(comp), [[11.2,  14.8]])
        assert np.allclose(B.parameters.value.get(comp), [[22.4,  29.6]])

    def test_add_conflicting_projection_object(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        C = TransferMechanism(name='composition-pytests-C')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        proj = MappingProjection(sender=A, receiver=B)
        with pytest.raises(CompositionError) as error:
            comp.add_projection(projection=proj, receiver=C)
        assert "receiver assignment" in str(error.value)
        assert "incompatible" in str(error.value)

    @pytest.mark.stress
    @pytest.mark.parametrize(
        'count', [
            1000,
        ]
    )
    def test_timing_stress(self, count):
        t = timeit('comp.add_projection(A, MappingProjection(), B)',
                   setup="""

from psyneulink.core.components.mechanisms.processingmechanisms.transfermechanism import TransferMechanism
from psyneulink.core.components.projections.pathwayprojections.mappingprojection import MappingProjection
from psyneulink.core.compositions.composition import Composition

comp = Composition()
A = TransferMechanism(name='composition-pytests-A')
B = TransferMechanism(name='composition-pytests-B')
comp.add_node(A)
comp.add_node(B)
""",
                   number=count
                   )
        print()
        logger.info('completed {0} addition{2} of a projection to a composition in {1:.8f}s'.format(count, t, 's' if count != 1 else ''))

    @pytest.mark.stress
    @pytest.mark.parametrize(
        'count', [
            1000,
        ]
    )
    def test_timing_stress(self, count):
        t = timeit('comp.add_projection(A, MappingProjection(), B)',
                   setup="""
from psyneulink.core.components.mechanisms.processing.transfermechanism import TransferMechanism
from psyneulink.core.components.projections.pathway.mappingprojection import MappingProjection
from psyneulink.core.compositions.composition import Composition
comp = Composition()
A = TransferMechanism(name='composition-pytests-A')
B = TransferMechanism(name='composition-pytests-B')
comp.add_node(A)
comp.add_node(B)
""",
                   number=count
                   )
        print()
        logger.info('completed {0} addition{2} of a projection to a composition in {1:.8f}s'.format(count, t, 's' if count != 1 else ''))


class TestAnalyzeGraph:

    def test_empty_call(self):
        comp = Composition()
        comp._analyze_graph()

    def test_singleton(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        comp.add_node(A)
        comp._analyze_graph()
        assert A in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert A in comp.get_nodes_by_role(NodeRole.TERMINAL)

    def test_two_independent(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        comp._analyze_graph()
        assert A in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert B in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert A in comp.get_nodes_by_role(NodeRole.TERMINAL)
        assert B in comp.get_nodes_by_role(NodeRole.TERMINAL)

    def test_two_in_a_row(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(), A, B)
        comp._analyze_graph()
        assert A in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert B not in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert A not in comp.get_nodes_by_role(NodeRole.TERMINAL)
        assert B in comp.get_nodes_by_role(NodeRole.TERMINAL)

    # (A)<->(B)
    def test_two_recursive(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(), A, B)

        comp.add_projection(MappingProjection(), B, A)
        comp._analyze_graph()
        assert A in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert B in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert A in comp.get_nodes_by_role(NodeRole.TERMINAL)
        assert B in comp.get_nodes_by_role(NodeRole.TERMINAL)

    # (A)->(B)<->(C)<-(D)
    @pytest.mark.skip
    def test_two_origins_pointing_to_recursive_pair(self):
        comp = Composition()
        A = TransferMechanism(name='composition-pytests-A')
        B = TransferMechanism(name='composition-pytests-B')
        C = TransferMechanism(name='composition-pytests-C')
        D = TransferMechanism(name='composition-pytests-D')
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(), A, B)
        comp.add_projection(MappingProjection(), C, B)
        comp.add_projection(MappingProjection(), B, C)
        comp.add_projection(MappingProjection(), D, C)
        comp._analyze_graph()
        assert A in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert D in comp.get_nodes_by_role(NodeRole.ORIGIN)
        assert B in comp.get_nodes_by_role(NodeRole.CYCLE)
        assert C in comp.get_nodes_by_role(NodeRole.RECURRENT_INIT)

    def test_controller_objective_mech_not_terminal(self):
        comp = Composition()
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        comp.add_linear_processing_pathway([A, B])
        comp.add_controller(controller=pnl.OptimizationControlMechanism(agent_rep=comp,
                                                                        features=[A.input_port],
                                                                        objective_mechanism=pnl.ObjectiveMechanism(
                                                                                function=pnl.LinearCombination(
                                                                                        operation=pnl.PRODUCT),
                                                                                monitor=[A]),
                                                                        function=pnl.GridSearch(),
                                                                        control_signals=[
                                                                            {PROJECTIONS:("slope", B),
                                                                             ALLOCATION_SAMPLES:np.arange(0.1,
                                                                                                          1.01,
                                                                                                          0.3)}]
                                                                        )
                                       )
        comp._analyze_graph()
        assert comp.controller.objective_mechanism not in comp.get_nodes_by_role(NodeRole.OUTPUT)

        # disable controller
        comp.enable_controller = False
        comp._analyze_graph()
        # assert comp.controller.objective_mechanism in comp.get_nodes_by_role(NodeRole.OUTPUT)
        assert comp.controller.objective_mechanism not in comp.get_nodes_by_role(NodeRole.OUTPUT)

    def test_controller_objective_mech_not_terminal_fall_back(self):
        comp = Composition()
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        comp.add_linear_processing_pathway([A, B])

        comp.add_controller(controller=pnl.OptimizationControlMechanism(agent_rep=comp,
                                                                        features=[A.input_port],
                                                                        objective_mechanism=pnl.ObjectiveMechanism(
                                                                                function=pnl.LinearCombination(
                                                                                        operation=pnl.PRODUCT),
                                                                                monitor=[A, B]),
                                                                        function=pnl.GridSearch(),
                                                                        control_signals=[
                                                                            {PROJECTIONS:("slope", B),
                                                                             ALLOCATION_SAMPLES:np.arange(0.1,
                                                                                                          1.01,
                                                                                                          0.3)}]
                                                                        )
                                       )
        comp._analyze_graph()
        # ObjectiveMechanism associated with controller should not be considered an OUTPUT node
        assert comp.controller.objective_mechanism not in comp.get_nodes_by_role(NodeRole.OUTPUT)
        assert B in comp.get_nodes_by_role(NodeRole.OUTPUT)

        # disable controller
        comp.enable_controller = False
        comp._analyze_graph()

        # assert comp.controller.objective_mechanism in comp.get_nodes_by_role(NodeRole.OUTPUT)
        # assert B not in comp.get_nodes_by_role(NodeRole.OUTPUT)

        # ObjectiveMechanism associated with controller should be treated the same (i.e., not be an OUTPUT node)
        #    irrespective of whether the controller is enabled or disabled
        assert comp.controller.objective_mechanism not in comp.get_nodes_by_role(NodeRole.OUTPUT)
        assert B in comp.get_nodes_by_role(NodeRole.OUTPUT)


class TestGraphCycles:

    def test_recurrent_transfer_mechanisms(self):
        R1 = RecurrentTransferMechanism(auto=1.0)
        R2 = RecurrentTransferMechanism(auto=1.0,
                                        function=Linear(slope=2.0))
        comp = Composition()
        comp.add_linear_processing_pathway(pathway=[R1, R2])

        # Trial 0:
        # input to R1 = 1.0, output from R1 = 1.0
        # input to R2 = 1.0, output from R2 = 2.0

        # Trial 1:
        # input to R1 = 1.0 + 1.0, output from R1 = 2.0
        # input to R2 = 2.0 + 2.0, output from R2 = 8.0

        # Trial 2:
        # input to R1 = 1.0 + 2.0, output from R1 = 3.0
        # input to R2 = 3.0 + 8.0, output from R2 = 22.0


        output = comp.run(inputs={R1: [1.0]}, num_trials=3)
        assert np.allclose(output, [[np.array([22.])]])


class TestExecutionOrder:
    def test_2_node_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")

        comp = Composition(name="comp")
        comp.add_linear_processing_pathway([A, B, C, D])
        comp.add_linear_processing_pathway([C, B])

        comp.run(inputs={A: 1.0})

    def test_double_loop(self):
        A1 = ProcessingMechanism(name="A1")
        A2 = ProcessingMechanism(name="A2")
        B1 = ProcessingMechanism(name="B1")
        B2 = ProcessingMechanism(name="B2")
        C1 = ProcessingMechanism(name="C1")
        C2 = ProcessingMechanism(name="C2")
        D = ProcessingMechanism(name="D")

        comp = Composition(name="comp")
        comp.add_linear_processing_pathway([A1, A2, D])
        comp.add_linear_processing_pathway([B1, B2, D])
        comp.add_linear_processing_pathway([C1, C2, D])
        comp.add_linear_processing_pathway([A2, B2])
        comp.add_linear_processing_pathway([B2, A2])
        comp.add_linear_processing_pathway([C2, B2])
        comp.add_linear_processing_pathway([B2, C2])

        comp.run(inputs={A1: 1.0,
                         B1: 1.0,
                         C1: 1.0})

    def test_feedback_pathway_spec(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        # comp.add_linear_processing_pathway([D, MappingProjection(matrix=4.0), B], feedback=True)
        comp.add_linear_processing_pathway([D, (MappingProjection(matrix=4.0), True), B])

        comp.run(inputs={A: 1.0})

        expected_consideration_queue = [{A}, {B}, {C}, {D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(comp.nodes)))

        expected_results = {A: 1.0,
                            B: 1.0,
                            C: 2.0,
                            D: 6.0,
                            E: 6.0}

        assert all(expected_results[mech] == mech.parameters.value.get(comp) for mech in expected_results)

        comp.run(inputs={A: 1.0})

        expected_results_2 = {A: 1.0,
                              B: 25.0,
                              C: 50.0,
                              D: 150.0,
                              E: 150.0}

        assert all(expected_results_2[mech] == mech.parameters.value.get(comp) for mech in expected_results_2)

    def test_feedback_projection_spec(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_projection(projection=MappingProjection(matrix=4.0), sender=D, receiver=B, feedback=True)

        comp.run(inputs={A: 1.0})

        expected_consideration_queue = [{A}, {B}, {C}, {D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(comp.nodes)))

        expected_results = {A: 1.0,
                            B: 1.0,
                            C: 2.0,
                            D: 6.0,
                            E: 6.0}

        assert all(expected_results[mech] == mech.parameters.value.get(comp) for mech in expected_results)

        comp.run(inputs={A: 1.0})

        expected_results_2 = {A: 1.0,
                              B: 25.0,
                              C: 50.0,
                              D: 150.0,
                              E: 150.0}

        assert all(expected_results_2[mech] == mech.parameters.value.get(comp) for mech in expected_results_2)

    def test_outer_feedback_inner_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_projection(projection=MappingProjection(matrix=4.0), sender=D, receiver=B, feedback=True)
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=D, receiver=C, feedback=False)

        expected_consideration_queue = [{A}, {B}, {C, D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

    def test_inner_feedback_outer_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=D, receiver=B, feedback=False)
        comp.add_projection(projection=MappingProjection(matrix=4.0), sender=D, receiver=C, feedback=True)

        expected_consideration_queue = [{A}, {B, C, D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

    def test_origin_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=B, receiver=A, feedback=False)
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=C, receiver=B, feedback=False)

        expected_consideration_queue = [{A, B, C}, {D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

        comp._analyze_graph()
        assert set(comp.get_nodes_by_role(NodeRole.ORIGIN)) == expected_consideration_queue[0]

        new_origin = ProcessingMechanism(name="new_origin")
        comp.add_linear_processing_pathway([new_origin, B])

        expected_consideration_queue = [{new_origin}, {A, B, C}, {D}, {E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

        comp._analyze_graph()
        assert set(comp.get_nodes_by_role(NodeRole.ORIGIN)) == expected_consideration_queue[0]

    def test_terminal_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=E, receiver=D, feedback=False)
        comp.add_projection(projection=MappingProjection(matrix=1.0), sender=D, receiver=C, feedback=False)

        expected_consideration_queue = [{A}, {B}, {C, D, E}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

        comp._analyze_graph()
        assert set(comp.get_nodes_by_role(NodeRole.TERMINAL)) == expected_consideration_queue[-1]

        new_terminal = ProcessingMechanism(name="new_terminal")
        comp.add_linear_processing_pathway([D, new_terminal])

        expected_consideration_queue = [{A}, {B}, {C, D, E}, {new_terminal}]
        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i]
                   for i in range(len(expected_consideration_queue)))

        comp._analyze_graph()
        assert set(comp.get_nodes_by_role(NodeRole.TERMINAL)) == expected_consideration_queue[-1]


    def test_simple_loop(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, MappingProjection(matrix=3.0), D, E])
        comp.add_linear_processing_pathway([D, MappingProjection(matrix=4.0), B])

        D.set_log_conditions("OutputPort-0")
        cycle_nodes = [B, C, D]
        for cycle_node in cycle_nodes:
            cycle_node.output_ports[0].value = [1.0]

        comp.run(inputs={A: [1.0]})
        expected_values = {A: 1.0,
                           B: 5.0,
                           C: 2.0,
                           D: 3.0,
                           E: 3.0}

        for node in expected_values:
            assert np.allclose(expected_values[node], node.parameters.value.get(comp))

        comp.run(inputs={A: [1.0]})
        expected_values_2 = {A: 1.0,
                             B: 13.0,
                             C: 10.0,
                             D: 6.0,
                             E: 6.0}

        print(D.log.nparray_dictionary(["OutputPort-0"]))
        for node in expected_values:
            assert np.allclose(expected_values_2[node], node.parameters.value.get(comp))



    def test_loop_with_extra_node(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        C2 = ProcessingMechanism(name="C2")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()

        cycle_nodes = [B, C, D, C2]
        for cycle_node in cycle_nodes:
            cycle_node.output_ports[0].parameters.value.set([1.0], override=True)

        comp.add_linear_processing_pathway([A, B, MappingProjection(matrix=2.0), C, D, MappingProjection(matrix=5.0), E])
        comp.add_linear_processing_pathway([D, MappingProjection(matrix=3.0), C2, MappingProjection(matrix=4.0), B])

        expected_consideration_queue = [{A}, {B, C, D, C2}, {E}]

        assert all(expected_consideration_queue[i] == comp.scheduler.consideration_queue[i] for i in range(3))
        comp.run(inputs={A: [1.0]})

        expected_values = {A: 1.0,
                           B: 5.0,
                           C: 2.0,
                           D: 1.0,
                           C2: 3.0,
                           E: 5.0}

        for node in expected_values:
            assert np.allclose(expected_values[node], node.parameters.value.get(comp))

        comp.run(inputs={A: [1.0]})
        expected_values_2 = {A: 1.0,
                             B: 13.0,
                             C: 10.0,
                             D: 2.0,
                             C2: 3.0,
                             E: 10.0}

        for node in expected_values:
            assert np.allclose(expected_values_2[node], node.parameters.value.get(comp))

    def test_two_overlapping_loops(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        C2 = ProcessingMechanism(name="C2")
        C3 = ProcessingMechanism(name="C3")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, C, D, E])
        comp.add_linear_processing_pathway([D, C2, B])
        comp.add_linear_processing_pathway([D, C3, B])

        comp.run(inputs={A: [1.0]})

        assert comp.scheduler.consideration_queue[0] == {A}
        assert comp.scheduler.consideration_queue[1] == {B, C, D, C2, C3}
        assert comp.scheduler.consideration_queue[2] == {E}

    def test_two_separate_loops(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        L1 = ProcessingMechanism(name="L1")
        L2 = ProcessingMechanism(name="L2")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")
        F = ProcessingMechanism(name="F")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, C, D, E, F])
        comp.add_linear_processing_pathway([E, L1, D])
        comp.add_linear_processing_pathway([C, L2, B])

        comp.run(inputs={A: [1.0]})

        assert comp.scheduler.consideration_queue[0] == {A}
        assert comp.scheduler.consideration_queue[1] == {C, L2, B}
        assert comp.scheduler.consideration_queue[2] == {E, L1, D}
        assert comp.scheduler.consideration_queue[3] == {F}

    def test_two_paths_converge(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([A, B, C, D])
        comp.add_linear_processing_pathway([E, D])

        comp.run(inputs={A: 1.0,
                         E: 1.0})

        assert comp.scheduler.consideration_queue[0] == {A, E}
        assert comp.scheduler.consideration_queue[1] == {B}
        assert comp.scheduler.consideration_queue[2] == {C}
        assert comp.scheduler.consideration_queue[3] == {D}

    def test_diverge_and_reconverge(self):
        S = ProcessingMechanism(name="START")
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp = Composition()
        comp.add_linear_processing_pathway([S, A, B, C, D])
        comp.add_linear_processing_pathway([S, E, D])

        comp.run(inputs={S: 1.0})

        assert comp.scheduler.consideration_queue[0] == {S}
        assert comp.scheduler.consideration_queue[1] == {A, E}
        assert comp.scheduler.consideration_queue[2] == {B}
        assert comp.scheduler.consideration_queue[3] == {C}
        assert comp.scheduler.consideration_queue[4] == {D}

    def test_diverge_and_reconverge_2(self):
        S = ProcessingMechanism(name="START")
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")
        F = ProcessingMechanism(name="F")
        G = ProcessingMechanism(name="G")

        comp = Composition()
        comp.add_linear_processing_pathway([S, A, B, C, D])
        comp.add_linear_processing_pathway([S, E, F, G, D])

        comp.run(inputs={S: 1.0})

        assert comp.scheduler.consideration_queue[0] == {S}
        assert comp.scheduler.consideration_queue[1] == {A, E}
        assert comp.scheduler.consideration_queue[2] == {B, F}
        assert comp.scheduler.consideration_queue[3] == {C, G}
        assert comp.scheduler.consideration_queue[4] == {D}

    def test_figure_eight(self):
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C1 = ProcessingMechanism(name="C1")
        D1 = ProcessingMechanism(name="D1")
        C2 = ProcessingMechanism(name="C2")
        D2 = ProcessingMechanism(name="D2")

        comp = Composition()

        comp.add_linear_processing_pathway([A, B])
        comp.add_linear_processing_pathway([B, C1, D1])
        comp.add_linear_processing_pathway([B, C2, D2])
        comp.add_linear_processing_pathway([D1, B])
        comp.add_linear_processing_pathway([D2, B])

        assert comp.scheduler.consideration_queue[0] == {A}
        assert comp.scheduler.consideration_queue[1] == {B, C1, D1, C2, D2}

    def test_many_loops(self):

        comp = Composition()

        start = ProcessingMechanism(name="start")
        expected_consideration_sets = [{start}]
        for i in range(10):
            A = ProcessingMechanism(name='A' + str(i))
            B = ProcessingMechanism(name='B' + str(i))
            C = ProcessingMechanism(name='C' + str(i))
            D = ProcessingMechanism(name='D' + str(i))

            comp.add_linear_processing_pathway([start, A, B, C, D])
            comp.add_linear_processing_pathway([C, B])

            expected_consideration_sets.append({A})
            expected_consideration_sets.append({B, C})
            expected_consideration_sets.append({D})

            start = D

        for i in range(len(comp.scheduler.consideration_queue)):
            assert comp.scheduler.consideration_queue[i] == expected_consideration_sets[i]

    def test_multiple_projections_along_pathway(self):

        comp = Composition()
        A = ProcessingMechanism(name="A")
        B = ProcessingMechanism(name="B")
        C = ProcessingMechanism(name="C")
        D = ProcessingMechanism(name="D")
        E = ProcessingMechanism(name="E")

        comp.add_linear_processing_pathway([A, B, C, D, E])
        comp.add_linear_processing_pathway([A, C])
        comp.add_linear_processing_pathway([C, E])

        expected_consideration_queue = [{A}, {B}, {C}, {D}, {E}]

        assert expected_consideration_queue == comp.scheduler.consideration_queue

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Frozen values")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_frozen_values(self, benchmark, mode):
        #
        #   B
        #  /|\
        # A-+-D
        #  \|/
        #   C
        #
        # A: 4 x 5 = 20
        # B: (20 + 0) x 4 = 80
        # C: (20 + 0) x 3 = 60
        # D: (20 + 80 + 60) x 2 = 320

        comp = Composition()
        A = TransferMechanism(name="A", function=Linear(slope=5.0))
        B = TransferMechanism(name="B", function=Linear(slope=4.0))
        C = TransferMechanism(name="C", function=Linear(slope=3.0))
        D = TransferMechanism(name="D", function=Linear(slope=2.0))
        comp.add_linear_processing_pathway([A, D])
        comp.add_linear_processing_pathway([B, C])
        comp.add_linear_processing_pathway([C, B])
        comp.add_linear_processing_pathway([A, B, D])
        comp.add_linear_processing_pathway([A, C, D])

        inputs_dict = {A: [4.0]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(output, 320)
        benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Control composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_multi_control_1_terminal(self, benchmark, mode):
        #
        #   A--LC
        #  /    \
        # B------C
        #  \     |
        #   -----+-> D
        #
        # B: 4 x 5 = 20
        # A: 20 x 1 = 20
        # LC: f(20)[0] = 0.50838675
        # C: 20 x 5 x 0.50838675 = 50.83865743
        # D: (20 + 50.83865743) x 5 = 354.19328716

        comp = Composition()
        B = TransferMechanism(name="B", function=Linear(slope=5.0))
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        A = ObjectiveMechanism(function=Linear,
                               monitor=[B],
                               name="A")
        LC = LCControlMechanism(name="LC",
                               modulated_mechanisms=C,
                               objective_mechanism=A)
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        comp.add_linear_processing_pathway([B, C, D])
        comp.add_linear_processing_pathway([B, D])
        comp.add_node(A)
        comp.add_node(LC)


        inputs_dict = {B: [4.0]}
        # sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict,
                          # scheduler=sched,
                          bin_execute=mode)
        assert np.allclose(output, 354.19328716)
        benchmark(comp.run, inputs=inputs_dict,
                  # scheduler=sched,
                  bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Control composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_additive_control_1_terminal(self, benchmark, mode):
        #
        #   A--LC
        #  /    \
        # B------C
        #  \     |
        #   -----+-> D
        #
        # B: 4 x 5 = 20
        # A: 20 x 1 = 20
        # LC: f(20)[0] = 0.50838675
        # C: 20 x 5 + 0.50838675 = 100.50838675
        # D: (20 + 100.50838675) x 5 = 650.83865743

        comp = Composition()
        B = TransferMechanism(name="B", function=Linear(slope=5.0))
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        A = ObjectiveMechanism(function=Linear,
                               monitor=[B],
                               name="A")
        LC = LCControlMechanism(name="LC", modulation=ADDITIVE,
                               modulated_mechanisms=C,
                               objective_mechanism=A)
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        comp.add_linear_processing_pathway([B, C, D])
        comp.add_linear_processing_pathway([B, D])
        comp.add_node(A)
        comp.add_node(LC)

        inputs_dict = {B: [4.0]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(output, 650.83865743)
        benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Control composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_override_control_1_terminal(self, benchmark, mode):
        #
        #   A--LC
        #  /    \
        # B------C
        #  \     |
        #   -----+-> D
        #
        # B: 4 x 5 = 20
        # A: 20 x 1 = 20
        # LC: f(20)[0] = 0.50838675
        # C: 20 x 0.50838675 = 10.167735
        # D: (20 + 10.167735) x 5 = 150.83865743

        comp = Composition()
        B = TransferMechanism(name="B", function=Linear(slope=5.0))
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        A = ObjectiveMechanism(function=Linear,
                               monitor=[B],
                               name="A")
        LC = LCControlMechanism(name="LC", modulation=OVERRIDE,
                               modulated_mechanisms=C,
                               objective_mechanism=A)
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        comp.add_linear_processing_pathway([B, C, D])
        comp.add_linear_processing_pathway([B, D])
        comp.add_node(A)
        comp.add_node(LC)


        inputs_dict = {B: [4.0]}
        # sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict,
                          # scheduler=sched,
                          bin_execute=mode)
        assert np.allclose(output, 150.83865743)
        benchmark(comp.run, inputs=inputs_dict,
                  # scheduler=sched,
                  bin_execute=mode)

    @pytest.mark.control
    @pytest.mark.composition
    @pytest.mark.benchmark(group="Control composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_disable_control_1_terminal(self, benchmark, mode):
        #
        #   A--LC
        #  /    \
        # B------C
        #  \     |
        #   -----+-> D
        #
        # B: 4 x 5 = 20
        # A: 20 x 1 = 20
        # LC: f(20)[0] = 0.50838675
        # C: 20 x 5 = 100
        # D: (20 + 100) x 5 = 600

        comp = Composition()
        B = TransferMechanism(name="B", function=Linear(slope=5.0))
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        A = ObjectiveMechanism(function=Linear,
                               monitor=[B],
                               name="A")
        LC = LCControlMechanism(name="LC", modulation=DISABLE,
                               modulated_mechanisms=C,
                               objective_mechanism=A)
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        comp.add_linear_processing_pathway([B, C, D])
        comp.add_linear_processing_pathway([B, D])
        comp.add_node(A)
        comp.add_node(LC)


        inputs_dict = {B: [4.0]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(output, 600)
        benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Transfer")
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm),
                             pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                             pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                             ])
    def test_transfer_mechanism(self, benchmark, mode):

        # mechanisms
        C = TransferMechanism(name="C",
                              function=Logistic,
                              integration_rate=0.1,
                              integrator_mode=True)

        # comp2 uses a TransferMechanism in integrator mode
        comp2 = Composition(name="comp2")
        comp2.add_node(C)

        # pass same 3 trials of input to comp1 and comp2
        benchmark(comp2.run, inputs={C: [1.0, 2.0, 3.0]}, bin_execute=mode)

        assert np.allclose(comp2.results[:3], [[[0.52497918747894]], [[0.5719961329315186]], [[0.6366838893983633]]])

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Transfer")
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm),
                             pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                             pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                             ])
    def test_transfer_mechanism_split(self, benchmark, mode):

        # mechanisms
        A = ProcessingMechanism(name="A",
                                function=AdaptiveIntegrator(rate=0.1))
        B = ProcessingMechanism(name="B",
                                function=Logistic)

        # comp1 separates IntegratorFunction fn and Logistic fn into mech A and mech B
        comp1 = Composition(name="comp1")
        comp1.add_linear_processing_pathway([A, B])

        benchmark(comp1.run, inputs={A: [1.0, 2.0, 3.0]}, bin_execute=mode)

        assert np.allclose(comp1.results[:3], [[[0.52497918747894]], [[0.5719961329315186]], [[0.6366838893983633]]])


class TestGetMechanismsByRole:

    def test_multiple_roles(self):

        comp = Composition()
        mechs = [TransferMechanism() for x in range(4)]

        for mech in mechs:
            comp.add_node(mech)

        comp._add_node_role(mechs[0], NodeRole.ORIGIN)
        comp._add_node_role(mechs[1], NodeRole.INTERNAL)
        comp._add_node_role(mechs[2], NodeRole.INTERNAL)

        for role in list(NodeRole):
            if role is NodeRole.ORIGIN:
                assert comp.get_nodes_by_role(role) == [mechs[0]]
            elif role is NodeRole.INTERNAL:
                assert comp.get_nodes_by_role(role) == [mechs[1], mechs[2]]
            else:
                assert comp.get_nodes_by_role(role) == []

    @pytest.mark.xfail(raises=CompositionError)
    def test_nonexistent_role(self):
        comp = Composition()
        comp.get_nodes_by_role(None)


class TestGraph:

    class TestProcessingGraph:

        def test_all_mechanisms(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            mechs = [A, B, C]
            for m in mechs:
                comp.add_node(m)

            assert len(comp.graph_processing.vertices) == 3
            assert len(comp.graph_processing.comp_to_vertex) == 3
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert comp.graph_processing.get_parents_from_component(A) == []
            assert comp.graph_processing.get_parents_from_component(B) == []
            assert comp.graph_processing.get_parents_from_component(C) == []

            assert comp.graph_processing.get_children_from_component(A) == []
            assert comp.graph_processing.get_children_from_component(B) == []
            assert comp.graph_processing.get_children_from_component(C) == []

        def test_triangle(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            mechs = [A, B, C]
            for m in mechs:
                comp.add_node(m)
            comp.add_projection(MappingProjection(), A, B)
            comp.add_projection(MappingProjection(), B, C)

            assert len(comp.graph_processing.vertices) == 3
            assert len(comp.graph_processing.comp_to_vertex) == 3
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert comp.graph_processing.get_parents_from_component(A) == []
            assert comp.graph_processing.get_parents_from_component(B) == [comp.graph_processing.comp_to_vertex[A]]
            assert comp.graph_processing.get_parents_from_component(C) == [comp.graph_processing.comp_to_vertex[B]]

            assert comp.graph_processing.get_children_from_component(A) == [comp.graph_processing.comp_to_vertex[B]]
            assert comp.graph_processing.get_children_from_component(B) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_children_from_component(C) == []

        def test_x(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            D = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-D')
            E = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-E')
            mechs = [A, B, C, D, E]
            for m in mechs:
                comp.add_node(m)
            comp.add_projection(MappingProjection(), A, C)
            comp.add_projection(MappingProjection(), B, C)
            comp.add_projection(MappingProjection(), C, D)
            comp.add_projection(MappingProjection(), C, E)

            assert len(comp.graph_processing.vertices) == 5
            assert len(comp.graph_processing.comp_to_vertex) == 5
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert comp.graph_processing.get_parents_from_component(A) == []
            assert comp.graph_processing.get_parents_from_component(B) == []
            assert set(comp.graph_processing.get_parents_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[A],
                comp.graph_processing.comp_to_vertex[B],
            ])
            assert comp.graph_processing.get_parents_from_component(D) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_parents_from_component(E) == [comp.graph_processing.comp_to_vertex[C]]

            assert comp.graph_processing.get_children_from_component(A) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_children_from_component(B) == [comp.graph_processing.comp_to_vertex[C]]
            assert set(comp.graph_processing.get_children_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[D],
                comp.graph_processing.comp_to_vertex[E],
            ])
            assert comp.graph_processing.get_children_from_component(D) == []
            assert comp.graph_processing.get_children_from_component(E) == []

        def test_cycle_linear(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            mechs = [A, B, C]
            for m in mechs:
                comp.add_node(m)
            comp.add_projection(MappingProjection(), A, B)
            comp.add_projection(MappingProjection(), B, C)
            comp.add_projection(MappingProjection(), C, A)

            assert len(comp.graph_processing.vertices) == 3
            assert len(comp.graph_processing.comp_to_vertex) == 3
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert comp.graph_processing.get_parents_from_component(A) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_parents_from_component(B) == [comp.graph_processing.comp_to_vertex[A]]
            assert comp.graph_processing.get_parents_from_component(C) == [comp.graph_processing.comp_to_vertex[B]]

            assert comp.graph_processing.get_children_from_component(A) == [comp.graph_processing.comp_to_vertex[B]]
            assert comp.graph_processing.get_children_from_component(B) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_children_from_component(C) == [comp.graph_processing.comp_to_vertex[A]]

        def test_cycle_x(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            D = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-D')
            E = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-E')
            mechs = [A, B, C, D, E]
            for m in mechs:
                comp.add_node(m)
            comp.add_projection(MappingProjection(), A, C)
            comp.add_projection(MappingProjection(), B, C)
            comp.add_projection(MappingProjection(), C, D)
            comp.add_projection(MappingProjection(), C, E)
            comp.add_projection(MappingProjection(), D, A)
            comp.add_projection(MappingProjection(), E, B)

            assert len(comp.graph_processing.vertices) == 5
            assert len(comp.graph_processing.comp_to_vertex) == 5
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert comp.graph_processing.get_parents_from_component(A) == [comp.graph_processing.comp_to_vertex[D]]
            assert comp.graph_processing.get_parents_from_component(B) == [comp.graph_processing.comp_to_vertex[E]]
            assert set(comp.graph_processing.get_parents_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[A],
                comp.graph_processing.comp_to_vertex[B],
            ])
            assert comp.graph_processing.get_parents_from_component(D) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_parents_from_component(E) == [comp.graph_processing.comp_to_vertex[C]]

            assert comp.graph_processing.get_children_from_component(A) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_children_from_component(B) == [comp.graph_processing.comp_to_vertex[C]]
            assert set(comp.graph_processing.get_children_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[D],
                comp.graph_processing.comp_to_vertex[E],
            ])
            assert comp.graph_processing.get_children_from_component(D) == [comp.graph_processing.comp_to_vertex[A]]
            assert comp.graph_processing.get_children_from_component(E) == [comp.graph_processing.comp_to_vertex[B]]

        def test_cycle_x_multiple_incoming(self):
            comp = Composition()
            A = TransferMechanism(function=Linear(slope=5.0, intercept=2.0), name='composition-pytests-A')
            B = TransferMechanism(function=Linear(intercept=4.0), name='composition-pytests-B')
            C = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-C')
            D = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-D')
            E = TransferMechanism(function=Linear(intercept=1.5), name='composition-pytests-E')
            mechs = [A, B, C, D, E]
            for m in mechs:
                comp.add_node(m)
            comp.add_projection(MappingProjection(), A, C)
            comp.add_projection(MappingProjection(), B, C)
            comp.add_projection(MappingProjection(), C, D)
            comp.add_projection(MappingProjection(), C, E)
            comp.add_projection(MappingProjection(), D, A)
            comp.add_projection(MappingProjection(), D, B)
            comp.add_projection(MappingProjection(), E, A)
            comp.add_projection(MappingProjection(), E, B)

            assert len(comp.graph_processing.vertices) == 5
            assert len(comp.graph_processing.comp_to_vertex) == 5
            for m in mechs:
                assert m in comp.graph_processing.comp_to_vertex

            assert set(comp.graph_processing.get_parents_from_component(A)) == set([
                comp.graph_processing.comp_to_vertex[D],
                comp.graph_processing.comp_to_vertex[E],
            ])
            assert set(comp.graph_processing.get_parents_from_component(B)) == set([
                comp.graph_processing.comp_to_vertex[D],
                comp.graph_processing.comp_to_vertex[E],
            ])
            assert set(comp.graph_processing.get_parents_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[A],
                comp.graph_processing.comp_to_vertex[B],
            ])
            assert comp.graph_processing.get_parents_from_component(D) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_parents_from_component(E) == [comp.graph_processing.comp_to_vertex[C]]

            assert comp.graph_processing.get_children_from_component(A) == [comp.graph_processing.comp_to_vertex[C]]
            assert comp.graph_processing.get_children_from_component(B) == [comp.graph_processing.comp_to_vertex[C]]
            assert set(comp.graph_processing.get_children_from_component(C)) == set([
                comp.graph_processing.comp_to_vertex[D],
                comp.graph_processing.comp_to_vertex[E],
            ])
            assert set(comp.graph_processing.get_children_from_component(D)) == set([
                comp.graph_processing.comp_to_vertex[A],
                comp.graph_processing.comp_to_vertex[B],
            ])
            assert set(comp.graph_processing.get_children_from_component(E)) == set([
                comp.graph_processing.comp_to_vertex[A],
                comp.graph_processing.comp_to_vertex[B],
            ])


class TestRun:

    # def test_run_2_mechanisms_default_input_1(self):
    #     comp = Composition()
    #     A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
    #     B = TransferMechanism(function=Linear(slope=5.0))
    #     comp.add_node(A)
    #     comp.add_node(B)
    #     comp.add_projection(A, MappingProjection(sender=A, receiver=B), B)
    #     sched = Scheduler(composition=comp)
    #     output = comp.run(
    #         scheduler=sched
    #     )
    #     assert 25 == output[0][0]

    @pytest.mark.projection
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_input_grow(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=[1.0, 2.0], function=Linear(slope=5.0))
        B = TransferMechanism(default_variable=[1.0, 2.0, 3.0], function=Linear(slope=5.0))
        P = MappingProjection(sender=A, receiver=B)
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(P, A, B)
        inputs_dict = {A: [5, 4]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(output, [[225, 225, 225]])

    @pytest.mark.projection
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_input_shrink(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=[1.0, 2.0, 3.0], function=Linear(slope=5.0))
        B = TransferMechanism(default_variable=[4.0, 5.0], function=Linear(slope=5.0))
        P = MappingProjection(sender=A, receiver=B)
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(P, A, B)
        inputs_dict = {A: [5, 4, 3]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode
        )
        assert np.allclose(output, [[300, 300]])

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_input_5(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [5]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(125, output[0][0])

    def test_projection_assignment_mistake_swap(self):

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=C), A, C)
        with pytest.raises(CompositionError) as error_text:
            comp.add_projection(MappingProjection(sender=B, receiver=D), B, C)
        assert "is incompatible with the positions of these Components in the Composition" in str(error_text.value)

    def test_projection_assignment_mistake_swap2(self):
        # A ----> C --
        #              ==> E
        # B ----> D --

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=C), A, C)
        with pytest.raises(CompositionError) as error_text:
            comp.add_projection(MappingProjection(sender=B, receiver=C), B, D)

        assert "is incompatible with the positions of these Components in the Composition" in str(error_text.value)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_5_mechanisms_2_origins_1_terminal(self, mode):
        # A ----> C --
        #              ==> E
        # B ----> D --

        # 5 x 1 = 5 ----> 5 x 5 = 25 --
        #                                25 + 25 = 50  ==> 50 * 5 = 250
        # 5 * 1 = 5 ----> 5 x 5 = 25 --

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=C), A, C)
        comp.add_projection(MappingProjection(sender=B, receiver=D), B, D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=D, receiver=E), D, E)
        inputs_dict = {A: [5],
                       B: [5]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)

        assert np.allclose([250], output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python']) # LLVM needs SimpleIntegrator
    def test_run_2_mechanisms_with_scheduling_AAB_integrator(self, mode):
        comp = Composition()

        A = IntegratorMechanism(name="A [integrator]", default_variable=2.0, function=SimpleIntegrator(rate=1.0))
        # (1) value = 0 + (5.0 * 1.0) + 0  --> return 5.0
        # (2) value = 5.0 + (5.0 * 1.0) + 0  --> return 10.0
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        # value = 10.0 * 5.0 --> return 50.0
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [5]}
        sched = Scheduler(composition=comp)
        sched.add_condition(B, EveryNCalls(A, 2))
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)

        assert np.allclose(50.0, output[0][0])

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_with_scheduling_AAB_transfer(self, mode):
        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        # (1) value = 5.0 * 2.0  --> return 10.0
        # (2) value = 5.0 * 2.0  --> return 10.0
        # ** TransferMechanism runs with the SAME input **
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        # value = 10.0 * 5.0 --> return 50.0
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [5]}
        sched = Scheduler(composition=comp)
        sched.add_condition(B, EveryNCalls(A, 2))
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(50.0, output[0][0])

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_with_multiple_trials_of_input_values(self, mode):
        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [1, 2, 3, 4]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)

        assert np.allclose([[[40.0]]], output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_sender_receiver_not_specified(self, mode):
        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(), A, B)
        inputs_dict = {A: [1, 2, 3, 4]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)

        assert np.allclose([[40.0]], output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_reuse_input(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [5]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, num_trials=5, bin_execute=mode)
        assert np.allclose([125], output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_2_mechanisms_double_trial_specs(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[5], [4], [3]]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, num_trials=3, bin_execute=mode)

        assert np.allclose(np.array([[75.]]), output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_execute_composition(self, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp._analyze_graph()
        inputs_dict = {A: 3}
        sched = Scheduler(composition=comp)
        output = comp.execute(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([75], output)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="LPP")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_LPP(self, benchmark, mode):

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0, intercept=1.0))   # 1 x 2 + 1 = 3
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0, intercept=2.0))   # 3 x 2 + 2 = 8
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=2.0, intercept=3.0))   # 8 x 2 + 3 = 19
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=2.0, intercept=4.0))   # 19 x 2 + 4 = 42
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=2.0, intercept=5.0))   # 42 x 2 + 5 = 89
        comp.add_linear_processing_pathway([A, B, C, D, E])
        comp._analyze_graph()
        inputs_dict = {A: [[1]]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.execute, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(89., output)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_LPP_with_projections(self, mode):
        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))  # 1 x 2 = 2
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))  # 2 x 2 = 4
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=2.0))  # 4 x 2 = 8
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=2.0))  # 8 x 2 = 16
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=2.0))  # 16 x 2 = 32
        A_to_B = MappingProjection(sender=A, receiver=B)
        D_to_E = MappingProjection(sender=D, receiver=E)
        comp.add_linear_processing_pathway([A, A_to_B, B, C, D, D_to_E, E])
        comp._analyze_graph()
        inputs_dict = {A: [[1]]}
        sched = Scheduler(composition=comp)
        output = comp.execute(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(32., output)

    def test_LPP_end_with_projection(self):
        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=2.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=2.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=2.0))
        A_to_B = MappingProjection(sender=A, receiver=B)
        C_to_E = MappingProjection(sender=C, receiver=E)
        with pytest.raises(CompositionError) as error_text:
            comp.add_linear_processing_pathway([A, A_to_B, B, C, D, E, C_to_E])

        assert "A projection cannot be the last item in a linear processing pathway." in str(error_text.value)

    def test_LPP_two_projections_in_a_row(self):
        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=2.0))
        A_to_B = MappingProjection(sender=A, receiver=B)
        B_to_C = MappingProjection(sender=B, receiver=C)
        with pytest.raises(CompositionError) as error_text:
            comp.add_linear_processing_pathway([A, B_to_C, A_to_B, B, C])

        assert "A Projection in a linear processing pathway must be preceded by a Composition Node (Mechanism or " \
               "Composition) and followed by a Composition Node" in str(error_text.value)

    def test_LPP_start_with_projection(self):
        comp = Composition()
        Nonsense_Projection = MappingProjection()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        with pytest.raises(CompositionError) as error_text:
            comp.add_linear_processing_pathway([Nonsense_Projection, A, B])

        assert "The first item in a linear processing pathway must be a Node (Mechanism or Composition)." in str(
            error_text.value)

    def test_LPP_wrong_component(self):
        from psyneulink.core.components.ports.inputport import InputPort
        comp = Composition()
        Nonsense = InputPort()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        with pytest.raises(CompositionError) as error_text:
            comp.add_linear_processing_pathway([A, Nonsense, B])

        assert "A linear processing pathway must be made up of Projections and Composition Nodes." in str(
            error_text.value)

    def test_lpp_invalid_matrix_keyword(self):
        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        with pytest.raises(CompositionError) as error_text:
        # Typo in IdentityMatrix
            comp.add_linear_processing_pathway([A, "IdntityMatrix", B])

        assert "Invalid projection" in str(error_text.value)

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_LPP_two_origins_one_terminal(self, mode):
        # A ----> C --
        #              ==> E
        # B ----> D --

        # 5 x 1 = 5 ----> 5 x 5 = 25 --
        #                                25 + 25 = 50  ==> 50 * 5 = 250
        # 5 * 1 = 5 ----> 5 x 5 = 25 --

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
        comp.add_linear_processing_pathway([A, C, E])
        comp.add_linear_processing_pathway([B, D, E])
        inputs_dict = {A: [5],
                       B: [5]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([250], output)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="LinearComposition")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_composition(self, benchmark, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs={A: [[1.0]]}, scheduler=sched, bin_execute=mode)
        assert np.allclose(25, output)


    @pytest.mark.skip
    @pytest.mark.composition
    @pytest.mark.benchmark(group="LinearComposition")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_composition_default(self, benchmark, mode):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, scheduler=sched, bin_execute=mode)
        assert 25 == output[0][0]

    @pytest.mark.composition
    @pytest.mark.benchmark(group="LinearComposition Vector")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    @pytest.mark.parametrize("vector_length", [2**x for x in range(1)])
    def test_run_composition_vector(self, benchmark, mode, vector_length):
        var = [1.0 for x in range(vector_length)]
        comp = Composition()
        A = IntegratorMechanism(default_variable=var, function=Linear(slope=5.0))
        B = TransferMechanism(default_variable=var, function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs={A: [var]}, scheduler=sched, bin_execute=mode)
        assert np.allclose([25.0 for x in range(vector_length)], output[0])

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Merge composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_terminal(self, benchmark, mode):
        # C --
        #              ==> E
        # D --

        # 5 x 5 = 25 --
        #                25 + 25 = 50  ==> 50 * 5 = 250
        # 5 x 5 = 25 --

        comp = Composition()
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        E = TransferMechanism(name="E", function=Linear(slope=5.0))
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=D, receiver=E), D, E)
        inputs_dict = {C: [5.0],
                       D: [5.0]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose(250, output)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Merge composition scalar")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_1_origin_2_terminals(self, benchmark, mode):
        #       ==> D
        # C
        #       ==> E

        #                25 * 4 = 100
        # 5 x 5 = 25 --
        #                25 * 6 = 150

        comp = Composition()
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        D = TransferMechanism(name="D", function=Linear(slope=4.0))
        E = TransferMechanism(name="E", function=Linear(slope=6.0))
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=D), C, D)
        comp.add_projection(MappingProjection(sender=C, receiver=E), C, E)
        inputs_dict = {C: [5.0]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([[100], [150]], output)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Merge composition scalar MIMO")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_terminal_mimo_last(self, benchmark, mode):
        # C --
        #              ==> E
        # D --

        # [6] x 5 = [30] --
        #                            [30, 40] * 5 = [150, 200]
        # [8] x 5 = [40] --

        comp = Composition()
        C = TransferMechanism(name="C", function=Linear(slope=5.0))
        D = TransferMechanism(name="D", function=Linear(slope=5.0))
        E = TransferMechanism(name="E", input_ports=['a', 'b'], function=Linear(slope=5.0))
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=E.input_ports['a']), C, E)
        comp.add_projection(MappingProjection(sender=D, receiver=E.input_ports['b']), D, E)
        inputs_dict = {C: [6.0],
                       D: [8.0]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([[150], [200]], output)


    @pytest.mark.composition
    @pytest.mark.benchmark(group="Merge composition scalar MIMO")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_terminal_mimo_parallel(self, benchmark, mode):
        # C --
        #              ==> E
        # D --

        # [5, 6] x 5 = [25, 30] --
        #                            [25 + 35, 30 + 40] = [60, 70]  ==> [60, 70] * 5 = [300, 350]
        # [7, 8] x 5 = [35, 40] --

        comp = Composition()
        C = TransferMechanism(name="C", input_ports=['a', 'b'], function=Linear(slope=5.0))
        D = TransferMechanism(name="D", input_ports=['a', 'b'], function=Linear(slope=5.0))
        E = TransferMechanism(name="E", input_ports=['a', 'b'], function=Linear(slope=5.0))
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C.output_ports[0], receiver=E.input_ports['a']), C, E)
        comp.add_projection(MappingProjection(sender=C.output_ports[1], receiver=E.input_ports['b']), C, E)
        comp.add_projection(MappingProjection(sender=D.output_ports[0], receiver=E.input_ports['a']), D, E)
        comp.add_projection(MappingProjection(sender=D.output_ports[1], receiver=E.input_ports['b']), D, E)
        inputs_dict = {C: [[5.0], [6.0]],
                       D: [[7.0], [8.0]]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([[300], [350]], output)


    @pytest.mark.composition
    @pytest.mark.benchmark(group="Merge composition scalar MIMO")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_3_mechanisms_2_origins_1_terminal_mimo_all_sum(self, benchmark, mode):
        # C --
        #              ==> E
        # D --

        # [5, 6] x 5 = [25, 30] --
        #                            [25 + 35 + 30 + 40] = 130  ==> 130 * 5 = 650
        # [7, 8] x 5 = [35, 40] --

        comp = Composition()
        C = TransferMechanism(name="C", input_ports=['a', 'b'], function=Linear(slope=5.0))
        D = TransferMechanism(name="D", input_ports=['a', 'b'], function=Linear(slope=5.0))
        E = TransferMechanism(name="E", function=Linear(slope=5.0))
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C.output_ports[0], receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=C.output_ports[1], receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=D.output_ports[0], receiver=E), D, E)
        comp.add_projection(MappingProjection(sender=D.output_ports[1], receiver=E), D, E)
        inputs_dict = {C: [[5.0], [6.0]],
                       D: [[7.0], [8.0]]}
        sched = Scheduler(composition=comp)
        output = benchmark(comp.run, inputs=inputs_dict, scheduler=sched, bin_execute=mode)
        assert np.allclose([[650]], output)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism(self, benchmark, mode):
        comp = Composition()
        A = RecurrentTransferMechanism(size=3, function=Linear(slope=5.0), name="A")
        comp.add_node(A)
        sched = Scheduler(composition=comp)
        output1 = comp.run(inputs={A: [[1.0, 2.0, 3.0]]}, scheduler=sched, bin_execute=(mode == 'LLVM'))
        assert np.allclose([5.0, 10.0, 15.0], output1)
        output2 = comp.run(inputs={A: [[1.0, 2.0, 3.0]]}, scheduler=sched, bin_execute=(mode == 'LLVM'))
        # Using the hollow matrix: (10 + 15 + 1) * 5 = 130,
        #                          ( 5 + 15 + 2) * 5 = 110,
        #                          ( 5 + 10 + 3) * 5 = 90
        assert np.allclose([130.0, 110.0, 90.0], output2)
        benchmark(comp.run, inputs={A: [[1.0, 2.0, 3.0]]}, scheduler=sched, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism_hetero(self, benchmark, mode):
        comp = Composition()
        R = RecurrentTransferMechanism(size=1,
                                       function=Logistic(),
                                       hetero=-2.0,
                                       output_ports = [RESULT])
        comp.add_node(R)
        comp._analyze_graph()
        sched = Scheduler(composition=comp)
        val = comp.execute(inputs={R: [[3.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.95257413]])
        val = comp.execute(inputs={R: [[4.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.98201379]])

        # execute 10 times
        for i in range(10):
            val = comp.execute(inputs={R: [[5.0]]}, bin_execute=mode)

        assert np.allclose(val, [[0.99330715]])

        benchmark(comp.execute, inputs={R: [[1.0]]}, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism_integrator(self, benchmark, mode):
        comp = Composition()
        R = RecurrentTransferMechanism(size=1,
                                       function=Logistic(),
                                       hetero=-2.0,
                                       integrator_mode=True,
                                       integration_rate=0.01,
                                       output_ports = [RESULT])
        comp.add_node(R)
        comp._analyze_graph()
        sched = Scheduler(composition=comp)
        val = comp.execute(inputs={R: [[3.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.50749944]])
        val = comp.execute(inputs={R: [[4.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.51741795]])

        # execute 10 times
        for i in range(10):
            val = comp.execute(inputs={R: [[5.0]]}, bin_execute=mode)

        assert np.allclose(val, [[0.6320741]])

        benchmark(comp.execute, inputs={R: [[1.0]]}, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism_vector_2(self, benchmark, mode):
        comp = Composition()
        R = RecurrentTransferMechanism(size=2, function=Logistic())
        comp.add_node(R)
        comp._analyze_graph()
        sched = Scheduler(composition=comp)
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.81757448, 0.92414182]])
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.87259959,  0.94361816]])

        # execute 10 times
        for i in range(10):
            val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

        assert np.allclose(val, [[0.87507549,  0.94660049]])

        benchmark(comp.execute, inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism_hetero_2(self, benchmark, mode):
        comp = Composition()
        R = RecurrentTransferMechanism(size=2,
                                       function=Logistic(),
                                       hetero=-2.0,
                                       output_ports = [RESULT])
        comp.add_node(R)
        comp._analyze_graph()
        sched = Scheduler(composition=comp)
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.5, 0.73105858]])
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.3864837, 0.73105858]])

        # execute 10 times
        for i in range(10):
            val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

        assert np.allclose(val, [[0.36286875, 0.78146724]])

        benchmark(comp.execute, inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

    @pytest.mark.composition
    @pytest.mark.benchmark(group="Recurrent")
    @pytest.mark.parametrize("mode", ['Python',
                                      pytest.param('LLVM', marks=pytest.mark.llvm),
                                      pytest.param('LLVMExec', marks=pytest.mark.llvm),
                                      pytest.param('LLVMRun', marks=pytest.mark.llvm),
                                      pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                                      pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                                      ])
    def test_run_recurrent_transfer_mechanism_integrator_2(self, benchmark, mode):
        comp = Composition()
        R = RecurrentTransferMechanism(size=2,
                                       function=Logistic(),
                                       hetero=-2.0,
                                       integrator_mode=True,
                                       integration_rate=0.01,
                                       output_ports = [RESULT])
        comp.add_node(R)
        comp._analyze_graph()
        sched = Scheduler(composition=comp)
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.5, 0.50249998]])
        val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)
        assert np.allclose(val, [[0.4999875, 0.50497484]])

        # execute 10 times
        for i in range(10):
            val = comp.execute(inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

        assert np.allclose(val, [[0.49922843, 0.52838607]])

        benchmark(comp.execute, inputs={R: [[1.0, 2.0]]}, bin_execute=mode)

    def test_run_termination_condition_custom_context(self):
        D = pnl.DDM(function=pnl.DriftDiffusionIntegrator)
        comp = pnl.Composition()

        comp.add_node(node=D)

        comp.run(
            inputs={D: 0},
            termination_processing={pnl.TimeScale.RUN: pnl.WhenFinished(D)},
            context='custom'
        )


class TestCallBeforeAfterTimescale:

    def test_call_before_record_timescale(self):

        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [1, 2, 3, 4]}
        sched = Scheduler(composition=comp)

        time_step_array = []
        trial_array = []
        pass_array = []

        def cb_timestep(scheduler, arr):

            def record_timestep():

                arr.append(scheduler.clocks[comp.default_execution_id].get_total_times_relative(TimeScale.TIME_STEP, TimeScale.TRIAL))

            return record_timestep

        def cb_pass(scheduler, arr):

            def record_pass():

                arr.append(scheduler.clocks[comp.default_execution_id].get_total_times_relative(TimeScale.PASS, TimeScale.RUN))

            return record_pass

        def cb_trial(scheduler, arr):

            def record_trial():

                arr.append(scheduler.clocks[comp.default_execution_id].get_total_times_relative(TimeScale.TRIAL, TimeScale.LIFE))

            return record_trial

        comp.run(inputs=inputs_dict, scheduler=sched,
                 call_after_time_step=cb_timestep(sched, time_step_array), call_before_pass=cb_pass(sched, pass_array),
                 call_before_trial=cb_trial(sched, trial_array))
        assert time_step_array == [0, 1, 0, 1, 0, 1, 0, 1]
        assert trial_array == [0, 1, 2, 3]
        assert pass_array == [0, 1, 2, 3]

    def test_call_beforeafter_values_onepass(self):
        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [1, 2, 3, 4]}
        sched = Scheduler(composition=comp)

        before = {}
        after = {}

        before_expected = {
            TimeScale.TIME_STEP: {
                A: [0, 2, 2, 4, 4, 6, 6, 8],
                B: [0, 0, 10, 10, 20, 20, 30, 30]
            },
            TimeScale.PASS: {
                A: [0, 2, 4, 6],
                B: [0, 10, 20, 30]
            },
            TimeScale.TRIAL: {
                A: [0, 2, 4, 6],
                B: [0, 10, 20, 30]
            },
        }

        after_expected = {
            TimeScale.TIME_STEP: {
                A: [2, 2, 4, 4, 6, 6, 8, 8],
                B: [0, 10, 10, 20, 20, 30, 30, 40]
            },
            TimeScale.PASS: {
                A: [2, 4, 6, 8],
                B: [10, 20, 30, 40]
            },
            TimeScale.TRIAL: {
                A: [2, 4, 6, 8],
                B: [10, 20, 30, 40]
            },
        }

        comp.run(
            inputs=inputs_dict,
            scheduler=sched,
            call_before_time_step=functools.partial(record_values, before, TimeScale.TIME_STEP, A, B, comp=comp),
            call_after_time_step=functools.partial(record_values, after, TimeScale.TIME_STEP, A, B, comp=comp),
            call_before_pass=functools.partial(record_values, before, TimeScale.PASS, A, B, comp=comp),
            call_after_pass=functools.partial(record_values, after, TimeScale.PASS, A, B, comp=comp),
            call_before_trial=functools.partial(record_values, before, TimeScale.TRIAL, A, B, comp=comp),
            call_after_trial=functools.partial(record_values, after, TimeScale.TRIAL, A, B, comp=comp),
        )

        for ts in before_expected:
            for mech in before_expected[ts]:
                np.testing.assert_allclose(before[ts][mech], before_expected[ts][mech], err_msg='Failed on before[{0}][{1}]'.format(ts, mech))

        for ts in after_expected:
            for mech in after_expected[ts]:
                comp = []
                for x in after[ts][mech]:
                    try:
                        comp.append(x[0])
                    except (TypeError, IndexError):
                        comp.append(x)
                np.testing.assert_allclose(comp, after_expected[ts][mech], err_msg='Failed on after[{0}][{1}]'.format(ts, mech))

    def test_call_beforeafter_values_twopass(self):
        comp = Composition()

        A = IntegratorMechanism(name="A [transfer]", function=SimpleIntegrator(rate=1))
        B = IntegratorMechanism(name="B [transfer]", function=SimpleIntegrator(rate=2))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [1, 2]}
        sched = Scheduler(composition=comp)
        sched.add_condition(B, EveryNCalls(A, 2))

        before = {}
        after = {}

        before_expected = {
            TimeScale.TIME_STEP: {
                A: [
                    0, 1, 2,
                    2, 4, 6,
                ],
                B: [
                    0, 0, 0,
                    4, 4, 4,
                ]
            },
            TimeScale.PASS: {
                A: [
                    0, 1,
                    2, 4,
                ],
                B: [
                    0, 0,
                    4, 4,
                ]
            },
            TimeScale.TRIAL: {
                A: [0, 2],
                B: [0, 4]
            },
        }

        after_expected = {
            TimeScale.TIME_STEP: {
                A: [
                    1, 2, 2,
                    4, 6, 6,
                ],
                B: [
                    0, 0, 4,
                    4, 4, 16,
                ]
            },
            TimeScale.PASS: {
                A: [
                    1, 2,
                    4, 6,
                ],
                B: [
                    0, 4,
                    4, 16,
                ]
            },
            TimeScale.TRIAL: {
                A: [2, 6],
                B: [4, 16]
            },
        }

        comp.run(
            inputs=inputs_dict,
            scheduler=sched,
            call_before_time_step=functools.partial(record_values, before, TimeScale.TIME_STEP, A, B, comp=comp),
            call_after_time_step=functools.partial(record_values, after, TimeScale.TIME_STEP, A, B, comp=comp),
            call_before_pass=functools.partial(record_values, before, TimeScale.PASS, A, B, comp=comp),
            call_after_pass=functools.partial(record_values, after, TimeScale.PASS, A, B, comp=comp),
            call_before_trial=functools.partial(record_values, before, TimeScale.TRIAL, A, B, comp=comp),
            call_after_trial=functools.partial(record_values, after, TimeScale.TRIAL, A, B, comp=comp),
        )

        for ts in before_expected:
            for mech in before_expected[ts]:
                np.testing.assert_allclose(before[ts][mech], before_expected[ts][mech], err_msg='Failed on before[{0}][{1}]'.format(ts, mech))

        for ts in after_expected:
            for mech in after_expected[ts]:
                comp = []
                for x in after[ts][mech]:
                    try:
                        comp.append(x[0])
                    except (TypeError, IndexError):
                        comp.append(x)
                np.testing.assert_allclose(comp, after_expected[ts][mech], err_msg='Failed on after[{0}][{1}]'.format(ts, mech))


    # when self.sched is ready:
    # def test_run_default_scheduler(self):
    #     comp = Composition()
    #     A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
    #     B = TransferMechanism(function=Linear(slope=5.0))
    #     comp.add_node(A)
    #     comp.add_node(B)
    #     comp.add_projection(A, MappingProjection(sender=A, receiver=B), B)
    #     inputs_dict = {A: [[5], [4], [3]]}
    #     output = comp.run(
    #         inputs=inputs_dict,
    #         num_trials=3
    #     )
    #     assert 75 == output[0][0]

    # def test_multilayer_no_learning(self):
    #     Input_Layer = TransferMechanism(
    #         name='Input Layer',
    #         function=Logistic,
    #         default_variable=np.zeros((2,)),
    #     )
    #
    #     Hidden_Layer_1 = TransferMechanism(
    #         name='Hidden Layer_1',
    #         function=Logistic(),
    #         default_variable=np.zeros((5,)),
    #     )
    #
    #     Hidden_Layer_2 = TransferMechanism(
    #         name='Hidden Layer_2',
    #         function=Logistic(),
    #         default_variable=[0, 0, 0, 0],
    #     )
    #
    #     Output_Layerrecord_values = TransferMechanism(
    #         name='Output Layer',
    #         function=Logistic,
    #         default_variable=[0, 0, 0],
    #     )
    #
    #     Input_Weights_matrix = (np.arange(2 * 5).reshape((2, 5)) + 1) / (2 * 5)
    #
    #     Input_Weights = MappingProjection(
    #         name='Input Weights',
    #         matrix=Input_Weights_matrix,
    #     )
    #
    #     comp = Composition()
    #     comp.add_node(Input_Layer)
    #     comp.add_node(Hidden_Layer_1)
    #     comp.add_node(Hidden_Layer_2)
    #     comp.add_node(Output_Layer)
    #
    #     comp.add_projection(Input_Layer, Input_Weights, Hidden_Layer_1)
    #     comp.add_projection(Hidden_Layer_1, MappingProjection(), Hidden_Layer_2)
    #     comp.add_projection(Hidden_Layer_2, MappingProjection(), Output_Layer)
    #
    #     stim_list = {Input_Layer: [[-1, 30]]}
    #     sched = Scheduler(composition=comp)
    #     output = comp.run(
    #         inputs=stim_list,
    #         scheduler=sched,
    #         num_trials=10
    #     )
    #
    #     # p = Process(
    #     #     default_variable=[0, 0],
    #     #     pathway=[
    #     #         Input_Layer,
    #     #         # The following reference to Input_Weights is needed to use it in the pathway
    #     #         #    since it's sender and receiver args are not specified in its declaration above
    #     #         Input_Weights,
    #     #         Hidden_Layer_1,
    #     #         # No projection specification is needed here since the sender arg for Middle_Weights
    #     #         #    is Hidden_Layer_1 and its receiver arg is Hidden_Layer_2
    #     #         # Middle_Weights,
    #     #         Hidden_Layer_2,
    #     #         # Output_Weights does not need to be listed for the same reason as Middle_Weights
    #     #         # If Middle_Weights and/or Output_Weights is not declared above, then the process
    #     #         #    will assign a default for missing projection
    #     #         # Output_Weights,
    #     #         Output_Layer
    #     #     ],
    #     #     clamp_input=SOFT_CLAMP,
    #     #     target=[0, 0, 1]
    #     #
    #     #
    #     # )
    #     #
    #     # s.run(
    #     #     num_executions=10,
    #     #     inputs=stim_list,
    #     # )
    #
    #     expected_Output_Layer_output = [np.array([0.97988347, 0.97988347, 0.97988347])]
    #
    #     np.testing.assert_allclose(expected_Output_Layer_output, Output_Layer.output_values)

# Waiting to reintroduce ClampInput tests until we decide how this feature interacts with input specification

# class TestClampInput:
#
#     def test_run_5_mechanisms_2_origins_1_terminal_hard_clamp(self):
#
#         comp = Composition()
#         A = RecurrentTransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
#         B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
#         C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
#         D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
#         E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
#         comp.add_node(A)
#         comp.add_node(B)
#         comp.add_node(C)
#         comp.add_node(D)
#         comp.add_projection(A, MappingProjection(sender=A, receiver=C), C)
#         comp.add_projection(B, MappingProjection(sender=B, receiver=D), D)
#         comp.add_node(E)
#         comp.add_projection(C, MappingProjection(sender=C, receiver=E), E)
#         comp.add_projection(D, MappingProjection(sender=D, receiver=E), E)
#         inputs_dict = {
#             A: [[5]],
#             B: [[5]]
#         }
#         sched = Scheduler(composition=comp)
#         sched.add_condition(A, EveryNPasses(1))
#         sched.add_condition(B, EveryNCalls(A, 2))
#         sched.add_condition(C, AfterNCalls(A, 2))
#         sched.add_condition(D, AfterNCalls(A, 2))
#         sched.add_condition(E, AfterNCalls(C, 1))
#         sched.add_condition(E, AfterNCalls(D, 1))
#         output = comp.run(
#             inputs=inputs_dict,
#             scheduler=sched,
#             # clamp_input=HARD_CLAMP
#         )
#         assert 250 == output[0][0]
#
#     def test_run_5_mechanisms_2_origins_1_terminal_soft_clamp(self):
#
#         comp = Composition()
#         A = RecurrentTransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
#         B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
#         C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
#         D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
#         E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
#         comp.add_node(A)
#         comp.add_node(B)
#         comp.add_node(C)
#         comp.add_node(D)
#         comp.add_projection(A, MappingProjection(sender=A, receiver=C), C)
#         comp.add_projection(B, MappingProjection(sender=B, receiver=D), D)
#         comp.add_node(E)
#         comp.add_projection(C, MappingProjection(sender=C, receiver=E), E)
#         comp.add_projection(D, MappingProjection(sender=D, receiver=E), E)
#         inputs_dict = {
#             A: [[5.]],
#             B: [[5.]]
#         }
#         sched = Scheduler(composition=comp)
#         sched.add_condition(A, EveryNPasses(1))
#         sched.add_condition(B, EveryNCalls(A, 2))
#         sched.add_condition(C, AfterNCalls(A, 2))
#         sched.add_condition(D, AfterNCalls(A, 2))
#         sched.add_condition(E, AfterNCalls(C, 1))
#         sched.add_condition(E, AfterNCalls(D, 1))
#         output = comp.run(
#             inputs=inputs_dict,
#             scheduler=sched,
#             clamp_input=SOFT_CLAMP
#         )
#         assert 375 == output[0][0]
#
#     def test_run_5_mechanisms_2_origins_1_terminal_pulse_clamp(self):
#
#         comp = Composition()
#         A = RecurrentTransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0))
#         B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
#         C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
#         D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
#         E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
#         comp.add_node(A)
#         comp.add_node(B)
#         comp.add_node(C)
#         comp.add_node(D)
#         comp.add_projection(A, MappingProjection(sender=A, receiver=C), C)
#         comp.add_projection(B, MappingProjection(sender=B, receiver=D), D)
#         comp.add_node(E)
#         comp.add_projection(C, MappingProjection(sender=C, receiver=E), E)
#         comp.add_projection(D, MappingProjection(sender=D, receiver=E), E)
#         inputs_dict = {
#             A: [[5]],
#             B: [[5]]
#         }
#         sched = Scheduler(composition=comp)
#         sched.add_condition(A, EveryNPasses(1))
#         sched.add_condition(B, EveryNCalls(A, 2))
#         sched.add_condition(C, AfterNCalls(A, 2))
#         sched.add_condition(D, AfterNCalls(A, 2))
#         sched.add_condition(E, AfterNCalls(C, 1))
#         sched.add_condition(E, AfterNCalls(D, 1))
#         output = comp.run(
#             inputs=inputs_dict,
#             scheduler=sched,
#             clamp_input=PULSE_CLAMP
#         )
#         assert 625 == output[0][0]
#
#     def test_run_5_mechanisms_2_origins_1_hard_clamp_1_soft_clamp(self):
#
#         #          __
#         #         |  |
#         #         V  |
#         # 5 -#1-> A -^--> C --
#         #                       ==> E
#         # 5 ----> B ----> D --
#
#         #         v Recurrent
#         # 5 * 1 = (5 + 5) x 1 = 10
#         # 5 x 1 = 5 ---->      10 x 5 = 50 --
#         #                                       50 + 25 = 75  ==> 75 * 5 = 375
#         # 5 * 1 = 5 ---->       5 x 5 = 25 --
#
#         comp = Composition()
#         A = RecurrentTransferMechanism(name="composition-pytests-A", function=Linear(slope=1.0))
#         B = RecurrentTransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
#         C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
#         D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
#         E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
#         comp.add_node(A)
#         comp.add_node(B)
#         comp.add_node(C)
#         comp.add_node(D)
#         comp.add_projection(A, MappingProjection(sender=A, receiver=C), C)
#         comp.add_projection(B, MappingProjection(sender=B, receiver=D), D)
#         comp.add_node(E)
#         comp.add_projection(C, MappingProjection(sender=C, receiver=E), E)
#         comp.add_projection(D, MappingProjection(sender=D, receiver=E), E)
#         inputs_dict = {
#             A: [[5]],
#             B: [[5]]
#         }
#         sched = Scheduler(composition=comp)
#         sched.add_condition(A, EveryNPasses(1))
#         sched.add_condition(B, EveryNPasses(1))
#         sched.add_condition(B, EveryNCalls(A, 1))
#         sched.add_condition(C, AfterNCalls(A, 2))
#         sched.add_condition(D, AfterNCalls(A, 2))
#         sched.add_condition(E, AfterNCalls(C, 1))
#         sched.add_condition(E, AfterNCalls(D, 1))
#         output = comp.run(
#             inputs=inputs_dict,
#             scheduler=sched,
#             clamp_input={A: SOFT_CLAMP,
#                          B: HARD_CLAMP}
#         )
#         assert 375 == output[0][0]
#
#     def test_run_5_mechanisms_2_origins_1_terminal_no_clamp(self):
#         # input ignored on all executions
#         #          _r_
#         #         |   |
#         # 0 -#2-> V   |
#         # 0 -#1-> A -^--> C --
#         #                       ==> E
#         # 0 ----> B ----> D --
#
#         # 1 * 2 + 1 = 3
#         # 0 x 2 + 1 = 1 ----> 4 x 5 = 20 --
#         #                                   20 + 5 = 25  ==> 25 * 5 = 125
#         # 0 x 1 + 1 = 1 ----> 1 x 5 = 5 --
#
#         comp = Composition()
#
#         A = RecurrentTransferMechanism(name="composition-pytests-A", function=Linear(slope=2.0, intercept=5.0))
#         B = RecurrentTransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0, intercept=1.0))
#         C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
#         D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
#         E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
#         comp.add_node(A)
#         comp.add_node(B)
#         comp.add_node(C)
#         comp.add_node(D)
#         comp.add_projection(A, MappingProjection(sender=A, receiver=C), C)
#         comp.add_projection(B, MappingProjection(sender=B, receiver=D), D)
#         comp.add_node(E)
#         comp.add_projection(C, MappingProjection(sender=C, receiver=E), E)
#         comp.add_projection(D, MappingProjection(sender=D, receiver=E), E)
#         inputs_dict = {
#             A: [[100.0]],
#             B: [[500.0]]
#         }
#         sched = Scheduler(composition=comp)
#         sched.add_condition(A, EveryNPasses(1))
#         sched.add_condition(B, EveryNCalls(A, 2))
#         sched.add_condition(C, AfterNCalls(A, 2))
#         sched.add_condition(D, AfterNCalls(A, 2))
#         sched.add_condition(E, AfterNCalls(C, 1))
#         sched.add_condition(E, AfterNCalls(D, 1))
#         output = comp.run(
#             inputs=inputs_dict,
#             scheduler=sched,
#             clamp_input=NO_CLAMP
#         )
#         # FIX: This value is correct given that there is a BUG in Recurrent Transfer Mech --
#         # Recurrent projection BEGINS with a value leftover from initialization
#         # (only shows up if the function has an additive component or default variable is not zero)
#         assert 925 == output[0][0]


class TestSystemComposition:

    # def test_run_2_mechanisms_default_input_1(self):
    #     sys = SystemComposition()
    #     A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
    #     B = TransferMechanism(function=Linear(slope=5.0))
    #     sys.add_node(A)
    #     sys.add_node(B)
    #     sys.add_projection(A, MappingProjection(sender=A, receiver=B), B)
    #     sched = Scheduler(composition=sys)
    #     output = sys.run(
    #         scheduler=sched
    #     )
    #     assert 25 == output[0][0]

    def test_run_2_mechanisms_input_5(self):
        sys = SystemComposition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        sys.add_node(A)
        sys.add_node(B)
        sys.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[5]]}
        sched = Scheduler(composition=sys)
        output = sys.run(inputs=inputs_dict, scheduler=sched)
        assert np.allclose(125, output[0][0])

    def test_call_beforeafter_values_onepass(self):
        comp = Composition()

        A = TransferMechanism(name="A [transfer]", function=Linear(slope=2.0))
        B = TransferMechanism(name="B [transfer]", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[1], [2], [3], [4]]}
        sched = Scheduler(composition=comp)

        before = {}
        after = {}

        before_expected = {
            TimeScale.TIME_STEP: {
                A: [0, 2, 2, 4, 4, 6, 6, 8],
                B: [0, 0, 10, 10, 20, 20, 30, 30]
            },
            TimeScale.PASS: {
                A: [0, 2, 4, 6],
                B: [0, 10, 20, 30]
            },
            TimeScale.TRIAL: {
                A: [0, 2, 4, 6],
                B: [0, 10, 20, 30]
            },
        }

        after_expected = {
            TimeScale.TIME_STEP: {
                A: [2, 2, 4, 4, 6, 6, 8, 8],
                B: [0, 10, 10, 20, 20, 30, 30, 40]
            },
            TimeScale.PASS: {
                A: [2, 4, 6, 8],
                B: [10, 20, 30, 40]
            },
            TimeScale.TRIAL: {
                A: [2, 4, 6, 8],
                B: [10, 20, 30, 40]
            },
        }

        comp.run(
            inputs=inputs_dict,
            scheduler=sched,
            call_before_time_step=functools.partial(record_values, before, TimeScale.TIME_STEP, A, B, comp=comp),
            call_after_time_step=functools.partial(record_values, after, TimeScale.TIME_STEP, A, B, comp=comp),
            call_before_pass=functools.partial(record_values, before, TimeScale.PASS, A, B, comp=comp),
            call_after_pass=functools.partial(record_values, after, TimeScale.PASS, A, B, comp=comp),
            call_before_trial=functools.partial(record_values, before, TimeScale.TRIAL, A, B, comp=comp),
            call_after_trial=functools.partial(record_values, after, TimeScale.TRIAL, A, B, comp=comp),
        )

        for ts in before_expected:
            for mech in before_expected[ts]:
                # extra brackets around 'before_expected[ts][mech]' were needed for np assert to work
                np.testing.assert_allclose([before[ts][mech]], [before_expected[ts][mech]], err_msg='Failed on before[{0}][{1}]'.format(ts, mech))

        for ts in after_expected:
            for mech in after_expected[ts]:
                comp = []
                for x in after[ts][mech]:
                    try:
                        comp.append(x[0])
                    except (TypeError, IndexError):
                        comp.append(x)
                np.testing.assert_allclose(comp, after_expected[ts][mech], err_msg='Failed on after[{0}][{1}]'.format(ts, mech))

    def test_call_beforeafter_values_twopass(self):
        comp = Composition()

        A = IntegratorMechanism(name="A [transfer]", function=SimpleIntegrator(rate=1))
        B = IntegratorMechanism(name="B [transfer]", function=SimpleIntegrator(rate=2))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[1], [2]]}
        sched = Scheduler(composition=comp)
        sched.add_condition(B, EveryNCalls(A, 2))

        before = {}
        after = {}

        before_expected = {
            TimeScale.TIME_STEP: {
                A: [
                    0, 1, 2,
                    2, 4, 6,
                ],
                B: [
                    0, 0, 0,
                    4, 4, 4,
                ]
            },
            TimeScale.PASS: {
                A: [
                    0, 1,
                    2, 4,
                ],
                B: [
                    0, 0,
                    4, 4,
                ]
            },
            TimeScale.TRIAL: {
                A: [0, 2],
                B: [0, 4]
            },
        }

        after_expected = {
            TimeScale.TIME_STEP: {
                A: [
                    1, 2, 2,
                    4, 6, 6,
                ],
                B: [
                    0, 0, 4,
                    4, 4, 16,
                ]
            },
            TimeScale.PASS: {
                A: [
                    1, 2,
                    4, 6,
                ],
                B: [
                    0, 4,
                    4, 16,
                ]
            },
            TimeScale.TRIAL: {
                A: [2, 6],
                B: [4, 16]
            },
        }

        comp.run(
            inputs=inputs_dict,
            scheduler=sched,
            call_before_time_step=functools.partial(record_values, before, TimeScale.TIME_STEP, A, B, comp=comp),
            call_after_time_step=functools.partial(record_values, after, TimeScale.TIME_STEP, A, B, comp=comp),
            call_before_pass=functools.partial(record_values, before, TimeScale.PASS, A, B, comp=comp),
            call_after_pass=functools.partial(record_values, after, TimeScale.PASS, A, B, comp=comp),
            call_before_trial=functools.partial(record_values, before, TimeScale.TRIAL, A, B, comp=comp),
            call_after_trial=functools.partial(record_values, after, TimeScale.TRIAL, A, B, comp=comp),
        )

        for ts in before_expected:
            for mech in before_expected[ts]:
                np.testing.assert_allclose(before[ts][mech], before_expected[ts][mech], err_msg='Failed on before[{0}][{1}]'.format(ts, mech))

        for ts in after_expected:
            for mech in after_expected[ts]:
                comp = []
                for x in after[ts][mech]:
                    try:
                        comp.append(x[0])
                    except (TypeError, IndexError):
                        comp.append(x)
                np.testing.assert_allclose(comp, after_expected[ts][mech], err_msg='Failed on after[{0}][{1}]'.format(ts, mech))

    # when self.sched is ready:
    # def test_run_default_scheduler(self):
    #     comp = Composition()
    #     A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
    #     B = TransferMechanism(function=Linear(slope=5.0))
    #     comp.add_node(A)
    #     comp.add_node(B)
    #     comp.add_projection(A, MappingProjection(sender=A, receiver=B), B)
    #     inputs_dict = {A: [[5], [4], [3]]}
    #     output = comp.run(
    #         inputs=inputs_dict,
    #         num_trials=3
    #     )
    #     assert 75 == output[0][0]

    # def test_multilayer_no_learning(self):
    #     Input_Layer = TransferMechanism(
    #         name='Input Layer',
    #         function=Logistic,
    #         default_variable=np.zeros((2,)),
    #     )
    #
    #     Hidden_Layer_1 = TransferMechanism(
    #         name='Hidden Layer_1',
    #         function=Logistic(),
    #         default_variable=np.zeros((5,)),
    #     )
    #
    #     Hidden_Layer_2 = TransferMechanism(
    #         name='Hidden Layer_2',
    #         function=Logistic(),
    #         default_variable=[0, 0, 0, 0],
    #     )
    #
    #     Output_Layer = TransferMechanism(
    #         name='Output Layer',
    #         function=Logistic,
    #         default_variable=[0, 0, 0],
    #     )
    #
    #     Input_Weights_matrix = (np.arange(2 * 5).reshape((2, 5)) + 1) / (2 * 5)
    #
    #     Input_Weights = MappingProjection(
    #         name='Input Weights',
    #         matrix=Input_Weights_matrix,
    #     )
    #
    #     comp = Composition()
    #     comp.add_node(Input_Layer)
    #     comp.add_node(Hidden_Layer_1)
    #     comp.add_node(Hidden_Layer_2)
    #     comp.add_node(Output_Layer)
    #
    #     comp.add_projection(Input_Layer, Input_Weights, Hidden_Layer_1)
    #     comp.add_projection(Hidden_Layer_1, MappingProjection(), Hidden_Layer_2)
    #     comp.add_projection(Hidden_Layer_2, MappingProjection(), Output_Layer)
    #
    #     stim_list = {Input_Layer: [[-1, 30]]}
    #     sched = Scheduler(composition=comp)
    #     output = comp.run(
    #         inputs=stim_list,
    #         scheduler=sched,
    #         num_trials=10
    #     )
    #
    #     # p = process(
    #     #     default_variable=[0, 0],
    #     #     pathway=[
    #     #         Input_Layer,
    #     #         # The following reference to Input_Weights is needed to use it in the pathway
    #     #         #    since it's sender and receiver args are not specified in its declaration above
    #     #         Input_Weights,
    #     #         Hidden_Layer_1,
    #     #         # No projection specification is needed here since the sender arg for Middle_Weights
    #     #         #    is Hidden_Layer_1 and its receiver arg is Hidden_Layer_2
    #     #         # Middle_Weights,
    #     #         Hidden_Layer_2,
    #     #         # Output_Weights does not need to be listed for the same reason as Middle_Weights
    #     #         # If Middle_Weights and/or Output_Weights is not declared above, then the process
    #     #         #    will assign a default for missing projection
    #     #         # Output_Weights,
    #     #         Output_Layer
    #     #     ],
    #     #     clamp_input=SOFT_CLAMP,
    #     #     target=[0, 0, 1]
    #     #
    #     #
    #     # )
    #     #
    #     # s.run(
    #     #     num_executions=10,
    #     #     inputs=stim_list,
    #     # )
    #
    #     expected_Output_Layer_output = [np.array([0.97988347, 0.97988347, 0.97988347])]
    #
    #     np.testing.assert_allclose(expected_Output_Layer_output, Output_Layer.output_values)


# Cannot test old syntax until we are ready for the current System and Process classes to create compositions
# class TestOldSyntax:
#
#     # new syntax pathway, old syntax system
#     def test_one_pathway_inside_one_system_old_syntax(self):
#         # create a PathwayComposition | blank slate for composition
#         myPath = PathwayComposition()
#
#         # create mechanisms to add to myPath
#         myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#         myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8
#
#         # add mechanisms to myPath with default MappingProjections between them
#         myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])
#
#         # analyze graph (assign roles)
#         myPath._analyze_graph()
#
#         # Create a system using the old factory method syntax
#         sys = system(processes=[myPath])
#
#         # assign input to origin mech
#         stimulus = {myMech1: [[1]]}
#
#         # schedule = Scheduler(composition=sys)
#         output = sys.run(
#             inputs=stimulus,
#             # scheduler=schedule
#         )
#         assert 8 == output[0][0]
#
#     # old syntax pathway (process)
#     def test_one_process_old_syntax(self):
#
#         # create mechanisms to add to myPath
#         myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#         myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8
#
#         # create a PathwayComposition | blank slate for composition
#         myPath = process(pathway=[myMech1, myMech2, myMech3])
#
#         # assign input to origin mech
#         stimulus = {myMech1: [[1]]}
#
#         # schedule = Scheduler(composition=sys)
#         output = myPath.run(
#             inputs=stimulus,
#             # scheduler=schedule
#         )
#         assert 8 == output[0][0]
#
#     # old syntax pathway (process), old syntax system
#     def test_one_process_inside_one_system_old_syntax(self):
#         # create mechanisms to add to myPath
#         myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#         myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8
#
#         # create a PathwayComposition | blank slate for composition
#         myPath = process(pathway=[myMech1, myMech2, myMech3])
#
#         # Create a system using the old factory method syntax
#         sys = system(processes=[myPath])
#
#         # assign input to origin mech
#         stimulus = {myMech1: [[1]]}
#
#         # schedule = Scheduler(composition=sys)
#         output = sys.run(
#             inputs=stimulus,
#             # scheduler=schedule
#         )
#         assert 8 == output[0][0]
#
#     # old syntax pathway (process), old syntax system; 2 processes in series
#     def test_two_processes_in_series_in_system_old_syntax(self):
#
#         # create mechanisms to add to myPath
#         myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#         myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8
#         # create a PathwayComposition | blank slate for composition
#         myPath = process(pathway=[myMech1, myMech2, myMech3])
#
#         # create a PathwayComposition | blank slate for composition
#         myPath2 = PathwayComposition()
#
#         # create mechanisms to add to myPath2
#         myMech4 = TransferMechanism(function=Linear(slope=2.0))  # 8 x 2 = 16
#         myMech5 = TransferMechanism(function=Linear(slope=2.0))  # 16 x 2 = 32
#         myMech6 = TransferMechanism(function=Linear(slope=2.0))  # 32 x 2 = 64
#
#         # add mechanisms to myPath2 with default MappingProjections between them
#         myPath2.add_linear_processing_pathway([myMech4, myMech5, myMech6])
#
#         # analyze graph (assign roles)
#         myPath2._analyze_graph()
#
#         # Create a system using the old factory method syntax
#         sys = system(processes=[myPath, myPath2])
#
#         # connect the two pathways in series
#         sys.add_projection(sender=myMech3,
#                            projection=MappingProjection(sender=myMech3, receiver=myMech4),
#                            receiver=myMech4)
#         # assign input to origin mech
#         stimulus = {myMech1: [[1]]}
#
#         # schedule = Scheduler(composition=sys)
#         output = sys.run(
#             inputs=stimulus,
#             # scheduler=schedule
#         )
#         assert 64 == output[0][0]
#
#     # old syntax pathway (process), old syntax system; 2 processes converge
#     def test_two_processes_converge_in_system_old_syntax(self):
#         # create a PathwayComposition | blank slate for composition
#         myPath = PathwayComposition()
#
#         # create mechanisms to add to myPath
#         myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#         myMech3 = TransferMechanism(function=Linear(slope=2.0))
#
#         # add mechanisms to myPath with default MappingProjections between them
#         myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])
#
#         # analyze graph (assign roles)
#         myPath._analyze_graph()
#
#         # create a PathwayComposition | blank slate for composition
#         myPath2 = PathwayComposition()
#
#         # create mechanisms to add to myPath2
#         myMech4 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
#         myMech5 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
#
#         # add mechanisms to myPath2 with default MappingProjections between them
#         myPath2.add_linear_processing_pathway([myMech4, myMech5, myMech3])
#
#         # analyze graph (assign roles)
#         myPath2._analyze_graph()
#
#         # Create a system using the old factory method syntax
#         sys = system(processes=[myPath, myPath2])
#
#         # assign input to origin mech
#         stimulus = {myMech1: [[1]],
#                     myMech4: [[1]]}
#
#         # schedule = Scheduler(composition=sys)
#         output = sys.run(
#             inputs=stimulus,
#             # scheduler=schedule
#         )
#         assert 16 == output[0][0]
#

class TestNestedCompositions:

    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm),
                             pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                             pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                             ])
    def test_transfer_mechanism_composition(self, mode):

        # mechanisms
        A = ProcessingMechanism(name="A",
                                function=AdaptiveIntegrator(rate=0.1))
        B = ProcessingMechanism(name="B",
                                function=Logistic)
        C = TransferMechanism(name="C",
                              function=Logistic,
                              integration_rate=0.1,
                              integrator_mode=True)

        # comp1 separates IntegratorFunction fn and Logistic fn into mech A and mech B
        comp1 = Composition(name="comp1")
        comp1.add_linear_processing_pathway([A, B])

        # comp2 uses a TransferMechanism in integrator mode
        comp2 = Composition(name="comp2")
        comp2.add_node(C)

        # pass same 3 trials of input to comp1 and comp2
        comp1.run(inputs={A: [1.0, 2.0, 3.0]}, bin_execute=mode)
        comp2.run(inputs={C: [1.0, 2.0, 3.0]}, bin_execute=mode)

        assert np.allclose(comp1.results, comp2.results)
        assert np.allclose(comp2.results, [[[0.52497918747894]], [[0.5719961329315186]], [[0.6366838893983633]]])

    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm),
                             pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                             pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                             ])
    def test_nested_transfer_mechanism_composition(self, mode):

        # mechanisms
        A = ProcessingMechanism(name="A",
                                function=AdaptiveIntegrator(rate=0.1))
        B = ProcessingMechanism(name="B",
                                function=Logistic)

        inner_comp = Composition(name="inner_comp")
        inner_comp.add_linear_processing_pathway([A, B])
        sched = Scheduler(composition=inner_comp)

        outer_comp = Composition(name="outer_comp")
        outer_comp.add_node(inner_comp)

        sched = Scheduler(composition=outer_comp)
        ret = outer_comp.run(inputs=[1.0], bin_execute=mode)

        assert np.allclose(ret, [[[0.52497918747894]]])


    @pytest.mark.nested
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python',
                             pytest.param('LLVM', marks=pytest.mark.llvm),
                             pytest.param('LLVMExec', marks=pytest.mark.llvm),
                             pytest.param('LLVMRun', marks=pytest.mark.llvm),
                             pytest.param('PTXExec', marks=[pytest.mark.llvm, pytest.mark.cuda]),
                             pytest.param('PTXRun', marks=[pytest.mark.llvm, pytest.mark.cuda])
                             ])
    def test_nested_transfer_mechanism_composition_parallel(self, mode):

        # mechanisms
        A = ProcessingMechanism(name="A",
                                function=AdaptiveIntegrator(rate=0.1))
        B = ProcessingMechanism(name="B",
                                function=Logistic)

        inner_comp1 = Composition(name="inner_comp1")
        inner_comp1.add_linear_processing_pathway([A, B])
        sched = Scheduler(composition=inner_comp1)

        C = TransferMechanism(name="C",
                              function=Logistic,
                              integration_rate=0.1,
                              integrator_mode=True)

        inner_comp2 = Composition(name="inner_comp2")
        inner_comp2.add_node(C)
        sched = Scheduler(composition=inner_comp2)

        outer_comp = Composition(name="outer_comp")
        outer_comp.add_node(inner_comp1)
        outer_comp.add_node(inner_comp2)

        sched = Scheduler(composition=outer_comp)
        ret = outer_comp.run(inputs={inner_comp1: [[1.0]], inner_comp2: [[1.0]]}, bin_execute=mode)
        assert np.allclose(ret, [[[0.52497918747894]],[[0.52497918747894]]])

    def test_invalid_projection_deletion_when_nesting_comps(self):
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

        ocomp_objective_mechanism = pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="oController Objective Mechanism"
                )

        ocomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=ocomp,
                features=[oa.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=ocomp_objective_mechanism,
                function=pnl.GridSearch(direction=pnl.MINIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0, stop=5.0, num=5))])
        )

        icomp_objective_mechanism = pnl.ObjectiveMechanism(
                    monitor=ib.output_port,
                    function=pnl.SimpleIntegrator,
                    name="iController Objective Mechanism"
                )

        icomp.add_controller(
            pnl.OptimizationControlMechanism(
                agent_rep=icomp,
                features=[ia.input_port],
                # feature_function=pnl.Buffer(history=2),
                name="Controller",
                objective_mechanism=icomp_objective_mechanism,
                function=pnl.GridSearch(direction=pnl.MAXIMIZE),
                control_signals=[pnl.ControlSignal(projections=[(pnl.SLOPE, ia)],
                                                   function=pnl.Linear,
                                                   variable=1.0,
                                                   intensity_cost_function=pnl.Linear(slope=0.0),
                                                   allocation_samples=pnl.SampleSpec(start=1.0, stop=5.0, num=5))])
        )
        assert not ocomp._check_for_existing_projections(sender=ib, receiver=ocomp_objective_mechanism)
        return ocomp
    # Does not work yet due to initial_values bug that causes first recurrent projection to pass different values
    # to TranfserMechanism version vs Logistic fn + AdaptiveIntegrator fn version
    # def test_recurrent_transfer_mechanism_composition(self):
    #
    #     # mechanisms
    #     A = ProcessingMechanism(name="A",
    #                             function=AdaptiveIntegrator(rate=0.1))
    #     B = ProcessingMechanism(name="B",
    #                             function=Logistic)
    #     C = RecurrentTransferMechanism(name="C",
    #                                    function=Logistic,
    #                                    integration_rate=0.1,
    #                                    integrator_mode=True)
    #
    #     # comp1 separates IntegratorFunction fn and Logistic fn into mech A and mech B and uses a "feedback" proj for recurrence
    #     comp1 = Composition(name="comp1")
    #     comp1.add_linear_processing_pathway([A, B])
    #     comp1.add_linear_processing_pathway([B, A], feedback=True)
    #
    #     # comp2 uses a RecurrentTransferMechanism in integrator mode
    #     comp2 = Composition(name="comp2")
    #     comp2.add_node(C)
    #
    #     # pass same 3 trials of input to comp1 and comp2
    #     comp1.run(inputs={A: [1.0, 2.0, 3.0]})
    #     comp2.run(inputs={C: [1.0, 2.0, 3.0]})
    #
    #     # assert np.allclose(comp1.results, comp2.results)

    def test_combine_two_disjunct_trees(self):
        # Goal:

        # Mech1 --
        #          --> Mech3 ----> Mech4 --
        # Mech2 --                          --> Mech6
        #                          Mech5 --

        # create first composition -----------------------------------------------

        # Mech1 --
        #           --> Mech3
        # Mech2 --

        tree1 = Composition()

        myMech1 = TransferMechanism(name="myMech1")
        myMech2 = TransferMechanism(name="myMech2")
        myMech3 = TransferMechanism(name="myMech3")
        myMech4 = TransferMechanism(name="myMech4")
        myMech5 = TransferMechanism(name="myMech5")
        myMech6 = TransferMechanism(name="myMech6")

        tree1.add_node(myMech1)
        tree1.add_node(myMech2)
        tree1.add_node(myMech3)
        tree1.add_projection(MappingProjection(sender=myMech1, receiver=myMech3), myMech1, myMech3)
        tree1.add_projection(MappingProjection(sender=myMech2, receiver=myMech3), myMech2, myMech3)

        # validate first composition ---------------------------------------------

        tree1._analyze_graph()
        origins = tree1.get_nodes_by_role(NodeRole.ORIGIN)
        assert len(origins) == 2
        assert myMech1 in origins
        assert myMech2 in origins
        terminals = tree1.get_nodes_by_role(NodeRole.TERMINAL)
        assert len(terminals) == 1
        assert myMech3 in terminals

        # create second composition ----------------------------------------------

        # Mech4 --
        #           --> Mech6
        # Mech5 --

        tree2 = Composition()
        tree2.add_node(myMech4)
        tree2.add_node(myMech5)
        tree2.add_node(myMech6)
        tree2.add_projection(MappingProjection(sender=myMech4, receiver=myMech6), myMech4, myMech6)
        tree2.add_projection(MappingProjection(sender=myMech5, receiver=myMech6), myMech5, myMech6)

        # validate second composition ----------------------------------------------

        tree2._analyze_graph()
        origins = tree2.get_nodes_by_role(NodeRole.ORIGIN)
        assert len(origins) == 2
        assert myMech4 in origins
        assert myMech5 in origins
        terminals = tree2.get_nodes_by_role(NodeRole.TERMINAL)
        assert len(terminals) == 1
        assert myMech6 in terminals

        # combine the compositions -------------------------------------------------

        tree1.add_pathway(tree2)
        tree1._analyze_graph()

        # BEFORE linking via 3 --> 4 projection ------------------------------------
        # Mech1 --
        #           --> Mech3
        # Mech2 --
        # Mech4 --
        #           --> Mech6
        # Mech5 --

        origins = tree1.get_nodes_by_role(NodeRole.ORIGIN)
        assert len(origins) == 4
        assert myMech1 in origins
        assert myMech2 in origins
        assert myMech4 in origins
        assert myMech5 in origins
        terminals = tree1.get_nodes_by_role(NodeRole.TERMINAL)
        assert len(terminals) == 2
        assert myMech3 in terminals
        assert myMech6 in terminals

        # AFTER linking via 3 --> 4 projection ------------------------------------
        # Mech1 --
        #          --> Mech3 ----> Mech4 --
        # Mech2 --                          --> Mech6
        #                          Mech5 --

        tree1.add_projection(MappingProjection(sender=myMech3, receiver=myMech4), myMech3, myMech4)
        tree1._analyze_graph()

        origins = tree1.get_nodes_by_role(NodeRole.ORIGIN)
        assert len(origins) == 3
        assert myMech1 in origins
        assert myMech2 in origins
        assert myMech5 in origins
        terminals = tree1.get_nodes_by_role(NodeRole.TERMINAL)
        assert len(terminals) == 1
        assert myMech6 in terminals

    def test_combine_two_overlapping_trees(self):
            # Goal:

            # Mech1 --
            #          --> Mech3 --
            # Mech2 --              --> Mech5
            #              Mech4 --

            # create first composition -----------------------------------------------

            # Mech1 --
            #           --> Mech3
            # Mech2 --

            tree1 = Composition()

            myMech1 = TransferMechanism(name="myMech1")
            myMech2 = TransferMechanism(name="myMech2")
            myMech3 = TransferMechanism(name="myMech3")
            myMech4 = TransferMechanism(name="myMech4")
            myMech5 = TransferMechanism(name="myMech5")

            tree1.add_node(myMech1)
            tree1.add_node(myMech2)
            tree1.add_node(myMech3)
            tree1.add_projection(MappingProjection(sender=myMech1, receiver=myMech3), myMech1, myMech3)
            tree1.add_projection(MappingProjection(sender=myMech2, receiver=myMech3), myMech2, myMech3)

            # validate first composition ---------------------------------------------

            tree1._analyze_graph()
            origins = tree1.get_nodes_by_role(NodeRole.ORIGIN)
            assert len(origins) == 2
            assert myMech1 in origins
            assert myMech2 in origins
            terminals = tree1.get_nodes_by_role(NodeRole.TERMINAL)
            assert len(terminals) == 1
            assert myMech3 in terminals

            # create second composition ----------------------------------------------

            # Mech3 --
            #           --> Mech5
            # Mech4 --

            tree2 = Composition()
            tree2.add_node(myMech3)
            tree2.add_node(myMech4)
            tree2.add_node(myMech5)
            tree2.add_projection(MappingProjection(sender=myMech3, receiver=myMech5), myMech3, myMech5)
            tree2.add_projection(MappingProjection(sender=myMech4, receiver=myMech5), myMech4, myMech5)

            # validate second composition ----------------------------------------------

            tree2._analyze_graph()
            origins = tree2.get_nodes_by_role(NodeRole.ORIGIN)
            assert len(origins) == 2
            assert myMech3 in origins
            assert myMech4 in origins
            terminals = tree2.get_nodes_by_role(NodeRole.TERMINAL)
            assert len(terminals) == 1
            assert myMech5 in terminals

            # combine the compositions -------------------------------------------------

            tree1.add_pathway(tree2)
            tree1._analyze_graph()
            # no need for a projection connecting the two compositions because they share myMech3

            origins = tree1.get_nodes_by_role(NodeRole.ORIGIN)
            assert len(origins) == 3
            assert myMech1 in origins
            assert myMech2 in origins
            assert myMech4 in origins
            terminals = tree1.get_nodes_by_role(NodeRole.TERMINAL)
            assert len(terminals) == 1
            assert myMech5 in terminals

    def test_one_pathway_inside_one_system(self):
        # create a PathwayComposition | blank slate for composition
        myPath = PathwayComposition()

        # create mechanisms to add to myPath
        myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8

        # add mechanisms to myPath with default MappingProjections between them
        myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])

        # assign input to origin mech
        stimulus = {myMech1: [[1]]}

        # execute path (just for comparison)
        myPath.run(inputs=stimulus)

        # create a SystemComposition | blank slate for composition
        sys = SystemComposition()

        # add a PathwayComposition [myPath] to the SystemComposition [sys]
        sys.add_pathway(myPath)

        # execute the SystemComposition
        output = sys.run(inputs=stimulus)
        assert np.allclose([8], output)

    def test_two_paths_converge_one_system(self):

        # mech1 ---> mech2 --
        #                   --> mech3
        # mech4 ---> mech5 --

        # 1x2=2 ---> 2x2=4 --
        #                   --> (4+4)x2=16
        # 1x2=2 ---> 2x2=4 --

        # create a PathwayComposition | blank slate for composition
        myPath = PathwayComposition()

        # create mechanisms to add to myPath
        myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8

        # add mechanisms to myPath with default MappingProjections between them
        myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])

        myPath2 = PathwayComposition()
        myMech4 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech5 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myPath2.add_linear_processing_pathway([myMech4, myMech5, myMech3])

        sys = SystemComposition()
        sys.add_pathway(myPath)
        sys.add_pathway(myPath2)
        # assign input to origin mechs
        stimulus = {myMech1: [[1]], myMech4: [[1]]}

        # schedule = Scheduler(composition=sys)
        output = sys.run(inputs=stimulus)
        assert np.allclose(16, output)

    def test_two_paths_in_series_one_system(self):

        # [ mech1 --> mech2 --> mech3 ] -->   [ mech4  -->  mech5  -->  mech6 ]
        #   1x2=2 --> 2x2=4 --> 4x2=8   --> (8+1)x2=18 --> 18x2=36 --> 36*2=64
        #                                X
        #                                |
        #                                1
        # (if mech4 were recognized as an origin mech, and used SOFT_CLAMP, we would expect the final result to be 72)
        # create a PathwayComposition | blank slate for composition
        myPath = PathwayComposition()

        # create mechanisms to add to myPath
        myMech1 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8

        # add mechanisms to myPath with default MappingProjections between them
        myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])

        myPath2 = PathwayComposition()
        myMech4 = TransferMechanism(function=Linear(slope=2.0))
        myMech5 = TransferMechanism(function=Linear(slope=2.0))
        myMech6 = TransferMechanism(function=Linear(slope=2.0))
        myPath2.add_linear_processing_pathway([myMech4, myMech5, myMech6])

        sys = SystemComposition()
        sys.add_pathway(myPath)
        sys.add_pathway(myPath2)
        sys.add_projection(projection=MappingProjection(sender=myMech3,
                                                        receiver=myMech4), sender=myMech3, receiver=myMech4)

        # assign input to origin mechs
        # myMech4 ignores its input from the outside world because it is no longer considered an origin!
        stimulus = {myMech1: [[1]]}

        # schedule = Scheduler(composition=sys)
        output = sys.run(inputs=stimulus)

        assert np.allclose([64], output)

    def test_two_paths_converge_one_system_scheduling_matters(self):

        # mech1 ---> mech2 --
        #                   --> mech3
        # mech4 ---> mech5 --

        # 1x2=2 ---> 2x2=4 --
        #                   --> (4+4)x2=16
        # 1x2=2 ---> 2x2=4 --

        # create a PathwayComposition | blank slate for composition
        myPath = PathwayComposition()

        # create mechanisms to add to myPath
        myMech1 = IntegratorMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech2 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myMech3 = TransferMechanism(function=Linear(slope=2.0))  # 4 x 2 = 8

        # add mechanisms to myPath with default MappingProjections between them
        myPath.add_linear_processing_pathway([myMech1, myMech2, myMech3])

        myPathScheduler = Scheduler(composition=myPath)
        myPathScheduler.add_condition(myMech2, AfterNCalls(myMech1, 2))

        myPath.run(inputs={myMech1: [[1]]}, scheduler=myPathScheduler)
        myPath.run(inputs={myMech1: [[1]]}, scheduler=myPathScheduler)
        myPath2 = PathwayComposition()
        myMech4 = TransferMechanism(function=Linear(slope=2.0))  # 1 x 2 = 2
        myMech5 = TransferMechanism(function=Linear(slope=2.0))  # 2 x 2 = 4
        myPath2.add_linear_processing_pathway([myMech4, myMech5, myMech3])

        sys = SystemComposition()
        sys.add_pathway(myPath)
        sys.add_pathway(myPath2)
        # assign input to origin mechs
        stimulus = {myMech1: [[1]], myMech4: [[1]]}

        # schedule = Scheduler(composition=sys)
        output = sys.run(inputs=stimulus)
        assert np.allclose(16, output)


class TestOverloadedCompositions:
    def test_mechanism_different_inputs(self):
        a = TransferMechanism(name='a', function=Linear(slope=2))
        b = TransferMechanism(name='b')
        c = TransferMechanism(name='c', function=Linear(slope=3))
        p = MappingProjection(sender=a, receiver=b)

        comp = Composition()
        comp2 = Composition()

        comp.add_node(a)
        comp.add_node(b)
        comp.add_projection(p, a, b)

        comp2.add_node(a)
        comp2.add_node(b)
        comp2.add_node(c)
        comp2.add_projection(p, a, b)
        comp2.add_projection(MappingProjection(sender=c, receiver=b), c, b)

        comp.run({a: 1})
        comp2.run({a: 1, c: 1})

        np.testing.assert_allclose(comp.results, [[np.array([2])]])
        np.testing.assert_allclose(comp2.results, [[np.array([5])]])


class TestCompositionInterface:

    def test_one_input_port_per_origin_two_origins(self):

        # 5 -#1-> A --^ --> C --
        #                       ==> E
        # 5 ----> B ------> D --

        # 5 x 1 = 5 ----> 5 x 5 = 25 --
        #                                25 + 25 = 50  ==> 50 * 5 = 250
        # 5 * 1 = 5 ----> 5 x 5 = 25 --

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=1.0)
                              )

        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=C), A, C)
        comp.add_projection(MappingProjection(sender=B, receiver=D), B, D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=D, receiver=E), D, E)
        inputs_dict = {
            A: [[5.]],
            # two trials of one InputPort each
            #        TRIAL 1     TRIAL 2
            # A : [ [ [0,0] ] , [ [0, 0] ]  ]

            # two trials of multiple input ports each
            #        TRIAL 1     TRIAL 2

            #       TRIAL1 IS1      IS2      IS3     TRIAL2    IS1      IS2
            # A : [ [     [0,0], [0,0,0], [0,0,0,0] ] ,     [ [0, 0],   [0] ]  ]
            B: [[5.]]
        }
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(250, output)

    def test_updating_input_values_for_second_execution(self):
        # 5 -#1-> A --^ --> C --
        #                       ==> E
        # 5 ----> B ------> D --

        # 5 x 1 = 5 ----> 5 x 5 = 25 --
        #                                25 + 25 = 50  ==> 50 * 5 = 250
        # 5 * 1 = 5 ----> 5 x 5 = 25 --

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=1.0)
                              )

        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        D = TransferMechanism(name="composition-pytests-D", function=Linear(slope=5.0))
        E = TransferMechanism(name="composition-pytests-E", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=C), A, C)
        comp.add_projection(MappingProjection(sender=B, receiver=D), B, D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=C, receiver=E), C, E)
        comp.add_projection(MappingProjection(sender=D, receiver=E), D, E)
        inputs_dict = {
            A: [[5.]],
            B: [[5.]]
        }
        sched = Scheduler(composition=comp)

        output = comp.run(inputs=inputs_dict, scheduler=sched)
        assert np.allclose(250, output)

        inputs_dict2 = {
            A: [[2.]],
            B: [[5.]],
            # two trials of one InputPort each
            #        TRIAL 1     TRIAL 2
            # A : [ [ [0,0] ] , [ [0, 0] ]  ]

            # two trials of multiple input ports each
            #        TRIAL 1     TRIAL 2

            #       TRIAL1 IS1      IS2      IS3     TRIAL2    IS1      IS2
            # A : [ [     [0,0], [0,0,0], [0,0,0,0] ] ,     [ [0, 0],   [0] ]  ]
            B: [[5.]]
        }
        sched = Scheduler(composition=comp)

        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose([np.array([[250.]]), np.array([[250.]])], output)

        # add a new branch to the composition
        F = TransferMechanism(name="composition-pytests-F", function=Linear(slope=2.0))
        G = TransferMechanism(name="composition-pytests-G", function=Linear(slope=2.0))
        comp.add_node(F)
        comp.add_node(G)
        comp.add_projection(projection=MappingProjection(sender=F, receiver=G), sender=F, receiver=G)
        comp.add_projection(projection=MappingProjection(sender=G, receiver=E), sender=G, receiver=E)

        # execute the updated composition
        inputs_dict2 = {
            A: [[1.]],
            B: [[2.]],
            F: [[3.]]
        }

        sched = Scheduler(composition=comp)
        output2 = comp.run(inputs=inputs_dict2, scheduler=sched)

        assert np.allclose(np.array([[135.]]), output2)

    def test_changing_origin_for_second_execution(self):

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=1.0)
                              )

        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp.add_projection(MappingProjection(sender=B, receiver=C), B, C)
        inputs_dict = {A: [[5.]]}
        sched = Scheduler(composition=comp)

        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(25, output)

        # add a new origin to the composition
        F = TransferMechanism(name="composition-pytests-F", function=Linear(slope=2.0))
        comp.add_node(F)
        comp.add_projection(projection=MappingProjection(sender=F, receiver=A), sender=F, receiver=A)


        # execute the updated composition
        inputs_dict2 = {F: [[3.]]}

        sched = Scheduler(composition=comp)
        output2 = comp.run(inputs=inputs_dict2, scheduler=sched)

        connections_to_A = []
        expected_connections_to_A = [(F.output_ports[0], A.input_ports[0])]
        for input_port in A.input_ports:
            for p_a in input_port.path_afferents:
                connections_to_A.append((p_a.sender, p_a.receiver))

        assert connections_to_A == expected_connections_to_A
        assert np.allclose(np.array([[30.]]), output2)

    def test_two_input_ports_new_inputs_second_trial(self):

        comp = Composition()
        my_fun = Linear(
            # default_variable=[[0], [0]],
            # ^ setting default_variable on the function actually does not matter -- does the mechanism update it?
            slope=1.0)
        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[0], [0]],
                              input_ports=[{NAME: "Input Port 1",
                                             },
                                            {NAME: "Input Port 2",
                                             }],
                              function=my_fun
                              )
        comp.add_node(A)
        inputs_dict = {A: [[5.], [5.]]}

        sched = Scheduler(composition=comp)
        comp.run(inputs=inputs_dict, scheduler=sched)

        inputs_dict2 = {A: [[2.], [4.]]}

        output = comp.run(inputs=inputs_dict2, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.], [4.]])
        assert np.allclose(output, np.array([[2.], [4.]]))

    def test_two_input_ports_new_origin_second_trial(self):

        # A --> B --> C

        comp = Composition()
        my_fun = Linear(
            # default_variable=[[0], [0]],
            # ^ setting default_variable on the function actually does not matter -- does the mechanism update it?
            slope=1.0)
        A = TransferMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            input_ports=[
                {NAME: "Input Port 1", },
                {NAME: "Input Port 2", }
            ],
            function=my_fun
        )

        B = TransferMechanism(name="composition-pytests-B", function=Linear(slope=2.0))
        C = TransferMechanism(name="composition-pytests-C", function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp.add_projection(MappingProjection(sender=B, receiver=C), B, C)

        inputs_dict = {A: [[5.], [5.]]}

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)
        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [5.])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [5.])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[5.], [5.]])
        assert np.allclose(output, [[50.]])

        # A --> B --> C
        #     ^
        # D __|

        D = TransferMechanism(
            name="composition-pytests-D",
            default_variable=[[0], [0]],
            input_ports=[
                {NAME: "Input Port 1", },
                {NAME: "Input Port 2", }
            ],
            function=my_fun
        )
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=D, receiver=B), D, B)
        # Need to analyze graph again (identify D as an origin so that we can assign input) AND create the scheduler
        # again (sched, even though it is tied to comp, will not update according to changes in comp)
        sched = Scheduler(composition=comp)

        inputs_dict2 = {A: [[2.], [4.]],
                        D: [[2.], [4.]]}
        output2 = comp.run(inputs=inputs_dict2, scheduler=sched)
        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.], [4.]])

        assert np.allclose(D.input_ports[0].parameters.value.get(comp), [2.])
        assert np.allclose(D.input_ports[1].parameters.value.get(comp), [4.])
        assert np.allclose(D.parameters.variable.get(comp.default_execution_id), [[2.], [4.]])

        assert np.allclose(np.array([[40.]]), output2)

    def test_output_cim_one_terminal_mechanism_multiple_output_ports(self):

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C",
                              function=Linear(slope=2.0),
                              output_ports=[RESULT, VARIANCE])
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)

        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp.add_projection(MappingProjection(sender=B, receiver=C), B, C)

        comp.run(inputs={A: [1.0]})

        for terminal_port in comp.output_CIM_ports:
            # all CIM OutputPort keys in the CIM --> Terminal mapping dict are on the actual output CIM
            assert (comp.output_CIM_ports[terminal_port][0] in comp.output_CIM.input_ports) and \
                   (comp.output_CIM_ports[terminal_port][1] in comp.output_CIM.output_ports)

        # all Terminal Output ports are in the CIM --> Terminal mapping dict
        assert C.output_ports[0] in comp.output_CIM_ports.keys()
        assert C.output_ports[1] in comp.output_CIM_ports.keys()

        assert len(comp.output_CIM.output_ports) == 2

    def test_output_cim_many_terminal_mechanisms(self):

        comp = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              function=Linear(slope=1.0))
        B = TransferMechanism(name="composition-pytests-B",
                              function=Linear(slope=1.0))
        C = TransferMechanism(name="composition-pytests-C",
                              function=Linear(slope=2.0))
        D = TransferMechanism(name="composition-pytests-D",
                              function=Linear(slope=3.0))
        E = TransferMechanism(name="composition-pytests-E",
                              function=Linear(slope=4.0),
                              output_ports=[RESULT, VARIANCE])
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_node(E)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        comp.add_projection(MappingProjection(sender=B, receiver=C), B, C)
        comp.add_projection(MappingProjection(sender=B, receiver=D), B, D)
        comp.add_projection(MappingProjection(sender=B, receiver=E), B, E)
        comp.run(inputs={A: [1.0]})

        for terminal_port in comp.output_CIM_ports:
            # all CIM OutputPort keys in the CIM --> Terminal mapping dict are on the actual output CIM
            assert (comp.output_CIM_ports[terminal_port][0] in comp.output_CIM.input_ports) and \
                   (comp.output_CIM_ports[terminal_port][1] in comp.output_CIM.output_ports)

        # all Terminal Output ports are in the CIM --> Terminal mapping dict
        assert C.output_port in comp.output_CIM_ports.keys()
        assert D.output_port in comp.output_CIM_ports.keys()
        assert E.output_ports[0] in comp.output_CIM_ports.keys()
        assert E.output_ports[1] in comp.output_CIM_ports.keys()

        assert len(comp.output_CIM.output_ports) == 4

    def test_default_variable_shape_of_output_CIM(self):
        comp = Composition(name='composition')
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')

        comp.add_node(A)
        comp.add_node(B)

        comp.run(inputs={A: [1.0],
                         B: [2.0]})

        out = comp.output_CIM

        assert np.allclose(np.shape(out.defaults.variable), (2,1))
        assert np.allclose(out.parameters.variable.get(comp), [[1.0], [2.0]])

        C = ProcessingMechanism(name='C')
        comp.add_node(C)

        comp.run(inputs={A: [1.0],
                         B: [2.0],
                         C: [3.0]})

        out = comp.output_CIM

        assert np.allclose(np.shape(out.defaults.variable), (3, 1))
        assert np.allclose(out.parameters.variable.get(comp), [[1.0], [2.0], [3.0]])

        T = ProcessingMechanism(name='T')
        comp.add_linear_processing_pathway([A, T])
        comp.add_linear_processing_pathway([B, T])
        comp.add_linear_processing_pathway([C, T])

        comp.run(inputs={A: [1.0],
                         B: [2.0],
                         C: [3.0]})

        out = comp.output_CIM
        print(out.input_values)
        print(out.variable)
        print(out.defaults.variable)
        assert np.allclose(np.shape(out.defaults.variable), (1, 1))
        assert np.allclose(out.parameters.variable.get(comp), [[6.0]])

    def test_inner_composition_change_before_run(self):
        outer_comp = Composition(name="Outer Comp")
        inner_comp = Composition(name="Inner Comp")

        A = pnl.TransferMechanism(name='A')
        B = pnl.TransferMechanism(name='B')
        C = pnl.TransferMechanism(name='C')

        inner_comp.add_nodes([B, C])
        outer_comp.add_nodes([A, inner_comp])

        outer_comp.add_projection(pnl.MappingProjection(), A, inner_comp)
        inner_comp.add_projection(pnl.MappingProjection(), B, C)

        # comp.show_graph()
        outer_comp.run(inputs={A: 1})

        # inner_comp is updated to make B not an OUTPUT node
        # after being added to comp
        assert len(outer_comp.output_CIM.output_ports) == 1
        assert len(outer_comp.results[0]) == 1


class TestInputPortSpecifications:

    def test_two_input_ports_created_with_dictionaries(self):

        comp = Composition()
        A = ProcessingMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            # input_ports=[
            #     {NAME: "Input Port 1", },
            #     {NAME: "Input Port 2", }
            # ],
            function=Linear(slope=1.0)
            # specifying default_variable on the function doesn't seem to matter?
        )

        comp.add_node(A)


        inputs_dict = {A: [[2.], [4.]]}
        sched = Scheduler(composition=comp)
        comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.0])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.0])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.0], [4.0]])

    def test_two_input_ports_created_first_with_deferred_init(self):
        comp = Composition()

        # create mechanism A
        I1 = InputPort(
            name="Input Port 1",
            reference_value=[0]
        )
        I2 = InputPort(
            name="Input Port 2",
            reference_value=[0]
        )
        A = TransferMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            input_ports=[I1, I2],
            function=Linear(slope=1.0)
        )

        # add mech A to composition
        comp.add_node(A)

        # get comp ready to run (identify roles, create sched, assign inputs)
        inputs_dict = { A: [[2.],[4.]]}

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.0])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.0])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.0], [4.0]])

    def test_two_input_ports_created_with_keyword(self):
        comp = Composition()

        # create mechanism A

        A = TransferMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            input_ports=[INPUT_PORT, INPUT_PORT],
            function=Linear(slope=1.0)
        )

        # add mech A to composition
        comp.add_node(A)

        # get comp ready to run (identify roles, create sched, assign inputs)
        inputs_dict = {A: [[2.], [4.]]}

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.0])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.0])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.0], [4.0]])

        assert np.allclose([[2], [4]], output)

    def test_two_input_ports_created_with_strings(self):
        comp = Composition()

        # create mechanism A

        A = TransferMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            input_ports=["Input Port 1", "Input Port 2"],
            function=Linear(slope=1.0)
        )

        # add mech A to composition
        comp.add_node(A)

        # get comp ready to run (identify roles, create sched, assign inputs)

        inputs_dict = {A: [[2.], [4.]]}

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.0])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.0])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.0], [4.0]])

    def test_two_input_ports_created_with_values(self):
        comp = Composition()

        # create mechanism A

        A = TransferMechanism(
            name="composition-pytests-A",
            default_variable=[[0], [0]],
            input_ports=[[0.], [0.]],
            function=Linear(slope=1.0)
        )

        # add mech A to composition
        comp.add_node(A)

        # get comp ready to run (identify roles, create sched, assign inputs)
        inputs_dict = {A: [[2.], [4.]]}

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)

        assert np.allclose(A.input_ports[0].parameters.value.get(comp), [2.0])
        assert np.allclose(A.input_ports[1].parameters.value.get(comp), [4.0])
        assert np.allclose(A.parameters.variable.get(comp.default_execution_id), [[2.0], [4.0]])


class TestInputSpecifications:

    # def test_2_mechanisms_default_input_1(self):
    #     comp = Composition()
    #     A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
    #     B = TransferMechanism(function=Linear(slope=5.0))
    #     comp.add_node(A)
    #     comp.add_node(B)
    #     comp.add_projection(A, MappingProjection(sender=A, receiver=B), B)
    #     sched = Scheduler(composition=comp)
    #     output = comp.run(
    #         scheduler=sched
    #     )
    #     assert 25 == output[0][0]

    def test_3_origins(self):
        comp = Composition()
        I1 = InputPort(
                        name="Input Port 1",
                        reference_value=[0]
        )
        I2 = InputPort(
                        name="Input Port 2",
                        reference_value=[0]
        )
        A = TransferMechanism(
                            name="composition-pytests-A",
                            default_variable=[[0], [0]],
                            input_ports=[I1, I2],
                            function=Linear(slope=1.0)
        )
        B = TransferMechanism(
                            name="composition-pytests-B",
                            default_variable=[0,0],
                            function=Linear(slope=1.0))
        C = TransferMechanism(
                            name="composition-pytests-C",
                            default_variable=[0, 0, 0],
                            function=Linear(slope=1.0))
        D = TransferMechanism(
                            name="composition-pytests-D",
                            default_variable=[0],
                            function=Linear(slope=1.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)
        comp.add_projection(MappingProjection(sender=A, receiver=D), A, D)
        comp.add_projection(MappingProjection(sender=B, receiver=D), B, D)
        comp.add_projection(MappingProjection(sender=C, receiver=D), C, D)
        inputs = {A: [[[0], [0]], [[1], [1]], [[2], [2]]],
                  B: [[0, 0], [1, 1], [2, 2]],
                  C: [[0, 0, 0], [1, 1, 1], [2, 2, 2]]
        }

        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs, scheduler=sched)

        assert np.allclose(np.array([[12.]]), output)

    def test_2_mechanisms_input_5(self):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[5]]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched)
        assert np.allclose([125], output)

    def test_run_2_mechanisms_reuse_input(self):
        comp = Composition()
        A = IntegratorMechanism(default_variable=1.0, function=Linear(slope=5.0))
        B = TransferMechanism(function=Linear(slope=5.0))
        comp.add_node(A)
        comp.add_node(B)
        comp.add_projection(MappingProjection(sender=A, receiver=B), A, B)
        inputs_dict = {A: [[5]]}
        sched = Scheduler(composition=comp)
        output = comp.run(inputs=inputs_dict, scheduler=sched, num_trials=5)
        assert np.allclose([125], output)

    def test_some_inputs_not_specified(self):
        comp = Composition()

        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[1.0, 2.0], [3.0, 4.0]],
                              function=Linear(slope=2.0))

        B = TransferMechanism(name="composition-pytests-B",
                              default_variable=[[0.0, 0.0, 0.0]],
                              function=Linear(slope=3.0))

        C = TransferMechanism(name="composition-pytests-C")

        D = TransferMechanism(name="composition-pytests-D")

        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)


        inputs = {B: [[1., 2., 3.]],
                  D: [[4.]]}

        sched = Scheduler(composition=comp)
        comp.run(inputs=inputs, scheduler=sched)[0]

        assert np.allclose(A.get_output_values(comp), [[2.0, 4.0], [6.0, 8.0]])
        assert np.allclose(B.get_output_values(comp), [[3., 6., 9.]])
        assert np.allclose(C.get_output_values(comp), [[0.]])
        assert np.allclose(D.get_output_values(comp), [[4.]])

    def test_some_inputs_not_specified_origin_node_is_composition(self):

        compA = Composition()
        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[1.0, 2.0], [3.0, 4.0]],
                              function=Linear(slope=2.0))
        compA.add_node(A)

        comp = Composition()

        B = TransferMechanism(name="composition-pytests-B",
                              default_variable=[[0.0, 0.0, 0.0]],
                              function=Linear(slope=3.0))

        C = TransferMechanism(name="composition-pytests-C")

        D = TransferMechanism(name="composition-pytests-D")

        comp.add_node(compA)
        comp.add_node(B)
        comp.add_node(C)
        comp.add_node(D)


        inputs = {B: [[1., 2., 3.]],
                  D: [[4.]]}

        sched = Scheduler(composition=comp)
        comp.run(inputs=inputs, scheduler=sched)[0]

        assert np.allclose(A.get_output_values(comp), [[2.0, 4.0], [6.0, 8.0]])
        assert np.allclose(compA.get_output_values(comp), [[2.0, 4.0], [6.0, 8.0]])
        assert np.allclose(B.get_output_values(comp), [[3., 6., 9.]])
        assert np.allclose(C.get_output_values(comp), [[0.]])
        assert np.allclose(D.get_output_values(comp), [[4.]])

    def test_generator_as_inputs(self):
        c = pnl.Composition()

        m1 = pnl.TransferMechanism()
        m2 = pnl.TransferMechanism()

        c.add_linear_processing_pathway([m1, m2])

        def test_generator():
            for i in range(10):
                yield {
                    m1: i
                }

        t_g = test_generator()

        c.run(inputs=t_g)
        assert c.parameters.results.get(c) == [[np.array([0.])], [np.array([1.])], [np.array([2.])], [np.array([3.])],
                                               [np.array([4.])], [np.array([5.])], [np.array([6.])], [np.array([7.])],
                                               [np.array([8.])], [np.array([9.])]]

    def test_generator_as_inputs_with_num_trials(self):
        c = pnl.Composition()

        m1 = pnl.TransferMechanism()
        m2 = pnl.TransferMechanism()

        c.add_linear_processing_pathway([m1, m2])

        def test_generator():
            for i in range(10):
                yield {
                    m1: i
                }

        t_g = test_generator()

        c.run(inputs=t_g,
              num_trials=1)
        assert c.parameters.results.get(c) == [[np.array([0.])]]

class TestProperties:
    @pytest.mark.composition
    @pytest.mark.parametrize("mode", ['Python', True,
                                      pytest.param('LLVM', marks=(pytest.mark.xfail, pytest.mark.llvm)),
                                      pytest.param('LLVMExec', marks=(pytest.mark.xfail, pytest.mark.llvm)),
                                      pytest.param('LLVMRun', marks=(pytest.mark.xfail, pytest.mark.llvm)),
                                      pytest.param('PTXExec', marks=(pytest.mark.xfail, pytest.mark.llvm))])
    def test_llvm_fallback(self, mode):
        comp = Composition()
        def myFunc(variable, params, context):
            return variable * 2
        U = UserDefinedFunction(custom_function=myFunc, default_variable=[[0, 0], [0, 0]])
        A = TransferMechanism(name="composition-pytests-A",
                              default_variable=[[1.0, 2.0], [3.0, 4.0]],
                              function=U)
        inputs = {A: [[10., 20.], [30., 40.]]}
        comp.add_node(A)

        res = comp.run(inputs=inputs, bin_execute=mode)
        assert np.allclose(res, [[20.0, 40.0], [60.0, 80.0]])


class TestAuxComponents:
    def test_two_transfer_mechanisms(self):
        A = TransferMechanism(name='A')
        B = TransferMechanism(name='B')

        A.aux_components = [B, MappingProjection(sender=A, receiver=B)]

        comp = Composition(name='composition')
        comp.add_node(A)

        comp.run(inputs={A: [[1.0]]})

        assert np.allclose(B.parameters.value.get(comp), [[1.0]])
        # First Run:
        # Input to A = 1.0 | Output = 1.0
        # Input to B = 1.0 | Output = 1.0

        comp.run(inputs={A: [[2.0]]})
        # Second Run:
        # Input to A = 2.0 | Output = 2.0
        # Input to B = 2.0 | Output = 2.0

        assert np.allclose(B.parameters.value.get(comp), [[2.0]])

    def test_two_transfer_mechanisms_with_feedback_proj(self):
        A = TransferMechanism(name='A')
        B = TransferMechanism(name='B')

        A.aux_components = [B, (MappingProjection(sender=A, receiver=B), True)]

        comp = Composition(name='composition')
        comp.add_node(A)

        comp.run(inputs={A: [[1.0]],
                         B: [[2.0]]})

        assert np.allclose(B.parameters.value.get(comp), [[2.0]])
        # First Run:
        # Input to A = 1.0 | Output = 1.0
        # Input to B = 2.0 | Output = 2.0

        comp.run(inputs={A: [[1.0]],
                         B: [[2.0]]})
        # Second Run:
        # Input to A = 1.0 | Output = 1.0
        # Input to B = 2.0 + 1.0 | Output = 3.0

        assert np.allclose(B.parameters.value.get(comp), [[3.0]])

    def test_required_node_roles(self):
        A = TransferMechanism(name='A')
        B = TransferMechanism(name='B',
                              function=Linear(slope=2.0))

        comp = Composition(name='composition')
        comp.add_node(A, required_roles=[NodeRole.TERMINAL])
        comp.add_linear_processing_pathway([A, B])

        result = comp.run(inputs={A: [[1.0]]})

        terminal_mechanisms = comp.get_nodes_by_role(NodeRole.TERMINAL)

        assert A in terminal_mechanisms and B in terminal_mechanisms
        assert np.allclose(result, [[1.0], [2.0]])

    def test_aux_component_with_required_role(self):
        A = TransferMechanism(name='A')
        B = TransferMechanism(name='B')
        C = TransferMechanism(name='C',
                              function=Linear(slope=2.0))

        A.aux_components = [(B, NodeRole.TERMINAL), MappingProjection(sender=A, receiver=B)]

        comp = Composition(name='composition')
        comp.add_node(A)
        comp.add_linear_processing_pathway([B, C])

        comp.run(inputs={A: [[1.0]]})

        assert np.allclose(B.parameters.value.get(comp), [[1.0]])
        # First Run:
        # Input to A = 1.0 | Output = 1.0
        # Input to B = 1.0 | Output = 1.0

        comp.run(inputs={A: [[2.0]]})
        # Second Run:
        # Input to A = 2.0 | Output = 2.0
        # Input to B = 2.0 | Output = 2.0

        assert np.allclose(B.parameters.value.get(comp), [[2.0]])

        assert B in comp.get_nodes_by_role(NodeRole.TERMINAL)
        assert np.allclose(C.parameters.value.get(comp), [[4.0]])
        assert np.allclose(comp.get_output_values(comp), [[2.0], [4.0]])

    def test_stateful_nodes(self):
        A = TransferMechanism(name='A')
        B1 = TransferMechanism(name='B1',
                               integrator_mode=True)
        B2 = IntegratorMechanism(name='B2')
        C = TransferMechanism(name='C')


        inner_composition1 = Composition(name="inner-composition-1")
        inner_composition1.add_linear_processing_pathway([A, B1])

        inner_composition2 = Composition(name="inner-composition2")
        inner_composition2.add_linear_processing_pathway([A, B2])

        outer_composition1 = Composition(name="outer-composition-1")
        outer_composition1.add_node(inner_composition1)
        outer_composition1.add_node(C)
        outer_composition1.add_projection(sender=inner_composition1, receiver=C)

        outer_composition2 = Composition(name="outer-composition-2")
        outer_composition2.add_node(inner_composition2)
        outer_composition2.add_node(C)
        outer_composition2.add_projection(sender=inner_composition2, receiver=C)

        expected_stateful_nodes = {inner_composition1: [B1],
                                   inner_composition2: [B2],
                                   outer_composition1: [inner_composition1],
                                   outer_composition2: [inner_composition2]}

        for comp in expected_stateful_nodes:
            assert comp.stateful_nodes == expected_stateful_nodes[comp]


class TestShadowInputs:

    def test_two_origins(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A')
        comp.add_node(A)
        B = ProcessingMechanism(name='B',
                                input_ports=[A.input_port])

        comp.add_node(B)
        comp.run(inputs={A: [[1.0]]})

        assert A.value == [[1.0]]
        assert B.value == [[1.0]]
        assert comp.shadows[A] == [B]

        C = ProcessingMechanism(name='C')
        comp.add_linear_processing_pathway([C, A])

        comp.run(inputs={C: 1.5})
        assert A.value == [[1.5]]
        assert B.value == [[1.5]]
        assert C.value == [[1.5]]

        # Since B is shadowing A, its old projection from the CIM should be deleted,
        # and a new projection from C should be added
        assert len(B.path_afferents) == 1
        assert B.path_afferents[0].sender.owner == C

    def test_two_origins_two_input_ports(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A',
                                function=Linear(slope=2.0))
        B = ProcessingMechanism(name='B',
                                input_ports=[A.input_port, A.output_port])
        comp.add_node(A)
        comp.add_node(B)
        comp.run(inputs={A: [[1.0]]})

        assert A.value == [[2.0]]
        assert np.allclose(B.value, [[1.0], [2.0]])
        assert comp.shadows[A] == [B]

        C = ProcessingMechanism(name='C')
        comp.add_linear_processing_pathway([C, A])

        comp.run(inputs={C: 1.5})
        assert A.value == [[3.0]]
        assert np.allclose(B.value, [[1.5], [3.0]])
        assert C.value == [[1.5]]

        # Since B is shadowing A, its old projection from the CIM should be deleted,
        # and a new projection from C should be added
        assert len(B.path_afferents) == 2
        for proj in B.path_afferents:
            assert proj.sender.owner in {A, C}

    def test_shadow_internal_projections(self):
        comp = Composition(name='comp')

        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C',
                                input_ports=[B.input_port])

        comp.add_linear_processing_pathway([A, B])
        comp.add_node(C)
        comp.run(inputs={A: [[1.0]]})
        assert A.value == [[1.0]]
        assert B.value == [[1.0]]
        assert C.value == [[1.0]]

        input_nodes = comp.get_nodes_by_role(NodeRole.INPUT)
        output_nodes = comp.get_nodes_by_role(NodeRole.OUTPUT)
        assert A in input_nodes
        assert B in output_nodes
        assert C not in input_nodes
        assert C in output_nodes
        A2 = ProcessingMechanism(name='A2')
        comp.add_linear_processing_pathway([A2, B])
        comp.run(inputs={A: [[1.0]],
                         A2: [[1.0]]})

        assert A.value == [[1.0]]
        assert A2.value == [[1.0]]
        assert B.value == [[2.0]]
        assert C.value == [[2.0]]

    def test_monitor_input_ports(self):
        comp = Composition(name='comp')

        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')

        obj = ObjectiveMechanism(name='A_input_plus_B_input',
                                 monitor=[A.input_port, B.input_port],
                                 function=LinearCombination())

        comp.add_node(A)
        comp.add_node(B)
        comp.add_node(obj)

        comp.run(inputs={A: 10.0,
                         B: 15.0})
        assert obj.value == [[25.0]]


class TestNodeRoles:

    def test_internal(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp.add_linear_processing_pathway([A, B, C])

        comp._analyze_graph()

        assert comp.get_nodes_by_role(NodeRole.INTERNAL) == [B]

    def test_feedback(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp.add_linear_processing_pathway([A, B, C])
        comp.add_projection(sender=C, receiver=A, feedback=True)

        comp._analyze_graph()

        assert comp.get_nodes_by_role(NodeRole.FEEDBACK_SENDER) == [C]

        assert comp.get_nodes_by_role(NodeRole.FEEDBACK_RECEIVER) == [A]

    def test_cycle(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A')
        B = ProcessingMechanism(name='B')
        C = ProcessingMechanism(name='C')

        comp.add_linear_processing_pathway([A, B, C])
        comp.add_projection(sender=C, receiver=A)

        comp._analyze_graph()

        assert set(comp.get_nodes_by_role(NodeRole.CYCLE)) == {A, B, C}


class TestMisc:

    def test_disable_all_history(self):
        comp = Composition(name='comp')
        A = ProcessingMechanism(name='A')

        comp.add_node(A)
        comp.disable_all_history()
        comp.run(inputs={A: [2]})

        assert len(A.parameters.value.history[comp.default_execution_id]) == 0
