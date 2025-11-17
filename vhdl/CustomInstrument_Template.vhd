library IEEE;
use IEEE.std_logic_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity SimpleCustomInstrument is
    Port (
        Clk : in std_logic;
        Reset : in std_logic;

        InputA : in signed(15 downto 0);
        InputB : in signed(15 downto 0);
        InputC : in signed(15 downto 0);

        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0);

        Control0 : in std_logic_vector(31 downto 0);
        Control1 : in std_logic_vector(31 downto 0);
        Control2 : in std_logic_vector(31 downto 0);
        Control3 : in std_logic_vector(31 downto 0);
        Control4 : in std_logic_vector(31 downto 0);
        Control5 : in std_logic_vector(31 downto 0);
        Control6 : in std_logic_vector(31 downto 0);
        Control7 : in std_logic_vector(31 downto 0);
        Control8 : in std_logic_vector(31 downto 0);
        Control9 : in std_logic_vector(31 downto 0);
        Control10 : in std_logic_vector(31 downto 0);
        Control11 : in std_logic_vector(31 downto 0);
        Control12 : in std_logic_vector(31 downto 0);
        Control13 : in std_logic_vector(31 downto 0);
        Control14 : in std_logic_vector(31 downto 0);
        Control15 : in std_logic_vector(31 downto 0)
    );
end CustomInstrument;

architecture Behavioral of CustomInstrument is

begin

    -- _________ <= InputA;
    -- _________ <= InputB;
    -- _________ <= InputC;
    -- _________ <= InputD;

    -- ______ <= Control0;
    -- ______ <= Control1;
    -- ______ <= Control2;
    --        ......
    -- ______ <= Control15;

    -- OutputA <= ______;
    -- OutputB <= ______;
    -- OutputC <= ______;
    -- OutputD <= ______;

end Behavioral;
