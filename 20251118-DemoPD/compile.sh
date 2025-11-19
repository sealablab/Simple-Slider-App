#!/bin/bash
ghdl -a ./forge_common_pkg.vhd ./CustomWrapper_test_stub.vhd ./moku_voltage_threshold_trigger_core.vhd ./DPD_main.vhd ./DPD_shim.vhd ./DPD.vhd
