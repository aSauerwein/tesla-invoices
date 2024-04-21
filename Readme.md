# Dsteiner Telsa Invoices
dsteiner script as docker container, capable of refreshing tokens automatically

## Security Risk
refreshtoken _should_ be persistent, otherwise we would need to change the tokens everytime we restart the container


## HowTo
Container runs per default in "deamon" mode, meaning that every hour the invoices of the current month are being downloaded
1. build container
```bash
$ docker build -t tesla-invoices .
```
2. write refresh token and access token to `secrets/refresh_token.txt` and `secrets/access_token.txt`
3. (optional) email export  
    a. copy `docker.env.example` to `docker.env`  
    b. fill in all variables and set `ENABLE_EMAIL_EXPORT` to "True"  
    c. start container with `--env-file`
    ```bash
    $ docker run -d --name tesla-invoices -v ./invoices:/opt/tesla-invoices/invoices -v ./secrets:/opt/tesla-invoices/secrets --env-file docker.env tesla-invoices
    ```
4. if you want no email export just run without `--env-file`  
    a. 
    ```bash
    $ docker run -d --name tesla-invoices -v ./invoices:/opt/tesla-invoices/invoices -v ./secrets:/opt/tesla-invoices/secrets tesla-invoices
    ```
    b. create invoices interactively
    ```bash
    $ docker exec -it tesla-invoices ./download_v2.py
    Bitte gewünschten Monat im Format 'YYYY-MM' bzw. 'cur' oder 'prev' oder 'all' für aktuellen oder vorherigen Monat oder alles eingeben [prev]: cur
    Using '2024-04'.
    DONE
    ```


## Developing
```bash
docker build -t tesla-invoices .
docker stop tesla-invoices
docker rm tesla-invoices
docker run -d --name tesla-invoices -v ./invoices:/opt/tesla-invoices/invoices -v ./secrets:/opt/tesla-invoices/secrets --env-file docker.env tesla-invoices 
```