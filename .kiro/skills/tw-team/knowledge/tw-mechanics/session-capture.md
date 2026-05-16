# Session Capture Method

## How It Works
Game sessions are captured using the Unix `script` command piping an SSH connection to a log file:

```bash
script -qf -c "ssh -i <keyfile> <user>@<host>" "$logfile"
```

The `-f` flag flushes output immediately (important for real-time parsing).
The `-q` flag suppresses script's own messages.

## Terminal Environment
- Terminal: `st-256color` (custom st fork)
- Typical game terminal: 80x23 (set by TWGS)
- HUD terminal: 100x30

## Data Stream Characteristics
- Raw bytes include all ANSI escape sequences the server sends
- Server is TWGS v2.20b running on Windows (note: `conhost.exe` in title sequence)
- Connection goes through SSH, so no telnet IAC sequences
- `script` adds header/footer lines with timestamps and metadata
- Data arrives in chunks (network packets), so patterns may be split across reads

## Log File Format
```
Script started on <timestamp> [COMMAND="ssh ..." TERM="st-256color" ...]
<raw terminal data>
Script done on <timestamp> [COMMAND_EXIT_CODE="0"]
```

The header line contains the full command and terminal info. This line is sensitive (contains key path and hostname) and must never be quoted verbatim in committed files.

## Relevant to Parser?
The log reader adapter handles tailing the file and stripping ANSI. The parser receives clean text. But understanding the raw format is essential for debugging parser issues.

## Sources
Observed in `~/traidwars/launch-with-guidance.sh` and session files.
