# MIT License
#
# Copyright (c) [2023] [son pham, tien nguyen, bach bao]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

""" Transmission and reflection techniques for state transition 0-1 and 1-2.
In here TR stands for transmission and reflection, and we derive the ideas of doing such method in space
01 and 12 based on Qiskit documents of doing calibration. Users can find it here:
https://qiskit.org/textbook/ch-quantum-hardware/calibrating-qubits-pulse.html
"""
import numpy as np

from qiskit.circuit import Gate, QuantumCircuit, Parameter
from qiskit import execute
from qiskit_ibm_provider.job import job_monitor

from src.backend.backend_ibm import CustomProvider
from src.pulse import Pulse01, Pulse12
from src.constant import QubitParameters
from src.utility import fit_function
from src.calibration.utility import _SetAttribute
from src.pulse_creation import GateSchedule
from src.analyzer import DataAnalysis

from numpy.typing import NDArray
from typing import List, Union, Optional

mhz_unit = QubitParameters.MHZ.value
ghz_unit = QubitParameters.GHZ.value


def set_up_freq(center_freq: float,
                freq_span: int = 40,
                freq_step: float = 0.5) -> NDArray:
    """ Set up frequency range in NDArray form

    Arg:
        default_freq: Either DEFAULT_F01 or DEFAULT_F12
    Returns:
        frequency_range: in GHz
    """
    max_freq = center_freq + freq_span * mhz_unit / 2
    min_freq = center_freq - freq_span * mhz_unit / 2

    freq_ghz = np.arange(min_freq / ghz_unit, max_freq / ghz_unit, freq_step * mhz_unit / ghz_unit)
    return freq_ghz


class _TR(_SetAttribute):
    """ The class act as an abstract class for transmission and reflection technique used in pulse model
    TR typical flow: set up pulse and gates -> submit job to IBM -> Analyze the resulted pulse
    -> return Pulse model and save job_id.
    An example of this flow::
        from qutritium.calibration.transmission_reflection import TR01, TR12
        from qutritium.pulse import Pulse01, Pulse12

        pulse01 = Pulse01(duration=144, x_amp=0.2)
        pulse12 = Pulse12(pulse01=pulse01, duration=pulse01.duration, x_amp=pulse01.x_amp)
        ... (TR_children_classes)

    Note:
        * You should not instantiate _TR as this is am abstract class. Use TR01 and TR12 instead

    Here is list of attributes available on the abstract "_TR" class, excluding SharedAttr attr:
        * frequency: in Hz
        * freq_sweeping_range_ghz: It is freq_sweeping_range but in ghz
        # lambda_list: return lambda_list that we use in this class
        * save_data(y_values): save given signal amplitude
        * run_monitor(package): custom run on IBMQ
        * analyze(): get the frequency of pulse after calibration
    """

    def __init__(self, pulse_model: Union[Pulse01, Pulse12],
                 custom_provider: CustomProvider, backend_name: str,
                 num_shots: int) -> None:
        """ _TR constructor

         Notes:
            * Frequency here is in Hz
            * freq_sweeping_range_ghz: frequency range in GHz -> convert to GHz later\
            * lambda_list: empirical, modified when running multiple experiments

        Args:
            pulse_model: Either Pulse01 or Pulse12
            custom_provider: EffProvider instance
            num_shots: number of shots
            backend_name:

        """
        super().__init__(pulse_model=pulse_model,
                         custom_provider=custom_provider,
                         backend_name=backend_name,
                         num_shots=num_shots)
        # Need to be modified by the constructor of children classes
        self.default_frequency: float = 0.
        self.freq_sweeping_range_ghz = None
        self.analyzer: Optional[DataAnalysis] = None
        self.package = []

        # Used for fit_function()
        self._lambda_list = [0, 0, 0, 0]
        self._sweep_gate = Gate("sweep", 1, [])
        self._tr_fit: Optional[NDArray] = None

    @property
    def lambda_list(self) -> List[float]:
        return self._lambda_list

    @lambda_list.setter
    def lambda_list(self, val_list: list) -> None:
        if len(val_list) != 4:
            raise ValueError("Lambda list does not have sufficient elements")
        self._lambda_list = val_list

    @property
    def tr_fit(self) -> NDArray:
        return self._tr_fit

    def analyze(self, job_id: Optional[str]) -> float:
        """ Plots IQ Data given freq_range
        Args:
            job_id: may need else we use the inherent submitted_job_id

        Returns:
            freq: Frequency after calculation
        """
        if job_id is None:
            experiment = self.custom_provider.retrieve_job(self.submitted_job)
        else:
            experiment = self.custom_provider.retrieve_job(job_id)
        self.analyzer = DataAnalysis(experiment)

        # Analyze data
        self.analyzer.retrieve_data(average=True)
        fit_params, self._tr_fit = fit_function(self.freq_sweeping_range_ghz, self.analyzer.IQ_data,
                                                lambda x, c1, q_freq, c2, c3:
                                                (c1 / np.pi) * (c2 / ((x - q_freq) ** 2 + c2 ** 2)) + c3,
                                                self.lambda_list)
        freq = fit_params[1] * QubitParameters.GHZ.value
        return freq

    def draw(self) -> None:
        """ Draw the circuit using qiskit standard library
        Implemented in next updates
        """
        pass

    def run_monitor(self,
                    num_shots: Optional[int] = 0,
                    meas_return: str = 'avg',
                    meas_level: int = 1,
                    **kwargs) -> None:
        """ Custom run execute()
        Args:
            num_shots: modify if needed
            meas_level:
            meas_return:

        Returns:

        """
        self.num_shots = num_shots if num_shots != 0 else self.num_shots
        submitted_job = self.backend.run(self.package,
                                         meas_level=meas_level,
                                         meas_return=meas_return,
                                         shots=self.num_shots)
        self.submitted_job = submitted_job.job_id()
        print(self.submitted_job)
        job_monitor(submitted_job)


