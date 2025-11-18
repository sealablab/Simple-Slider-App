--------------------------------------------------------------------------------
-- File: DPD_shim.vhd
-- Modified: 2025-11-14
--
-- Description:
--   Register mapping shim for Demo Probe Driver (DPD) ForgeApp.
--   Maps raw Control Registers (CR20-CR30) to friendly signal names
--   and instantiates the application main entity.
--
-- Layer 2 of 3-Layer Forge Architecture:
--   Layer 1: DPD.vhd (TOP)
--   Layer 2: DPD_shim.vhd (THIS FILE - register mapping)
--   Layer 3: DPD_main.vhd (hand-written app logic)
--
-- Register Mapping:
--   CR1[3:0]   : Lifecycle control (arm_enable, ext_trigger_in, auto_rearm, fault_clear)
--   CR2[15:0]  : Trigger output voltage (mV)
--   CR3[15:0]  : Trigger pulse duration (ns)
--   CR4[15:0]  : Intensity output voltage (mV)
--   CR5[15:0]  : Intensity pulse duration (ns)
--   CR6[15:0]  : Trigger wait timeout (s)
--   CR7[23:0]  : Cooldown interval (μs)
--   CR8[1:0]   : Monitor control (enable, expect_negative)
--   CR9[15:0]  : Monitor threshold voltage (mV)
--   CR10[31:0] : Monitor window start delay (ns)
--   CR11[31:0] : Monitor window duration (ns)
--
-- References:
--   - forge_common_pkg.vhd (FORGE_READY control scheme)
--   - external_Example/DS1140_polo_shim.vhd (pattern reference)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;

entity DPD_shim is
    port (
        ------------------------------------------------------------------------
        -- Clock and Reset
        ------------------------------------------------------------------------
        Clk         : in  std_logic;
        Reset       : in  std_logic;  -- Active-high reset

        ------------------------------------------------------------------------
        -- FORGE Control Signals (from MCC_TOP_forge_loader or CustomWrapper)
        ------------------------------------------------------------------------
        forge_ready  : in  std_logic;  -- CR0[31] - Set by loader
        user_enable  : in  std_logic;  -- CR0[30] - User control
        clk_enable   : in  std_logic;  -- CR0[29] - Clock gating
        loader_done  : in  std_logic;  -- BRAM loader FSM done signal

        ------------------------------------------------------------------------
        -- Application Registers (from MCC_TOP_forge_loader)
        -- Raw Control Registers CR1-CR11 (MCC provides CR0-CR15)
        ------------------------------------------------------------------------
        app_reg_1 : in  std_logic_vector(31 downto 0);
        app_reg_2 : in  std_logic_vector(31 downto 0);
        app_reg_3 : in  std_logic_vector(31 downto 0);
        app_reg_4 : in  std_logic_vector(31 downto 0);
        app_reg_5 : in  std_logic_vector(31 downto 0);
        app_reg_6 : in  std_logic_vector(31 downto 0);
        app_reg_7 : in  std_logic_vector(31 downto 0);
        app_reg_8 : in  std_logic_vector(31 downto 0);
        app_reg_9 : in  std_logic_vector(31 downto 0);
        app_reg_10 : in  std_logic_vector(31 downto 0);
        app_reg_11 : in  std_logic_vector(31 downto 0);

        ------------------------------------------------------------------------
        -- BRAM Interface (from forge_bram_loader FSM)
        ------------------------------------------------------------------------
        bram_addr   : in  std_logic_vector(11 downto 0);  -- 4KB address space
        bram_data   : in  std_logic_vector(31 downto 0);  -- 32-bit data
        bram_we     : in  std_logic;                      -- Write enable

        ------------------------------------------------------------------------
        -- MCC I/O (from CustomWrapper)
        -- Native MCC types: signed(15 downto 0) for all ADC/DAC channels
        ------------------------------------------------------------------------
        InputA      : in  signed(15 downto 0);
        InputB      : in  signed(15 downto 0);
        OutputA     : out signed(15 downto 0);
        OutputB     : out signed(15 downto 0);
        OutputC     : out signed(15 downto 0);
        OutputD     : out signed(15 downto 0)
    );
