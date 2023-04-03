"""
Contain pulse classes
"""
from __future__ import annotations
from abc import ABC
from typing import Dict, Optional
import os
import json
import pandas as pd
import uuid


class Pulse_List(list["Pulse"]):
    """List of pulses which in turn can be saved in csv or test files"""

    def pulse_dictionary(self) -> Dict:
        """Convert list of pulse to dictionary"""
        dict_pulses = {'pulse id': [],
                       'mode': [],
                       'duration': [],
                       'frequency': [],
                       'x_amp': [],
                       'sx_amp': [],
                       'beta_dephase': [],
                       'beta_leakage': [],
                       'sigma': [],
                       'pulse_pointer': [],
                       }
        for pulse in self:
            pulse: Pulse
            dict_pulses['pulse id'].append(pulse.id)
            if isinstance(pulse, Pulse01):
                pulse: Pulse01
                dict_pulses['mode'].append("01")
                dict_pulses['pulse_pointer'].append(pulse.pulse12.id if pulse.pulse12 else None)
            elif isinstance(pulse, Pulse12):
                pulse: Pulse12
                dict_pulses['mode'].append("12")
                dict_pulses['pulse_pointer'].append(pulse.pulse01.id)
            else:
                dict_pulses['mode'].append(None)
                dict_pulses['pulse_pointer'].append(None)
            dict_pulses['duration'].append(pulse.duration)
            dict_pulses['frequency'].append(pulse.frequency)
            dict_pulses['x_amp'].append(pulse.x_amp)
            dict_pulses['sx_amp'].append(pulse.sx_amp)
            dict_pulses['beta_dephase'].append(pulse.beta_dephase)
            dict_pulses['beta_leakage'].append(pulse.beta_leakage)
            dict_pulses['sigma'].append(pulse.sigma)

        return dict_pulses

    def save_pulses(self, saved_type: str, file_name: str = "pulses"):
        """
        Save list of pulses in csv using panda.DataFrame and json using python standard library
        Save file in output path which is in qutrit/output
        :param saved_type:
        :param file_name:
        :return:
        """
        dict_pulses = self.pulse_dictionary()
        # Get the current directory of the script
        file_path = os.path.abspath(__file__).split("\\")[:-2]
        file_path = "\\".join(file_path)
        file_path = os.path.join(file_path, "output")
        if saved_type == 'csv':
            # Save CSV
            save_pulses_df = pd.DataFrame(dict_pulses)
            save_pulses_df['mode'] = save_pulses_df['mode'].apply('="{}"'.format)
            print(save_pulses_df['mode'])
            full_path = file_path + f"\\{file_name}" + ".csv"
            save_pulses_df.to_csv(full_path, index=False, )
        elif saved_type == "json":
            # Save JSON
            json_pulse = json.dumps(dict_pulses, indent=4)
            full_path = file_path + f"\\{file_name}" + ".json"
            with open(full_path, "w") as outfile:
                outfile.write(json_pulse)
        else:
            raise IOError("Unsupported type!")


class Pulse(ABC):
    """
    Our pulse have 5 distinct parameters which can be accessed, shown and saved as a plot.
    For developers, we attempt to use these variables as inner variables only
    """
    pulse_list = Pulse_List()

    def __init__(self, frequency: float = 0, x_amp: float = 0, sx_amp: float = 0,
                 beta_dephase: float = 0, beta_leakage: float = 0, duration: int = 0) -> None:
        """

        :param frequency:
        :param x_amp:
        :param sx_amp:
        :param beta_dephase:
        :param beta_leakage:
        :param duration:
        """
        self.frequency = frequency
        self.x_amp = x_amp
        self.sx_amp = sx_amp
        self.beta_leakage = beta_leakage
        self.beta_dephase = beta_dephase
        self.duration = duration
        self.sigma = duration / 4 if duration else 0
        self.id = uuid.uuid4()
        Pulse.pulse_list.append(self)

    @staticmethod
    def convert_to_qiskit_pulse():
        """Convert to qiskit pulse type"""
        pass


