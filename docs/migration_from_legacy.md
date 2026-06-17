# Migration From Legacy

The files under `legacy/` are historical preserved artifacts. Their paths,
commands, versions, and environment assumptions may be obsolete. They are not
the recommended execution path for the new harness.

The historical script performed interactive PacBio dataset merging, pbmm2
alignment, DeepVariant germline SNV/indel calling, pbsv germline SV calling, and
basic SVTYPE counting.

The modern harness retains the scientific Phase 2A behavior but removes
interactive prompts, global workflow state, hard-coded local paths, manually
loaded environment assumptions, unsafe shell string construction, silent failure,
and unstructured outputs.

To translate an old run:

1. Put sample metadata into a TSV manifest.
2. Put reference, tool, backend, and output settings into YAML config.
3. Run `validate`.
4. Run `dry-run` and inspect planned commands.
5. Run or resume with an explicit attempt ID.

Historical files remain available only for comparison and reproducibility
review.

Phase 2A.1 adds stricter schema validation, explicit `schema_version`, tool
probing, reference validation, BAM validation, and attempt collision protection.
Older loose configs may need updates before they validate.