class TR01(_TR):
    """ Used specifically for pulse01 model
    An example of this flow::
        from qutritium.backend.backend_ibm import CustomProvider
        from qutritium.pulse import Pulse01
        from qutritium.calibration.transmission_reflection import TR01

        pulse01 = Pulse01(duration=144, x_amp=0.2)
        custom_provider = CustomProvider()
        tr_01 = TR01(custom_provider=custom_provider, pulse_model=pulse01)
        tr_01.prepare_circuit()
        tr_01.run_monitor()
        tr_01.modify_pulse_model()
        print(tr_01.pulse_model)

    Here is list of attributes available on the ''TR_01'' class:
        + prepare_circuit(): implement abstract run_circuit() from ''_TR''
        * modify_pulse_model(): implement abstract modify_pulse_model() from ''_TR''
    """

    def __init__(self, pulse_model: Pulse01,
                 custom_provider: CustomProvider, backend_name: str = "ibm_brisbane",
                 num_shots: int = 4096) -> None:
        """ TR_01 constructor

        Args:
            custom_provider: EffProvider instance
            pulse_model: Pulse01
            num_shots: default 4096 shots
            backend_name: default = 'ibmq_manila'

        Returns:
            * Instance of TR01
        """
        super().__init__(pulse_model=pulse_model,
                         custom_provider=custom_provider,
                         backend_name=backend_name,
                         num_shots=num_shots)
        self.lambda_list = [10, 4.9, 1, -2]
        self.default_frequency = int(self.backend_params['drive_frequency'])
        self.freq_sweeping_range_ghz: NDArray = set_up_freq(center_freq=self.default_frequency)

    def prepare_circuit(self) -> None:
        """ Calibrate single qubit state with custom pulse_model
        Notes:
            * The syntax is contingent but the idea stays the same for every update
        """

        self.pulse_model: Pulse01

        # Sweeping
        frequencies_hz = self.freq_sweeping_range_ghz * ghz_unit
        for freq in frequencies_hz:
            qc_sweep = QuantumCircuit(self.qubit + 1, self.cbit + 1)
            # noinspection DuplicatedCode
            qc_sweep.append(self._sweep_gate, [0])
            freq_schedule = GateSchedule.freq_gaussian(
                backend=self.backend,
                frequency=freq,
                pulse_model=self.pulse_model,
                qubit=self.qubit
            )
            freq = Parameter('freq')
            qc_sweep.measure(self.qubit, self.cbit)
            qc_sweep.add_calibration(self._sweep_gate, (self.qubit,), freq_schedule, [freq])
            self.package.append(qc_sweep)

    def modify_pulse_model(self, job_id: str = None) -> None:
        """ Only used for debugging + getting result from past job
        Args:
            job_id: string representation of submitted job
        """
        self.pulse_model: Pulse01
        self.pulse_model.frequency = self.analyze(job_id=job_id)


