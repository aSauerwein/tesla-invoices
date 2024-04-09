#!/bin/bash
refresh_token=$(cat "/opt/tesla-invoices/secrets/refresh_token.txt") 
bearer_token=$(cat "/opt/tesla-invoices/secrets/access_token.txt") 
curl --silent --request POST 'https://auth.tesla.com/oauth2/v3/token' \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer ${bearer_token}" \
--data "{
  \"grant_type\": \"refresh_token\",
  \"client_id\": \"ownerapi\",
  \"refresh_token\": \"${refresh_token}\",
  \"scope\": \"openid email offline_access\"
}" | jq .access_token -r > /opt/tesla-invoices/secrets/access_token.txt