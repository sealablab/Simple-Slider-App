"""
Progressive Test Level 1 (P1) - Demo Probe Driver Wrapper (BASIC)

Fast smoke tests for CustomWrapper (bpd_forge architecture) integration.

Test Coverage:
- Reset behavior
- FORGE control scheme (CR0[31:29])
- Basic FSM state transitions (software trigger)
- Basic FSM state transitions (hardware trigger)
- Output pulse verification during FIRING

Expected Runtime: <5s
Expected Output: <20 lines (P1 standard)

Author: Moku Instrument Forge Team
Date: 2025-11-18
"""

import cocotb
from cocotb.triggers import ClockCycles
import sys
from pathlib import Path

# Add cocotb_tests directory to path for local test_base
COCOTB_TESTS_PATH = Path(__file__).parent.parent
if COCOTB_TESTS_PATH.exists():
    sys.path.insert(0, str(COCOTB_TESTS_PATH))

from test_base import TestBase

# Import DPD test utilities
from conftest import (
    setup_clock,
    reset_active_high,
    init_mcc_inputs,
    mcc_set_regs,
    wait_for_mcc_ready,
    forge_cr0,
)

from dpd_wrapper_tests.dpd_wrapper_constants import (
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    MCC_CR0_ALL_ENABLED,
    P1TestValues,
)

from dpd_wrapper_tests.dpd_helpers import (
    read_output_c,
    assert_state,
    wait_for_state,
    wait_cycles_relaxed,
    arm_dpd,
    software_trigger,
    hardware_trigger,
    wait_for_fsm_complete_cycle,
)


