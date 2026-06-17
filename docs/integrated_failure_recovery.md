# Integrated Failure Recovery

Failure summaries retain pair ID, integrated status, failure categories, and
caller-specific failure hints. Rerun recommendations are stage-specific:
identity/reference mismatches require manifest or reference correction, failed
DeepSomatic outputs recommend DeepSomatic-only rerun, failed Severus or BND
validation recommends Severus-only rerun, and report failures recommend
regenerating integrated reports only.

No rerun command is submitted automatically.
