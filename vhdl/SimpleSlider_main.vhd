library IEEE;
use IEEE.Numeric_Std.all;

architecture Behavioural of CustomWrapper is
begin
    OutputA <= signed(Control10(15 downto 0));
    OutputB <= signed(Control11(15 downto 0));
end architecture;
