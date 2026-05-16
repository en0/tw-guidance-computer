# UI Spec: [Title]

## Interface
HUD section | CLI command | Both

## Information Priority
1. [Most important — always visible]
2. [Secondary — visible when relevant]
3. [Tertiary — available on demand]

## Layout

```
┌─────────────────────────────────────┐
│ ASCII mockup of the interface       │
│ with approximate dimensions         │
│ and content placement               │
└─────────────────────────────────────┘
```

Dimensions: [width]x[height] characters

## Color Scheme
- [Element]: [color] — [why]
- [Element]: [color] — [why]

## Update Triggers
What causes this display to refresh? (New sector, new parse, timer, user action)

## States
- **Normal**: [what it looks like with data]
- **Empty**: [what it looks like with no data]
- **Error**: [what it looks like when something's wrong]

## CLI Syntax (if applicable)
```
tw command [required] [-o optional] [--flag]
```

### Output Format
```
Example output the user would see.
```

## Data Requirements
What data does this need from the store? Any new queries?

## Interaction Notes
How does the player interact with this? Keyboard shortcuts? Scrolling? Static display?
