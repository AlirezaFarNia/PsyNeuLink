import numpy as np
import psyneulink as pnl
import pytest

import psyneulink.core.components.functions.learningfunctions
import psyneulink.core.components.functions.transferfunctions


class TestContrastiveHebbian:

    def test_scheduled_contrastive_hebbian(self):
        o = pnl.TransferMechanism()
        m = pnl.ContrastiveHebbianMechanism(
                input_size=2,
                hidden_size=0,
                target_size=2,
                separated=False,
                mode=pnl.SIMPLE_HEBBIAN,
                integrator_mode=True,
                enable_learning=False,
                matrix=[[0,-1],[-1, 0]],
            # auto=0,
            # hetero=-1,
        )

        # set max passes to ensure failure if no convergence instead of infinite loop
        m.max_passes = 1000

        c = pnl.Composition()
        c.add_linear_processing_pathway([m, o])
        c.scheduler.add_condition(o, pnl.WhenFinished(m))
        c._analyze_graph()
        print('matrix:\n', m.afferents[1].matrix)
        c.run(inputs={m:[2, 2]}, num_trials=4)
        results = c.results
        print(results)
        np.testing.assert_allclose(results, [[np.array([2.])], [np.array([2.])], [np.array([2.])], [np.array([2.])]])

    def test_using_Hebbian_learning_of_orthognal_inputs_without_integrator_mode(self):
        """Same as tests/mechanisms/test_recurrent_transfer_mechanism/test_learning_of_orthognal_inputs

        Tests that ContrastiveHebbianMechanism behaves like RecurrentTransferMechanism with Hebbian LearningFunction
        (allowing for epsilon differences due CONVERGENCE CRITERION.
        """
        size=4
        R = pnl.ContrastiveHebbianMechanism(
                input_size=4,
                hidden_size=0,
                target_size=4,
                mode=pnl.SIMPLE_HEBBIAN,
                enable_learning=True,
                function=psyneulink.core.components.functions.transferfunctions.Linear,
                learning_function=psyneulink.core.components.functions.learningfunctions.Hebbian,
                minus_phase_termination_threshold=.01,
                plus_phase_termination_threshold=.01,
                # auto=0,
                hetero=np.full((size,size),0.0)
        )

        C = pnl.Composition()
        C.add_node(R)

        inputs_dict = {R:[1,0,1,0]}
        C.run(num_trials=4,
              inputs=inputs_dict)

        # KDM 10/2/18: removing this test from here, as it's kind of unimportant to this specific test
        #   and the behavior of the scheduler's time can be a bit odd - should hopefully fix that in future
        #   and test in its own module
        # assert S.scheduler.get_clock(S).previous_time.pass_ == 6
        np.testing.assert_allclose(R.output_ports[pnl.ACTIVITY_DIFFERENCE].parameters.value.get(C),
                                   [1.20074767, 0.0, 1.20074767, 0.0])
        np.testing.assert_allclose(R.parameters.plus_phase_activity.get(C), [1.20074767, 0.0, 1.20074767, 0.0])
        np.testing.assert_allclose(R.parameters.minus_phase_activity.get(C), [0.0, 0.0, 0.0, 0.0])
        np.testing.assert_allclose(R.output_ports[pnl.CURRENT_ACTIVITY].parameters.value.get(C),
                                   [1.20074767, 0.0, 1.20074767, 0.0])
        np.testing.assert_allclose(
            R.recurrent_projection.get_mod_matrix(C),
            [
                [0.0,         0.0,         0.2399363,  0.0 ],
                [0.0,         0.0,         0.0,       0.0  ],
                [0.2399363,    0.0,         0.0,       0.0 ],
                [0.0,         0.0,         0.0,       0.0  ]
            ]
        )

        # Reset state so learning of new pattern is "uncontaminated" by activity from previous one
        R.output_port.parameters.value.set([0, 0, 0, 0], C, override=True)
        inputs_dict = {R:[0,1,0,1]}
        C.run(num_trials=4,
              inputs=inputs_dict)
        np.testing.assert_allclose(
            R.recurrent_projection.get_mod_matrix(C),
            [
                [0.0,        0.0,        0.2399363,   0.0      ],
                [0.0,        0.0,        0.0,        0.2399363 ],
                [0.2399363,   0.0,        0.0,        0.0      ],
                [0.0,        0.2399363,   0.0,        0.0      ]
            ]
        )
        np.testing.assert_allclose(R.output_ports[pnl.ACTIVITY_DIFFERENCE].parameters.value.get(C),
                                   [0.0, 1.20074767, 0.0, 1.20074767])
        np.testing.assert_allclose(R.parameters.plus_phase_activity.get(C), [0.0, 1.20074767, 0.0, 1.20074767])
        np.testing.assert_allclose(R.parameters.minus_phase_activity.get(C), [0.0, 0.0, 0.0, 0.0])

    # FIX: 10/26/19 - DOES NOT WORK WITH COMPOSITION
    def test_using_Hebbian_learning_of_orthognal_inputs_with_integrator_mode(self):
        """Same as tests/mechanisms/test_recurrent_transfer_mechanism/test_learning_of_orthognal_inputs

        Tests that ContrastiveHebbianMechanism behaves like RecurrentTransferMechanism with Hebbian LearningFunction
        (allowing for epsilon differences due to INTEGRATION and convergence criterion).
        """
        size=4
        R = pnl.ContrastiveHebbianMechanism(
                input_size=4,
                hidden_size=0,
                target_size=4,
                separated=False,
                mode=pnl.SIMPLE_HEBBIAN,
                enable_learning=True,
                function=psyneulink.core.components.functions.transferfunctions.Linear,
                integrator_mode=True,
                integration_rate=0.2,
                learning_function=psyneulink.core.components.functions.learningfunctions.Hebbian,
                minus_phase_termination_threshold=.01,
                plus_phase_termination_threshold=.01,
                # auto=0,
                hetero=np.full((size,size),0.0)
        )
        P=pnl.Process(pathway=[R])
        S=pnl.System(processes=[P])

        inputs_dict = {R:[1,0,1,0]}
        S.run(num_trials=4,
              inputs=inputs_dict)
        # KDM 10/2/18: removing this test from here, as it's kind of unimportant to this specific test
        #   and the behavior of the scheduler's time can be a bit odd - should hopefully fix that in future
        #   and test in its own module
        # assert S.scheduler.get_clock(S).previous_time.pass_ == 19
        np.testing.assert_allclose(R.output_ports[pnl.ACTIVITY_DIFFERENCE].parameters.value.get(S),
                                   [1.14142296, 0.0, 1.14142296, 0.0])
        np.testing.assert_allclose(R.parameters.plus_phase_activity.get(S), [1.14142296, 0.0, 1.14142296, 0.0])
        np.testing.assert_allclose(R.parameters.minus_phase_activity.get(S), [0.0, 0.0, 0.0, 0.0])
        np.testing.assert_allclose(R.output_ports[pnl.CURRENT_ACTIVITY].parameters.value.get(S),
                                   [1.1414229612568625, 0.0, 1.1414229612568625, 0.0])
        np.testing.assert_allclose(
            R.recurrent_projection.get_mod_matrix(S),
            [
                [0.0,         0.0,         0.22035998,  0.0        ],
                [0.0,         0.0,         0.0,         0.0        ],
                [0.22035998,  0.0,         0.0,         0.0        ],
                [0.0,         0.0,         0.0,         0.0        ]
            ]
        )
        # Reset state so learning of new pattern is "uncontaminated" by activity from previous one
        R.output_port.parameters.value.set([0, 0, 0, 0], S, override=True)
        inputs_dict = {R:[0,1,0,1]}
        S.run(num_trials=4,
              inputs=inputs_dict)
        np.testing.assert_allclose(
            R.recurrent_projection.get_mod_matrix(S),
            [
                [0.0,        0.0,        0.22035998, 0.0       ],
                [0.0,        0.0,        0.0,        0.22035998],
                [0.22035998, 0.0,        0.0,        0.        ],
                [0.0,        0.22035998, 0.0,        0.        ]
            ]
        )
        np.testing.assert_allclose(R.output_ports[pnl.CURRENT_ACTIVITY].parameters.value.get(S),
                                   [0.0, 1.1414229612568625, 0.0, 1.1414229612568625])
        np.testing.assert_allclose(R.output_ports[pnl.ACTIVITY_DIFFERENCE].parameters.value.get(S),
                                   [ 0.0, 1.14142296, 0.0, 1.14142296])
        np.testing.assert_allclose(R.parameters.plus_phase_activity.get(S), [0.0, 1.14142296, 0.0, 1.14142296])
        np.testing.assert_allclose(R.parameters.minus_phase_activity.get(S), [0.0, 0.0, 0.0, 0.0])

    def test_additional_output_ports(self):
        CHL1 = pnl.ContrastiveHebbianMechanism(
                input_size=2, hidden_size=0, target_size=2,
                additional_output_ports=[pnl.PLUS_PHASE_ACTIVITY, pnl.MINUS_PHASE_ACTIVITY])
        assert len(CHL1.output_ports)==5
        assert pnl.PLUS_PHASE_ACTIVITY in CHL1.output_ports.names

        CHL2 = pnl.ContrastiveHebbianMechanism(
                input_size=2, hidden_size=0, target_size=2,
                additional_output_ports=[pnl.PLUS_PHASE_ACTIVITY, pnl.MINUS_PHASE_ACTIVITY],
                separated=False)
        assert len(CHL2.output_ports)==5
        assert pnl.PLUS_PHASE_ACTIVITY in CHL2.output_ports.names

    def test_configure_learning(self):

        o = pnl.TransferMechanism()
        m = pnl.ContrastiveHebbianMechanism(
                input_size=2, hidden_size=0, target_size=2,
                mode=pnl.SIMPLE_HEBBIAN,
                separated=False,
                matrix=[[0,-.5],[-.5,0]]
        )

        with pytest.warns(UserWarning) as record:
            m.learning_enabled = True

        correct_message_found = False
        for warning in record:
            if ("Learning cannot be enabled" in str(warning.message) and
                    "because it has no LearningMechanism" in str(warning.message)):
                correct_message_found = True
                break
        assert correct_message_found

        m.configure_learning()
        m.reinitialize_when=pnl.Never()

        c = pnl.Composition()
        c.add_linear_processing_pathway([m,o])
        c.scheduler.add_condition(o, pnl.WhenFinished(m))
        c.run(inputs={m:[2,2]}, num_trials=4)
        results = c.parameters.results.get(c)
        np.testing.assert_allclose(results, [[[2.671875]],
                                             [[2.84093837]],
                                             [[3.0510183]],
                                             [[3.35234623]]])