class Pulse01(Pulse):
    """Pulse of 0 -> 1 state"""

    def __init__(self, frequency: float = 0, x_amp: float = 0, sx_amp: float = 0,
                 beta_dephase: float = 0, beta_leakage: float = 0, duration: int = 0,
                 pulse12: Pulse12 = None) -> None:
        """

        :param frequency:
        :param x_amp:
        :param sx_amp:
        :param beta_dephase:
        :param beta_leakage:
        :param duration:
        :param pulse12: point to related 12 state
        """
        super().__init__(frequency=frequency, x_amp=x_amp, sx_amp=sx_amp,
                         beta_dephase=beta_dephase, beta_leakage=beta_leakage, duration=duration)
        self.pulse12 = pulse12

    def __str__(self) -> str:
        return (
            f"Pulse01: id={self.id}, frequency={self.frequency}, "
            f"x_amp={self.x_amp}, sx_amp={self.sx_amp}, "
            f"beta_dephase={self.beta_dephase}, beta_leakage={self.beta_leakage}, "
            f"duration={self.duration}, sigma={self.sigma}"
        )

    def __repr__(self) -> str:
        return (
            f"Pulse01: id={self.id}, frequency={self.frequency}, "
            f"x_amp={self.x_amp}, sx_amp={self.sx_amp}, "
            f"beta_dephase={self.beta_dephase}, beta_leakage={self.beta_leakage}, "
            f"duration={self.duration}, sigma={self.sigma}"
        )

    def __eq__(self, other: "Pulse01") -> bool:
        return (
                self.frequency == other.frequency
                and self.x_amp == other.x_amp
                and self.sx_amp == other.sx_amp
                and self.beta_leakage == other.beta_leakage
                and self.beta_dephase == other.beta_dephase
                and self.duration == other.duration
        )

    def is_pulse12_there(self) -> bool:
        """

        :return:
        """
        return self.pulse12 is not None


class Pulse12(Pulse):
    """Pulse of 1 -> 2 state"""

    def __init__(self, pulse01: Pulse01, frequency: float = 0, x_amp: float = 0, sx_amp: float = 0,
                 beta_dephase: float = 0, beta_leakage: float = 0, duration: int = 0,
                 ) -> None:
        """

        :param frequency:
        :param x_amp:
        :param sx_amp:
        :param beta_dephase:
        :param beta_leakage:
        :param duration:
        :param pulse01: Not allowed to be None
        """
        super().__init__(frequency=frequency, x_amp=x_amp, sx_amp=sx_amp,
                         beta_dephase=beta_dephase, beta_leakage=beta_leakage, duration=duration)
        self.pulse01 = pulse01
        self.pulse01.pulse12 = self

    def __str__(self) -> str:
        return (
            f"Pulse12: id={self.id}, frequency={self.frequency}, "
            f"x_amp={self.x_amp}, sx_amp={self.sx_amp}, "
            f"beta_dephase={self.beta_dephase}, beta_leakage={self.beta_leakage}, "
            f"duration={self.duration}, sigma={self.sigma}"
        )

    def __repr__(self) -> str:
        return (
            f"Pulse12: id={self.id}, frequency={self.frequency},"
            f" x_amp={self.x_amp}, sx_amp={self.sx_amp}, "
            f"beta_dephase={self.beta_dephase}, beta_leakage={self.beta_leakage}, "
            f"duration={self.duration}, sigma={self.sigma}"
        )

    def __eq__(self, other: "Pulse12") -> bool:
        return (
                self.frequency == other.frequency
                and self.x_amp == other.x_amp
                and self.sx_amp == other.sx_amp
                and self.beta_leakage == other.beta_leakage
                and self.beta_dephase == other.beta_dephase
                and self.duration == other.duration
                and self.pulse01 == other.pulse01
        )

    def is_pulse01_there(self) -> bool:
        """

        :return:
        """
        return self.pulse01 is not None


# Run demo on save_pulses
# pulse1 = Pulse01(duration=144, frequency=15000, x_amp=40, sx_amp=50, beta_dephase=5)
# pulse2 = Pulse01(duration=120, frequency=4000, x_amp=50, sx_amp=4, beta_leakage=10)
# pulse3 = Pulse12(pulse01=pulse2, duration=150, frequency=5000, beta_dephase=5)
#
# Pulse.pulse_list.save_pulses(saved_type='csv')
