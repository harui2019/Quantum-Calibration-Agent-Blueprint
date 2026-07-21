from __future__ import annotations

import sys

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from qblox_scheduler.qblox.hardware_agent import HardwareAgent
from single_qubit_experiment_helpers.experiment import Experiment

# 1. Initialize the Hardware Agent
hw_agent = HardwareAgent(
    hardware_configuration="./dependencies/configs/2x2/hw_config_AS_QRC.json",
    quantum_device_configuration="./dependencies/configs/2x2/dut_config_AS_QRC.json",
    output_dir=r"/Users/renychang/Desktop/qblox/2x2"
)

Experiment.hw_agent = hw_agent
Experiment.quantum_device = hw_agent.quantum_device

# 2. Fetch Qubits
q1 = hw_agent.quantum_device.get_element("q1")
q2 = hw_agent.quantum_device.get_element("q2")
q3 = hw_agent.quantum_device.get_element("q3")
q4 = hw_agent.quantum_device.get_element("q4")

# 3. Fetch Couplers
c12 = hw_agent.quantum_device.get_element("c12")
c23 = hw_agent.quantum_device.get_element("c23")
c34 = hw_agent.quantum_device.get_element("c34")
c14 = hw_agent.quantum_device.get_element("c14")

# Master lists for easy iteration
all_qubits = [q1, q2, q3, q4]
all_couplers = [c12, c23, c34, c14]
all_elements = all_qubits + all_couplers

# 5. Fetch Global Hardware Objects
clusters = hw_agent.get_clusters() # Note: returns a dict with 'cluster_A' and 'cluster_B'
hw_options = hw_agent.hardware_configuration.hardware_options

# 6. Verification Printout
print("\n--- Hardware Agent Initialized ---")
print(f"Total Qubits Loaded: {len(all_qubits)}")
print(f"Total Couplers Loaded: {len(all_couplers)}")
# cluster = clusters["cluster_A"]
# module = cluster.module4
