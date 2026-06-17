# System Architecture

```mermaid
flowchart TD
  A["Input validation"] --> B["Manifest/config resolution"]
  B --> C["Germline branch"]
  C --> C1["DeepVariant"]
  C --> C2["pbsv"]
  C --> C3["GLnexus"]
  B --> D["Somatic branch"]
  D --> D1["Tumor-normal preflight"]
  D --> D2["DeepSomatic"]
  D --> D3["Severus"]
  D --> D4["Integrated somatic evidence"]
  C1 --> E["Caller-native outputs"]
  C2 --> E
  D2 --> E
  D3 --> E
  C3 --> F["Validated derived outputs"]
  D4 --> F
  E --> G["QC / validation / provenance"]
  F --> G
  G --> H["Local or Slurm execution planning"]
  H --> I["Status / rerun / reports"]
  I --> J["Attempt preservation"]
  I --> K["Failure isolation"]
  J --> L["Synthetic/mocked validation boundary"]
  K --> L
```

Caller-native outputs remain caller-owned. Integrated reports are
derived outputs that link back to source attempts, validation status,
checksums where available, and provenance.
