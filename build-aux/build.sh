#!/bin/bash
cd plugins/polars/eruo-strutil
maturin build --release
cp target/wheels/*.whl ../../../dist/
cd ../../..