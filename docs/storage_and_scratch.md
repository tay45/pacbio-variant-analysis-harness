# Storage And Scratch

Phase 2B includes planning-only storage estimates and safe scratch configuration
validation.

Storage estimates are approximations grouped into categories such as aligned
BAM, BAM indexes, DeepVariant intermediates, VCF/gVCF, pbsv signatures, SV VCF,
logs/QC/reports, and temporary scratch.

Scratch configuration is optional. The harness does not assume `$TMPDIR` exists,
does not delete source inputs, and restricts cleanup to declared scratch paths.

The storage estimator is for operational planning and does not promise exact
usage.