class DPDWrapperBasicTests(TestBase):
    """P1 (BASIC) tests for Demo Probe Driver wrapper"""

    def __init__(self, dut):
        super().__init__(dut, "dpd_wrapper")

    async def run_p1_basic(self):
        """P1 test suite entry point - 5 essential tests"""
        # Setup clock and reset
        await setup_clock(self.dut, period_ns=8, clk_signal="Clk")
        await reset_active_high(self.dut, rst_signal="Reset", cycles=10)
        await init_mcc_inputs(self.dut)

        # Initialize all Control Registers to 0
        for i in range(16):
            ctrl_name = f"Control{i}"
            if hasattr(self.dut, ctrl_name):
                getattr(self.dut, ctrl_name).value = 0

        # Run 5 essential tests
        await self.test("Reset behavior", self.test_reset)
        await self.test("FORGE control scheme", self.test_forge_control)
        await self.test("FSM cycle (software trigger)", self.test_fsm_software_trigger)
        await self.test("FSM cycle (hardware trigger)", self.test_fsm_hardware_trigger)
        await self.test("Output pulses during FIRING", self.test_output_pulses)

    async def test_reset(self):
        """Verify Reset drives FSM to IDLE state via OutputC"""
        # Assert reset
        self.dut.Reset.value = 1
        await ClockCycles(self.dut.Clk, 5)

        # Check FSM is in IDLE via HVS digital encoding on OutputC
        assert_state(self.dut, HVS_DIGITAL_IDLE, context="after reset")

        # Check outputs are inactive
        output_a = int(self.dut.OutputA.value.signed_integer)
        output_b = int(self.dut.OutputB.value.signed_integer)
        assert output_a == 0, f"OutputA should be 0 after reset, got {output_a}"
        assert output_b == 0, f"OutputB should be 0 after reset, got {output_b}"

        # Release reset
        self.dut.Reset.value = 0
        await ClockCycles(self.dut.Clk, 2)

    async def test_forge_control(self):
        """Verify FORGE control scheme enables module correctly"""
        # Release reset
        self.dut.Reset.value = 0
        await ClockCycles(self.dut.Clk, 2)

        # Test: Partial FORGE enable (missing clk_enable) - FSM should NOT arm
        await mcc_set_regs(self.dut, {
            0: 0xC0000000,  # forge_ready=1, user_enable=1, clk_enable=0 (WRONG!)
            1: 0x00000001,  # arm_enable=1
        })
        await ClockCycles(self.dut.Clk, 20)

        # FSM should remain IDLE (global_enable=0 blocks operation)
        assert_state(self.dut, HVS_DIGITAL_IDLE, context="partial FORGE enable")

        # Test: Complete FORGE enable (all 3 bits) - FSM should arm
        await mcc_set_regs(self.dut, {
            0: MCC_CR0_ALL_ENABLED,  # forge_ready=1, user_enable=1, clk_enable=1
            1: 0x00000001,  # arm_enable=1
        })

        # Wait for ARMED state
        await wait_for_state(self.dut, HVS_DIGITAL_ARMED, timeout_us=100)

    async def test_fsm_software_trigger(self):
        """Verify complete FSM cycle using software trigger (sw_trigger)"""
        # Ensure FORGE control enabled and FSM in IDLE
        self.dut.Reset.value = 0
        await mcc_set_regs(self.dut, {0: MCC_CR0_ALL_ENABLED})
        await ClockCycles(self.dut.Clk, 5)

        # Arm FSM with P1 test timing values (fast for P1)
        await arm_dpd(
            self.dut,
            trig_duration=P1TestValues.TRIG_OUT_DURATION,
            intensity_duration=P1TestValues.INTENSITY_DURATION,
            cooldown=P1TestValues.COOLDOWN_INTERVAL,
        )

        # FSM should be ARMED
        assert_state(self.dut, HVS_DIGITAL_ARMED, context="after arm")

        # Software trigger via CR1[1]
        await software_trigger(self.dut)

        # FSM should be FIRING
        assert_state(self.dut, HVS_DIGITAL_FIRING, context="after software trigger")

        # Wait for complete FSM cycle: FIRING → COOLDOWN → IDLE
        total_firing = P1TestValues.TRIG_OUT_DURATION + P1TestValues.INTENSITY_DURATION
        await wait_for_fsm_complete_cycle(
            self.dut,
            firing_cycles=total_firing,
            cooldown_cycles=P1TestValues.COOLDOWN_INTERVAL,
        )

        # Should be back in IDLE
        assert_state(self.dut, HVS_DIGITAL_IDLE, context="after FSM cycle complete")

    async def test_fsm_hardware_trigger(self):
        """Verify complete FSM cycle using hardware trigger (InputA voltage)"""
        # Ensure FORGE control enabled and FSM in IDLE
        self.dut.Reset.value = 0
        await mcc_set_regs(self.dut, {0: MCC_CR0_ALL_ENABLED})
        await ClockCycles(self.dut.Clk, 5)

        # Arm FSM
        await arm_dpd(
            self.dut,
            trig_duration=P1TestValues.TRIG_OUT_DURATION,
            intensity_duration=P1TestValues.INTENSITY_DURATION,
            cooldown=P1TestValues.COOLDOWN_INTERVAL,
        )

        # FSM should be ARMED
        assert_state(self.dut, HVS_DIGITAL_ARMED, context="after arm (hardware test)")

        # Hardware trigger via InputA voltage
        await hardware_trigger(
            self.dut,
            voltage_mv=P1TestValues.TRIGGER_TEST_VOLTAGE_MV,  # 1500mV
            threshold_mv=P1TestValues.TRIGGER_THRESHOLD_MV,  # 950mV
        )

        # FSM should be FIRING
        assert_state(self.dut, HVS_DIGITAL_FIRING, context="after hardware trigger")

        # Wait for complete FSM cycle
        total_firing = P1TestValues.TRIG_OUT_DURATION + P1TestValues.INTENSITY_DURATION
        await wait_for_fsm_complete_cycle(
            self.dut,
            firing_cycles=total_firing,
            cooldown_cycles=P1TestValues.COOLDOWN_INTERVAL,
        )

        # Should be back in IDLE
        assert_state(self.dut, HVS_DIGITAL_IDLE, context="after hardware trigger cycle")

    async def test_output_pulses(self):
        """Verify OutputA and OutputB pulses are active during FIRING state"""
        # Ensure FORGE control enabled
        self.dut.Reset.value = 0
        await mcc_set_regs(self.dut, {0: MCC_CR0_ALL_ENABLED})
        await ClockCycles(self.dut.Clk, 5)

        # Arm with non-zero output voltages
        await arm_dpd(
            self.dut,
            trig_duration=P1TestValues.TRIG_OUT_DURATION,
            intensity_duration=P1TestValues.INTENSITY_DURATION,
            cooldown=P1TestValues.COOLDOWN_INTERVAL,
        )

        # Set output voltages (CR2[15:0] = trig, CR3[15:0] = intensity)
        await mcc_set_regs(self.dut, {
            2: (950 << 16) | 2000,  # CR2: threshold=950mV, trig_voltage=2000mV
            3: 1500,  # CR3: intensity_voltage=1500mV
        }, set_forge_ready=False)

        # Trigger
        await software_trigger(self.dut)

        # In FIRING state - check outputs are non-zero
        await ClockCycles(self.dut.Clk, 10)  # Let outputs settle
        output_a = int(self.dut.OutputA.value.signed_integer)
        output_b = int(self.dut.OutputB.value.signed_integer)

        assert output_a != 0, f"OutputA should be active during FIRING, got {output_a}"
        assert output_b != 0, f"OutputB should be active during FIRING, got {output_b}"

        # Wait for FIRING to complete, check outputs return to zero
        total_firing = P1TestValues.TRIG_OUT_DURATION + P1TestValues.INTENSITY_DURATION
        await wait_cycles_relaxed(self.dut, total_firing, margin_percent=50)
        await wait_for_state(self.dut, HVS_DIGITAL_COOLDOWN, timeout_us=200)

        # Outputs should be zero in COOLDOWN
        output_a_cooldown = int(self.dut.OutputA.value.signed_integer)
        output_b_cooldown = int(self.dut.OutputB.value.signed_integer)
        assert output_a_cooldown == 0, f"OutputA should be 0 in COOLDOWN, got {output_a_cooldown}"
        assert output_b_cooldown == 0, f"OutputB should be 0 in COOLDOWN, got {output_b_cooldown}"


@cocotb.test()
async def test_dpd_wrapper_p1(dut):
    """Entry point for P1 tests"""
    tester = DPDWrapperBasicTests(dut)
    await tester.run_all_tests()
