--------------------------------------------------------------------------------
-- FSM Observer - Compatibility Wrapper for forge_hierarchical_encoder
--
-- **DEPRECATED:** This is now a thin compatibility wrapper around forge_hierarchical_encoder
--                 to provide backward compatibility for existing designs.
--
-- **IMPORTANT CHANGES (2025-11-07):**
--   - OLD IMPLEMENTATION: LUT-based voltage spreading (0V → 2.5V)
--   - NEW IMPLEMENTATION: Uses forge_hierarchical_encoder internally
--   - OUTPUT SCALING CHANGED: Now uses 200 digital units per state
--
-- **Migration Notice:**
--   All new designs should use forge_hierarchical_encoder directly.
--   This wrapper exists ONLY for backward compatibility.
--
-- **Output Differences:**
--   Legacy (LUT-based): State 0→0V, 1→0.625V, 2→1.25V, 3→1.875V
--   Current (hierarchical): State 0→0mV, 1→30mV, 2→61mV, 3→91mV (on ±5V platform)
--
-- **Why This Change:**
--   - Unifying all FSM observation to use forge_hierarchical_encoder
--   - Zero LUT usage (pure arithmetic)
--   - Support for status encoding (8 additional bits)
--   - Platform-agnostic digital encoding
--
-- **For Documentation on New Approach:**
--   See: libs/forge-vhdl/vhdl/debugging/forge_hierarchical_encoder.vhd
--   Migration Guide: Obsidian/Project/Architecture/FSM_OBSERVER_UNIFICATION_STRATEGY.md
--
-- Author: Refactored to wrapper (2025-11-07)
-- Status: DEPRECATED - Use forge_hierarchical_encoder directly
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity fsm_observer is
    generic (
        -- Legacy generics - IGNORED but kept for backward compatibility
        NUM_STATES : positive := 8;
        V_MIN : real := 0.0;
        V_MAX : real := 2.5;
        FAULT_STATE_THRESHOLD : natural := 8;

        -- State name generics also ignored
        STATE_0_NAME : string := "STATE_0";
        STATE_1_NAME : string := "STATE_1";
        STATE_2_NAME : string := "STATE_2";
        STATE_3_NAME : string := "STATE_3";
        STATE_4_NAME : string := "STATE_4";
        STATE_5_NAME : string := "STATE_5";
        STATE_6_NAME : string := "STATE_6";
        STATE_7_NAME : string := "STATE_7"
    );
    port (
        -- Clock/reset
        clk          : in  std_logic := '0';
        reset        : in  std_logic := '0';  -- Active-low reset

        -- FSM state input (6 bits)
        state_vector : in  std_logic_vector(5 downto 0);

        -- Oscilloscope output (16-bit signed)
        voltage_out  : out signed(15 downto 0)
    );
end entity fsm_observer;

architecture wrapper of fsm_observer is

    -- ========================================================================
    -- Wrapper Architecture - Uses forge_hierarchical_encoder internally
    -- ========================================================================
    -- This wrapper provides backward compatibility for existing designs
    -- while transitioning to the unified hierarchical encoder approach.

    -- Internal signals
    signal status_vector : std_logic_vector(7 downto 0);
    signal state_index   : natural range 0 to 63;
    signal is_fault      : boolean;
    signal reset_active_high : std_logic;

begin

    -- ========================================================================
    -- Deprecation Warning (synthesis-time only)
    -- ========================================================================
    assert false report
        "WARNING: fsm_observer is DEPRECATED (2025-11-07). " &
        "This is now a wrapper around forge_hierarchical_encoder. " &
        "Output scaling has changed from legacy voltage spreading. " &
        "Use forge_hierarchical_encoder directly for new designs. " &
        "See: Obsidian/Project/Architecture/FSM_OBSERVER_UNIFICATION_STRATEGY.md"
        severity warning;

    -- ========================================================================
    -- Fault Detection Logic
    -- ========================================================================
    -- Convert state to index for fault detection
    state_index <= to_integer(unsigned(state_vector));
    is_fault <= (state_index >= FAULT_STATE_THRESHOLD) and (FAULT_STATE_THRESHOLD < NUM_STATES);

    -- Build status vector
    -- For backward compatibility, we simulate fault detection:
    -- - Status[7] = fault flag (sign flip control)
    -- - Status[6:1] = state copy (for redundancy)
    -- - Status[0] = 0
    status_vector <= '1' & state_vector & '0' when is_fault else
                     '0' & state_vector & '0';

    -- Convert active-low reset to active-high for hierarchical encoder
    reset_active_high <= not reset;

    -- ========================================================================
    -- Instantiate forge_hierarchical_encoder (the new standard)
    -- ========================================================================
    hierarchical_encoder : entity work.forge_hierarchical_encoder
        port map (
            clk           => clk,
            reset         => reset_active_high,  -- Encoder expects active-high
            state_vector  => state_vector,
            status_vector => status_vector,
            voltage_out   => voltage_out
        );

    -- ========================================================================
    -- Output Notes:
    -- ========================================================================
    -- The output scaling is DIFFERENT from the legacy fsm_observer:
    --
    -- LEGACY (LUT-based voltage spreading):
    --   State 0: 0.0V
    --   State 1: 0.625V  (with V_MAX=2.5V, NUM_STATES=5)
    --   State 2: 1.25V
    --   State 3: 1.875V
    --   State 4: 2.5V
    --
    -- NEW (hierarchical encoder, 200 units/state):
    --   State 0: 0 mV     (0 digital units)
    --   State 1: 30.5 mV  (200 digital units on ±5V platform)
    --   State 2: 61 mV    (400 digital units)
    --   State 3: 91.5 mV  (600 digital units)
    --   State 4: 122 mV   (800 digital units)
    --
    -- Tests that expect the old voltage spreading WILL FAIL!
    -- Update your test expectations or use forge_hierarchical_encoder directly.

end architecture wrapper;
