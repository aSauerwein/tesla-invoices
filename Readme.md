# Dsteiner Telsa Invoices
dsteiner script as docker container, capable of refreshing tokens automatically

## Security Risk
refreshtoken _should_ be persistent, otherwise we would need to change the tokens everytime we restart the container


## HowTo
1. build container
```bash
$ docker build -t tesla-invoices .
```
2. write refresh token and access token to `secrets/refresh_token.txt` and `secrets/access_token.txt`
3. run container
```bash
$ docker run -d --name tesla-invoices -v ./invoices:/opt/tesla-invoices/invoices -v ./secrets:/opt/tesla-invoices/secrets tesla-invoices
```
4. container will atomatically refresh the tokens
5. create invoices
```bash
$ docker exec -it tesla-invoices ./download_v2.py
Bitte gewünschten Monat im Format 'YYYY-MM' bzw. 'cur' oder 'prev' oder 'all' für aktuellen oder vorherigen Monat oder alles eingeben [prev]: cur
Using '2024-04'.
DONE
```

