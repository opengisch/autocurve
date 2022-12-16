#!/bin/bash

echo "Starting..."
exec $@ | tee output.log

echo "Done !"

cat output.log | grep -q 'FAILED'
IS_FAILED="$?"

cat output.log | grep -q 'OK'
IS_OK="$?"

if [ "$IS_OK" -eq "0" ] && [ "$IS_FAILED" -eq "1" ]; then
    echo "SUCCESS !"
    exit 0
fi

echo "FAILURE !"
exit 1
