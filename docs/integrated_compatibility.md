# Integrated Compatibility

The integrated layer checks subject, tumor sample, normal sample, analysis mode,
reference ID, reference signature, and manifest row hash when those fields are
available. Compatibility failures produce `inconsistent` status and do not
silently merge evidence across mismatched pairs.
