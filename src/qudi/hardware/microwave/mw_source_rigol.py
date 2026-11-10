# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Rigol microwave device.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

try:
    import pyvisa as visa
except ImportError:
    import visa
import time
import numpy as np

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.util.enums import SamplingOutputMode


class MicrowaveRigol():
    """ This is the Interface class to define the controls for the simple
        microwave hardware.

    Example config for copy-paste:

    mw_source_smiq:
        module.Class: 'microwave.mw_source_smiq.MicrowaveSmiq'
        options:
            visa_address: 'GPIB0::28::INSTR'
            visa_timeout: 10000  # in milliseconds
            visa_baud_rate: null  # optional
            rising_edge_trigger: True  # optional
            frequency_min: null  # optional, in Hz
            frequency_max: null  # optional, in Hz
            power_min: null  # optional, in dBm
            power_max: null  # optional, in dBm
    """

    def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)

        self._rm = None
        self._device = None

    def _set_visa_params(self, visa_address, visa_timeout, visa_baud_rate=None):
        self._visa_address = visa_address
        self._visa_timeout = visa_timeout
        self._visa_baud_rate = visa_baud_rate
        
    
    def activate_visa(self, visa_address, visa_timeout, visa_baud_rate=None):
        self._set_visa_params(visa_address, visa_timeout, visa_baud_rate)
        # Connect to hardware
        self._rm = visa.ResourceManager()

        if self._visa_baud_rate is None:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._visa_timeout,
                                                  write_termination="\n",
                                                  read_termination="\n")
        else:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._visa_timeout,
                                                  baud_rate=self._visa_baud_rate,
                                                  write_termination="\n",
                                                  read_termination="\n")
    
    def deactivate_visa(self):
        """ Cleanup performed during deactivation of the module. """
        self._device.close()
        self._rm.close()
        self._device = None
        self._rm = None
        
    
    def write(self, message):
        self._device.write(message)

    def read(self):
        return self._device.read()

    def query(self, message):
        return self._device.query(message)

    def preset(self):
        self.write(":SYST:PRES:TYPE FAC")
        self.write(":SYST:PRES")

    def output_on(self):
        self.write("OUTP ON")

    def output_off(self):
        self.write("OUTP OFF")

    def is_output_on(self):
        return self.query("OUTPUT?")

    def set_power_limit(self, power_limit, unit='dBm'):
        """
        Set the limit of the RF output amplitude. 
        """
        self.write(f"LEVEL:LIMIT {power_limit}{unit}")

    def get_power_limit(self):
        """
        Get the limit of the RF output amplitude. 
        """        
        return self.query("LEVEL:LIMIT?")

    def set_freq(self, freq, unit="Hz"):
        """
        Set the frequency with unit. 
        The unit option includes Hz, kHz, MHz, and GHz.
        """
        self.write(f"FREQ {freq}{unit}")

    def get_freq(self):
        return self.query(f"FREQ?")
    
    def set_power(self, power, unit="dBm"):
        """
        Set the RF signal power.
        """
        #TODO check range
        self.write(f"LEV {power}{unit}")

    def get_power(self):
        """
        Get the RF power.
        """
        return self.query(f"LEV?")
    
    def set_sweep_type(self, sweep_type):
        """
        Set sweep type, LIST or STEP.
        """
        self.write(f":SWEEP:TYPE {sweep_type}")

    def get_sweep_type(self):
        """
        Set sweep type, LIST or STEP.
        """
        return self.query(f":SWEEP:TYPE?")

    def set_dwell_time(self, dwell_time, unit="ms"):
        """
        Set the dwell time of step sweep. 
        """
        self.write(f"SWEEP:STEP:DWELL {dwell_time}{unit}")

    def get_dwell_time(self):
        """
        Get the dwell time of step sweep. 
        """
        return self.query(f"SWEEP:STEP:DWELL?")
        
    def set_sweep_mode(self, mode="CONT"):
        """
        Set the sweep mode from CONTinue or SINGle.
        """
        self.write(f"SWEEP:MODE {mode}")

    def get_sweep_mode(self):
        """
        Get the sweep mode from CONTinue or SINGle.
        """
        return self.query(f"SWEEP:MODE?")

    
    def set_sweep_manner(self, sweep_manner):
        """
        Set the sweep manner from OFF, FREQuency, LEVel, or LEVel,FREQuency.
        """
        self.write(f"SWEEP:STATE {sweep_manner}")

    def get_sweep_manner(self):
        """
        Get the sweep manner from OFF, FREQuency, LEVel, or LEVel,FREQuency.
        """
        return self.query(f"SWEEP:STATE?")

    def abort_sweep(self):
        """
        Abort the ongoing sweep by switching off the sweep and turning off the output.
        """
        self.output_off()

        # self.set_sweep_manner("OFF")
    
    def set_sweep_trig_mode(self, trig_mode="EXT"):
        """
        Set the trigger mode of the sweeep period from AUTO|KEY|BUS|EXT.
        """
        self.write(f":SWEEP:SWEEP:TRIGGER:TYPE {trig_mode}")        

    def get_sweep_trig_mode(self):
        """
        Get the trigger mode of the sweeep period from AUTO|KEY|BUS|EXT.
        """
        return self.query(f":SWEEP:SWEEP:TRIGGER:TYPE?")        
        
    def set_point_trig_mode(self, trig_mode="AUTO"):
        """
        Set the point trigger mode of the sweep from AUTO, KEY, BUS or EXT.
        This specifies how to move to another point in the sweep.
        """
        self.write(f":SWEEP:POINT:TRIGGER:TYPE {trig_mode}")

    def get_point_trig_mode(self):
        """
        Set the point trigger mode of the sweep from AUTO, KEY, BUS or EXT.
        This specifies how to move to another point in the sweep.
        """
        return self.query(f":SWEEP:POINT:TRIGGER:TYPE?")
    
    def set_trigger_slope(self, polarity):
        """
        Set the polarity of the external trigger input signal from POSitive or NEGative.
        """
        self.write(f":INPUT:TRIGGER:SLOPE {polarity}")

    def get_trigger_slope(self):
        """
        Set the polarity of the external trigger input signal from POSitive or NEGative.
        """
        return self.query(f":INPUT:TRIGGER:SLOPE?")

    def reset_sweep_point(self):
        self.write("SWEEP:RESET")
        
    def configure_step_freq_sweep(self, start_freq, stop_freq, point, unit="Hz"):
        self.write(f":SWEEP:STEP:STAR:FREQ {start_freq}{unit}")
        self.write(f":SWEEP:STEP:STOP:FREQ {stop_freq}{unit}")
        self.write(f":SWEEP:STEP:POINTS {point}")

    def send_trigger(self):
        """
        Trigger a pulse modulation, RF sweep or IQ wavetable output immediately. 
        """
        self.write("*TRG")

