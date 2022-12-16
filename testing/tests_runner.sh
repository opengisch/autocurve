#!/bin/bash

exec $@ | tee /tmp/output.log

cat /tmp/output.log | grep -q 'FAILED'
IS_FAILED="$?"

cat /tmp/output.log | grep -q 'OK'
IS_OK="$?"

if [ "$IS_OK" -eq "0" ] && [ "$IS_FAILED" -eq "1" ]; then
    # Sucess
    exit 0
else
    # Failure
    exit 1
fi