end entity DPD_shim;

architecture rtl of DPD_shim is

    ----------------------------------------------------------------------------
    -- Template-Level Application Register Signals (Generic Naming)
    -- These use app_reg_* prefix for template reusability
    ----------------------------------------------------------------------------

    -- Lifecycle control
    signal app_reg_arm_enable           : std_logic;  -- Arm FSM (IDLE→ARMED transition)
    signal app_reg_ext_trigger_in       : std_logic;  -- External trigger input
    signal app_reg_auto_rearm_enable    : std_logic;  -- Re-arm after cooldown
    signal app_reg_fault_clear          : std_logic;  -- Clear fault state

    -- Trigger output control
    signal app_reg_trig_out_voltage     : signed(15 downto 0);    -- Voltage (mV)
    signal app_reg_trig_out_duration    : unsigned(15 downto 0);  -- Duration (ns)

    -- Intensity output control
    signal app_reg_intensity_voltage    : signed(15 downto 0);    -- Voltage (mV)
    signal app_reg_intensity_duration   : unsigned(15 downto 0);  -- Duration (ns)

    -- Timing control
    signal app_reg_trigger_wait_timeout : unsigned(15 downto 0);  -- Timeout (s)
    signal app_reg_cooldown_interval    : unsigned(23 downto 0);  -- Cooldown (μs)

    -- Monitor/feedback
    signal app_reg_monitor_enable            : std_logic;              -- Enable comparator
    signal app_reg_monitor_expect_negative   : std_logic;              -- Polarity select
    signal app_reg_monitor_threshold_voltage : signed(15 downto 0);    -- Threshold (mV)
    signal app_reg_monitor_window_start      : unsigned(31 downto 0);  -- Window delay (ns)
    signal app_reg_monitor_window_duration   : unsigned(31 downto 0);  -- Window length (ns)

    ----------------------------------------------------------------------------
    -- Global Enable Signal
    -- Combines all FORGE_READY control bits for safe operation
    ----------------------------------------------------------------------------
    signal global_enable : std_logic;

