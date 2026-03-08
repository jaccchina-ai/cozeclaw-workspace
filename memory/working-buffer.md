# Working Buffer (Danger Zone Log)

**Purpose**: Capture EVERY exchange in the danger zone between memory flush and compaction.

**Status**: STANDBY
**Started**: [ISO-8601 timestamp]

---

**Protocol**:
1. At 60% context: CLEAR old buffer, start fresh
2. Every message after 60%: Append both human's message AND your response summary
3. After compaction: Read the buffer FIRST, extract important context
4. Leave buffer as-is until next 60% threshold

---

## Buffer Entries
[Log entries will appear here when context hits 60%]

---

**Last Updated**: [ISO-8601 timestamp]
