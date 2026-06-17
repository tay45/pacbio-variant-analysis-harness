# Joint Sharding

Supported sharding modes:

- `contig`
- `interval_file`

The default is contig sharding in reference order. Each shard receives a stable
ID, stable array index, interval bounds, output VCF path, and output index path.

Target-base sharding is deferred.

