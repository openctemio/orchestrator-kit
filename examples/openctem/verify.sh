#!/bin/bash
# Post-deploy probes; exit 0 only when every probe passes.
ready=$(docker exec openctemio-api-1 wget -qO /dev/null -S http://localhost:8080/ready 2>&1 | grep -m1 -o 'HTTP/1.1 [0-9]*')
login=$(docker exec openctemio-api-1 wget -qO- --header 'Content-Type: application/json' \
  --post-data '{"email":"nobody@example.invalid","password":"wrong-password-x"}' \
  http://localhost:8080/api/v1/auth/login 2>&1 | grep -o '40[0-9]' | head -1)
web=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/)
pgerr=$(docker logs --since 10m openctemio-postgres-1 2>&1 | grep -c ERROR)
hb=$(docker logs --since 3m openctem-sensor-01 2>&1 | grep -c 'heartbeat.*200')
echo "ready ${ready:-down} login $login web $web pg_errors $pgerr sensor_hb $hb"
[ "${ready##* }" = 200 ] && [ "$login" = 401 ] && [ "$web" = 200 ] && [ "$pgerr" = 0 ] && [ "$hb" != 0 ]
