import os

from openff.evaluator import unit
from openff.evaluator.attributes import UNDEFINED
from openff.evaluator.protocols.paprika.restraints import ApplyRestraints
from openff.evaluator.thermodynamics import ThermodynamicState
from openff.evaluator.utils.observables import Observable
from openff.evaluator.workflow import Protocol, workflow_protocol
from openff.evaluator.workflow.attributes import InputAttribute, OutputAttribute


@workflow_protocol()
class AnalyzeAPRPhase(Protocol):
    """A protocol which will analyze the outputs of the attach, pull or release
    phases of an APR calculation and return the change in free energy for that
    phase of the calculation.
    """

    topology_path = InputAttribute(
        docstring="The file path to a coordinate file which contains topological "
        "information about the system.",
        type_hint=str,
        default_value=UNDEFINED,
    )
    trajectory_paths = InputAttribute(
        docstring="A list of paths to the trajectories (in the correct order) "
        "generated during the phase being analyzed.",
        type_hint=list,
        default_value=UNDEFINED,
    )

    phase = InputAttribute(
        docstring="The phase of the calculation being analyzed.",
        type_hint=str,
        default_value=UNDEFINED,
    )

    restraints_path = InputAttribute(
        docstring="The file path to the JSON file which contains the restraint "
        "definitions. This will usually have been generated by a "
        "`GenerateXXXRestraints` protocol.",
        type_hint=str,
        default_value=UNDEFINED,
    )

    result = OutputAttribute(
        docstring="The analysed free energy.", type_hint=Observable
    )

    def _execute(self, directory, available_resources):

        from paprika import analyze

        # Set-up the expected directory structure.
        windows_directory = os.path.join(directory, "windows")
        os.makedirs(windows_directory, exist_ok=True)

        window_phase = {"attach": "a", "pull": "p", "release": "r"}[self.phase]

        for window_index, trajectory_path in enumerate(self.trajectory_paths):

            # Create a directory to link the trajectory into.
            window_directory = f"{window_phase}{str(window_index).zfill(3)}"
            os.makedirs(
                os.path.join(windows_directory, window_directory), exist_ok=True
            )

            # Sym-link the trajectory into the new directory to avoid copying
            # large trajectory files.
            destination_path = os.path.join(
                windows_directory, window_directory, "trajectory.dcd"
            )
            if not os.path.isfile(destination_path):
                os.symlink(os.path.join(os.getcwd(), trajectory_path), destination_path)

            # Also sym-link the topology path
            destination_path = os.path.join(
                windows_directory, window_directory, "topology.pdb"
            )
            if not os.path.isfile(destination_path):
                os.symlink(
                    os.path.join(os.getcwd(), self.topology_path), destination_path
                )

        restraints = ApplyRestraints.load_restraints(self.restraints_path)

        flat_restraints = [
            restraint
            for restraint_type in restraints
            for restraint in restraints[restraint_type]
        ]

        results = analyze.compute_phase_free_energy(
            phase=self.phase,
            restraints=flat_restraints,
            windows_directory=windows_directory,
            topology_name="topology.pdb",
            analysis_method="ti-block",
        )

        multiplier = {"attach": -1.0, "pull": -1.0, "release": 1.0}[self.phase]

        self.result = Observable(
            unit.Measurement(
                multiplier
                * results[self.phase]["ti-block"]["fe"]
                * unit.kilocalorie
                / unit.mole,
                results[self.phase]["ti-block"]["sem"] * unit.kilocalorie / unit.mole,
            )
        )


@workflow_protocol()
class ComputeSymmetryCorrection(Protocol):
    """Computes the symmetry correction for an APR calculation which involves
    a guest with symmetry.
    """

    n_microstates = InputAttribute(
        docstring="The number of symmetry microstates of the guest molecule.",
        type_hint=int,
        default_value=UNDEFINED,
    )
    thermodynamic_state = InputAttribute(
        docstring="The thermodynamic state that the calculation was performed at.",
        type_hint=ThermodynamicState,
        default_value=UNDEFINED,
    )

    result = OutputAttribute(docstring="The symmetry correction.", type_hint=Observable)

    def _execute(self, directory, available_resources):

        from paprika.evaluator import Analyze

        self.result = Observable(
            unit.Measurement(
                Analyze.symmetry_correction(
                    self.n_microstates,
                    self.thermodynamic_state.temperature.to(unit.kelvin).magnitude,
                )
                * unit.kilocalorie
                / unit.mole,
                0 * unit.kilocalorie / unit.mole,
            )
        )


@workflow_protocol()
class ComputeReferenceWork(Protocol):
    """Computes the reference state work."""

    thermodynamic_state = InputAttribute(
        docstring="The thermodynamic state that the calculation was performed at.",
        type_hint=ThermodynamicState,
        default_value=UNDEFINED,
    )

    restraints_path = InputAttribute(
        docstring="The file path to the JSON file which contains the restraint "
        "definitions. This will usually have been generated by a "
        "`GenerateXXXRestraints` protocol.",
        type_hint=str,
        default_value=UNDEFINED,
    )

    result = OutputAttribute(
        docstring="The reference state work.", type_hint=Observable
    )

    def _execute(self, directory, available_resources):

        from paprika.evaluator import Analyze

        restraints = ApplyRestraints.load_restraints(self.restraints_path)
        guest_restraints = restraints["guest"]

        self.result = Observable(
            unit.Measurement(
                -Analyze.compute_ref_state_work(
                    self.thermodynamic_state.temperature.to(unit.kelvin).magnitude,
                    guest_restraints,
                )
                * unit.kilocalorie
                / unit.mole,
                0 * unit.kilocalorie / unit.mole,
            )
        )
