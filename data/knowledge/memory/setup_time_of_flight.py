"""
Setup script to initialize qblox hardware and run time of flight experiment.
"""
import sys
import os

# Add the flux-tunable-transmons path to sys.path
flux_tunable_path = '/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting'
if flux_tunable_path not in sys.path:
    sys.path.insert(0, flux_tunable_path)

from qblox_scheduler.qblox.hardware_agent import HardwareAgent
from qblox_scheduler.calibration.nodes.cal00_time_of_flight import Cal00TimeOfFlight

def setup_qblox():
    """Initialize the qblox hardware agent."""
    base_dir = '/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers'
    
    hw_config_path = os.path.join(
        base_dir, 
        'docs/applications/superconducting/dependencies/configs/2x2/hw_config_AS_QRC.json'
    )
    
    dut_config_path = os.path.join(
        base_dir, 
        'docs/applications/superconducting/dependencies/configs/2x2/dut_config_AS_QRC.json'
    )
    
    output_dir = '/Users/renychang/Desktop/qblox/2x2'
    
    print(f"Initializing qblox hardware agent...")
    print(f"  Hardware config: {hw_config_path}")
    print(f"  DUT config: {dut_config_path}")
    print(f"  Output dir: {output_dir}")
    
    hw_agent = HardwareAgent(
        hardware_configuration=hw_config_path,
        quantum_device_configuration=dut_config_path,
        output_dir=output_dir
    )
    
    # Set the hardware agent on the calibration node
    Cal00TimeOfFlight.hw_agent = hw_agent
    Cal00TimeOfFlight.quantum_device = hw_agent.quantum_device
    
    print("Hardware agent initialized successfully!")
    return hw_agent

def run_time_of_flight(qubit_name='q1', module_number=0):
    """Run the time of flight experiment on the specified qubit."""
    setup_qblox()
    
    params = {
        'qubits': [qubit_name],
        'module_number': module_number,
        'frequency_detuning_hz': 10000000.0,
        'pulse_duration_s': 2e-06,
        'pulse_amplitude': 0.1,
        'acquisition_duration_s': 4e-06,
        'repetitions': 100,
        'acquisition_delay_s': 0.0,
        'playback_delay_s': 1.46e-07,
        'apply_update': False
    }
    
    print(f"Running time of flight experiment on {qubit_name}...")
    Cal00TimeOfFlight.execute(params)
    print("Experiment completed!")

if __name__ == '__main__':
    qubit = sys.argv[1] if len(sys.argv) > 1 else 'q1'
    run_time_of_flight(qubit)
