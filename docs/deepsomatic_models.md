# DeepSomatic Models

Model compatibility is version-aware and centralized in the compatibility
module. Unknown future release families fail under strict policy and may warn
only under explicit permissive policy.

`model.example_info.json` can be required by policy. When supplied, it is read
without modification, checked for structural metadata, model type, analysis mode,
technology, referenced model files, and checksums where supplied.
