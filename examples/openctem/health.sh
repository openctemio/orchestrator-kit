#!/bin/bash
# Exit 0 when the live api answers /ready with 200.
code=$(docker exec openctemio-api-1 wget -qO /dev/null -S http://localhost:8080/ready 2>&1 | grep -m1 -o 'HTTP/1.1 [0-9]*')
echo "${code:-down}"
[ "${code##* }" = 200 ]