begin

    ----------------------------------------------------------------------------
    -- Global Enable Computation
    --
    -- All 4 conditions must be met for app to operate:
    --   1. forge_ready  = 1  (loader has deployed bitstream)
    --   2. user_enable  = 1  (user has enabled module)
    --   3. clk_enable   = 1  (clock gating enabled)
    --   4. loader_done  = 1  (BRAM loading complete)
    ----------------------------------------------------------------------------
    global_enable <= combine_forge_ready(forge_ready, user_enable, clk_enable, loader_done);

    ----------------------------------------------------------------------------
    -- Register Synchronization: Control Registers → app_reg_* signals
    --
    -- Synchronizes register updates on each clock cycle
    ----------------------------------------------------------------------------
    REGISTER_SYNC: process(Clk, Reset)
    begin
        if Reset = '1' then
            -- Initialize all app_reg_* signals to safe defaults
            app_reg_arm_enable           <= '0';
            app_reg_ext_trigger_in       <= '0';
            app_reg_auto_rearm_enable    <= '0';
            app_reg_fault_clear          <= '0';
            app_reg_trig_out_voltage     <= (others => '0');
            app_reg_trig_out_duration    <= to_unsigned(100, 16);   -- Safe default 100ns
            app_reg_intensity_voltage    <= (others => '0');
            app_reg_intensity_duration   <= to_unsigned(200, 16);   -- Safe default 200ns
            app_reg_trigger_wait_timeout <= to_unsigned(2, 16);     -- Safe default 2s
            app_reg_cooldown_interval    <= to_unsigned(10, 24);    -- Safe default 10μs
            app_reg_monitor_enable            <= '1';               -- Enabled by default
            app_reg_monitor_expect_negative   <= '1';               -- Negative polarity
            app_reg_monitor_threshold_voltage <= to_signed(-200, 16); -- -200mV default
            app_reg_monitor_window_start      <= (others => '0');
            app_reg_monitor_window_duration   <= to_unsigned(5000, 32); -- 5μs default

        elsif rising_edge(Clk) then
            -- Latch new register values on each clock cycle

            -- CR1: Lifecycle control bits
            app_reg_arm_enable        <= app_reg_1(0);
            app_reg_ext_trigger_in    <= app_reg_1(1);
            app_reg_auto_rearm_enable <= app_reg_1(2);
            app_reg_fault_clear       <= app_reg_1(3);

            -- CR2: Trigger output voltage
            app_reg_trig_out_voltage  <= signed(app_reg_2(15 downto 0));

            -- CR3: Trigger pulse duration
            app_reg_trig_out_duration <= unsigned(app_reg_3(15 downto 0));

            -- CR4: Intensity output voltage
            app_reg_intensity_voltage <= signed(app_reg_4(15 downto 0));

            -- CR5: Intensity pulse duration
            app_reg_intensity_duration <= unsigned(app_reg_5(15 downto 0));

            -- CR6: Trigger wait timeout
            app_reg_trigger_wait_timeout <= unsigned(app_reg_6(15 downto 0));

            -- CR7: Cooldown interval
            app_reg_cooldown_interval <= unsigned(app_reg_7(23 downto 0));

            -- CR8: Monitor control bits
            app_reg_monitor_enable          <= app_reg_8(0);
            app_reg_monitor_expect_negative <= app_reg_8(1);

            -- CR9: Monitor threshold voltage
            app_reg_monitor_threshold_voltage <= signed(app_reg_9(15 downto 0));

            -- CR10: Monitor window start delay
            app_reg_monitor_window_start <= unsigned(app_reg_10);

            -- CR11: Monitor window duration
            app_reg_monitor_window_duration <= unsigned(app_reg_11);
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Instantiate Application Main Entity
    --
    -- Direct mapping: app_reg_* signals to DPD_main ports
    -- Main app is MCC-agnostic, uses domain-specific naming
    ----------------------------------------------------------------------------
    DPD_MAIN_INST: entity WORK.DPD_main
        generic map (
            CLK_FREQ_HZ => 125000000  -- Moku:Go clock frequency
        )
        port map (
            -- Clock and Control
            Clk    => Clk,
            Reset  => Reset,
            Enable => global_enable,
            ClkEn  => '1',  -- Always enabled for now

            -- Direct mapping: DPD_main ports ← app_reg_* signals
            arm_enable           => app_reg_arm_enable,
            ext_trigger_in       => app_reg_ext_trigger_in,
            trigger_wait_timeout => app_reg_trigger_wait_timeout,
            auto_rearm_enable    => app_reg_auto_rearm_enable,
            fault_clear          => app_reg_fault_clear,

            trig_out_voltage     => app_reg_trig_out_voltage,
            trig_out_duration    => app_reg_trig_out_duration,

            intensity_voltage    => app_reg_intensity_voltage,
            intensity_duration   => app_reg_intensity_duration,

            cooldown_interval    => app_reg_cooldown_interval,

            probe_monitor_feedback    => InputA,
            monitor_enable            => app_reg_monitor_enable,
            monitor_threshold_voltage => app_reg_monitor_threshold_voltage,
            monitor_expect_negative   => app_reg_monitor_expect_negative,
            monitor_window_start      => app_reg_monitor_window_start,
            monitor_window_duration   => app_reg_monitor_window_duration,

            -- BRAM Interface (reserved for future use)
            bram_addr => bram_addr,
            bram_data => bram_data,
            bram_we   => bram_we,

            -- Physical I/O (3 outputs from DPD_main)
            OutputA => OutputA,
            OutputB => OutputB,
            OutputC => OutputC
        );



end architecture rtl;

