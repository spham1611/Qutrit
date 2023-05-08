"""List all the vm_backend available and assign qubit value"""
from qiskit_ibm_provider import IBMProvider, IBMBackend
from typing import DefaultDict, Tuple, List
from src.constant import QUBIT_PARA


class BackEndDict(DefaultDict[str, Tuple]):
    """Show the name of backends and map the qubit used for each vm_backend"""

    def __init__(self, /, token: str = '', overwrite: bool = True) -> None:
        """

        """
        super().__init__()
        # IBM Config -> activate account in this file
        self.provider = IBMProvider()
        if not self.provider.active_account() and not token:
            raise EnvironmentError("Can't find the account saved in this session. Please activate in the script folder")
        elif token:
            try:
                self.provider.save_account(token=token, overwrite=overwrite)
                # Create dummy var to check if we can access IBM account
                self.provider.get_backend('ibm_nairobi')
            except TimeoutError:
                print('Invalid token')

        self._available_backends: List[IBMBackend] = []
        self._set_up()

    def _set_up(self) -> None:
        """
        Get the name from each vm_backend
        :return:
        """
        self._available_backends = self.provider.backends()
        for backend in self._available_backends:
            # We set it all to 0 except nairobi vm_backend
            if "nairobi" in str(backend_name := backend.name):
                self[backend_name] = backend, QUBIT_PARA.NUM_QUBIT_TYPE2.value
            else:
                self[backend_name] = backend, QUBIT_PARA.NUM_QUBIT_TYPE1.value

    def show(self) -> None:
        """
        Show the name of all available backends and their associated qubit used
        :return:
        """
        print(f"{'Backend name:':<30}{'# Qubit used:':<40}")
        for name in self:
            print(f"{name:<30}{self[name][1]:<40}")

    def default_backend(self, quantum_computer: str = 'ibm_nairobi') -> Tuple[IBMBackend, int]:
        """
        Return nairobi vm_backend as the default and its qubit value
        :return:
        """
        backend = self[quantum_computer][0]
        return backend, self[quantum_computer][1]
