# Status Bar (Compact)

## What It Captures
Player state snapshot: sector, turns, credits, fighters, shields, holds, cargo quantities.

## Raw Example (with ANSI noted)
```
[30m[47m Sect 616│Turns 1,000│Creds 25│Figs 1│Shlds 30│Hlds 1│Ore 0│Org 0│Equ 0│Col 0  [m [23;1H
 Phot 0│Armd 0│Lmpt 0│GTorp 0│TWarp No│Clks 0│Beacns 0│AtmDt 0│Crbo 0│EPrb 0    
[30m[47m MDis 0│PsPrb No│PlScn No│LRS Dens│Aln 0│Exp 16│Corp 6│Ship 46 EscPod          [m [23;1H
```

## Clean Text (after strip)
```
 Sect 616│Turns 1,000│Creds 25│Figs 1│Shlds 30│Hlds 1│Ore 0│Org 0│Equ 0│Col 0  
 Phot 0│Armd 0│Lmpt 0│GTorp 0│TWarp No│Clks 0│Beacns 0│AtmDt 0│Crbo 0│EPrb 0    
 MDis 0│PsPrb No│PlScn No│LRS Dens│Aln 0│Exp 16│Corp 6│Ship 46 EscPod          
```

## Regex
```python
bar_re = re.compile(
    r"Sect\s+(\d+)"
    r"\s*│\s*Turns\s+([0-9,]+)"
    r"\s*│\s*Creds\s+([0-9,]+)"
    r"\s*│\s*Figs\s+[0-9,]+"
    r"\s*│\s*Shlds\s+[0-9,]+"
    r"\s*│\s*Hlds\s+([0-9,]+)"
    r"\s*│\s*Ore\s+(\d+)"
    r"\s*│\s*Org\s+(\d+)"
    r"\s*│\s*Equ\s+(\d+)"
    r"\s*│\s*Col\s+(\d+)"
)
```

## Edge Cases
- Numbers can have commas (e.g., "1,000")
- The bar appears after every command prompt response
- Three lines total but only first line is currently parsed for cargo
- Second line has: Photon torpedoes, Armid mines, Limpet mines, Genesis torpedoes, TransWarp, Cloaks, Beacons, Atomic Detonators, Corbomite, Ether Probes
- Third line has: Mine Disruptors, PsychProbe, Planet Scanner, Long Range Scanner type, Alignment, Experience, Corp number, Ship number and type
