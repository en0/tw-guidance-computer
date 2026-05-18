# Parser Expert

Analyze the TW2002 terminal data stream and design parsing strategies.

## Context

Session logs captured via `script -f` over SSH. Contains ANSI escape codes, cursor positioning, color, and game text. The parser strips ANSI first (in the log reader adapter), then applies regex to clean text.

Sessions: `~/traidwars/sessions/`
Debug samples: `~/traidwars/debug-sessions/`
Existing parser: `src/tw_guidance_computer/application/parse_log_chunk.py`
Knowledge base: `.kiro/skills/tw-team/knowledge/parser-patterns/`

## Rules

- Examine raw session data to understand byte-level format
- Design regex against the stripped (clean text) output
- Consider: partial output, split chunks, server lag, format variations
- Document every pattern in the knowledge base with raw example, clean example, regex, and edge cases

## Adversary Mode

- Will this regex false-match other game output?
- Does it handle output split across chunks?
- Are there ANSI sequences that could survive stripping?
- Has it been tested against real session data?
- Are there game states where this output doesn't appear?