class TR12(_TR):
    """ Used specifically for Pulse12

    An example of this flow::
        from qutritium.calibration.transmission_reflection import TR12
        from qutritium.pulse import Pulse12

        pulse01 = Pulse01(duration=144, x_amp=0.2)
        pulse12 = Pulse12(pulse01=pulse01, duration=pulse01.duration, x_amp=pulse01.x_amp)

        tr_12 = TR_12(pulse_model=pulse12)
        tr_12.prepare_circuit()
        tr_12.run_monitor()
        tr_12.modify_pulse_model()
        print(tr_12.pulse_model)

    Here is the list of attributes available "TR_12: class, excluding parents classes:
        * run_circuit(): implement abstract run_circuit() from _TR
        * modify_pulse_model(): implement abstract modify_pulse_model() from _TR
    """

    def __init__(self, pulse_model: Pulse12,
                 custom_provider: CustomProvider, backend_name: str = "ibm_brisbane",
                 num_shots: int = 4096) -> None:
        """

        Args:
            pulse_model: Pulse12
            custom_provider:
            num_shots: default 4096 shots
            backend_name: default = 'ibmq_manila'

        """
        super().__init__(pulse_model=pulse_model,
                         custom_provider=custom_provider,
                         backend_name=backend_name,
                         num_shots=num_shots)
        self.lambda_list = [10, 4.8, 1, -2]
        self.default_frequency = int(self.backend_params['drive_frequency'] + self.backend_params['anharmonicity'])
        self.freq_sweeping_range_ghz: NDArray = set_up_freq(center_freq=self.default_frequency)

    def prepare_circuit(self) -> None:
        """ Some logic as TR1, however we add X gate to resemble state 12
        """

        self.pulse_model: Pulse12
        freq_sweeping_range = self.freq_sweeping_range_ghz * ghz_unit
        # Sweeping
        for freq in freq_sweeping_range:
            qc_sweep = QuantumCircuit(self.qubit + 1, self.cbit + 1)
            qc_sweep.x(self.qubit)
            # noinspection DuplicatedCode
            qc_sweep.append(self._sweep_gate, [self.qubit])
            freq_schedule = GateSchedule.freq_gaussian(
                backend=self.backend,
                frequency=freq,
                pulse_model=self.pulse_model,
                qubit=self.qubit
            )
            qc_sweep.measure(self.qubit, self.cbit)
            qc_sweep.add_calibration(self._sweep_gate, [self.qubit], freq_schedule)
            self.package.append(qc_sweep)

    def modify_pulse_model(self, job_id: str = None) -> None:
        """ Only used for debugging + getting result from past job
        Args:
            job_id: string representation of submitted job

        Returns:

        """
        self.pulse_model: Pulse12
        f12 = self.analyze(job_id=job_id)
        self.pulse_model.frequency = f12
