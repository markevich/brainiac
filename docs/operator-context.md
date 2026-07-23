# Jarvis Operator Context

Use Brainiac commands before broad filesystem reads. Start with `brainiac index info`, then search or inspect bounded candidates.

After creating or materially changing a source note:

1. Run `brainiac inspect <path>`.
2. If it has umbrella backlinks, decide whether the changed information affects the umbrella’s categories, list, status, rating, or choice guidance.
3. If it does, propose an umbrella update. If it does not, stop.
4. If no umbrella backlink exists, use bounded search only when there is a clear navigation problem. Do not automatically create an umbrella.

Sensitive domains are read-only by default unless the user explicitly authorizes a write.