class MicrowaveRigolHardware(MicrowaveInterface, MicrowaveRigol):
    """
    Example config for copy-paste:

    mw_source_rigol:
        module.Class: 'microwave.mw_source_rigol.MicrowaveRigolHardware'
        options:
            visa_address: ''
            visa_timeout: 10000  # in milliseconds
            visa_baud_rate: null  # optional
            rising_edge_trigger: True  # optional
            frequency_min: null  # optional, in Hz
            frequency_max: null  # optional, in Hz
            power_min: null  # optional, in dBm
            power_max: 10  # optional, in dBm

        There are two modes of operation:
        - CW: constant frequency and constant power (with no external trigger)
        - scan: variable frequency and constant power (with external trigger)

    For the scan, the following scanning method is implemented:
        - equidistant sweep: a start and stop frequency, and step count

    """
    _visa_address = ConfigOption('visa_address', missing='error')
    _visa_timeout = ConfigOption('visa_timeout', default=10, missing='warn')
    _visa_baud_rate = ConfigOption('visa_baud_rate', default=None)
    _rising_edge_trigger = ConfigOption('rising_edge_trigger', default=True, missing='info')

    #User defined limits
    _config_freq_min = ConfigOption('frequency_min', default=None)
    _config_freq_max = ConfigOption('frequency_max', default=None)
    _config_power_min = ConfigOption('power_min', default=None)
    _config_power_max = ConfigOption('power_max', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._model = ''
        self._constraints = None
        self._cw_power = -110
        self._cw_frequency = 2.0e9
        self._scan_power = -110
        self._scan_frequencies = None
        self._scan_mode = None
        self._scan_sample_rate = 0.

        self._thread_lock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        self.activate_visa(self._visa_address, self._visa_timeout)
        
        self._model = self.query('*IDN?').split(',')[1]
        # # Reset device
        # self._command_wait('*CLS')
        # self._command_wait('*RST')

        # Generate constraints
        if self._model == 'DSG3136B':
            freq_limits = (9e3, 13.6e9)
            power_limits = (-130, 27)
        else:
            self.log.warning('Model string unknown, hardware limits may be wrong.')
            
        # Apply configured soft-boundaries
        if self._config_power_min is not None:
            assert self._config_power_min < power_limits[1]
            power_limits = (max(power_limits[0], self._config_power_min), power_limits[1])
        if self._config_power_max is not None:
            assert self._config_power_max > power_limits[0]
            power_limits = (power_limits[0], min(power_limits[1], self._config_power_max))
            self.set_power_limit(self._config_power_max)
        if self._config_freq_min is not None:
            assert self._config_freq_min < freq_limits[1]
            freq_limits = (max(freq_limits[0], self._config_freq_min), freq_limits[1])
        if self._config_freq_max is not None:
            assert self._config_freq_max > freq_limits[0]
            freq_limits = (freq_limits[0], min(freq_limits[1], self._config_freq_max))
        self._constraints = MicrowaveConstraints(
            power_limits=power_limits,
            frequency_limits=freq_limits,
            scan_size_limits=(2, 65535),
            sample_rate_limits=(0.01, 50), #Dwell time: 20e-3 - 100 s  
            scan_modes=(#SamplingOutputMode.JUMP_LIST, 
                        SamplingOutputMode.EQUIDISTANT_SWEEP,)
        )

        self._scan_frequencies = None
        self._scan_power = self._constraints.min_power
        self._cw_power = self._constraints.min_power
        self._cw_frequency = 2870.0e6
        self._scan_mode = SamplingOutputMode.EQUIDISTANT_SWEEP
        self._scan_sample_rate = self._constraints.max_sample_rate

    def on_deactivate(self):
        self.deactivate_visa()

    @property
    def constraints(self):
        return self._constraints

    @property
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used together with
        module_state() to determine if the currently running microwave output is a scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        with self._thread_lock:
            return (self.module_state() != 'idle') and self._sweep_mode != "CW"

    @property
    def cw_power(self):
        """The CW microwave power in dBm. Must implement setter as well.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            return self._cw_power

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return self._cw_frequency

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning. Must implement setter as well.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @property
    def scan_frequencies(self):
        """The microwave frequencies used for scanning. Must implement setter as well.

        In case of scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been specified, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        with self._thread_lock:
            return self._scan_frequencies

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return self._scan_mode

    @property
    def scan_sample_rate(self):
        """Read-only property returning the currently configured scan sample rate in Hz.

        @return float: The currently set scan sample rate in Hz
        """
        with self._thread_lock:
            return self._scan_sample_rate

    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set CW parameters. Microwave output active.')
            self._assert_cw_parameters_args(frequency, power)

            if self._sweep_mode != "CW":
                self._configure_cw_mode()
            self.set_freq(frequency)
            self.set_power(power)

            self._cw_frequency = float(self.get_freq())
            self._cw_power = float(self.get_power())

    def _configure_cw_mode(self):
        self.set_sweep_manner("OFF")
        # The following two modes are not necessary in "OFF" sweep manner.
        # They are written for clarity.
        self.set_sweep_trig_mode("AUTO")
        self.set_point_trig_mode("AUTO")

    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        Configure a frequency scan.
        
        @param float power: the power in dBm to be used during the scan
        @param float[] frequencies: an array of all frequencies (jump list)
                                    or a tuple of start, stop frequency and number of steps (equidistant sweep)
        @param SamplingOutputMode mode: enum stating the way how the frequencies are defined
        @param float sample_rate: external scan trigger rate
        """
        with self._thread_lock:
            # Sanity checks
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to configure frequency scan. Microwave output active.')
            self._assert_scan_configuration_args(power, frequencies, mode, sample_rate)

            # configure scan according to scan mode
            self._scan_mode = mode
            self._scan_sample_rate = sample_rate
            self._scan_power = power
            if mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._configure_sweep_mode()
                self._configure_trigger()
                self._scan_frequencies = tuple(frequencies)
                self._write_sweep()
            else:
                self.log.error("This mode is not implemented")

    def _configure_sweep_mode(self):
        self.set_sweep_manner("FREQ")
        self.set_sweep_trig_mode("EXT")
        self.set_point_trig_mode("AUTO")

    @property
    def _sweep_mode(self):
        """
        Sweep mode: CW or SWEEP.
        
        """
        sweep_manner = self.get_sweep_manner()
        sweep_trig_mode = self.get_sweep_trig_mode()

        if "OFF" in sweep_manner  and "AUTO" in sweep_trig_mode :
            return "CW"

        elif "FREQ" in sweep_manner and "EXT" in sweep_trig_mode:
            return "SWEEP"

        else:
            return "UNKNOWN"

    @property
    def is_output_on(self):
        return bool(int(super().is_output_on()))


    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self.output_off()
                # while self.is_output_on:
                #     time.sleep(0.2)

                self.module_state.unlock()
    
    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            # if self.module_state() != 'idle':
                # if self._sweep_mode == "CW":
                #     return
                # raise RuntimeError(
                #     'Unable to start CW microwave output. Microwave output is currently active.'
                # )
            if self._sweep_mode == "SWEEP":
                self._configure_cw_mode()
                self.set_freq(self._cw_frequency)
                self.set_power(self._cw_power)

            self.output_on()
            while self.is_output_on == False:
                time.sleep(0.2)
            self.module_state.lock()

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if self._sweep_mode != "CW":
                    return
                raise RuntimeError('Unable to start frequency scan. CW microwave output is active.')
            assert self._scan_frequencies is not None, \
                'No scan_frequencies set. Unable to start scan.'

            if self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                # self._write_sweep()

                self.output_on()
                # while self.is_output_on == False:
                #     time.sleep(0.2)
            else:
                raise RuntimeError(
                    f'Invalid scan mode encountered ({self._scan_mode}). Please set scan_mode '
                    f'property before configuring or starting a frequency scan.'
                )
            self.module_state.lock()

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        #TODO
        with self._thread_lock:
            if self.module_state() == 'idle':
                return
            
            if self._sweep_mode == "CW":
                raise RuntimeError('Can not reset frequency scan. CW microwave output active.')

            elif self._sweep_mode == "SWEEP":
                self.abort_sweep()
                
    # elif self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
            #     self._command_wait(':ABOR:SWE')

    def _command_wait(self, command_str):
        #TODO
        """ Writes the command in command_str via PyVisa and waits until the device has finished
        processing it.

        @param str command_str: The command to be written
        """
        self.write(command_str)
        self.write('*WAI')
        while int(float(self.query('*OPC?'))) != 1:
            time.sleep(0.2)

    def _configure_trigger(self):
        # self.set_point_trig_mode("EXT")
        edge = 'POS' if self._rising_edge_trigger else 'NEG'
        self.set_trigger_slope(edge)
    
    def _write_sweep(self):
        self.set_sweep_manner("FREQ")
        self.set_sweep_type("STEP")
        self.set_sweep_mode("CONT")

        self.set_power(self._scan_power)

        start_freq, stop_freq, points = self._scan_frequencies
        self.configure_step_freq_sweep(start_freq, stop_freq, points) 


        # self.write('*WAI')

        # self._command_wait(':TRIG1:SWE:SOUR EXT')



